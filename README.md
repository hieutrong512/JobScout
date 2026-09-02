# JobMatching

Trợ lý tìm và xếp hạng các job phù hợp nhất với **target** và **CV** của ứng viên, song ngữ Việt–Anh.
Lấy dữ liệu job qua Search Engine + Web scraping (**không cần API key**). Chạy được trên **3 nền tảng**
từ cùng một nguồn logic (skills + rubric + schema).

| Nền tảng | Cách dùng | Bắt đầu từ |
|---|---|---|
| **Claude Code** | Plugin (`.claude-plugin`) | [Cài đặt](#cài-đặt) bên dưới |
| **Codex CLI** | Plugin (`.codex-plugin`) | [Cài đặt](#cài-đặt) bên dưới |
| **ChatGPT** (Custom GPT / Project / chat) | Dán Instructions | [`chatgpt/README.md`](chatgpt/README.md) |

- Plugin (nguồn chân lý duy nhất): [`job-matching-plugin/`](job-matching-plugin/) — chứa cả `.claude-plugin/` và `.codex-plugin/`, dùng chung `skills/`, `schemas/`.
- Adapter ChatGPT: [`chatgpt/`](chatgpt/) — orchestrator dán-là-chạy, tự sinh bộ Knowledge từ plugin.
- Marketplace Claude: [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
- Hướng dẫn: [`claude-runtime-notes.md`](job-matching-plugin/docs/claude-runtime-notes.md) (Claude) · [`AGENTS.md`](job-matching-plugin/AGENTS.md) (Codex) · [`chatgpt/GPT-INSTRUCTIONS.md`](chatgpt/GPT-INSTRUCTIONS.md) (ChatGPT)

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

### Cách 3 — ChatGPT (Custom GPT / Project)

Không cần plugin. Tạo một Custom GPT, bật **Web Search**, dán [`chatgpt/GPT-INSTRUCTIONS.md`](chatgpt/GPT-INSTRUCTIONS.md) vào ô Instructions rồi dán CV là chạy. Muốn tăng độ chính xác thì upload thêm bộ Knowledge:

```bash
bash build-chatgpt.sh          # macOS/Linux
powershell -ExecutionPolicy Bypass -File .\build-chatgpt.ps1   # Windows
```

→ ra `dist/chatgpt-knowledge/` (các skill `*.md` + `*.schema.json`) để kéo-thả vào mục Knowledge. Chi tiết 3 cách (Custom GPT / Project / chat thường): [`chatgpt/README.md`](chatgpt/README.md).

## Pipeline

```
CV + Target
   │
   ▼
[1] candidate-intake (skill) ──► data/profiles/<candidate>.json
   │
   ▼
[2] job-collector (subagent) ──► data/jobs/<run-id>.json      (Job boards)
   │
   ▼
[3] job-matcher (subagent) ───► data/results/<run-id>.shortlist.json
   │
   ▼
[4] fit-analyzer (skill) ─────► data/results/<run-id>.fit_report.md
   │
   ▼
[5] application-assistant (skill, optional) ──► CV bullets / cover letter / tin nhắn tiếp cận HR
```

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `candidate-intake` | Skill | Parse CV + hỏi target → `profile.json` |
| `job-collector` | Subagent | Search + scrape JD từ Job boards → `jobs.json` |
| `job-matcher` | Subagent | Chấm điểm & rank → `shortlist.json` |
| `fit-analyzer` | Skill | Giải thích fit + gap → `fit_report.md` |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR |
| `scoring-rubric` | Skill | Công thức tính điểm khớp (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job (kèm contact) |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh |

## Data contracts

Mọi thành phần trao đổi qua JSON theo `job-matching-plugin/schemas/`:
- `profile.schema.json` — hồ sơ ứng viên (CV + target)
- `job.schema.json` — tin tuyển dụng đã chuẩn hóa (kèm contact info nếu JD có)
- `match.schema.json` — kết quả chấm điểm từng job

## Cách dùng (điển hình)

1. Đặt CV vào `data/profiles/` (hoặc dán nội dung), chạy intake để tạo `profile.json`.
2. Gọi `job-collector` với profile → thu thập job từ Web tuyển dụng.
3. Gọi `job-matcher` → nhận shortlist đã xếp hạng.
4. Chạy `fit-analyzer` trên top N để có báo cáo fit/gap.
5. (Tùy chọn) `application-assistant` để tailor hồ sơ hoặc soạn tin nhắn liên hệ HR.

## Lưu ý scraping

- Quét từ các trang tuyển dụng chính thống (ITviec, TopCV, VietnamWorks, LinkedIn...). Chỉ giữ job xem được full JD và còn hạn.
- Tôn trọng robots.txt và ToS; không vượt qua anti-bot/CAPTCHA; không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
