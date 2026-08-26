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
[2] job-collector (subagent) ──► data/jobs/<run-id>.json      (WebSearch: Job boards & FB Public Groups)
   │
   ▼
[3] job-matcher (subagent) ───► data/results/<run-id>.shortlist.json
   │
   ▼
[4] fit-analyzer (skill) ─────► data/results/<run-id>.fit_report.md
   │
   ▼
[5] application-assistant (skill, optional) ──► CV bullets / cover letter / tin nhắn tiếp cận HR (Zalo/FB)
```

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `candidate-intake` | Skill | Parse CV + hỏi target → `profile.json` |
| `job-collector` | Subagent | Search + scrape JD từ Job boards & FB Groups → `jobs.json` |
| `job-matcher` | Subagent | Chấm điểm & rank → `shortlist.json` |
| `fit-analyzer` | Skill | Giải thích fit + gap → `fit_report.md` |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR (Zalo/FB) |
| `scoring-rubric` | Skill | Công thức tính điểm khớp (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job (kèm contact & FB posts) |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh & văn phong MXH |

## Data contracts

Mọi thành phần trao đổi qua JSON theo `schemas/`:
- `profile.schema.json` — hồ sơ ứng viên (CV + target)
- `job.schema.json` — tin tuyển dụng đã chuẩn hóa (kèm contact info)
- `match.schema.json` — kết quả chấm điểm từng job

## Cách dùng (điển hình)

1. Đặt CV vào `data/profiles/` (hoặc dán nội dung), chạy intake để tạo `profile.json`.
2. Gọi `job-collector` với profile → thu thập job từ Web tuyển dụng & Facebook Groups.
3. Gọi `job-matcher` → nhận shortlist đã xếp hạng.
4. Chạy `fit-analyzer` trên top N để có báo cáo fit/gap.
5. (Tùy chọn) `application-assistant` để tailor hồ sơ hoặc soạn tin nhắn liên hệ HR qua Zalo/FB.

## Lưu ý scraping & thu thập theo nguồn

- **Job boards truyền thống**: Ưu tiên `WebSearch` (lấy danh sách) → `WebFetch` (lấy full JD). Phải xem được full JD và còn hạn.
- **Hội nhóm Facebook công khai**: Chấp nhận bài đăng ngắn/teaser có **Title + Vị trí/Địa điểm + Kênh liên hệ / Link bài post** (không bắt buộc có link full JD ngoài).
- Tôn trọng robots.txt và ToS; không vượt qua anti-bot/CAPTCHA; không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
