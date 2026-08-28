---
name: find-jobs
description: Chạy full pipeline tìm việc song ngữ Việt–Anh — parse CV, thu thập job (web search), chấm điểm, xuất báo cáo fit/gap. Dùng khi người dùng muốn "tìm job cho tôi" từ một CV hoặc profile đã có.
---

# find-jobs — điều phối full pipeline tìm việc

Skill điều phối, chạy tuần tự 4 bước. Đối số là đường dẫn CV (PDF/DOCX/text) hoặc tên
profile đã có trong `data/profiles/`.

Dùng `<run-id>` = ngày hiện tại (YYYY-MM-DD). Tạo `data/profiles`, `data/jobs`,
`data/results` trong thư mục làm việc nếu chưa có.

> **Yêu cầu (bước 2 — thu thập job):**
> - **Claude Code**: `WebSearch`/`WebFetch` có sẵn — không cần cấu hình.
> - **Codex**: cần bật `web_search` bằng `codex --search` hoặc `tools.web_search = true` trong `~/.codex/config.toml`. Nếu chưa bật, dừng ở bước 2 và báo người dùng.

## Bước 1 — Intake → profile.json
Áp skill **`candidate-intake`**.
- Nếu đối số là file CV → parse và tạo `data/profiles/<slug>.json` theo `schemas/profile.schema.json`.
- Nếu là tên profile đã tồn tại → dùng lại, hỏi có cập nhật target không.
- Thu thập/xác nhận target: vai trò, cấp bậc, địa điểm/remote, lương, priorities (→ trọng số), dealbreakers.
- Tóm tắt cho người dùng xác nhận.
- **Tùy chọn nguồn Facebook (Minh bạch & Động)**:
  - Hỏi người dùng: *"Bạn có muốn quét thêm tin tuyển dụng từ các Hội nhóm Facebook không?"*
  - *(Cảnh báo minh bạch: Nếu chọn Có và chưa có session, trình duyệt sẽ tự động mở lên để bạn đăng nhập Facebook lấy cookie session — được lưu bảo mật cục bộ tại `data/.auth/`, không bao giờ commit lên Git).*
  - **Nếu người dùng chọn CÓ**: Yêu cầu người dùng **gửi danh sách link các Group Facebook công khai** mà họ muốn quét (ví dụ: `https://facebook.com/groups/pythonvietnam`, `https://facebook.com/groups/1407434203194440`...).
  - Agent tự động ghi danh sách link này vào `data/config/facebook_groups.json`.

## Bước 2 — Collect → data/jobs/<run-id>.json
Spawn subagent **`job-collector`** (context riêng, tốn nhiều lượt search/fetch).
- Truyền đường dẫn `profile.json` và output `data/jobs/<run-id>.json`.
- **Nguồn Job Boards**: Luôn quét từ ITviec, TopCV, VietnamWorks, LinkedIn...
- **Nguồn Facebook Groups (Nếu người dùng đồng ý & cung cấp link ở Bước 1)**: Gọi tool MCP local `run_facebook_crawler` của server `facebook_crawler`; truyền `workspace_root` tuyệt đối, profile, config, groups và queries. Đọc file JSON tại `output_path` tool trả về. Không chạy Python/Playwright trực tiếp trong sandbox và không fallback sang shell nếu MCP lỗi.
- Giữ job thỏa mãn tiêu chuẩn: Job board cần full JD; Facebook post chỉ cần Title + Vị trí/Tech stack + Kênh liên hệ/Link bài viết. Tối đa 20 job hợp lệ.

## Bước 3 — Match → data/results/<run-id>.shortlist.json
Spawn subagent **`job-matcher`** (context riêng, chấm điểm bulk).
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
