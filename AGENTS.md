# JobMatching — hướng dẫn cho Codex

Bộ công cụ (chạy trên **OpenAI Codex CLI**) giúp tìm và xếp hạng job phù hợp nhất với
**target** và **CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua
**Search Engine + web scraping** (tool `web_search` của Codex, không cần API key).

## Cách chạy

- **Full pipeline:** slash command `/find-jobs <đường-dẫn-CV | tên-profile>`
  (định nghĩa ở `codex/prompts/find-jobs.md`; cài đặt: xem README).
- **Ngôn ngữ tự nhiên:** "tìm job cho tôi từ CV này", "chấm điểm lại các job", "làm báo cáo fit".
  Khi đó tự chạy các phase tương ứng theo `codex/reference/`.

## Bật web search (bắt buộc cho bước thu thập job)

Bước collect job cần tool `web_search`. Bật một trong hai:
- Chạy Codex với cờ: `codex --search`
- Hoặc đặt trong `~/.codex/config.toml`:
  ```toml
  [tools]
  web_search = true
  ```
Nếu chưa bật, dừng ở bước 2 và báo người dùng bật trước.

## Pipeline (Codex không có subagent → chạy tuần tự trong 1 context)

```
CV + Target
   │  [1] intake            → data/profiles/<slug>.json
   ▼
   │  [2] collect (web_search) → data/jobs/<run-id>.json   (chỉ job xem được full JD & còn hạn, tối đa 20)
   ▼
   │  [3] match (scoring)   → data/results/<run-id>.shortlist.json
   ▼
   │  [4] fit report        → data/results/<run-id>.fit_report.md
   ▼
   [5] application-assistant (tùy chọn) → CV bullets / cover letter
```

`<run-id>` = ngày hiện tại (YYYY-MM-DD).

## Reference docs (logic chi tiết — đọc khi chạy từng bước)

| File | Vai trò |
|---|---|
| `codex/reference/candidate-intake.md` | Parse CV + hỏi target → profile.json |
| `codex/reference/job-collector.md` | Search + scrape JD → jobs.json (bộ lọc "xem được & còn hạn") |
| `codex/reference/job-matcher.md` | Chấm điểm & rank → shortlist.json |
| `codex/reference/scoring-rubric.md` | Công thức tính điểm khớp (nền tảng) |
| `codex/reference/fit-analyzer.md` | Giải thích fit + gap → fit_report.md |
| `codex/reference/bilingual-normalization.md` | Chuẩn hóa skill/chức danh/lương Việt–Anh |
| `codex/reference/job-schema.md` | Cách điền `schemas/job.schema.json` |
| `codex/reference/application-assistant.md` | Tailor CV / cover letter (tùy chọn) |

## Data contracts (JSON theo `schemas/`)

- `schemas/profile.schema.json` — hồ sơ ứng viên (CV + target)
- `schemas/job.schema.json` — tin tuyển dụng đã chuẩn hóa
- `schemas/match.schema.json` — kết quả chấm điểm từng job

Dữ liệu chạy nằm trong `data/profiles`, `data/jobs`, `data/results` (không commit dữ liệu nhạy cảm).

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ Ứng viên override được qua `target.priorities` trong profile (chuẩn hóa tổng = 1).

## Nguyên tắc vận hành (bắt buộc)

- **Chỉ thu thập job xem được full JD và còn hạn ứng tuyển**; job snippet-only / hết hạn / 404-410 → bỏ.
- **Không bịa** trường dữ liệu job/CV. Thiếu → `unknown`, hạ `confidence` (không chấm 0 mù quáng).
- Giữ nguyên **đơn vị lương gốc** theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; **không vượt anti-bot/CAPTCHA**.
- **Không tự nộp hồ sơ / gửi email** thay người dùng.
