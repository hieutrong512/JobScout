# JobMatching

AI tìm và xếp hạng việc làm phù hợp nhất với CV của bạn — song ngữ Việt–Anh, không cần API key.

Thu thập job thật từ ITviec, TopCV, VietnamWorks, LinkedIn… qua web search, chấm điểm 6 chiều
(skills · seniority · domain · compensation · location · culture), xuất báo cáo fit/gap chi tiết
với link apply cho từng job.

## Bắt đầu nhanh

### Claude Code

```bash
/plugin marketplace add https://github.com/hieutrong512/JobMatching
/plugin install job-matching
/find-jobs path/to/CV.pdf
```

### Codex CLI

```bash
# Trỏ plugin tới repo đã clone
codex --search   # bật web search
# Gọi skill find-jobs với đường dẫn CV
```

### ChatGPT

1. [Tải repo về](https://github.com/hieutrong512/JobMatching/archive/refs/heads/main.zip) và giải nén.
2. Vào [chatgpt.com/gpts/editor](https://chatgpt.com/gpts/editor) → **Create** → tab **Configure**:
   - **Name**: `JobMatching`
   - **Description**: "Tìm & xếp hạng việc làm phù hợp CV, song ngữ Việt–Anh"
   - **Instructions**: mở file `chatgpt/GPT-INSTRUCTIONS.md` từ thư mục vừa giải nén, copy toàn bộ nội dung dán vào
   - **Knowledge**: kéo-thả **tất cả** file trong `chatgpt/knowledge/` vào (skills + schemas, tăng độ chính xác)
   - **Capabilities**: bật **Web Search** (bắt buộc). Bật **Code Interpreter** nếu muốn tải báo cáo về (tùy chọn)
3. **Save** → **Publish** ("Anyone with a link" để chia sẻ, hoặc "Only me" để dùng riêng)
4. Mở GPT, dán CV vào là chạy.

> **Nâng cao**: Muốn tự build bộ Knowledge mới nhất từ source:
> ```bash
> bash build-chatgpt.sh          # macOS/Linux
> powershell -File build-chatgpt.ps1   # Windows
> ```
> → ra `dist/chatgpt-knowledge/` để upload.

## Pipeline

```
CV + Target
   │
   ▼  [1] candidate-intake     Parse CV → profile.json
   │
   ▼  [2] job-collector        Web search → tối đa 20 job hợp lệ
   │
   ▼  [3] job-matcher          Chấm điểm 6 chiều → shortlist xếp hạng
   │
   ▼  [4] fit-analyzer         Báo cáo fit/gap + link apply từng job
   │
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

Override trọng số bằng cách khai `priorities` khi được hỏi target (tổng tự chuẩn hóa về 1).

## Cấu trúc repo

```
├── job-matching-plugin/          ← nguồn chân lý duy nhất
│   ├── .claude-plugin/           Claude Code manifest
│   ├── .codex-plugin/            Codex CLI manifest
│   ├── skills/*/SKILL.md         Logic pipeline + rubric
│   ├── schemas/*.json            Data contracts (profile / job / match)
│   ├── agents/*.md               Subagent definitions (Claude)
│   └── commands/find-jobs.md     Slash command /find-jobs
│
├── chatgpt/                      ← adapter ChatGPT
│   ├── GPT-INSTRUCTIONS.md       Orchestrator dán vào Custom GPT
│   ├── knowledge/                Skills + schemas flatten sẵn để upload
│   └── README.md                 Hướng dẫn chi tiết
│
├── .claude-plugin/marketplace.json
├── build-release.sh / .ps1       Đóng gói plugin (.zip)
└── build-chatgpt.sh / .ps1       Build bộ Knowledge cho ChatGPT
```

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `candidate-intake` | Skill | Parse CV + hỏi target → `profile.json` |
| `job-collector` | Subagent | Search + scrape JD từ job boards → `jobs.json` |
| `job-matcher` | Subagent | Chấm điểm & xếp hạng → `shortlist.json` |
| `fit-analyzer` | Skill | Báo cáo fit/gap chi tiết → `fit_report.md` |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR |
| `scoring-rubric` | Skill | Công thức tính điểm 6 chiều (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job + cách map dữ liệu thô |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh |

## Data contracts

Mọi thành phần trao đổi qua JSON schema trong `job-matching-plugin/schemas/`:
- **`profile.schema.json`** — hồ sơ ứng viên (CV + target + priorities)
- **`job.schema.json`** — tin tuyển dụng đã chuẩn hóa (kèm contact nếu JD có)
- **`match.schema.json`** — kết quả chấm điểm từng job (6 chiều + rationale)

## Lưu ý

- Quét từ các trang tuyển dụng chính thống. Chỉ giữ job xem được full JD và còn hạn.
- Tôn trọng robots.txt và ToS; không vượt qua anti-bot/CAPTCHA.
- Không bịa dữ liệu job/CV. Thiếu thông tin → `unknown` + hạ confidence (không chấm 0 mù quáng).
- **Không tự nộp hồ sơ / gửi tin nhắn thay người dùng.**

## License

MIT
