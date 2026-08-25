---
name: fit-analyzer
description: Với các job trong shortlist, giải thích mức độ phù hợp, khoảng cách kỹ năng/kinh nghiệm, rủi ro, và gợi ý cải thiện — dạng báo cáo dễ đọc cho ứng viên. Dùng sau khi job-matcher đã tạo shortlist.
---

# Fit Analyzer — báo cáo phù hợp & khoảng cách

Đầu vào: `profile.json` + `data/results/<run-id>.shortlist.json` (mảng MatchResult + job tương ứng).
Đầu ra: `data/results/<run-id>.fit_report.md`.

## Nội dung báo cáo

Phân tích chi tiết cho **top N** (mặc định **20**, hoặc toàn bộ nếu ít hơn) job có điểm cao nhất, mỗi job trình bày:

1. **Header**: `#N. Title @ Company` — overall_score, recommendation, **link nộp CV (url)**, lương, location/remote, hạn nộp (nếu có).
2. **Vì sao hợp** (2–3 gạch đầu dòng): điểm mạnh khớp — matched_skills chính, domain, seniority, lương.
3. **Khoảng cách** (gaps): missing_must_have + gaps[] kèm severity. Nói rõ cái nào là "học nhanh được" vs "cần thời gian".
4. **Rủi ro / cần xác minh**: nếu `confidence` thấp (JD chỉ có snippet) → khuyến nghị đọc kỹ JD gốc; overqualified/underqualified; lương unknown.
5. **Hành động đề xuất**: nên apply ngay / cân nhắc / bổ sung gì trước khi apply.

## Tổng quan đầu báo cáo

- Bảng xếp hạng: rank | title | company | score | recommendation | lương | location | **link nộp CV**. **MỌI job trong bảng đều phải có link nộp CV (url) bấm được** — không chỉ các job top. Dùng markdown link (vd `[Nộp CV](url)`).
- Nhận xét chung: xu hướng thị trường quan sát được, gap lặp lại nhiều lần (gợi ý kỹ năng nên học), có nên nới target không (vd lương kỳ vọng quá cao so với mặt bằng).

## Nguyên tắc

- Trung thực: nếu match yếu, nói thẳng; đừng thổi phồng.
- Ưu tiên hành động cụ thể hơn nhận xét chung chung.
- Song ngữ khi cần (thuật ngữ giữ tiếng Anh, giải thích tiếng Việt).
- Không tạo kỳ vọng sai về khả năng trúng tuyển.
