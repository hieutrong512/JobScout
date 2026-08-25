# JobMatching (Codex edition)

Bộ công cụ cho **OpenAI Codex CLI** giúp tìm và xếp hạng các job phù hợp nhất với
**target** và **CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua
**Search Engine + web scraping** (tool `web_search` của Codex — không cần API key).

> Trước đây repo là plugin Claude Code (skills + subagents). Bản này đã port sang Codex:
> Codex không có subagent/skill tự-kích-hoạt, nên toàn bộ logic gộp thành **một luồng
> tuần tự** điều khiển bởi `AGENTS.md` + reference docs, chạy qua lệnh `/find-jobs`.

## Cài đặt

Codex tự nạp `AGENTS.md` ở gốc repo → chỉ cần mở Codex trong thư mục này là dùng được
bằng ngôn ngữ tự nhiên. Để có slash command `/find-jobs`, copy prompt vào `~/.codex/prompts/`:

**Windows (PowerShell):**
```bash
Copy-Item codex\prompts\find-jobs.md "$env:USERPROFILE\.codex\prompts\find-jobs.md"
```

**macOS/Linux:**
```bash
mkdir -p ~/.codex/prompts && cp codex/prompts/find-jobs.md ~/.codex/prompts/
```

Bật web search (bắt buộc cho bước thu thập job) — chọn một:
```bash
codex --search
```
hoặc thêm vào `~/.codex/config.toml`:
```toml
[tools]
web_search = true
```

## Cách dùng

Full pipeline:
```bash
/find-jobs D:\path\to\CV.pdf
```

Hoặc bằng ngôn ngữ tự nhiên (Codex đọc `AGENTS.md`): "parse CV này", "tìm job cho tôi",
"chấm điểm các job", "làm báo cáo fit".

## Pipeline

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

## Cấu trúc repo

| Đường dẫn | Vai trò |
|---|---|
| `AGENTS.md` | Playbook Codex tự nạp: pipeline, nguyên tắc, trỏ tới reference |
| `codex/prompts/find-jobs.md` | Lệnh `/find-jobs` — điều phối full pipeline |
| `codex/reference/*.md` | Logic chi tiết từng bước (intake, collector, matcher, scoring, fit, normalization, schema, application) |
| `schemas/*.json` | Data contracts: profile / job / match |
| `data/{profiles,jobs,results}/` | Dữ liệu chạy (không commit dữ liệu nhạy cảm) |

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ Ứng viên override được qua `target.priorities` trong profile.

## Ghi chú vận hành

- Chỉ thu thập job **xem được full JD và còn hạn ứng tuyển**; snippet-only / hết hạn / 404-410 bị bỏ.
- Giữ nguyên đơn vị lương gốc theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; không vượt anti-bot/CAPTCHA; không tự nộp hồ sơ thay người dùng.
