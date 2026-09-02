# JobMatching cho ChatGPT

Adapter để dùng bộ skill JobMatching trên **ChatGPT** (không cần Claude Code / Codex).
Cùng một logic pipeline + rubric chấm điểm, chạy bằng **web browsing** sẵn có của ChatGPT.

File chính: [`GPT-INSTRUCTIONS.md`](GPT-INSTRUCTIONS.md) — orchestrator dán-là-chạy, tự chứa đủ
rubric nên hoạt động ngay cả khi không upload thêm file nào.

## Cách 1 — Custom GPT (khuyên dùng, chia sẻ link cho nhiều người)

1. Vào <https://chatgpt.com/gpts/editor> → **Create**.
2. Tab **Configure**:
   - **Name**: `JobMatching` · **Description**: "Tìm & xếp hạng việc làm phù hợp CV, song ngữ Việt–Anh".
   - **Instructions**: dán **toàn bộ** nội dung [`GPT-INSTRUCTIONS.md`](GPT-INSTRUCTIONS.md) (~7.6k ký tự, vừa giới hạn 8k).
   - **Capabilities**: bật **Web Search** (bắt buộc, để thu thập job). Bật **Code Interpreter** nếu muốn xuất file báo cáo tải về (tùy chọn).
3. *(Tùy chọn, tăng độ chính xác)* mục **Knowledge** → upload bộ file chi tiết. Tạo bộ này bằng:
   ```bash
   bash build-chatgpt.sh          # macOS/Linux
   powershell -File build-chatgpt.ps1   # Windows
   ```
   → ra thư mục `dist/chatgpt-knowledge/` gồm các skill `*.md` + `*.schema.json` (kéo-thả tất cả).
4. **Save** → **Publish** (Only me / Anyone with link). Xong — mở GPT, dán CV là chạy.

## Cách 2 — ChatGPT Project

1. Tạo **Project** mới.
2. **Instructions** của Project: dán [`GPT-INSTRUCTIONS.md`](GPT-INSTRUCTIONS.md).
3. *(Tùy chọn)* Kéo các file trong `dist/chatgpt-knowledge/` vào **Files** của Project.
4. Bắt đầu chat trong Project — nhớ đảm bảo tài khoản đang bật browsing.

## Cách 3 — Chat thường (nhanh, 1 lần)

Dán prompt bootstrap này rồi dán CV ngay sau:

```
Đọc kỹ và tuân theo bộ chỉ dẫn JobMatching dưới đây cho toàn bộ cuộc trò chuyện.
Dùng công cụ tìm kiếm web để thu thập job thật (không bịa). CV của tôi ở cuối tin nhắn.

<<< dán toàn bộ nội dung GPT-INSTRUCTIONS.md vào đây >>>

--- CV ---
<<< dán CV >>>
```

## Khác biệt so với Claude Code / Codex

| | Claude Code / Codex | ChatGPT |
|---|---|---|
| Cài đặt | Plugin manifest | Dán Instructions vào Custom GPT/Project |
| Web | `WebSearch`/`web_search` | Web Search (browsing) |
| Lưu trữ | Ghi `data/*.json` ra ổ đĩa | JSON trong hội thoại (hoặc Code Interpreter tạm) |
| Báo cáo | File `.md` trong `data/results/` | Markdown trong chat (hoặc file tải về) |

Logic pipeline, trọng số chấm điểm và data contract **giống hệt** các nền tảng khác —
đều bắt nguồn từ `job-matching-plugin/skills/` + `schemas/` (nguồn chân lý duy nhất).
