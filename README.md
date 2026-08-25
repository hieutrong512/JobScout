# JobMatching — Codex plugin

Plugin cho **OpenAI Codex CLI**: tìm và xếp hạng các job phù hợp nhất với **target** và
**CV** của ứng viên. Song ngữ Việt–Anh, lấy dữ liệu job qua **Search Engine + web scraping**
(tool `web_search` của Codex — không cần API key).

## Cài đặt

Plugin cài qua marketplace của Codex (v0.120.0+). Trỏ tới repo local hoặc git:

```bash
codex marketplace add D:\StartUp\JobMatching
```

Hoặc từ GitHub shorthand / git URL:

```bash
codex marketplace add <owner>/<repo>
```

Plugin có `install_policy = "AVAILABLE"` (opt-in) — sau khi add, bật nó trong Codex rồi dùng.

> Kiểm tra lệnh chính xác theo phiên bản Codex của bạn: `codex marketplace --help`.

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

Chạy full pipeline — kích hoạt skill `find-jobs`:

> "tìm job cho tôi từ CV `D:\path\CV.pdf`"

Hoặc gọi từng phần bằng ngôn ngữ tự nhiên (skill/agent tự kích hoạt theo mô tả):
"parse CV này", "thu thập job", "chấm điểm các job", "làm báo cáo fit", "tailor CV cho job này".

## Pipeline

```
CV + Target
   │  [1] candidate-intake (skill)   → data/profiles/<slug>.json
   ▼
   │  [2] job-collector (agent)      → data/jobs/<run-id>.json   (web_search; chỉ job xem được full JD & còn hạn, tối đa 20)
   ▼
   │  [3] job-matcher (agent)        → data/results/<run-id>.shortlist.json
   ▼
   │  [4] fit-analyzer (skill)       → data/results/<run-id>.fit_report.md
   ▼
   [5] application-assistant (skill, tùy chọn) → CV bullets / cover letter
```

## Cấu trúc plugin

| Đường dẫn | Vai trò |
|---|---|
| `plugin.json` | Manifest — khai báo skills + agents + install_policy |
| `skills/find-jobs/` | Skill điều phối full pipeline (một-lệnh) |
| `skills/candidate-intake/` | Parse CV + hỏi target → profile.json |
| `skills/scoring-rubric/` | Công thức tính điểm khớp (nền tảng) |
| `skills/job-schema/` | Cách điền `schemas/job.schema.json` |
| `skills/bilingual-normalization/` | Chuẩn hóa skill/chức danh/lương Việt–Anh |
| `skills/fit-analyzer/` | Giải thích fit + gap → fit_report.md |
| `skills/application-assistant/` | Tailor CV / cover letter (tùy chọn) |
| `agents/job-collector.toml` | Subagent: search + scrape JD → jobs.json |
| `agents/job-matcher.toml` | Subagent: chấm điểm & rank → shortlist.json |
| `schemas/*.json` | Data contracts: profile / job / match |
| `data/{profiles,jobs,results}/` | Dữ liệu chạy (gitignore dữ liệu nhạy cảm) |

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ Ứng viên override được qua `target.priorities` trong profile.

## Ghi chú vận hành

- Chỉ thu thập job **xem được full JD và còn hạn ứng tuyển**; snippet-only / hết hạn / 404-410 bị bỏ.
- Giữ nguyên đơn vị lương gốc theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; không vượt anti-bot/CAPTCHA; không tự nộp hồ sơ thay người dùng.
