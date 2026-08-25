Chạy full pipeline tìm việc song ngữ Việt–Anh, tuần tự 4 bước, trong CÙNG một context.

Đối số `$ARGUMENTS` = đường dẫn CV (PDF/DOCX/text) hoặc tên profile đã có trong `data/profiles/`.

Dùng `<run-id>` = ngày hiện tại (YYYY-MM-DD). Tạo `data/profiles`, `data/jobs`, `data/results` nếu chưa có.

Đọc `AGENTS.md` để biết nguyên tắc chung và các reference doc. Toàn bộ logic chi tiết nằm trong `codex/reference/`.

## Bước 1 — Intake → profile.json
Theo `codex/reference/candidate-intake.md`.
- Nếu `$ARGUMENTS` là file CV → parse (pdftotext/python-docx/đọc text) và tạo `data/profiles/<slug>.json` theo `schemas/profile.schema.json`.
- Nếu là tên profile đã tồn tại → dùng lại, hỏi có cập nhật target không.
- Thu thập/xác nhận target: vai trò, cấp bậc, địa điểm/remote, lương, priorities (→ trọng số), dealbreakers.
- **Tóm tắt cho người dùng xác nhận trước khi sang bước 2.**

## Bước 2 — Collect jobs → data/jobs/<run-id>.json
Theo `codex/reference/job-collector.md`.
- Search + fetch bằng tool `web_search` (giữ nguyên cơ chế Search Engine + scraping, không cần API key). Cần bật web search (`codex --search` hoặc `tools.web_search=true`).
- **Chỉ giữ job xem được full JD VÀ còn hạn** (bỏ snippet-only, 404/410, hết hạn). Tối đa 20 job hợp lệ.

## Bước 3 — Match → data/results/<run-id>.shortlist.json
Theo `codex/reference/job-matcher.md` + `codex/reference/scoring-rubric.md`.
- Chấm điểm 6 chiều, dùng trọng số từ `target.priorities` (chuẩn hóa tổng = 1).
- Xếp hạng giảm dần; excluded xuống cuối.

## Bước 4 — Fit report → data/results/<run-id>.fit_report.md
Theo `codex/reference/fit-analyzer.md`.
- Bảng xếp hạng: **mọi job đều có link nộp CV (url) bấm được**; phân tích chi tiết top 20 (hoặc toàn bộ).
- Báo đường dẫn file báo cáo cho người dùng.

## Sau khi xong
Đề xuất bước tiếp: tailor hồ sơ cho job top (`codex/reference/application-assistant.md`), hoặc mở rộng nguồn (remote quốc tế / thành phố khác).

## Nguyên tắc
- Không bịa dữ liệu job/CV. Thiếu → unknown, hạ confidence.
- Tôn trọng robots/ToS khi scrape; không vượt anti-bot/CAPTCHA.
- Không tự nộp hồ sơ thay người dùng.
