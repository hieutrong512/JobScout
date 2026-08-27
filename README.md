# JobMatching — Codex plugin

Plugin cho **OpenAI Codex CLI**: tìm và xếp hạng các job phù hợp nhất với **target** và
**CV** của ứng viên. Song ngữ Việt–Anh, lấy dữ liệu job qua **Search Engine + web scraping**
(tool `web_search` của Codex — không cần API key).

## Cài đặt

Plugin dùng manifest chuẩn tại `.codex-plugin/plugin.json`. Khi phát triển local, đăng ký thư mục
plugin vào personal marketplace bằng skill `$plugin-creator`, sau đó cài từ Codex Plugins Directory.
Marketplace giữ chính sách cài đặt (`AVAILABLE`/`INSTALLED_BY_DEFAULT`); chính sách này không nằm
trong manifest plugin.

Sau khi cập nhật plugin, tăng cachebuster bằng helper của `$plugin-creator`, cài lại plugin và mở
một task mới để Codex nạp lại skills/MCP tools.

Bật web search (bắt buộc cho bước thu thập job) — chọn một:

```bash
codex --search
```

hoặc thêm vào `~/.codex/config.toml`:

```toml
[tools]
web_search = true
```

Nguồn Facebook chạy qua MCP server local đi kèm plugin. Máy cần Python 3.9+ và Playwright Chromium:

```bash
pip install playwright
playwright install chromium
```

Nếu Playwright nằm trong một Python riêng, đặt `JOB_MATCHING_PYTHON` thành đường dẫn tuyệt đối tới `python.exe` đó trước khi mở Codex.

## Cách dùng

Chạy full pipeline — kích hoạt skill `find-jobs`:

> "tìm job cho tôi từ CV `D:\path\CV.pdf`"

Hoặc gọi từng phần bằng ngôn ngữ tự nhiên (skill/agent tự kích hoạt theo mô tả):
"parse CV này", "thu thập job", "chấm điểm các job", "làm báo cáo fit", "tailor CV cho job này".

## Pipeline

```
CV + Target
   │  [1] candidate-intake (skill)   → data/profiles/<slug>.json (kèm hỏi người dùng bật nguồn Facebook)
   ▼
   │  [2] job-collector (agent)      → data/jobs/<run-id>.json   (Job boards + Tùy chọn: In-Group Facebook Crawler, tối đa 20)
   ▼
   │  [3] job-matcher (agent)        → data/results/<run-id>.shortlist.json
   ▼
   │  [4] fit-analyzer (skill)       → data/results/<run-id>.fit_report.md
   ▼
   [5] application-assistant (skill, tùy chọn) → CV bullets / cover letter / tin nhắn tiếp cận HR (Zalo/FB)
```

## Cấu trúc plugin

| Đường dẫn | Vai trò |
|---|---|
| `.codex-plugin/plugin.json` | Manifest Codex duy nhất — khai báo skills + MCP server |
| `.mcp.json` | Khai báo local MCP server `facebook_crawler` |
| `skills/find-jobs/` | Skill điều phối full pipeline (hỏi bật nguồn Facebook minh bạch) |
| `skills/candidate-intake/` | Parse CV + hỏi target → profile.json |
| `skills/fb-crawler/` | Skill cào Facebook Groups In-Group Search qua Playwright |
| `skills/scoring-rubric/` | Công thức tính điểm khớp (nền tảng) |
| `skills/job-schema/` | Cách điền `schemas/job.schema.json` (kèm contact & FB posts) |
| `skills/bilingual-normalization/` | Chuẩn hóa skill/chức danh/lương Việt–Anh & văn phong MXH |
| `skills/fit-analyzer/` | Giải thích fit + gap → fit_report.md |
| `skills/application-assistant/` | Tailor CV / cover letter / mẫu tin nhắn HR (Zalo/FB) |
| `agents/job-collector.toml` | Subagent: search + scrape JD từ Web (và FB Groups nếu được bật) → jobs.json |
| `agents/job-matcher.toml` | Subagent: chấm điểm & rank → shortlist.json |
| `scripts/fb_crawler.py` | Script Playwright In-Group Search & Profile Target Filter |
| `mcp/facebook_crawler_server.py` | Tool local chạy crawler ngoài sandbox và trả đường dẫn JSON |
| `schemas/*.json` | Data contracts: profile / job / match |
| `data/{profiles,jobs,results}/` | Dữ liệu chạy (gitignore dữ liệu nhạy cảm) |

## Kiểm tra trước khi phát hành

```bash
python -m unittest discover -s tests -v
python -m compileall -q -f scripts mcp tests
python <plugin-creator>/scripts/validate_plugin.py <plugin-root>
```

Không commit `data/`, session Facebook, CV gốc, log hay `__pycache__`.

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ Ứng viên override được qua `target.priorities` trong profile.

## Ghi chú vận hành

- **Tiêu chuẩn thu thập theo nguồn**:
  - *Job boards truyền thống* (ITviec, TopCV, VietnamWorks, LinkedIn): Luôn được quét chính thống, chỉ giữ job xem được full JD và còn hạn.
  - *Hội nhóm Facebook (Tùy chọn)*: Quét qua In-Group Search trực tiếp với từ khóa chuyên môn. Cần người dùng xác nhận bật và đăng nhập lấy session cookie (lưu bảo mật tại `data/.auth/`).
- Giữ nguyên đơn vị lương gốc theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; không vượt anti-bot/CAPTCHA; không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
