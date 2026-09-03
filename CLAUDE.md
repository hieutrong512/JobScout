# JobMatching — Claude Code plugin

Repo này **là một Claude Code plugin marketplace**: tìm và xếp hạng job phù hợp nhất với **target**
và **CV** của ứng viên, song ngữ Việt–Anh. Lấy dữ liệu job qua **Search Engine + web scraping**
(tool `WebSearch` / `WebFetch` của Claude Code — không cần API key).

## Bố cục repo

- `.claude-plugin/marketplace.json` — marketplace, trỏ tới plugin `./job-matching-plugin`.
- `job-matching-plugin/` — **nguồn chân lý duy nhất** của plugin:
  - `.claude-plugin/plugin.json` — manifest plugin.
  - `commands/find-jobs.md` — slash command `/find-jobs` điều phối full pipeline.
  - `skills/*/SKILL.md` — `candidate-intake`, `scoring-rubric`, `job-schema`,
    `bilingual-normalization`, `fit-analyzer`, `application-assistant`.
  - `agents/*.md` — subagent `job-collector`, `job-matcher` (chạy context riêng cho bước tốn token).
  - `schemas/*.json` — data contracts profile / job / match.
  - `tests/*.py` — unit test cho tính toàn vẹn plugin.
- `data/` — dữ liệu chạy trong thư mục làm việc (được gitignore phần nhạy cảm).

> Không tạo bản sao skill/agent thứ hai ở gốc repo. Trước đây từng có `.claude/`, `schemas/`,
> `scripts/` ở gốc bị trôi lệch (drift) so với plugin — đã gỡ bỏ để tránh hai nguồn.

## Bật web search

`WebSearch` / `WebFetch` là tool sẵn có của Claude Code — không cần cấu hình thêm.

## Pipeline

```
CV + Target
   │  [1] candidate-intake (skill)   → data/profiles/<slug>.json
   ▼
   │  [2] job-collector (subagent)   → data/jobs/<run-id>.json   (Job boards, tối đa 20)
   ▼
   │  [3] job-matcher (subagent)     → data/results/<run-id>.shortlist.json
   ▼
   │  [4] fit-analyzer (skill)       → data/results/<run-id>.fit_report.md
   ▼
   [5] application-assistant (skill, tùy chọn) → CV bullets / cover letter / tin nhắn tiếp cận HR
```

`<run-id>` = ngày hiện tại (YYYY-MM-DD). Dữ liệu chạy ghi vào `data/` trong thư mục làm việc.

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ override qua `target.priorities` trong profile (chuẩn hóa tổng = 1).

## Kiểm tra trước khi phát hành

```bash
cd job-matching-plugin
python -m unittest discover -s tests -v
python -m compileall -q -f tests
```

Không commit `data/profiles`, `data/jobs`, `data/results`, CV gốc (`*.pdf`/`*.docx`), log hay `__pycache__`.

## Nguyên tắc vận hành (bắt buộc)

- **Tiêu chuẩn thu thập**: Chỉ giữ job xem được full JD và còn hạn (ITviec, TopCV, VietnamWorks,
  LinkedIn...); snippet-only / hết hạn / 404-410 → bỏ.
- **Không bịa** trường dữ liệu job/CV. Thiếu → `unknown`, hạ `confidence` (không chấm 0 mù quáng).
- Giữ nguyên **đơn vị lương gốc** theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; **không vượt anti-bot/CAPTCHA**.
- **Không tự nộp hồ sơ / gửi email / gửi tin nhắn** thay người dùng.
