# JobMatching

Bộ agent/skill (Claude Code) giúp tìm và xếp hạng các job phù hợp nhất với **target** và **CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua Search Engine + Web scraping (không cần API key).

## Pipeline

```
CV + Target
   │
   ▼
[1] candidate-intake (skill) ──► data/profiles/<candidate>.json
   │
   ▼
[2] job-collector (subagent) ──► data/jobs/<run-id>.json      (WebSearch + WebFetch/browser)
   │
   ▼
[3] job-matcher (subagent) ───► data/results/<run-id>.shortlist.json
   │
   ▼
[4] fit-analyzer (skill) ─────► data/results/<run-id>.fit_report.md
   │
   ▼
[5] application-assistant (skill, optional) ──► CV bullets / cover letter
```

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `candidate-intake` | Skill | Parse CV + hỏi target → `profile.json` |
| `job-collector` | Subagent | Search + scrape JD → `jobs.json` |
| `job-matcher` | Subagent | Chấm điểm & rank → `shortlist.json` |
| `fit-analyzer` | Skill | Giải thích fit + gap → `fit_report.md` |
| `application-assistant` | Skill | Tailor CV / cover letter |
| `scoring-rubric` | Skill | Công thức tính điểm khớp (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh |

## Data contracts

Mọi thành phần trao đổi qua JSON theo `schemas/`:
- `profile.schema.json` — hồ sơ ứng viên (CV + target)
- `job.schema.json` — tin tuyển dụng đã chuẩn hóa
- `match.schema.json` — kết quả chấm điểm từng job

## Cách dùng (điển hình)

1. Đặt CV vào `data/profiles/` (hoặc dán nội dung), chạy intake để tạo `profile.json`.
2. Gọi `job-collector` với profile → thu thập job.
3. Gọi `job-matcher` → nhận shortlist đã xếp hạng.
4. Chạy `fit-analyzer` trên top N để có báo cáo fit/gap.
5. (Tùy chọn) `application-assistant` để tailor hồ sơ cho job cụ thể.

## Lưu ý scraping

Ưu tiên `WebSearch` (lấy danh sách + snippet) → `WebFetch` (trang cho phép) → browser (`preview_start`/`navigate`, chỉ khi cần render JS). Tôn trọng robots.txt và ToS của từng trang; không vượt qua anti-bot/CAPTCHA.
