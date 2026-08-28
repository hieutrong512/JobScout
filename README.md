# JobMatching

**Claude Code plugin marketplace** giúp tìm và xếp hạng các job phù hợp nhất với **target** và **CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua Search Engine + Web scraping (không cần API key) và tùy chọn cào Facebook Groups công khai.

- Marketplace: [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
- Plugin (nguồn chân lý): [`job-matching-plugin/`](job-matching-plugin/) — xem [README plugin](job-matching-plugin/README.md)
- Hướng dẫn cho người phát triển repo: [`CLAUDE.md`](CLAUDE.md)

## Cài đặt nhanh

```bash
/plugin marketplace add <đường-dẫn-hoặc-git-repo-này>
```

```bash
/plugin install job-matching
```

Sau đó chạy full pipeline: `/find-jobs D:\path\to\CV.pdf`

## Pipeline

```
CV + Target
   │
   ▼
[1] candidate-intake (skill) ──► data/profiles/<candidate>.json
   │
   ▼ (Hỏi xác nhận người dùng nếu muốn bật nguồn Facebook)
[2] job-collector (subagent) ──► data/jobs/<run-id>.json      (Job boards + Tùy chọn: Facebook Groups Crawler)
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
| `job-collector` | Subagent | Search + scrape JD từ Job boards (và FB Groups nếu được bật) → `jobs.json` |
| `job-matcher` | Subagent | Chấm điểm & rank → `shortlist.json` |
| `fit-analyzer` | Skill | Giải thích fit + gap → `fit_report.md` |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR (Zalo/FB) |
| `scoring-rubric` | Skill | Công thức tính điểm khớp (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job (kèm contact & FB posts) |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh & văn phong MXH |

## Data contracts

Mọi thành phần trao đổi qua JSON theo `job-matching-plugin/schemas/`:
- `profile.schema.json` — hồ sơ ứng viên (CV + target)
- `job.schema.json` — tin tuyển dụng đã chuẩn hóa (kèm contact info)
- `match.schema.json` — kết quả chấm điểm từng job

## Cách dùng (điển hình)

1. Đặt CV vào `data/profiles/` (hoặc dán nội dung), chạy intake để tạo `profile.json`.
2. Gọi `job-collector` với profile → thu thập job từ Web tuyển dụng (và hỏi người dùng nếu muốn quét thêm Facebook Groups qua script có đăng nhập tương tác).
3. Gọi `job-matcher` → nhận shortlist đã xếp hạng.
4. Chạy `fit-analyzer` trên top N để có báo cáo fit/gap.
5. (Tùy chọn) `application-assistant` để tailor hồ sơ hoặc soạn tin nhắn liên hệ HR qua Zalo/FB.

## Lưu ý scraping & thu thập theo nguồn

- **Job boards truyền thống**: Luôn được quét từ các trang chính thống (ITviec, TopCV, VietnamWorks, LinkedIn...). Phải xem được full JD và còn hạn.
- **Hội nhóm Facebook (Tùy chọn)**: Quét qua In-Group Search trực tiếp với từ khóa chuyên môn. Cần người dùng xác nhận bật và đăng nhập lấy session cookie (lưu bảo mật tại `data/.auth/`).
- Tôn trọng robots.txt và ToS; không vượt qua anti-bot/CAPTCHA; không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
