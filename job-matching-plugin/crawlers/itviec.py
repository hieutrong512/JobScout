"""Adapter ITviec (itviec.com).

ITviec render server-side và nhúng JSON-LD chuẩn schema.org:
- Trang search `/it-jobs/<keyword>` (hoặc `?query=`) có JSON-LD `ItemList` chứa URL job.
- Trang JD có JSON-LD `JobPosting` đầy đủ (title, datePosted, validThrough, baseSalary, skills, ...).

Nhờ vậy adapter chỉ đọc JSON-LD → map sang job.schema, không cần bs4/regex nặng.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date

from base import (
    FetchError,
    clean_skills,
    days_since,
    emit,  # noqa: F401 — tiện lợi cho debug thủ công
    employment_type,
    extract_jsonld,
    find_jobposting,
    html_to_text,
    http_get,
    is_expired,
    language_guess,
    lexical_relevance,
    location_from_ld,
    now_iso,
    remote_guess,
    salary_from_ld,
    stable_id,
    truncate_words,
)

PLATFORM = "itviec"
DOMAINS = ("itviec.com",)
BASE = "https://itviec.com"


def _matches(domain: str) -> bool:
    return any(d in domain for d in DOMAINS)


def _title_from_url(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"-\d+$", "", slug)  # bỏ đuôi -<job_id>
    return slug.replace("-", " ").strip().title()


def search(query: str, max_n: int = 20, today: date | None = None) -> list[dict]:
    """Trả candidate gọn: {url, title, platform, relevance, posted_days}.

    posted_days ở pha search = unknown (ItemList không có ngày); pha fetch sẽ điền chính xác.
    """
    url = f"{BASE}/it-jobs?" + urllib.parse.urlencode({"query": query})
    html = http_get(url)
    lists = [o for o in extract_jsonld(html) if o.get("@type") == "ItemList"]
    urls: list[str] = []
    for lst in lists:
        for el in lst.get("itemListElement", []):
            u = el.get("url")
            if u:
                urls.append(u)
    # khử trùng giữ thứ tự
    seen: dict[str, None] = {}
    for u in urls:
        seen.setdefault(u, None)
    out: list[dict] = []
    for u in list(seen)[:max_n]:
        title = _title_from_url(u)
        out.append(
            {
                "url": u,
                "title": title,
                "platform": PLATFORM,
                "relevance": lexical_relevance(query, title),
                "posted_days": "unknown",
            }
        )
    return out


def fetch_one(url: str, today: date | None = None) -> dict:
    """Fetch 1 trang JD → dict theo job.schema. Ném FetchError nếu hết hạn/không phải JD."""
    html = http_get(url)
    jp = find_jobposting(url and html)
    if not jp:
        raise FetchError(f"Không thấy JobPosting JSON-LD: {url}")

    valid_through = jp.get("validThrough")
    if is_expired(valid_through, today):
        raise FetchError(f"Hết hạn (validThrough={valid_through}): {url}")

    date_posted = jp.get("datePosted")
    posted_days = days_since(date_posted, today)
    if posted_days is not None and posted_days >= 30:
        raise FetchError(f"Tin cũ ≥ 30 ngày (datePosted={date_posted}): {url}")

    org = jp.get("hiringOrganization") or {}
    company = org.get("name") if isinstance(org, dict) else str(org)

    desc_text = html_to_text(jp.get("description", ""))
    exp = jp.get("experienceRequirements")
    min_years = None
    if isinstance(exp, dict):
        mv = exp.get("monthsOfExperience")
        if isinstance(mv, (int, float)):
            min_years = round(mv / 12, 1)
    elif isinstance(exp, (int, float)):
        min_years = float(exp)

    loc = location_from_ld(jp.get("jobLocation"))
    remote = remote_guess(f"{jp.get('title','')} {desc_text} {loc}", jp.get("jobLocationType"))
    skills = clean_skills(jp.get("skills"))

    job = {
        "schema_version": "1.0",
        "id": stable_id(url),
        "title": (jp.get("title") or "").strip() or "unknown",
        "company": (company or "unknown").strip(),
        "location": loc,
        "remote": remote,
        "url": url,
        "source": PLATFORM,
        "posted_date": date_posted if date_posted else "unknown",
        "application_deadline": valid_through if valid_through else "unknown",
        "employment_type": employment_type(jp.get("employmentType")),
        "language": language_guess(f"{jp.get('title','')} {desc_text}"),
        "description": truncate_words(desc_text, 60),
        "requirements": {
            "must_have_skills": skills,
            "nice_to_have_skills": [],
            "min_years": min_years,
            "seniority": "unknown",
            "education": "unknown",
        },
        "salary": salary_from_ld(jp.get("baseSalary")),
        "industry": (jp.get("industry") or "unknown"),
        "company_size": "unknown",
        "collected_at": now_iso(),
        "extraction_confidence": 0.9,  # đọc full JobPosting JSON-LD
    }
    return job
