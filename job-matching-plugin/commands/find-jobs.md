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

## Bước 2 — Collector (subagent `job-collector`)
- Truyền đường dẫn `profile.json` và `data/jobs/<run-id>.json` làm output.
- **Nguồn Job Boards**: Luôn quét từ ITviec, TopCV, VietnamWorks, LinkedIn...
- **Nguồn Facebook Groups (Nếu người dùng đồng ý & cung cấp link ở Bước 1)**: Chạy `python scripts/fb_crawler.py --profile <profile.json> --config data/config/facebook_groups.json` để tìm kiếm trực tiếp trong các group mục tiêu vừa nạp.
- Giữ job theo chuẩn: Job boards cần full JD & còn hạn; Facebook post chỉ cần Title + Vị trí/Địa điểm + Kênh liên hệ/Link bài viết. Mục tiêu tối đa 20 job hợp lệ.

## Bước 3 — Matcher (subagent `job-matcher`)
- Truyền `profile.json` + `data/jobs/<run-id>.json`.
- Chấm điểm theo skill `scoring-rubric`, dùng trọng số từ `target.priorities`.
- Ghi `data/results/<run-id>.shortlist.json`.

## Bước 4 — Fit report (skill `fit-analyzer`)
- Đọc shortlist → tạo `data/results/<run-id>.fit_report.md`.
- **Mọi job trong bảng xếp hạng đều có link nộp CV / bài post**; phân tích chi tiết top 20 (hoặc toàn bộ).
- Gửi file báo cáo cho người dùng.

## Sau khi xong
Đề xuất bước tiếp: tailor hồ sơ cho job top (skill `application-assistant`), hoặc mở rộng nguồn (remote quốc tế / thành phố khác).

## Nguyên tắc
- Không bịa dữ liệu job/CV. Thiếu → unknown, hạ confidence.
- Tôn trọng robots/ToS khi scrape; không vượt anti-bot/CAPTCHA.
- Không tự nộp hồ sơ thay người dùng.
