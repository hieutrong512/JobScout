---
name: job-matcher
description: Chấm điểm và xếp hạng danh sách job so với profile ứng viên. Dùng trong bước match của pipeline find-jobs sau khi collector đã tạo jobs JSON.
---

# Job Matcher

Nhận `profile.json`, `data/jobs/<run_id>.json` và output `data/results/<run_id>.shortlist.json`.

1. Khử trùng job theo `id`, giữ bản có `extraction_confidence` cao hơn.
2. Áp `scoring-rubric` và `bilingual-normalization` cho từng job.
3. Chuẩn hóa mọi bộ trọng số, kể cả mặc định, để tổng bằng 1 trước khi tính điểm.
4. Hard-filter dealbreakers chỉ khi có đủ bằng chứng; thiếu dữ liệu thì hạ confidence.
5. Ghi mảng `{match, job_ref}` theo `schemas/match.schema.json`, sắp xếp giảm dần và để excluded cuối.

Luôn ghi `weights_used`, rationale và các gap; không thổi phồng recommendation.
