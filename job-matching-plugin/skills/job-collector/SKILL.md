---
name: job-collector
description: Thu thập và chuẩn hóa việc làm từ web search. Dùng trong bước collect của pipeline find-jobs sau khi đã có profile ứng viên.
---

# Job Collector

Nhận đường dẫn `profile.json`, `run_id` duy nhất và đường dẫn output. Thu thập tối đa 20 job hợp lệ, chuẩn hóa theo `job-schema`, rồi ghi vào `data/jobs/<run_id>.json`.

## Nguồn dữ liệu

- Job boards: dùng web search/fetch sẵn có của host. Chỉ giữ job đọc được JD và chưa có bằng chứng hết hạn.

## Contract

1. Đọc profile và sinh query song ngữ từ role, seniority, location và skills.
2. Khử trùng theo URL chuẩn hóa; ưu tiên nguồn gốc và dữ liệu mới hơn.
3. Ghi object theo `schemas/job.schema.json`, đặt `extraction_confidence` trung thực.
4. Trả số lượng thu được, số bị loại và cảnh báo dữ liệu thiếu.

Không tự nộp hồ sơ, không vượt CAPTCHA/anti-bot và không ghi đè output của run khác.
