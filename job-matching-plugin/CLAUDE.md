# JobMatching — plugin dual-manifest (Claude Code + Codex)

Thư mục `job-matching-plugin/` **là một plugin dùng được ở CẢ Claude Code lẫn Codex**: tìm và xếp
hạng job phù hợp nhất với **target** và **CV** của ứng viên, song ngữ Việt–Anh. Lấy dữ liệu job qua
**Search Engine + web scraping** (tool `WebSearch`/`WebFetch` trên Claude, `web_search` trên Codex —
không cần API key) và tùy chọn **In-Group Facebook Crawler** chạy cục bộ qua Playwright.

## Bố cục repo

- `.claude-plugin/marketplace.json` (gốc repo) — marketplace Claude, trỏ tới plugin `./job-matching-plugin`.
- `job-matching-plugin/` — **nguồn chân lý duy nhất** của plugin (dùng chung cho cả hai hệ):
  - `.claude-plugin/plugin.json` — manifest Claude (khai báo `mcpServers: ./.mcp.json`).
  - `.codex-plugin/plugin.json` — manifest Codex (khai báo `skills` + `mcpServers: ./.codex-plugin/mcp.json`).
  - `.mcp.json` — MCP server `facebook_crawler` cho Claude (python + `${CLAUDE_PLUGIN_ROOT}`).
  - `.codex-plugin/mcp.json` — MCP server `facebook_crawler` cho Codex (launcher `scripts/launch_facebook_crawler_mcp.cmd`).
  - `CLAUDE.md` / `AGENTS.md` — hướng dẫn cho Claude / Codex.
  - `commands/find-jobs.md` — slash command `/find-jobs` (Claude). Trên Codex dùng `skills/find-jobs/SKILL.md`.
  - `skills/*/SKILL.md` — dùng chung: `find-jobs`, `candidate-intake`, `scoring-rubric`, `job-schema`,
    `bilingual-normalization`, `fit-analyzer`, `application-assistant`, `fb-crawler`.
  - `agents/*.md` (Claude) **và** `agents/*.toml` (Codex) — subagent `job-collector`, `job-matcher`.
  - `schemas/*.json` — data contracts profile / job / match.
  - `scripts/fb_crawler.py` — script Playwright In-Group Search & Profile Target Filter.
  - `scripts/launch_facebook_crawler_mcp.cmd` — launcher MCP cho Codex (Windows).
  - `mcp/facebook_crawler_server.py` — stdio MCP server (stdlib-only) bọc crawler thành tool `run_facebook_crawler`.
  - `tests/*.py` — unit test cho crawler logic, MCP server và tính toàn vẹn plugin.
- `data/` — dữ liệu chạy trong thư mục làm việc (được gitignore phần nhạy cảm).

> Không tạo bản sao skill/agent thứ hai ở gốc repo. Skill dùng chung viết trung lập tên tool
> (`WebSearch`/`WebFetch` cho Claude, `web_search` cho Codex) để một nguồn phục vụ cả hai hệ.

## Bật web search & Playwright

1. `WebSearch` / `WebFetch` là tool sẵn có của Claude Code — không cần cấu hình thêm.
2. Nguồn Facebook (tùy chọn) dùng Playwright:
   ```bash
   pip install playwright && playwright install chromium
   ```

## Pipeline

```
CV + Target
   │  [1] candidate-intake (skill)   → data/profiles/<slug>.json (kèm hỏi người dùng bật nguồn Facebook)
   ▼
   │  [2] job-collector (subagent)   → data/jobs/<run-id>.json   (Job boards + Tùy chọn: In-Group Facebook Crawler, tối đa 20)
   ▼
   │  [3] job-matcher (subagent)     → data/results/<run-id>.shortlist.json
   ▼
   │  [4] fit-analyzer (skill)       → data/results/<run-id>.fit_report.md
   ▼
   [5] application-assistant (skill, tùy chọn) → CV bullets / cover letter / tin nhắn tiếp cận HR (Zalo/FB)
```

`<run-id>` = ngày hiện tại (YYYY-MM-DD). Dữ liệu chạy ghi vào `data/` trong thư mục làm việc.

## Facebook crawler chạy thế nào

Nguồn Facebook là **MCP tool `run_facebook_crawler`** (server `facebook_crawler` trong `.mcp.json`).
Đây là một tool riêng để model **không thể tự thay bằng WebSearch** — WebSearch không đọc được feed
trong group. Tool bọc `scripts/fb_crawler.py`, tự lo đăng nhập & chờ tới khi xong, trả `output_path`.

- Server (`mcp/facebook_crawler_server.py`) chỉ dùng thư viện chuẩn nên khởi động dưới bất kỳ Python
  nào. Nó chạy crawler subprocess bằng interpreter `JOB_MATCHING_PYTHON` (nếu đặt) hoặc `sys.executable`
  — **Python đó phải có Playwright**. `.mcp.json` mặc định gọi `python`; nếu `python` mặc định thiếu
  Playwright, đặt `JOB_MATCHING_PYTHON` trỏ tới python có Playwright.
- `workspace_root` bỏ trống → dùng thư mục làm việc hiện tại nên `data/` đọc/ghi trong project của
  người dùng, không phải thư mục cài plugin.
- Lần đầu (chưa có session) crawler tự mở Chromium headed để người dùng đăng nhập; session lưu tại
  `data/.auth/facebook_state.json` (đã gitignore). **Claude không tự nhập mật khẩu Facebook.**
- **Chỉ đăng nhập được ở máy local có màn hình.** Cloud container / headless (không có `DISPLAY`) sẽ
  dừng sớm với `NoDisplayError`. Cách dùng Facebook từ cloud: đăng nhập một lần ở local để tạo
  `data/.auth/facebook_state.json`, copy sang cloud rồi chạy `--headless` (session gắn IP/thiết bị —
  có thể bị Facebook chặn khi dùng từ IP lạ). Không có session → bỏ Facebook, chỉ dùng job boards.

Fallback chẩn đoán khi MCP tool không khả dụng — chạy trực tiếp qua Bash:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/fb_crawler.py" --profile data/profiles/<slug>.json
```

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ override qua `target.priorities` trong profile (chuẩn hóa tổng = 1).

## Kiểm tra trước khi phát hành

```bash
cd job-matching-plugin
python -m unittest discover -s tests -v
python -m compileall -q -f scripts mcp tests
```

Không commit `data/profiles`, `data/jobs`, `data/results`, session Facebook (`data/.auth/`),
CV gốc (`*.pdf`/`*.docx`), log hay `__pycache__`.

## Nguyên tắc vận hành (bắt buộc)

- **Tiêu chuẩn thu thập theo nguồn**:
  - *Job boards truyền thống* (ITviec, TopCV, VietnamWorks, LinkedIn): Chỉ giữ job xem được full JD
    và còn hạn; snippet-only / hết hạn / 404-410 → bỏ.
  - *Hội nhóm Facebook công khai*: HR thường đăng bài ngắn (inbox/Zalo lấy JD), chỉ cần có
    **Title + Vị trí/Địa điểm + Kênh liên hệ/Link bài post**.
- **Không bịa** trường dữ liệu job/CV. Thiếu → `unknown`, hạ `confidence` (không chấm 0 mù quáng).
- Giữ nguyên **đơn vị lương gốc** theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; **không vượt anti-bot/CAPTCHA**.
- **Không tự nộp hồ sơ / gửi email / gửi tin nhắn** thay người dùng.
