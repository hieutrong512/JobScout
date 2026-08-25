# JobMatching — Codex plugin

Repo này **là một Codex plugin** (`plugin.json` ở gốc): tìm và xếp hạng job phù hợp nhất
với **target** và **CV** của ứng viên, song ngữ Việt–Anh. Lấy dữ liệu job qua
**Search Engine + web scraping** (tool `web_search` của Codex — không cần API key).

## Thành phần plugin

- **Skills** (`skills/*/SKILL.md`): `find-jobs` (điều phối full pipeline), `candidate-intake`,
  `scoring-rubric`, `job-schema`, `bilingual-normalization`, `fit-analyzer`, `application-assistant`.
- **Agents** (`agents/*.toml`): `job-collector`, `job-matcher` — subagent chạy context riêng
  cho các bước tốn token (search/scrape, chấm điểm bulk).
- **Schemas** (`schemas/*.json`): data contracts profile / job / match.

## Bật web search (bắt buộc cho bước thu thập job)

Bước collect cần tool `web_search`. Bật một trong hai:
- `codex --search`
- hoặc trong `~/.codex/config.toml`:
  ```toml
  [tools]
  web_search = true
  ```

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

`<run-id>` = ngày hiện tại (YYYY-MM-DD). Dữ liệu chạy ghi vào `data/` trong thư mục làm việc.

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ override qua `target.priorities` trong profile (chuẩn hóa tổng = 1).

## Nguyên tắc vận hành (bắt buộc)

- **Chỉ thu thập job xem được full JD và còn hạn**; snippet-only / hết hạn / 404-410 → bỏ.
- **Không bịa** trường dữ liệu job/CV. Thiếu → `unknown`, hạ `confidence` (không chấm 0 mù quáng).
- Giữ nguyên **đơn vị lương gốc** theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; **không vượt anti-bot/CAPTCHA**.
- **Không tự nộp hồ sơ / gửi email** thay người dùng.
