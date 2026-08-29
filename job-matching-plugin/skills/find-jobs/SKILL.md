---
name: find-jobs
description: Chạy full pipeline tìm việc song ngữ Việt–Anh — parse CV, thu thập job (web search), chấm điểm, xuất báo cáo fit/gap. Dùng khi người dùng muốn "tìm job cho tôi" từ một CV hoặc profile đã có.
---

# find-jobs — điều phối full pipeline tìm việc

Skill điều phối, chạy tuần tự 4 bước. Đối số là đường dẫn CV (PDF/DOCX/text) hoặc tên
profile đã có trong `data/profiles/`.

Dùng `<run-id>` duy nhất theo mẫu `<candidate-slug>-<YYYYMMDD-HHMMSS>-<suffix>` và giữ nguyên
ID này xuyên suốt pipeline. Tạo `data/profiles`, `data/jobs`, `data/results` trong thư mục làm việc
nếu chưa có.

> **Yêu cầu (bước 2 — thu thập job):**
> - **Claude Code**: `WebSearch`/`WebFetch` có sẵn — không cần cấu hình.
> - **Codex**: cần bật `web_search` bằng `codex --search` hoặc `tools.web_search = true` trong `~/.codex/config.toml`. Nếu chưa bật, dừng ở bước 2 và báo người dùng.

## Bước 1 — Intake → profile.json
Áp skill **`candidate-intake`**.
- Nếu đối số là file CV → parse và tạo `data/profiles/<slug>.json` theo `schemas/profile.schema.json`.
- Nếu là tên profile đã tồn tại → dùng lại, hỏi có cập nhật target không.
- Thu thập/xác nhận target: vai trò, cấp bậc, địa điểm/remote, lương, priorities (→ trọng số), dealbreakers.
- Tóm tắt cho người dùng xác nhận.

## Bước 2 — Collect → data/jobs/<run-id>.json
Spawn một subagent context riêng và yêu cầu nó áp skill **`job-collector`**; không phụ thuộc custom
agent cài ngoài plugin.
- Truyền đường dẫn `profile.json`, `<run-id>` và output `data/jobs/<run-id>.json`.
- **Nguồn Job Boards**: Quét từ ITviec, TopCV, VietnamWorks, LinkedIn...
- Giữ job thỏa mãn tiêu chuẩn: chỉ giữ job xem được full JD & còn hạn. Tối đa 20 job hợp lệ.

## Bước 3 — Match → data/results/<run-id>.shortlist.json
Spawn một subagent context riêng và yêu cầu nó áp skill **`job-matcher`** (chấm điểm bulk).
- Truyền `profile.json` + `data/jobs/<run-id>.json`.
- Chấm điểm theo skill **`scoring-rubric`**, dùng trọng số từ `target.priorities`.

## Bước 4 — Fit report → data/results/<run-id>.fit_report.md
Áp skill **`fit-analyzer`**.
- Bảng xếp hạng: **mọi job đều có link nộp CV (url) bấm được**; phân tích chi tiết top 20 (hoặc toàn bộ).
- Báo đường dẫn file báo cáo cho người dùng.

## Sau khi xong
Đề xuất bước tiếp: tailor hồ sơ cho job top (skill `application-assistant`), hoặc mở rộng
nguồn (remote quốc tế / thành phố khác).

## Nguyên tắc
- Không bịa dữ liệu job/CV. Thiếu → unknown, hạ confidence.
- Tôn trọng robots/ToS khi scrape; không vượt anti-bot/CAPTCHA.
- Không tự nộp hồ sơ thay người dùng.
