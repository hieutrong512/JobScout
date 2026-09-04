"""Khung crawler dùng chung — CHỈ dùng thư viện chuẩn (stdlib), không cần pip install.

Mục tiêu: bóc tin tuyển dụng ngoài vòng lặp của Claude để tiết kiệm token. Adapter mỗi
nền tảng chỉ cần biết cách lấy danh sách URL (search) và cách map JSON-LD/HTML của board đó
sang `job.schema.json`. Ưu tiên đọc `JobPosting` JSON-LD (schema.org) vì rẻ và ổn định;
chỉ regex HTML khi board không có JSON-LD.

Nguyên tắc (đồng bộ với agents/job-collector.md):
- Không bịa trường dữ liệu. Thiếu bằng chứng → "unknown"/null/[].
- Tôn trọng robots/ToS, đặt User-Agent thật, có nghỉ giữa request. KHÔNG vượt anti-bot/CAPTCHA.
- `description` chỉ giữ tóm tắt ≤ 60 từ, KHÔNG chép nguyên văn JD (giữ token thấp cho matcher/report).
"""

from __future__ import annotations

import gzip
import hashlib
import html as _html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Iterable

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 25
POLITE_DELAY_SEC = 1.0  # nghỉ giữa các request tới cùng một board


class FetchError(Exception):
    """Không lấy được trang (mạng, HTTP 4xx/5xx, chặn bot)."""


# ----------------------------- HTTP ---------------------------------------

def http_get(url: str, timeout: int = DEFAULT_TIMEOUT, retries: int = 1) -> str:
    """GET một URL, trả về HTML text. Tự giải nén gzip. Thử lại `retries` lần khi lỗi tạm thời."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en,vi;q=0.9",
            "Accept-Encoding": "gzip",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            # 404/410 → hết hạn/không tồn tại, không thử lại.
            if e.code in (404, 410):
                raise FetchError(f"HTTP {e.code} {url}") from e
            last = e
        except Exception as e:  # noqa: BLE001 — mạng/timeout, sẽ thử lại
            last = e
        if attempt < retries:
            time.sleep(POLITE_DELAY_SEC)
    raise FetchError(f"GET thất bại: {url} ({last})")


# --------------------------- Parse helpers --------------------------------

_LD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def extract_jsonld(html: str) -> list:
    """Trả về danh sách object JSON-LD parse được (bỏ qua block hỏng)."""
    out: list = []
    for block in _LD_RE.findall(html):
        try:
            obj = json.loads(block.strip())
        except Exception:  # noqa: BLE001 — JSON-LD bẩn thì bỏ qua
            continue
        if isinstance(obj, list):
            out.extend(x for x in obj if isinstance(x, dict))
        elif isinstance(obj, dict):
            # Có board bọc trong @graph
            if isinstance(obj.get("@graph"), list):
                out.extend(x for x in obj["@graph"] if isinstance(x, dict))
            else:
                out.append(obj)
    return out


def find_jobposting(html: str) -> dict | None:
    """Tìm object JSON-LD có @type == JobPosting (kể cả khi @type là list)."""
    for obj in extract_jsonld(html):
        t = obj.get("@type")
        if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
            return obj
    return None


def html_to_text(fragment: str) -> str:
    """Bỏ tag, giải mã entity, gộp khoảng trắng → text thuần."""
    if not fragment:
        return ""
    text = _TAG_RE.sub(" ", fragment)
    text = _html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def truncate_words(text: str, limit: int = 60) -> str:
    """Cắt cứng ≤ `limit` từ (giữ token thấp; KHÔNG chép nguyên văn JD)."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(",.;:") + " …"


def stable_id(url: str) -> str:
    """Hash ổn định để khử trùng theo URL."""
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]


def days_since(date_str: str | None, today: date | None = None) -> int | None:
    """Số ngày từ `date_str` (YYYY-MM-DD hoặc ISO) tới `today`. None nếu không parse được."""
    if not date_str:
        return None
    today = today or date.today()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(date_str))
    if not m:
        return None
    try:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return (today - d).days


def is_expired(valid_through: str | None, today: date | None = None) -> bool:
    """True nếu deadline (validThrough) đã qua."""
    if not valid_through:
        return False
    d = days_since(valid_through, today)
    return d is not None and d > 0


# --------------------- Map JSON-LD JobPosting → job.schema -----------------

_EMPLOYMENT_MAP = {
    "FULL_TIME": "full-time",
    "PART_TIME": "part-time",
    "CONTRACTOR": "contract",
    "CONTRACT": "contract",
    "TEMPORARY": "contract",
    "INTERN": "internship",
    "INTERNSHIP": "internship",
}


def employment_type(ld_value) -> str:
    if isinstance(ld_value, list):
        ld_value = ld_value[0] if ld_value else None
    if not ld_value:
        return "unknown"
    return _EMPLOYMENT_MAP.get(str(ld_value).upper().replace("-", "_"), "unknown")


def salary_from_ld(base_salary) -> dict:
    """MonetaryAmount JSON-LD → {min,max,currency,period,negotiable}."""
    out = {"currency": "unknown", "period": "unknown", "negotiable": False}
    if not isinstance(base_salary, dict):
        return out
    cur = str(base_salary.get("currency", "")).upper()
    out["currency"] = cur if cur in ("VND", "USD") else "unknown"
    val = base_salary.get("value") or {}
    if isinstance(val, dict):
        lo, hi = val.get("minValue"), val.get("maxValue")
        single = val.get("value")
        for key, src in (("min", lo), ("max", hi)):
            if isinstance(src, (int, float)):
                out[key] = float(src)
        if "min" not in out and isinstance(single, (int, float)):
            out["min"] = out["max"] = float(single)
        unit = str(val.get("unitText", "")).upper()
        out["period"] = {"MONTH": "month", "YEAR": "year", "HOUR": "unknown"}.get(unit, "unknown")
    return out


def location_from_ld(job_location) -> str:
    """jobLocation JSON-LD (Place hoặc list) → chuỗi địa điểm gọn."""
    places = job_location if isinstance(job_location, list) else [job_location]
    parts: list[str] = []
    for p in places:
        if not isinstance(p, dict):
            continue
        addr = p.get("address")
        if isinstance(addr, dict):
            city = addr.get("addressLocality") or addr.get("addressRegion")
            country = addr.get("addressCountry")
            if isinstance(country, dict):
                country = country.get("name")
            chunk = ", ".join(x for x in (city, country) if x)
            if chunk:
                parts.append(chunk)
        elif isinstance(addr, str):
            parts.append(addr)
    # khử trùng giữ thứ tự
    seen: dict[str, None] = {}
    for x in parts:
        seen.setdefault(x, None)
    return " / ".join(seen) or "unknown"


_REMOTE_RE = re.compile(r"\bremote\b|làm việc từ xa|wfh|work from home", re.I)
_HYBRID_RE = re.compile(r"\bhybrid\b|kết hợp", re.I)


def remote_guess(text: str, job_location_type=None) -> str:
    if job_location_type and "TELECOMMUTE" in str(job_location_type).upper():
        return "remote"
    if _HYBRID_RE.search(text):
        return "hybrid"
    if _REMOTE_RE.search(text):
        return "remote"
    return "unknown"


def language_guess(text: str) -> str:
    vi = len(re.findall(r"[ăâđêôơưàáảãạằắẳẵặèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]", text.lower()))
    has_en = bool(re.search(r"[a-z]", text.lower()))
    if vi >= 5 and has_en:
        return "mixed"
    if vi >= 5:
        return "vi"
    return "en" if has_en else "mixed"


def lexical_relevance(query: str, title: str) -> float:
    """Độ liên quan thô (lexical) 0-1 để cap top-K rẻ. Agent vẫn re-rank ngữ nghĩa sau."""
    q = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 1}
    t = {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 1}
    if not q or not t:
        return 0.0
    return round(len(q & t) / len(q), 3)


def clean_skills(skills) -> list[str]:
    """skills JSON-LD (str CSV hoặc list) → list gọn, khử trùng."""
    if isinstance(skills, str):
        items = re.split(r"[,/;]", skills)
    elif isinstance(skills, list):
        items = [str(x) for x in skills]
    else:
        return []
    seen: dict[str, None] = {}
    for s in items:
        s = s.strip()
        if s:
            seen.setdefault(s, None)
    return list(seen)


# ------------------------------- CLI --------------------------------------

def emit(obj) -> None:
    """In JSON gọn ra stdout (giao tiếp với agent qua Bash)."""
    print(json.dumps(obj, ensure_ascii=False))


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def dedupe_by(items: Iterable[dict], key: str) -> list[dict]:
    seen: dict = {}
    for it in items:
        k = it.get(key)
        if k and k not in seen:
            seen[k] = it
    return list(seen.values())
