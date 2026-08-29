---
description: Chạy full pipeline tìm việc — parse CV, thu thập job, chấm điểm, xuất báo cáo fit/gap.
argument-hint: [đường dẫn CV hoặc tên profile]
---

# /find-jobs — Điều phối pipeline tìm việc

Chạy tuần tự 4 bước. `$ARGUMENTS` là đường dẫn CV (PDF/DOCX/text) hoặc tên profile đã có.

Dùng `<run-id>` duy nhất theo mẫu `<candidate-slug>-<YYYYMMDD-HHMMSS>-<suffix>` và giữ nguyên ID này xuyên suốt pipeline. Tạo thư mục `data/profiles`, `data/jobs`, `data/results` trong thư mục làm việc nếu chưa có.

## Bước 1 — Intake (skill `candidate-intake`)
- Nếu `$ARGUMENTS` là file CV → parse và tạo `data/profiles/<slug>.json`.
- Nếu là tên profile đã tồn tại → dùng lại, hỏi xem có cập nhật target không.
- Thu thập/ xác nhận target: vai trò, cấp bậc, địa điểm/remote, lương, ưu tiên (priorities → trọng số), dealbreakers.
- Tóm tắt cho người dùng xác nhận.

## Bước 2 — Collector (subagent `job-collector`)
- Truyền đường dẫn `profile.json`, `data/jobs/<run-id>.json` (output).
- **Nguồn Job Boards**: Quét từ ITviec, TopCV, VietnamWorks, LinkedIn... (WebSearch + WebFetch).
- Giữ job theo chuẩn: chỉ giữ job xem được full JD & còn hạn. Mục tiêu tối đa 20 job hợp lệ.

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
