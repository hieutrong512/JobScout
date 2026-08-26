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
- Tóm tắt cho người dùng xác nhận trước khi sang bước 2.

## Bước 2 — Collector (subagent `job-collector`)
- Truyền đường dẫn `profile.json` và `data/jobs/<run-id>.json` làm output.
- Tìm kiếm từ các Job Boards (ITviec, TopCV, VietnamWorks, LinkedIn...) và các **Hội nhóm Facebook công khai** (Vietnam AI Community, J2TEAM, Tuyển Dụng IT...).
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
