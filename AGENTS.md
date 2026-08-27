# JobMatching — Codex plugin

Repo này **là một Codex plugin** (`.codex-plugin/plugin.json` là manifest chuẩn): tìm và xếp hạng job phù hợp nhất
với **target** và **CV** của ứng viên, song ngữ Việt–Anh. Lấy dữ liệu job qua
**Search Engine + web scraping** (tool `web_search` của Codex — không cần API key).

## Thành phần plugin

- **Skills** (`skills/*/SKILL.md`): `find-jobs` (điều phối full pipeline), `candidate-intake`,
  `scoring-rubric`, `job-schema`, `bilingual-normalization`, `fit-analyzer`, `application-assistant`, `fb-crawler`.
- **Agents** (`agents/*.toml`): `job-collector`, `job-matcher` — subagent chạy context riêng
  cho các bước tốn token (search/scrape, chấm điểm bulk).
- **Schemas** (`schemas/*.json`): data contracts profile / job / match.

## Bật web search & Playwright

1. Bước collect cần tool `web_search`. Bật một trong hai:
   - `codex --search`
   - hoặc trong `~/.codex/config.toml`: `tools.web_search = true`
2. Bước cào Facebook Groups dùng Playwright:
   - `pip install playwright && playwright install chromium`

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

`<run-id>` = ngày hiện tại (YYYY-MM-DD). Dữ liệu chạy ghi vào `data/` trong thư mục làm việc.

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ override qua `target.priorities` trong profile (chuẩn hóa tổng = 1).

## Nguyên tắc vận hành (bắt buộc)

- **Tiêu chuẩn thu thập theo nguồn**:
  - *Job boards truyền thống* (ITviec, TopCV, VietnamWorks, LinkedIn): Chỉ giữ job xem được full JD và còn hạn; snippet-only / hết hạn / 404-410 → bỏ.
  - *Hội nhóm Facebook công khai*: Do HR thường đăng bài ngắn câu tương tác (inbox/Zalo lấy JD), chỉ cần có **Title + Vị trí/Địa điểm + Kênh liên hệ/Link bài post** (không bắt buộc có link full JD ngoài).
- **Không bịa** trường dữ liệu job/CV. Thiếu → `unknown`, hạ `confidence` (không chấm 0 mù quáng).
- Giữ nguyên **đơn vị lương gốc** theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; **không vượt anti-bot/CAPTCHA**.
- **Không tự nộp hồ sơ / gửi email / gửi tin nhắn** thay người dùng.

