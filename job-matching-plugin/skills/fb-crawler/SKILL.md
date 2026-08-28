---
name: fb-crawler
description: Quét và bóc tách các bài viết tuyển dụng AI/CV/LLM từ các Facebook Group công khai sử dụng script Playwright. Dùng khi người dùng muốn cào bài tuyển dụng từ Facebook, hoặc trong pipeline tìm việc.
---

# Facebook Group Job Scraper

Cào bài tuyển dụng AI/CV/LLM từ các Facebook Group mục tiêu, hỗ trợ In-Group Search, bóc tách Direct Permalink và lọc theo Profile ứng viên.

## Yêu cầu môi trường
- Python 3.9+
- `pip install playwright`
- `playwright install chromium`
- **Cần MÁY LOCAL có màn hình cho lần đăng nhập đầu tiên.** Cloud container / môi trường headless (không có `DISPLAY`) **không mở được** trình duyệt để nhập mật khẩu + 2FA → crawler dừng sớm với `NoDisplayError`. Trong trường hợp đó: đăng nhập một lần ở máy local để tạo `data/.auth/facebook_state.json`, rồi có thể **copy** file session sang môi trường cloud và chạy `--headless` (session gắn IP/thiết bị — dùng từ IP lạ có thể bị Facebook chặn). Nếu không có session, đây là lý do **hợp lệ** để bỏ nguồn Facebook và chỉ dùng job boards.

## Cách chạy

### Cách 1 (khuyến nghị) — MCP tool `run_facebook_crawler`
Gọi tool `run_facebook_crawler` (server `facebook_crawler` đi kèm plugin). Tham số chính:
- `profile_path` — profile JSON để suy từ khóa & lọc theo target.
- `groups` — danh sách URL Facebook Group công khai (hoặc `config_path` trỏ tới file đã lưu).
- `queries`, `limit`, `scrolls` — tùy chọn. `workspace_root` bỏ trống = thư mục hiện tại.
- `login_only: true` — chỉ mở Chromium để đăng nhập & lưu session.

Tool tự lo đăng nhập (lần đầu mở Chromium; **không tự nhập mật khẩu hộ người dùng**), chờ tới khi xong, trả về `output_path`, `session_path`, `job_count`, `status`. Đọc JSON tại `output_path`.

> **Đây là NGUỒN Facebook duy nhất — `WebSearch`/`WebFetch` KHÔNG thay thế được** (không đọc được feed trong group). Facebook load chậm là bình thường; **đợi tool trả về**, không bỏ giữa chừng. Chỉ dừng khi tool trả `isError`/`status: error`, và khi đó nói rõ lỗi cho người dùng.

### Cách 2 (fallback / chẩn đoán) — Bash trực tiếp
Chỉ dùng khi MCP tool không khả dụng. Chạy bằng **tool Bash** với **timeout = 600000ms** (script Playwright, không dùng WebFetch; cào nhiều group → `run_in_background`), rồi Read `data/jobs/raw_fb_posts_<date>.json`.

### 1. Quét theo danh sách link group do người dùng cung cấp:
```bash
python "./scripts/fb_crawler.py" --groups "<link-group-1>, <link-group-2>" --limit 10
```

### 2. Quét theo target Profile và config mặc định:
```bash
python "./scripts/fb_crawler.py" --profile data/profiles/nguyen-trong-hieu.json --limit 10
```

### 3. Chỉ mở trình duyệt để đăng nhập lưu session (nếu chưa đăng nhập):
```bash
python "./scripts/fb_crawler.py" --login-only
```

### 4. Chạy ngầm (headless) khi đã có session:
```bash
python "./scripts/fb_crawler.py" --headless --limit 10
```

## Các cờ (flags) quan trọng
- `--workspace-root "<path>"`: Ghim thư mục làm việc chứa `data/` (mặc định: thư mục hiện tại). Dùng khi cần chắc chắn `data/` không ghi nhầm vào thư mục cài plugin.
- `--groups "<urls>"`: Danh sách URL các Facebook Group (cách nhau bởi dấu phẩy).
- `--profile "<path>"`: Đường dẫn file profile JSON để tự động lấy từ khóa AI/CV/LLM và lọc theo địa điểm HCM/Remote.
- `--queries "AI Engineer,LLM"`: Tùy chỉnh danh sách từ khóa tìm kiếm trong group.
- `--no-search`: Tắt In-Group Search, cuộn feed theo thứ tự thời gian.
- `--limit <N>`: Số bài viết tối đa mỗi group (mặc định: 15).
- `--scrolls <N>`: Số lần cuộn mỗi trang tìm kiếm (mặc định: 5).
- `--login-only`: Chỉ mở trình duyệt headed để đăng nhập và lưu session vào `data/.auth/facebook_state.json`.
- `--force-login`: Bắt buộc đăng nhập lại từ đầu.
- `--headless`: Chạy browser ẩn (chỉ dùng khi đã có session hợp lệ).

## Cơ chế hoạt động & Lưu ý
1. **Lần đầu chạy hoặc session hết hạn**: Script sẽ tự mở cửa sổ trình duyệt thật (headed) trên màn hình để người dùng đăng nhập thủ công (nhập mật khẩu, 2FA/OTP). Claude Code không tự nhập mật khẩu Facebook của người dùng.
2. **Session Persistence**: Session được lưu bảo mật cục bộ tại `data/.auth/facebook_state.json` (đã nằm trong `.gitignore`), các lần sau có thể chạy mà không cần đăng nhập lại.
3. **Đầu ra**: Dữ liệu cào được lưu tại `data/jobs/raw_fb_posts_<YYYY-MM-DD>.json`.
