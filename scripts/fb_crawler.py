#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Group Job Scraper with Interactive Login & Session Persistence
Hệ thống tự động đăng nhập tương tác & cào bài viết tuyển dụng từ các Facebook Groups mục tiêu.
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

# Đường dẫn mặc định
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AUTH_DIR = WORKSPACE_ROOT / "data" / ".auth"
STATE_FILE = AUTH_DIR / "facebook_state.json"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "data" / "config" / "facebook_groups.json"
DEFAULT_JOBS_DIR = WORKSPACE_ROOT / "data" / "jobs"
DEFAULT_PROFILE_DIR = WORKSPACE_ROOT / "data" / "profiles"

# Regex nhận diện thông tin liên hệ (hỗ trợ số có dấu chấm, khoảng trắng, gạch ngang)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE)
RAW_PHONE_REGEX = re.compile(r"(?:\+84|84|0)[3|5|7|8|9](?:[\s.-]*\d){8}\b")
TELEGRAM_REGEX = re.compile(r"(?:t\.me\/|telegram[:\s@]+)([a-zA-Z0-9_]{4,32})", re.IGNORECASE)
ZALO_REGEX = re.compile(
    r"(?:zalo|zl|zlo)[\s:–—]*((?:\+84|84|0)[3|5|7|8|9](?:[\s.-]*\d){8}|[0-9]{9,11})",
    re.IGNORECASE
)


def load_candidate_profile(profile_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Tải hồ sơ ứng viên từ đường dẫn hoặc tự động tìm file json trong data/profiles/."""
    if profile_path and Path(profile_path).exists():
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[⚠️] Không thể đọc profile từ {profile_path}: {e}")
            
    if DEFAULT_PROFILE_DIR.exists():
        profiles = [p for p in DEFAULT_PROFILE_DIR.glob("*.json") if not p.name.startswith(".")]
        if profiles:
            try:
                with open(profiles[0], "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"[*] Đã tự động tải Profile ứng viên: {profiles[0].name} (Target: {data.get('candidate', {}).get('name', 'N/A')})")
                    return data
            except Exception as e:
                print(f"[⚠️] Không thể đọc profile tự động: {e}")
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
        return [q.strip() for q in custom_queries.split(",") if q.strip()]
        
    if profile:
        target = profile.get("target", {})
        desired_roles = target.get("desired_roles", [])
        if desired_roles:
            # Chọn các từ khóa đại diện ngắn gọn nhất
            queries = []
            for r in desired_roles:
                clean_r = re.sub(r"\b(engineer|developer|lead|senior|expert)\b", "", r, flags=re.IGNORECASE).strip()
                if clean_r and clean_r not in queries:
                    queries.append(clean_r)
                if r not in queries:
                    queries.append(r)
            # Giữ top 3-4 query chất lượng nhất
            top_queries = ["AI Engineer", "Computer Vision", "LLM", "YOLO"]
            return [q for q in top_queries if q]
            
    return ["AI Engineer", "Computer Vision", "LLM", "YOLO"]


def is_job_relevant(text: str, profile: Optional[Dict[str, Any]] = None) -> bool:
    """
    Kiểm tra bài post theo tiêu chí tuyển dụng và so khớp NGHIÊM NGẶT với Target trong Profile ứng viên.
    """
    text_lower = text.lower()
    
    # 1. Tín hiệu tuyển dụng bắt buộc
    hiring_cues = [
        "tuyển", "tuyển dụng", "hiring", "tìm đồng đội", "recruiting", "jd", "cơ hội việc làm",
        "offer", "lương", "lương:", "deal", "ứng tuyển", "inbox nhận jd", "gửi cv", "apply", "vị trí"
    ]
    if not any(cue in text_lower for cue in hiring_cues):
        return False
        
    # 2. LOẠI TRỪ NGHIÊM NGẶT: Các vị trí Data Engineer, Data Analyst, Web, Mobile, Tester...
    # (Trừ khi bài đăng tuyển kèm AI Engineer / Computer Vision / LLM)
    pure_excluded_roles = [
        "data engineer", "data analyst", "bi engineer", "data governance", "database administrator",
        "ios developer", "android developer", "flutter developer", "react native",
        "php developer", "laravel developer", "tester manual", "qa/qc", "automation test",
        "sales it", "telesales", "content marketing", "graphic designer", "kế toán"
    ]
    has_excluded_role = any(re.search(rf"\b{re.escape(cue)}\b", text_lower) for cue in pure_excluded_roles)
    
    # 3. Danh sách từ khóa LÕI AI/CV/LLM của ứng viên
    strong_ai_keywords = [
        "ai", "computer vision", "vision", "cv", "yolo", "ocr", "segmentation",
        "llm", "rag", "agent", "ai agent", "genai", "prompt", "deep learning", "machine learning",
        "edge ai", "jetson", "npu", "rknn", "tensorrt", "pytorch"
    ]
    
    # Phải có ít nhất 1 từ khóa chuyên môn lõi AI/ML
    has_strong_ai = any(re.search(rf"\b{re.escape(k)}\b", text_lower) for k in strong_ai_keywords)
    if not has_strong_ai:
        return False
        
    # Nếu bài viết có role loại trừ (như Data Engineer/iOS), chỉ giữ khi có nhắc rõ "AI Engineer" hoặc "Computer Vision"
    if has_excluded_role:
        must_have_ai_cues = ["ai engineer", "computer vision", "yolo", "llm", "ai agent", "deep learning"]
        if not any(cue in text_lower for cue in must_have_ai_cues):
            return False
            
    # 4. KIỂM TRA ĐỊA ĐIỂM NGHIÊM NGẶT (Target: HCM / Remote)
    if profile:
        target = profile.get("target", {})
        locations = [loc.lower() for loc in target.get("locations", [])]
        is_hcm_or_remote = any("ho chi minh" in loc or "hcm" in loc or "remote" in loc for loc in locations)
        
        if is_hcm_or_remote:
            hanoi_danang_cues = [
                "hà nội", "ha noi", "cầu giấy", "nam từ liêm", "bắc từ liêm", "đống đa",
                "thanh xuân", "hoàn kiếm", "ba đình", "hai bà trưng", "hoàng mai", "tây hồ",
                "hòa lạc", "phạm hùng", "đà nẵng", "da nang", "hải châu"
            ]
            hcm_remote_cues = [
                "hcm", "hồ chí minh", "ho chi minh", "sài gòn", "sai gon", "tp.hcm", "tphcm",
                "quận 1", "quận 7", "quận 2", "thủ đức", "tân bình", "bình thạnh", "phú nhuận", "q1", "q7",
                "remote", "wfh", "làm việc từ xa", "toàn quốc", "hybrid", "relocation", "hỗ trợ relocation", "chuyển vùng"
            ]
            
            has_north_central_location = any(hn in text_lower for hn in hanoi_danang_cues)
            has_hcm_or_remote = any(k in text_lower for k in hcm_remote_cues)
            
            # Nếu bài viết xác định địa điểm ở Hà Nội / Đà Nẵng mà KHÔNG nhắc đến HCM / Remote / Relocation -> LOẠI NGAY
            if has_north_central_location and not has_hcm_or_remote:
                return False
                
    return True


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
            print(f"\n[✅] Đã nhận diện tài khoản (c_user: {c_user})!")
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
            
    print(f"  -> Đã thu thập {len(extracted_posts)} bài viết AI/CV/LLM phù hợp từ {group_name}.")
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


def main():
    parser = argparse.ArgumentParser(description="Facebook Group Job Scraper with In-Group Search & Target Filtering")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH), help="Đường dẫn file config groups")
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
            DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "description": "Danh sách các Facebook Group mục tiêu do người dùng cung cấp",
                    "groups": user_groups
                }, f, ensure_ascii=False, indent=2)
            print(f"[✅] Đã cập nhật {len(user_groups)} Facebook Group do người dùng cung cấp vào: {DEFAULT_CONFIG_PATH}")
    
    with sync_playwright() as p:
        context = ensure_facebook_session(p, force_login=args.force_login, headless=args.headless)
        
        if args.login_only:
            print("\n[✅] Hoàn tất bước đăng nhập & lưu session. Kết thúc.")
            context.close()
            return
            
        # Đọc danh sách group từ config
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"[❌] Không tìm thấy file config tại {config_path}")
            context.close()
            sys.exit(1)
            
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
        groups = [g for g in config_data.get("groups", []) if g.get("enabled", True)]
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
        out_path = Path(args.output) if args.output else (DEFAULT_JOBS_DIR / f"raw_fb_posts_{today_str}.json")
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
            
        print("\n" + "=" * 60)
        print(f"[✅] HOÀN TẤT CÀO DỮ LIỆU FACEBOOK GROUPS!")
        print(f"Tổng số bài tuyển dụng bóc tách được: {len(all_posts)}")
        print(f"Đã lưu kết quả tại: {out_path}")
        print("=" * 60)


if __name__ == "__main__":
    main()
