# JobMatching

Plugin **dùng được ở CẢ Claude Code lẫn Codex** (dual-manifest) giúp tìm và xếp hạng các job phù hợp nhất với **target** và **CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua Search Engine + Web scraping (không cần API key) và tùy chọn cào Facebook Groups công khai.

- Plugin (nguồn chân lý duy nhất): [`job-matching-plugin/`](job-matching-plugin/) — chứa cả `.claude-plugin/` và `.codex-plugin/`, dùng chung `skills/`, `schemas/`, `scripts/`, `mcp/`.
- Marketplace Claude: [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
- Hướng dẫn: [`CLAUDE.md`](job-matching-plugin/CLAUDE.md) (Claude) · [`AGENTS.md`](job-matching-plugin/AGENTS.md) (Codex)

## Cài đặt

### Cách 1 — Tải package (.zip)

Build 1 file zip tải-về-là-dùng cho cả hai hệ:

```bash
powershell -ExecutionPolicy Bypass -File .\build-release.ps1   # Windows
```
```bash
bash build-release.sh                                          # macOS/Linux
```

Ra `dist/job-matching-v<version>.zip`. Giải nén rồi:
- **Claude Code**: `/plugin marketplace add <thư-mục-giải-nén>` → `/plugin install job-matching`
- **Codex**: trỏ plugin tới `<thư-mục-giải-nén>/job-matching-plugin` (đọc `.codex-plugin/plugin.json`). Bật web search: `codex --search` hoặc `tools.web_search = true`.

### Cách 2 — Từ git repo (Claude)

```bash
/plugin marketplace add <đường-dẫn-hoặc-git-repo-này>
/plugin install job-matching
```

Sau đó chạy full pipeline — Claude: `/find-jobs D:\path\to\CV.pdf` · Codex: gọi skill `find-jobs` với đường dẫn CV.

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
