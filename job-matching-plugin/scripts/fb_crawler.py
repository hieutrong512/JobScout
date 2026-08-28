#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Group Job Scraper with Interactive Login & Session Persistence
Hệ thống tự động đăng nhập tương tác & cào bài viết tuyển dụng từ các Facebook Groups mục tiêu.

Chạy trong Claude Code qua Bash tool:
    python "${CLAUDE_PLUGIN_ROOT}/scripts/fb_crawler.py" --profile data/profiles/<slug>.json

Mặc định workspace là thư mục làm việc hiện tại (Path.cwd()) — nơi Claude Code đang chạy —
nên `data/` được đọc/ghi trong project của người dùng, không phải trong thư mục cài plugin.
Có thể ghim workspace bằng --workspace-root hoặc biến môi trường JOB_MATCHING_WORKSPACE_ROOT.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# Thư mục cài plugin (để tham chiếu tài nguyên đóng gói nếu cần).
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
# Mặc định workspace = thư mục làm việc của Claude Code, KHÔNG phải thư mục cài plugin.
WORKSPACE_ROOT = Path.cwd()
AUTH_DIR = WORKSPACE_ROOT / "data" / ".auth"
STATE_FILE = AUTH_DIR / "facebook_state.json"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "data" / "config" / "facebook_groups.json"
DEFAULT_JOBS_DIR = WORKSPACE_ROOT / "data" / "jobs"
DEFAULT_PROFILE_DIR = WORKSPACE_ROOT / "data" / "profiles"

DEFAULT_SEARCH_QUERIES = ["AI Engineer", "Computer Vision", "LLM", "YOLO"]
GENERIC_ROLE_WORDS = {
    "engineer", "developer", "lead", "senior", "junior", "mid", "middle",
    "expert", "manager", "specialist", "intern", "internship",
}


def configure_workspace_root(workspace_root: Optional[str] = None) -> Path:
    """Cấu hình toàn bộ đường dẫn runtime từ một workspace root rõ ràng.

    Mặc định (workspace_root=None) là Path.cwd() — thư mục Claude Code đang chạy.
    """
    global WORKSPACE_ROOT, AUTH_DIR, STATE_FILE
    global DEFAULT_CONFIG_PATH, DEFAULT_JOBS_DIR, DEFAULT_PROFILE_DIR

    root = Path(workspace_root).expanduser() if workspace_root else Path.cwd()
    WORKSPACE_ROOT = root.resolve()
    AUTH_DIR = WORKSPACE_ROOT / "data" / ".auth"
    STATE_FILE = AUTH_DIR / "facebook_state.json"
    DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "data" / "config" / "facebook_groups.json"
    DEFAULT_JOBS_DIR = WORKSPACE_ROOT / "data" / "jobs"
    DEFAULT_PROFILE_DIR = WORKSPACE_ROOT / "data" / "profiles"
    return WORKSPACE_ROOT


def resolve_workspace_path(value: str) -> Path:
    """Resolve đường dẫn tương đối theo workspace thay vì Path.cwd() ngầm định."""
    path = Path(value).expanduser()
    resolved = path.resolve() if path.is_absolute() else (WORKSPACE_ROOT / path).resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError(f"Đường dẫn phải nằm trong workspace: {resolved}") from exc
    return resolved


class NoDisplayError(RuntimeError):
    """Không có display để mở trình duyệt đăng nhập Facebook (vd: cloud container headless)."""


def interactive_display_available() -> bool:
    """Có thể mở cửa sổ trình duyệt thật cho người dùng đăng nhập hay không.

    - Windows / macOS: luôn có desktop.
    - Linux: cần biến môi trường DISPLAY (X11) hoặc WAYLAND_DISPLAY.
    """
    if sys.platform in ("win32", "darwin"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


NO_DISPLAY_MESSAGE = (
    "Không thể đăng nhập Facebook trong môi trường KHÔNG có màn hình (headless/cloud container).\n"
    "Đăng nhập Facebook lần đầu cần một cửa sổ trình duyệt thật để bạn nhập mật khẩu + 2FA/OTP.\n"
    "\n"
    "Cách xử lý:\n"
    "  1) Chạy pipeline ở MÁY LOCAL có màn hình (Claude Code trên desktop/CLI), rồi đăng nhập một lần.\n"
    "  2) HOẶC đăng nhập một lần ở máy local để tạo file session, sau đó COPY\n"
    "     `data/.auth/facebook_state.json` sang môi trường này và chạy lại với --headless\n"
    "     (lưu ý: session gắn với IP/thiết bị, dùng từ IP cloud lạ có thể bị Facebook chặn/checkpoint).\n"
    "Trong lúc chưa có session, hãy bỏ qua nguồn Facebook và chỉ dùng job boards (WebSearch/WebFetch)."
)

# Regex nhận diện thông tin liên hệ (hỗ trợ số có dấu chấm, khoảng trắng, gạch ngang)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE)
RAW_PHONE_REGEX = re.compile(r"(?:\+84|84|0)[35789](?:[\s.-]*\d){8}\b")
TELEGRAM_REGEX = re.compile(r"(?:t\.me\/|telegram[:\s@]+)([a-zA-Z0-9_]{4,32})", re.IGNORECASE)
ZALO_REGEX = re.compile(
    r"(?:zalo|zl|zlo)[\s:–—]*((?:\+84|84|0)[35789](?:[\s.-]*\d){8}|[0-9]{9,11})",
    re.IGNORECASE
)


def load_candidate_profile(profile_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Tải hồ sơ ứng viên từ đường dẫn hoặc tự động tìm file json trong data/profiles/."""
    resolved_profile = resolve_workspace_path(profile_path) if profile_path else None
    if resolved_profile:
        if not resolved_profile.is_file():
            raise FileNotFoundError(f"Không tìm thấy profile: {resolved_profile}")
        try:
            data = json.loads(resolved_profile.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Không thể đọc profile {resolved_profile}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Profile phải là một JSON object: {resolved_profile}")
        return data

    if DEFAULT_PROFILE_DIR.exists():
        profiles = sorted(
            (p for p in DEFAULT_PROFILE_DIR.glob("*.json") if not p.name.startswith(".")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for profile in profiles:
            try:
                data = json.loads(profile.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("profile phải là một JSON object")
                print(f"[*] Đã tự động tải Profile ứng viên: {profile.name} (Target: {data.get('candidate', {}).get('name', 'N/A')})")
                return data
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                print(f"[⚠️] Bỏ qua profile không hợp lệ {profile.name}: {exc}")
    return None


def clean_phone(phone_str: str) -> str:
    """Chuẩn hóa số điện thoại: bỏ chấm, khoảng cách, đổi +84/84 về 0."""
    digits = re.sub(r"[^\d+]", "", phone_str)
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def extract_contacts(text: str) -> Dict[str, Any]:
    """Bóc tách số điện thoại, Zalo, Email, Telegram từ văn bản."""
    contacts: Dict[str, Any] = {}

    # Email
    emails = EMAIL_REGEX.findall(text)
    if emails:
        valid_emails = [e for e in emails if not e.endswith((".png", ".jpg", ".jpeg", ".webp"))]
        if valid_emails:
            contacts["email"] = valid_emails[0]

    # Phone
    phones = RAW_PHONE_REGEX.findall(text)
    if phones:
        contacts["phone"] = clean_phone(phones[0])

    # Zalo
    zalo_match = ZALO_REGEX.search(text)
    if zalo_match:
        z_str = zalo_match.group(1)
        contacts["zalo"] = clean_phone(z_str)
    elif phones:
        contacts["zalo"] = clean_phone(phones[0])

    # Telegram
    tele_match = TELEGRAM_REGEX.search(text)
    if tele_match:
        contacts["telegram"] = tele_match.group(1)

    return contacts


def get_search_queries(profile: Optional[Dict[str, Any]] = None, custom_queries: Optional[str] = None) -> List[str]:
    """Tạo danh sách các truy vấn tìm kiếm trực tiếp trong Facebook Group."""
    if custom_queries:
        return _unique_strings(custom_queries.split(","))[:8]

    if profile:
        target = profile.get("target", {})
        desired_roles = target.get("desired_roles", [])
        if desired_roles:
            queries: List[str] = []
            for role in desired_roles:
                if not isinstance(role, str):
                    continue
                role = role.strip()
                if not role:
                    continue
                queries.append(role)
                specific = " ".join(
                    token for token in re.findall(r"[\w+#.-]+", role, flags=re.UNICODE)
                    if token.lower() not in GENERIC_ROLE_WORDS
                ).strip()
                if specific and specific.casefold() != role.casefold():
                    queries.append(specific)
            normalized = _unique_strings(queries)
            if normalized:
                return normalized[:8]

    return DEFAULT_SEARCH_QUERIES.copy()


def _unique_strings(values) -> List[str]:
    """Loại chuỗi rỗng/trùng nhưng giữ nguyên thứ tự đầu vào."""
    result: List[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = " ".join(value.split())
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _profile_relevance_terms(profile: Optional[Dict[str, Any]]) -> List[str]:
    """Lấy role/skill đặc trưng từ profile; fallback giữ hành vi crawler AI cũ."""
    if not profile:
        return [query.casefold() for query in DEFAULT_SEARCH_QUERIES]

    target = profile.get("target") if isinstance(profile.get("target"), dict) else {}
    roles = target.get("desired_roles") if isinstance(target.get("desired_roles"), list) else []
    terms: List[str] = [role for role in roles if isinstance(role, str)]

    for role in roles:
        if not isinstance(role, str):
            continue
        tokens = [
            token for token in re.findall(r"[\w+#.-]+", role.casefold(), flags=re.UNICODE)
            if token not in GENERIC_ROLE_WORDS and len(token) >= 2
        ]
        terms.extend(tokens)

    skills = profile.get("skills") if isinstance(profile.get("skills"), list) else []
    for skill in skills[:15]:
        if isinstance(skill, dict) and isinstance(skill.get("name"), str):
            terms.append(skill["name"])

    normalized = _unique_strings(terms)
    return [term.casefold() for term in normalized] or [query.casefold() for query in DEFAULT_SEARCH_QUERIES]


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE) is not None


def is_job_relevant(text: str, profile: Optional[Dict[str, Any]] = None) -> bool:
    """
    Kiểm tra tín hiệu tuyển dụng và mức liên quan với target trong profile.
    """
    text_lower = text.casefold()

    # 1. Tín hiệu tuyển dụng bắt buộc
    hiring_cues = [
        "tuyển", "tuyển dụng", "hiring", "tìm đồng đội", "recruiting", "jd", "cơ hội việc làm",
        "offer", "lương", "lương:", "deal", "ứng tuyển", "inbox nhận jd", "gửi cv", "apply", "vị trí"
    ]
    if not any(cue in text_lower for cue in hiring_cues):
        return False

    return any(_contains_term(text_lower, term) for term in _profile_relevance_terms(profile))


def ensure_facebook_session(playwright_instance, force_login: bool = False, headless: bool = False) -> BrowserContext:
    """
    Khởi tạo Browser Context và đảm bảo người dùng đã đăng nhập.
    Nếu chưa đăng nhập hoặc hết hạn, tự động mở cửa sổ trình duyệt (headed) để người dùng đăng nhập.
    """
    AUTH_DIR.mkdir(parents=True, exist_ok=True)

    has_state = STATE_FILE.exists() and not force_login

    if has_state:
        print(f"[*] Tìm thấy session cũ tại: {STATE_FILE}")
        browser = playwright_instance.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=str(STATE_FILE),
            viewport={"width": 1280, "height": 800},
            locale="vi-VN",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Kiểm tra xem session còn sống không
        page = context.new_page()
        try:
            page.goto("https://www.facebook.com/", timeout=20000, wait_until="domcontentloaded")
            time.sleep(2)

            cookies = context.cookies()
            c_user_present = any(c.get("name") == "c_user" and c.get("value") for c in cookies)
            is_login_page = "login" in page.url or page.locator("input[name='email']").count() > 0

            if c_user_present and not is_login_page:
                print("[✅] Session Facebook hợp lệ! Sẵn sàng quét dữ liệu.")
                page.close()
                return context
            else:
                print("[⚠️] Session đã hết hạn hoặc chưa đăng nhập. Đang chuyển sang chế độ đăng nhập tương tác...")
                page.close()
                context.close()
                browser.close()
        except Exception as e:
            print(f"[⚠️] Lỗi kiểm tra session: {e}. Đang mở lại trình duyệt để đăng nhập...")
            try:
                page.close()
                context.close()
                browser.close()
            except Exception:
                pass

    # Preflight: cần đăng nhập tương tác nhưng môi trường không có màn hình → dừng sớm, báo rõ.
    if not interactive_display_available():
        raise NoDisplayError(NO_DISPLAY_MESSAGE)

    # Mở trình duyệt TRỰC QUAN (headed) để người dùng đăng nhập
    print("\n" + "=" * 76)
    print("👉 YÊU CẦU ĐĂNG NHẬP FACEBOOK:")
    print("Trình duyệt đang được mở lên. Vui lòng đăng nhập tài khoản Facebook của bạn.")
    print("(Hỗ trợ đầy đủ xác thực 2FA / OTP).")
    print("Hệ thống sẽ tự động nhận diện và lưu phiên đăng nhập ngay khi bạn vào Newsfeed!")
    print("=" * 76 + "\n")

    browser = playwright_instance.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1280, "height": 850},
        locale="vi-VN",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")

    start_time = time.time()
    max_wait = 300  # 5 phút
    logged_in = False

    while time.time() - start_time < max_wait:
        time.sleep(2)
        cookies = context.cookies()
        c_user = next((c.get("value") for c in cookies if c.get("name") == "c_user"), None)
        current_url = page.url

        if c_user and ("login" not in current_url) and ("checkpoint" not in current_url):
            print("\n[✅] Đã xác nhận phiên đăng nhập Facebook hợp lệ!")
            time.sleep(3)
            context.storage_state(path=str(STATE_FILE))
            print(f"[✅] Đã lưu session an toàn vào: {STATE_FILE}")
            logged_in = True
            break

    if not logged_in:
        print("[❌] Quá thời gian chờ đăng nhập (5 phút). Vui lòng thử lại!")
        context.close()
        browser.close()
        sys.exit(1)

    page.close()
    return context


def clean_article_text(raw_text: str) -> str:
    """Làm sạch nội dung bài viết, loại bỏ các dòng rác Facebook, obfuscated timestamp, nút bấm."""
    lines = raw_text.splitlines()
    cleaned_lines = []
    for line in lines:
        s = line.strip()
        if not s or s == "Facebook" or s == "·":
            continue
        if s.startswith("Viết bình luận") or s.startswith("Xem thêm bình luận") or s.startswith("Gợi ý cho bạn"):
            continue
        if s in ["Tác giả", "Trả lời", "Chia sẻ", "Ẩn bớt", "Xem thêm", "See more", "See less", "… Xem thêm", "... Xem thêm"]:
            continue
        # Bỏ các dòng chỉ chứa ký tự rác do Facebook obfuscate timestamp
        s_no_diacritics = re.sub(r"[\s\u0300-\u036f\ufe00-\ufe0f\u200b-\u200f]", "", s)
        if len(s_no_diacritics) <= 1 and len(s) <= 4:
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()
    return text


def extract_posts_from_page(
    page: Page,
    group_name: str,
    group_url: str,
    profile: Optional[Dict[str, Any]],
    seen_hashes: set,
    limit_posts: int = 15,
    max_scrolls: int = 4
) -> List[Dict[str, Any]]:
    """Trích xuất danh sách bài viết từ một trang feed / search page hiện tại."""
    extracted: List[Dict[str, Any]] = []

    # Tắt popup nếu có
    try:
        close_buttons = page.locator("div[aria-label='Đóng'], div[aria-label='Close'], div[aria-label='Không phải bây giờ'], div[aria-label='Not Now']")
        if close_buttons.count() > 0:
            close_buttons.first.click(timeout=1500)
    except Exception:
        pass

    for scroll_idx in range(max_scrolls):
        post_containers = page.locator("div[role='feed'] > div, div[data-pagelet^='GroupFeed_'], div[data-pagelet^='GroupFeed'], div[role='article']").all()

        for container in post_containers:
            try:
                # 1. Bấm 'Xem thêm' để mở rộng bài viết
                try:
                    see_more = container.locator("div[role='button']:has-text('Xem thêm'), span[role='button']:has-text('Xem thêm'), span:has-text('Xem thêm'), div[role='button']:has-text('See more'), span:has-text('See more')")
                    if see_more.count() > 0:
                        for sm_idx in range(see_more.count()):
                            try:
                                see_more.nth(sm_idx).dispatch_event("click")
                            except Exception:
                                try:
                                    see_more.nth(sm_idx).click(force=True, timeout=200)
                                except Exception:
                                    pass
                        time.sleep(0.15)
                except Exception:
                    pass

                # 2. Lấy nội dung văn bản
                raw_text = container.inner_text()
                full_text = clean_article_text(raw_text)
                if not full_text or len(full_text.strip()) < 35:
                    continue

                if full_text.startswith("Gợi ý cho bạn") or full_text.startswith("Suggested for you"):
                    continue

                # Hash tránh trùng
                text_hash = hashlib.md5(full_text[:200].encode("utf-8")).hexdigest()
                if text_hash in seen_hashes:
                    continue
                seen_hashes.add(text_hash)

                # Kiểm tra lọc theo Profile nghiêm ngặt
                if not is_job_relevant(full_text, profile=profile):
                    continue

                # 3. Trích xuất tác giả
                author_name = "Thành viên Facebook"
                author_link = ""
                try:
                    user_links = container.locator("a[href*='/user/']").all()
                    for ul in user_links:
                        u_name = ul.get_attribute("aria-label") or ul.inner_text().strip()
                        u_href = ul.get_attribute("href") or ""
                        if u_name and u_name.startswith("Trang cá nhân của "):
                            u_name = u_name.replace("Trang cá nhân của ", "").strip()
                        if u_name and (author_name == "Thành viên Facebook" or not author_name):
                            author_name = u_name
                        if u_href and "/user/" in u_href:
                            clean_u_href = u_href.split("?")[0]
                            author_link = f"https://www.facebook.com{clean_u_href}" if clean_u_href.startswith("/") else clean_u_href
                except Exception:
                    pass

                # 4. Trích xuất Direct Post Permalink (hover timestamp link)
                post_url = group_url
                try:
                    candidate_links = container.locator("a[href*='__cft__'], a[href*='/posts/'], a[href*='/permalink/'], a[href*='multi_permalinks']").all()
                    for cl in candidate_links:
                        raw_href = cl.get_attribute("href") or ""
                        if "/user/" in raw_href or "profile.php" in raw_href or "/hashtag/" in raw_href:
                            continue

                        if "/posts/" not in raw_href and "/permalink/" not in raw_href:
                            try:
                                cl.hover(timeout=400, force=True)
                                time.sleep(0.1)
                                raw_href = cl.get_attribute("href") or raw_href
                            except Exception:
                                pass

                        if "/posts/" in raw_href or "/permalink/" in raw_href or "multi_permalinks" in raw_href:
                            clean_post = raw_href.split("?")[0]
                            post_url = f"https://www.facebook.com{clean_post}" if clean_post.startswith("/") else clean_post
                            break
                except Exception:
                    pass

                # 5. Bóc tách liên hệ
                contacts = extract_contacts(full_text)
                if author_name and author_name != "Thành viên Facebook":
                    contacts["facebook_author"] = author_name
                    if author_link:
                        contacts["facebook_author_url"] = author_link

                post_item = {
                    "id": f"fb_{text_hash[:8]}",
                    "group_name": group_name,
                    "group_url": group_url,
                    "author": author_name,
                    "author_url": author_link,
                    "post_url": post_url,
                    "text": full_text.strip(),
                    "contacts": contacts,
                    "scraped_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }

                extracted.append(post_item)
                print(f"    [🎯 Tìm thấy JD Khớp] {author_name} ({post_url}): {full_text[:70].replace(chr(10), ' ')}...")

                if len(extracted) >= limit_posts:
                    return extracted
            except Exception:
                continue

        if len(extracted) >= limit_posts:
            break

        page.evaluate("window.scrollBy(0, window.innerHeight * 1.5);")
        time.sleep(2)

    return extracted


def crawl_facebook_group(
    context: BrowserContext,
    group_name: str,
    group_url: str,
    profile: Optional[Dict[str, Any]] = None,
    search_queries: Optional[List[str]] = None,
    use_search: bool = True,
    max_scrolls: int = 5,
    limit_posts: int = 15
) -> List[Dict[str, Any]]:
    """
    Truy cập vào một Facebook Group và tìm kiếm bài viết trực tiếp qua tính năng In-Group Search.
    """
    print(f"\n[*] Đang xử lý Group: {group_name}")
    print(f"    URL: {group_url}")

    extracted_posts: List[Dict[str, Any]] = []
    seen_hashes = set()

    clean_group_base = group_url.split("?")[0].rstrip("/")
    queries = search_queries if (search_queries and use_search) else []

    if use_search and queries:
        for q in queries:
            if len(extracted_posts) >= limit_posts:
                break
            search_target = f"{clean_group_base}/search/?q={urllib.parse.quote(q)}"
            print(f"  🔍 Tìm kiếm trong nhóm với từ khóa: '{q}'")
            print(f"     Search URL: {search_target}")

            page = context.new_page()
            try:
                page.goto(search_target, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3.5)
                posts = extract_posts_from_page(
                    page=page,
                    group_name=group_name,
                    group_url=group_url,
                    profile=profile,
                    seen_hashes=seen_hashes,
                    limit_posts=limit_posts - len(extracted_posts),
                    max_scrolls=max_scrolls
                )
                extracted_posts.extend(posts)
            except Exception as e:
                print(f"     [⚠️] Lỗi tìm kiếm '{q}': {e}")
            finally:
                page.close()
                time.sleep(1.5)
    else:
        # Fallback: Cuộn feed thông thường
        print("  [+] Đang cuộn feed nhóm theo thứ tự thời gian...")
        page = context.new_page()
        try:
            target_url = f"{clean_group_base}/?sorting_setting=CHRONOLOGICAL"
            page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(4)
            posts = extract_posts_from_page(
                page=page,
                group_name=group_name,
                group_url=group_url,
                profile=profile,
                seen_hashes=seen_hashes,
                limit_posts=limit_posts,
                max_scrolls=max_scrolls
            )
            extracted_posts.extend(posts)
        except Exception as e:
            print(f"     [⚠️] Lỗi cuộn feed: {e}")
        finally:
            page.close()

    print(f"  -> Đã thu thập {len(extracted_posts)} bài viết phù hợp target từ {group_name}.")
    return extracted_posts


def parse_group_urls(input_data: str) -> List[Dict[str, Any]]:
    """Phân tích chuỗi URL hoặc danh sách link do người dùng cung cấp thành danh sách group hợp lệ."""
    raw_urls = re.findall(r"https?://(?:www\.)?facebook\.com/groups/[a-zA-Z0-9._-]+/?", input_data)
    if not raw_urls:
        tokens = [t.strip() for t in re.split(r"[,\n\s]+", input_data) if t.strip()]
        for t in tokens:
            if "facebook.com/groups/" in t:
                raw_urls.append(t.split("?")[0].rstrip("/"))
            elif t.isalnum():
                raw_urls.append(f"https://www.facebook.com/groups/{t}")

    groups = []
    seen = set()
    for u in raw_urls:
        clean_u = u.split("?")[0].rstrip("/")
        if clean_u in seen:
            continue
        seen.add(clean_u)

        slug = clean_u.split("/groups/")[-1].strip("/")
        groups.append({
            "name": f"FB Group ({slug})",
            "url": clean_u,
            "enabled": True,
            "category": "user-provided",
            "description": f"Group do người dùng cung cấp ({slug})"
        })
    return groups


def normalize_group_config(config_data: Any) -> List[Dict[str, Any]]:
    """Chuẩn hóa config group mới và định dạng list cũ thành danh sách group bật."""
    if isinstance(config_data, list):
        raw_groups = config_data
    elif isinstance(config_data, dict):
        raw_groups = config_data.get("groups", [])
        if not isinstance(raw_groups, list):
            raise ValueError("Config Facebook phải có trường 'groups' là một danh sách")
    else:
        raise ValueError("Config Facebook phải là JSON object hoặc danh sách groups")

    groups = [
        group for group in raw_groups
        if isinstance(group, dict)
        and isinstance(group.get("url"), str)
        and group["url"].strip()
        and group.get("enabled", True)
    ]
    if not groups:
        raise ValueError(
            "Chưa có Facebook Group nào để crawl. Hãy truyền tham số 'groups' cho MCP tool "
            "hoặc thêm URL vào data/config/facebook_groups.json."
        )
    return groups


def main():
    parser = argparse.ArgumentParser(description="Facebook Group Job Scraper with In-Group Search & Target Filtering")
    parser.add_argument("--workspace-root", type=str, default=os.environ.get("JOB_MATCHING_WORKSPACE_ROOT"), help="Thư mục làm việc chứa data/ (mặc định: thư mục hiện tại)")
    parser.add_argument("--config", type=str, default=None, help="Đường dẫn file config groups")
    parser.add_argument("--groups", type=str, default=None, help="Danh sách link Facebook Group do người dùng gửi (cách nhau bởi dấu phẩy)")
    parser.add_argument("--profile", type=str, default=None, help="Đường dẫn file profile.json để lọc theo target ứng viên")
    parser.add_argument("--queries", type=str, default=None, help="Từ khóa tìm kiếm trong group, cách nhau bởi dấu phẩy (vd: 'AI Engineer, Computer Vision, LLM')")
    parser.add_argument("--no-search", action="store_true", help="Tắt chế độ tìm kiếm trong group, chuyển sang cuộn feed thông thường")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn file JSON xuất kết quả")
    parser.add_argument("--login-only", action="store_true", help="Chỉ mở trình duyệt để đăng nhập và lưu session")
    parser.add_argument("--force-login", action="store_true", help="Bắt buộc đăng nhập lại từ đầu")
    parser.add_argument("--headless", action="store_true", help="Chạy browser ẩn danh (chỉ áp dụng khi đã có session)")
    parser.add_argument("--limit", type=int, default=15, help="Số bài viết tối đa mỗi group")
    parser.add_argument("--scrolls", type=int, default=5, help="Số lần cuộn mỗi trang tìm kiếm")

    args = parser.parse_args()
    if not 1 <= args.limit <= 50:
        parser.error("--limit phải nằm trong khoảng 1-50")
    if not 1 <= args.scrolls <= 20:
        parser.error("--scrolls phải nằm trong khoảng 1-20")
    configure_workspace_root(args.workspace_root)
    config_path = resolve_workspace_path(args.config) if args.config else DEFAULT_CONFIG_PATH

    print("=" * 60)
    print("   FACEBOOK GROUP JOB SCRAPER — IN-GROUP SEARCH & TARGET FILTERING")
    print("=" * 60)

    # Tải profile ứng viên để lọc thông minh
    profile_data = load_candidate_profile(args.profile)

    # Sinh danh sách từ khóa tìm kiếm mục tiêu
    search_queries = get_search_queries(profile=profile_data, custom_queries=args.queries)
    if not args.no_search:
        print(f"[*] Từ khóa tìm kiếm trong nhóm: {search_queries}")

    # Xử lý danh sách groups do người dùng gửi (nếu có)
    if args.groups:
        user_groups = parse_group_urls(args.groups)
        if user_groups:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "description": "Danh sách các Facebook Group mục tiêu do người dùng cung cấp",
                    "groups": user_groups
                }, f, ensure_ascii=False, indent=2)
            print(f"[✅] Đã cập nhật {len(user_groups)} Facebook Group do người dùng cung cấp vào: {config_path}")

    with sync_playwright() as p:
        try:
            context = ensure_facebook_session(p, force_login=args.force_login, headless=args.headless)
        except NoDisplayError as exc:
            print("\n[❌] " + str(exc), file=sys.stderr)
            sys.exit(3)

        if args.login_only:
            print("\n[✅] Hoàn tất bước đăng nhập & lưu session. Kết thúc.")
            context.close()
            return

        # Đọc danh sách group từ config
        if not config_path.exists():
            print(f"[❌] Không tìm thấy file config tại {config_path}")
            context.close()
            sys.exit(1)

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        try:
            groups = normalize_group_config(config_data)
        except ValueError as exc:
            raise ValueError(f"Config Facebook không hợp lệ tại {config_path}: {exc}") from exc
        print(f"\n[*] Đã tải {len(groups)} Facebook Groups mục tiêu từ config.")

        all_posts: List[Dict[str, Any]] = []
        for g in groups:
            posts = crawl_facebook_group(
                context=context,
                group_name=g.get("name", "Unknown Group"),
                group_url=g.get("url", ""),
                profile=profile_data,
                search_queries=search_queries,
                use_search=not args.no_search,
                max_scrolls=args.scrolls,
                limit_posts=args.limit
            )
            all_posts.extend(posts)
            time.sleep(2)

        context.close()

        # Xác định file output
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        DEFAULT_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = resolve_workspace_path(args.output) if args.output else (DEFAULT_JOBS_DIR / f"raw_fb_posts_{today_str}.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print(f"[✅] HOÀN TẤT CÀO DỮ LIỆU FACEBOOK GROUPS!")
        print(f"Tổng số bài tuyển dụng bóc tách được: {len(all_posts)}")
        print(f"Đã lưu kết quả tại: {out_path}")
        print("=" * 60)


if __name__ == "__main__":
    main()
