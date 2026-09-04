---
name: job-collector
description: Thu thập và chuẩn hóa việc làm từ web search. Dùng trong bước collect của pipeline find-jobs sau khi đã có profile ứng viên.
---

# Job Collector

Nhận đường dẫn `profile.json`, `run_id` duy nhất và đường dẫn output. Thu thập tối đa 20 job hợp lệ, chuẩn hóa theo `job-schema`, rồi ghi vào `data/jobs/<run_id>.json`.

## Nguồn dữ liệu

- **Tier 1 — script crawler (thử trước):** `crawlers/run.py` (Python stdlib, không cần cài gì) bóc job
  ngoài context để tiết kiệm token. Board có adapter (vd `itviec.com`) → JSON đúng `job.schema`;
  board chưa hỗ trợ trả `no_adapter` (exit 3) → fallback web search/fetch. Hợp đồng: `crawlers/README.md`.
  - search: `python crawlers/run.py --platform <domain> --mode search --query "<song ngữ>" --max <N> --today <run-id>`
  - fetch: `python crawlers/run.py --platform <domain> --mode fetch --urls-file <urls.json|-> --out data/jobs/<run_id>.<platform>.json --today <run-id>`
- **Tier 2 — web search/fetch** của host cho board chưa có adapter. Chỉ giữ job đọc được JD và chưa có bằng chứng hết hạn.

## Contract

1. Đọc profile và sinh query song ngữ từ role, seniority, location và skills.
2. Khử trùng theo URL chuẩn hóa; ưu tiên nguồn gốc và dữ liệu mới hơn.
3. Ghi object theo `schemas/job.schema.json`, đặt `extraction_confidence` trung thực.
4. Trả số lượng thu được, số bị loại và cảnh báo dữ liệu thiếu.

Không tự nộp hồ sơ, không vượt CAPTCHA/anti-bot và không ghi đè output của run khác.
