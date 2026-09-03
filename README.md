# JobMatching

AI tìm và xếp hạng việc làm phù hợp nhất với CV của bạn — song ngữ Việt–Anh, không cần API key.

Thu thập job thật từ ITviec, TopCV, VietnamWorks, LinkedIn… qua web search, chấm điểm 6 chiều
(skills · seniority · domain · compensation · location · culture), xuất báo cáo fit/gap chi tiết
với link apply cho từng job.

**Chạy được trên Claude Code và Codex CLI** — cùng một logic, một lệnh cài đặt.

## Cài đặt

```bash
npx jobscout setup
```

Hiện menu chọn nền tảng (Claude Code / Codex / All) ngay trên terminal — dùng ↑/↓ di chuyển,
`space` chọn, `enter` xác nhận. Cài xong sẽ hiển thị hướng dẫn bước tiếp theo. Hoặc chỉ định thẳng:

```bash
npx jobscout setup claude    # Claude Code
npx jobscout setup codex     # Codex CLI
npx jobscout setup all       # Tất cả
```

## Sau khi setup

### Claude Code

```
/plugin marketplace add .
/plugin install jobscout
/find-jobs path/to/CV.pdf
```

### Codex CLI

```bash
codex --search
# Gọi skill find-jobs với đường dẫn CV
```

## Pipeline

```
CV + Target
   ▼  [1] candidate-intake     Parse CV → profile.json
   ▼  [2] job-collector        Web search → tối đa 20 job hợp lệ
   ▼  [3] job-matcher          Chấm điểm 6 chiều → shortlist xếp hạng
   ▼  [4] fit-analyzer         Báo cáo fit/gap + link apply từng job
   ▼  [5] application-assistant (tùy chọn)  Tailor CV / cover letter / tin nhắn HR
```

## Trọng số chấm điểm

| Chiều | Mặc định | Ý nghĩa |
|---|---|---|
| skills | 35% | Khớp kỹ năng must-have / nice-to-have |
| seniority | 20% | Cấp bậc & năm kinh nghiệm |
| domain | 15% | Ngành / lĩnh vực |
| compensation | 15% | Lương so với kỳ vọng |
| location | 5% | Địa điểm & remote |
| culture | 5% | Quy mô / loại hình công ty |

Override bằng cách khai `priorities` khi được hỏi target (tổng tự chuẩn hóa về 1).

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `candidate-intake` | Skill | Parse CV + hỏi target → `profile.json` |
| `job-collector` | Subagent | Search + scrape JD từ job boards → `jobs.json` |
| `job-matcher` | Subagent | Chấm điểm & xếp hạng → `shortlist.json` |
| `fit-analyzer` | Skill | Báo cáo fit/gap chi tiết → `fit_report.md` |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR |
| `scoring-rubric` | Skill | Công thức tính điểm 6 chiều |
| `job-schema` | Skill | Schema chuẩn cho job + cách map dữ liệu thô |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh |

## Data contracts

JSON schema trong `job-matching-plugin/schemas/`:
- **`profile.schema.json`** — hồ sơ ứng viên (CV + target + priorities)
- **`job.schema.json`** — tin tuyển dụng chuẩn hóa (kèm contact nếu JD có)
- **`match.schema.json`** — kết quả chấm điểm (6 chiều + rationale)

## Cấu trúc repo

```
├── bin/cli.mjs                   ← CLI (npx jobscout setup)
├── job-matching-plugin/          ← nguồn chân lý duy nhất
│   ├── .claude-plugin/             Claude Code manifest
│   ├── .codex-plugin/              Codex CLI manifest
│   ├── skills/*/SKILL.md           Logic pipeline + rubric
│   ├── schemas/*.json              Data contracts
│   ├── agents/*.md                 Subagent definitions
│   └── commands/find-jobs.md       Slash command /find-jobs
└── package.json
```

## Lưu ý

- Quét từ các trang tuyển dụng chính thống. Chỉ giữ job xem được full JD và còn hạn.
- Tôn trọng robots.txt và ToS; không vượt qua anti-bot/CAPTCHA.
- Không bịa dữ liệu job/CV. Thiếu thông tin → `unknown` + hạ confidence.
- **Không tự nộp hồ sơ / gửi tin nhắn thay người dùng.**

## License

MIT
