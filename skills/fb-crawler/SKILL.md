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

## Cách chạy trong plugin

Luôn gọi tool MCP local `run_facebook_crawler` của server `facebook_crawler`. Không chạy lệnh Python trực tiếp trong sandbox.

Truyền tối thiểu:
- `workspace_root`: đường dẫn tuyệt đối của workspace hiện tại.
- `profile_path`: profile JSON nếu có.
- `config_path`: thường là `data/config/facebook_groups.json`.
- `groups`: danh sách URL group do người dùng đã đồng ý cung cấp.
- `queries`, `limit`, `scrolls` khi cần tùy chỉnh.

Tool trả `output_path`, `session_path`, `job_count` và trạng thái. Đọc JSON từ `output_path` sau khi tool hoàn tất. Nếu chưa có session, tool tự mở Chromium headed để người dùng đăng nhập một lần.

## Chạy thủ công để chẩn đoán

### 1. Quét theo danh sách link group do người dùng cung cấp:
```bash
python scripts/fb_crawler.py --workspace-root "<absolute-workspace>" --groups "<link-group-1>, <link-group-2>" --limit 10
```

### 2. Quét theo target Profile và config mặc định:
```bash
python scripts/fb_crawler.py --workspace-root "<absolute-workspace>" --profile data/profiles/nguyen-trong-hieu.json --limit 10
```

### 3. Chỉ mở trình duyệt để đăng nhập lưu session (nếu chưa đăng nhập):
```bash
python scripts/fb_crawler.py --workspace-root "<absolute-workspace>" --login-only
```

### 4. Chạy ngầm (headless) khi đã có session:
```bash
python scripts/fb_crawler.py --workspace-root "<absolute-workspace>" --headless --limit 10
```

## Các cờ (flags) quan trọng
- `--workspace-root "<path>"`: Workspace cố định chứa `data/`; không phụ thuộc thư mục gọi lệnh.
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
1. **Lần đầu chạy hoặc session hết hạn**: Script sẽ tự mở cửa sổ trình duyệt thật (headed) trên màn hình để người dùng đăng nhập thủ công (nhập mật khẩu, 2FA/OTP).
2. **Session Persistence**: Session được lưu bảo mật cục bộ tại `data/.auth/facebook_state.json` (đã nằm trong `.gitignore`), các lần sau có thể chạy mà không cần đăng nhập lại.
3. **Đầu ra**: Dữ liệu cào được lưu tại `data/jobs/raw_fb_posts_<YYYY-MM-DD>.json`.
