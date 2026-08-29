---
name: job-collector
description: Thu thập và chuẩn hóa việc làm từ web search cùng dữ liệu Facebook đã được người dùng cho phép. Dùng trong bước collect của pipeline find-jobs sau khi đã có profile ứng viên.
---

# Job Collector

Nhận đường dẫn `profile.json`, `run_id` duy nhất và đường dẫn output. Thu thập tối đa 20 job hợp lệ, chuẩn hóa theo `job-schema`, rồi ghi vào `data/jobs/<run_id>.json`.

## Nguồn dữ liệu

- Job boards: dùng web search/fetch sẵn có của host. Chỉ giữ job đọc được JD và chưa có bằng chứng hết hạn.
- Facebook Groups: chỉ dùng khi người dùng đã đồng ý. Luồng chính gọi MCP `run_facebook_crawler` trước; collector chỉ đọc `output_path` trả về. Không tự thay Facebook bằng web search và không bịa dữ liệu khi crawler lỗi.

## Contract

1. Đọc profile và sinh query song ngữ từ role, seniority, location và skills.
2. Khử trùng theo URL chuẩn hóa; ưu tiên nguồn gốc và dữ liệu mới hơn.
3. Với Facebook, chỉ giữ bài có title/vị trí và permalink hoặc kênh liên hệ thực sự. Nếu `posted_date` không xác định, ghi rõ `unknown`; không khẳng định bài còn mới.
4. Ghi object theo `schemas/job.schema.json`, đặt `extraction_confidence` trung thực.
5. Trả số lượng theo nguồn, số bị loại và cảnh báo dữ liệu thiếu.

Không tự nộp hồ sơ, không vượt CAPTCHA/anti-bot và không ghi đè output của run khác.
