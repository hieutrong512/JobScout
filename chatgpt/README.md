# JobMatching cho ChatGPT

Cùng một logic pipeline + rubric chấm điểm như Claude Code / Codex, chạy bằng **web browsing**
sẵn có của ChatGPT — không cần cài plugin hay API key.

## Cách cài (Custom GPT — khuyên dùng)

1. [Tải repo về](https://github.com/hieutrong512/JobMatching/archive/refs/heads/main.zip) và giải nén.
2. Vào [chatgpt.com/gpts/editor](https://chatgpt.com/gpts/editor) → **Create** → tab **Configure**:
   - **Name**: `JobMatching`
   - **Description**: "Tìm & xếp hạng việc làm phù hợp CV, song ngữ Việt–Anh"
   - **Instructions**: mở [`GPT-INSTRUCTIONS.md`](GPT-INSTRUCTIONS.md), copy toàn bộ nội dung dán vào
   - **Knowledge**: kéo-thả **tất cả** file trong thư mục [`knowledge/`](knowledge/) vào
   - **Capabilities**: bật **Web Search** (bắt buộc). Bật **Code Interpreter** nếu muốn tải báo cáo (tùy chọn)
3. **Save** → **Publish** ("Anyone with a link" để chia sẻ, hoặc "Only me" để dùng riêng)
4. Mở GPT, dán CV vào là chạy.

## Cách khác

### ChatGPT Project

1. Tạo **Project** mới → dán [`GPT-INSTRUCTIONS.md`](GPT-INSTRUCTIONS.md) vào Instructions.
2. Kéo các file trong [`knowledge/`](knowledge/) vào **Files** của Project.
3. Bắt đầu chat, dán CV.

### Chat thường (nhanh, 1 lần)

Dán prompt này rồi dán CV ngay sau:

```
Đọc kỹ và tuân theo bộ chỉ dẫn JobMatching dưới đây cho toàn bộ cuộc trò chuyện.
Dùng công cụ tìm kiếm web để thu thập job thật (không bịa). CV của tôi ở cuối tin nhắn.

<<< dán toàn bộ nội dung GPT-INSTRUCTIONS.md vào đây >>>

--- CV ---
<<< dán CV >>>
```

## Nội dung thư mục

```
chatgpt/
├── GPT-INSTRUCTIONS.md     Orchestrator (~7.6k chars, vừa giới hạn 8k Instructions)
├── knowledge/               Bộ knowledge upload sẵn (skills + schemas flatten)
│   ├── skill-*.md           Từng skill chi tiết
│   └── *.schema.json        Data contracts
└── README.md                File này
```

## Build lại knowledge từ source (tùy chọn)

Thư mục `knowledge/` đã có sẵn trong repo. Nếu muốn build lại sau khi chỉnh skill:

```bash
bash build-chatgpt.sh          # macOS/Linux
powershell -File build-chatgpt.ps1   # Windows
```

→ ra `dist/chatgpt-knowledge/` (copy đè vào `chatgpt/knowledge/` nếu muốn commit).

## Khác biệt so với Claude Code / Codex

| | Claude Code / Codex | ChatGPT |
|---|---|---|
| Cài đặt | `/plugin marketplace add` | Tạo Custom GPT, upload knowledge |
| Web search | `WebSearch` / `web_search` | Web Search (browsing) |
| Lưu trữ | Ghi `data/*.json` ra ổ đĩa | JSON trong chat (hoặc Code Interpreter tạm) |
| Báo cáo | File `.md` trong `data/results/` | Markdown trong chat (hoặc file tải về) |

Logic pipeline, trọng số chấm điểm và data contract **giống hệt** — đều bắt nguồn từ
`job-matching-plugin/skills/` + `schemas/` (nguồn chân lý duy nhất).
