---
description: Chạy full pipeline tìm việc — parse CV, thu thập job, chấm điểm, xuất báo cáo fit/gap.
argument-hint: [đường dẫn CV hoặc tên profile]
---

# /find-jobs — Điều phối pipeline tìm việc

Chạy tuần tự 4 bước. `$ARGUMENTS` là đường dẫn CV (PDF/DOCX/text) hoặc tên profile đã có.

Dùng `<run-id>` = ngày hiện tại (YYYY-MM-DD). Tạo thư mục `data/profiles`, `data/jobs`, `data/results` trong thư mục làm việc nếu chưa có.

## Bước 1 — Intake (skill `candidate-intake`)
- Nếu `$ARGUMENTS` là file CV → parse và tạo `data/profiles/<slug>.json`.
- Nếu là tên profile đã tồn tại → dùng lại, hỏi xem có cập nhật target không.
- Thu thập/ xác nhận target: vai trò, cấp bậc, địa điểm/remote, lương, ưu tiên (priorities → trọng số), dealbreakers.
- Tóm tắt cho người dùng xác nhận.
- **Tùy chọn nguồn Facebook (Minh bạch & Động)**:
  - Hỏi người dùng: *"Bạn có muốn quét thêm tin tuyển dụng từ các Hội nhóm Facebook không?"*
  - *(Cảnh báo minh bạch: Nếu chọn Có và chưa có session, trình duyệt sẽ tự động mở lên để bạn đăng nhập Facebook lấy cookie session — được lưu bảo mật cục bộ tại `data/.auth/`, không bao giờ commit lên Git).*
  - **Nếu người dùng chọn CÓ**: Yêu cầu người dùng **gửi danh sách link các Group Facebook công khai** mà họ muốn quét (ví dụ: `https://facebook.com/groups/pythonvietnam`, `https://facebook.com/groups/1407434203194440`...).
  - Agent tự động ghi danh sách link này vào [`data/config/facebook_groups.json`](file:///d:/StartUp/JobMatching/data/config/facebook_groups.json).

## Bước 2a — Cào Facebook (luồng chính, CHỈ khi người dùng đã bật ở Bước 1)

> Nguồn Facebook chạy qua MCP tool Claude `mcp__plugin_job-matching_facebook_crawler__run_facebook_crawler` (tool `run_facebook_crawler` của server `facebook_crawler` đi kèm plugin). Đây là **một tool riêng, KHÔNG phải WebSearch** — không được tự thay bằng nguồn khác. Chạy ở luồng chính vì lần đầu cần người dùng đang xem màn hình để đăng nhập.

1. Nếu chưa có `data/.auth/facebook_state.json`, thông báo rõ cho người dùng rằng một cửa sổ Chromium sắp mở và họ cần tự đăng nhập Facebook. Sau đó gọi MCP tool với `login_only: true`, `headless: false`. Đợi tool trả `status: login_saved` rồi mới tiếp tục.
2. **Gọi MCP tool để cào dữ liệu** với tham số:
   - `profile_path`: `data/profiles/<slug>.json`
   - `groups`: danh sách link group người dùng cung cấp ở Bước 1 (hoặc để trống nếu đã ghi vào `config_path`)
   - `config_path`: `data/config/facebook_groups.json`
   - (tùy chọn) `limit`, `scrolls`, `queries`; bỏ trống `workspace_root` → tool tự dùng thư mục hiện tại.
3. Nếu session đã tồn tại, truyền `headless: true`. Nếu session hết hạn và tool cần mở lại Chromium, thông báo cho người dùng trước khi thử lại với `login_only: true`, `headless: false`.
4. Khi tool trả về, đọc `output_path` (mặc định `data/jobs/raw_fb_posts_<date>.json`) và xem `job_count`.
5. Nếu tool trả `isError`/`status: error` (thiếu Playwright → `pip install playwright && playwright install chromium`; group riêng tư; đăng nhập thất bại): **nói thẳng lỗi**, hỏi người dùng thử lại hay bỏ qua, rồi tiếp tục pipeline chỉ với nguồn web. **Không bịa job Facebook.**

**Fallback chẩn đoán** (chỉ khi MCP tool không khả dụng): Bash `python "${CLAUDE_PLUGIN_ROOT}/scripts/fb_crawler.py" --profile data/profiles/<slug>.json --config data/config/facebook_groups.json` với **timeout = 600000ms** (cân nhắc `run_in_background`), rồi Read file kết quả.

### ⚠️ Quy tắc BẮT BUỘC
- Facebook load chậm / cuộn lâu là **bình thường** — tool/script tự quản lý thời gian chờ và cuộn bên trong. **KHÔNG** đánh giá "đang tải chậm" giữa chừng để tự dừng.
- **TUYỆT ĐỐI KHÔNG** thay nguồn Facebook bằng `WebSearch`/`WebFetch` và gọi đó là "hiệu quả hơn". WebSearch **không đọc được** feed bên trong Facebook Group → đây là hai nguồn khác nhau, **không thay thế cho nhau**. WebSearch chỉ phục vụ Kênh 2 (job boards).
- Chỉ được bỏ nguồn Facebook khi: (a) người dùng chọn không bật, hoặc (b) crawler **thực sự lỗi/timeout** — và khi đó phải **nói thẳng lỗi**, hỏi người dùng muốn thử lại hay bỏ qua; **không âm thầm** đổi nguồn rồi coi như xong.
- **Môi trường cloud/headless (không có display)**: nếu chưa có session, crawler **không thể đăng nhập** (cần màn hình thật cho mật khẩu + 2FA). Tool/script sẽ báo lỗi `NoDisplayError` rõ ràng. Khi đó: nói cho người dùng **hai cách** — (1) chạy pipeline ở **máy local có màn hình** rồi đăng nhập một lần; hoặc (2) đăng nhập local một lần để tạo `data/.auth/facebook_state.json` rồi **copy** file đó sang môi trường cloud và chạy `--headless` (lưu ý session gắn IP/thiết bị, dùng từ IP cloud lạ có thể bị Facebook chặn). Trong lúc đó, **tiếp tục pipeline chỉ với job boards** — đây là trường hợp bỏ Facebook **hợp lệ và trung thực** (khác hẳn việc tự đổi nguồn khi crawler vẫn chạy được).

## Bước 2b — Collector (subagent `job-collector`)
- Truyền đường dẫn `profile.json`, `data/jobs/<run-id>.json` (output), và đường dẫn `raw_fb_posts_<date>.json` nếu đã cào được ở Bước 2a.
- **Nguồn Job Boards**: Luôn quét từ ITviec, TopCV, VietnamWorks, LinkedIn... (WebSearch + WebFetch).
- **Nguồn Facebook**: Đọc (Read) file `raw_fb_posts_<date>.json` và chuẩn hóa vào schema (không chạy lại crawler ở subagent).
- Giữ job theo chuẩn: Job boards cần full JD & còn hạn; Facebook post chỉ cần Title + Vị trí/Địa điểm + Kênh liên hệ/Link bài viết. Mục tiêu tối đa 20 job hợp lệ.

## Bước 3 — Matcher (subagent `job-matcher`)
- Truyền `profile.json` + `data/jobs/<run-id>.json`.
- Chấm điểm theo skill `scoring-rubric`, dùng trọng số từ `target.priorities`.
- Ghi `data/results/<run-id>.shortlist.json`.

## Bước 4 — Fit report (skill `fit-analyzer`)
- Đọc shortlist → tạo `data/results/<run-id>.fit_report.md`.
- **Phân tích chi tiết TẤT CẢ job trong shortlist** (nếu >20 thì chi tiết 20 job điểm cao nhất, phần còn lại vẫn liệt kê đủ trong bảng). **KHÔNG rút gọn báo cáo chỉ còn top 3.**
- Có thể đánh dấu thêm nhóm "Ưu tiên apply ngay" ở đầu, nhưng đó là phần bổ sung — không thay thế phần phân tích chi tiết từng job bên dưới.
- **Mọi job trong bảng xếp hạng đều có link nộp CV / bài post bấm được.**
- Gửi file báo cáo cho người dùng.

## Sau khi xong
Đề xuất bước tiếp: tailor hồ sơ cho job top (skill `application-assistant`), hoặc mở rộng nguồn (remote quốc tế / thành phố khác).

## Nguyên tắc
- Không bịa dữ liệu job/CV. Thiếu → unknown, hạ confidence.
- Tôn trọng robots/ToS khi scrape; không vượt anti-bot/CAPTCHA.
- Không tự nộp hồ sơ thay người dùng.
