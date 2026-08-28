---
name: fit-analyzer
description: Với các job trong shortlist, giải thích mức độ phù hợp, khoảng cách kỹ năng/kinh nghiệm, rủi ro, và gợi ý cải thiện — dạng báo cáo dễ đọc cho ứng viên. Dùng sau khi job-matcher đã tạo shortlist.
---

# Fit Analyzer — báo cáo phù hợp & khoảng cách

Đầu vào: `profile.json` + `data/results/<run-id>.shortlist.json` (mảng MatchResult + job tương ứng).
Đầu ra: `data/results/<run-id>.fit_report.md`.

## Phạm vi báo cáo (QUAN TRỌNG)

Phân tích chi tiết **TẤT CẢ job trong shortlist**, không rút gọn còn top 3. Nếu shortlist có nhiều hơn **20** job thì phân tích chi tiết 20 job điểm cao nhất và vẫn liệt kê đủ phần còn lại trong bảng xếp hạng. Có thể thêm mục "🏆 Ưu tiên apply ngay" (2–3 job) ở đầu như phần tóm tắt, nhưng **phần thân báo cáo vẫn phải có block chi tiết cho từng job** (không bỏ job nào).

## Nội dung báo cáo

Với **mỗi** job (theo thứ tự điểm giảm dần), trình bày:

1. **Header**: `#N. Title @ Company` — overall_score, recommendation, **link nộp CV / bài post (url)**, lương, location/remote, hạn nộp (nếu có).
   - Nếu là tin từ Facebook / MXH: hiển thị rõ **kênh liên hệ** (Zalo, Email, Facebook Author, Telegram, hoặc "Inbox FB nhận JD").
2. **Vì sao hợp** (2–3 gạch đầu dòng): điểm mạnh khớp — matched_skills chính, domain, seniority, lương.
3. **Khoảng cách** (gaps): missing_must_have + gaps[] kèm severity. Nói rõ cái nào là "học nhanh được" vs "cần thời gian".
4. **Rủi ro / cần xác minh**:
   - Nếu là bài post Facebook ngắn: nhắc người dùng đây là bài đăng teaser, cần chủ động inbox/liên hệ HR để lấy full JD.
   - Nếu `confidence` thấp → khuyến nghị đọc kỹ JD gốc; overqualified/underqualified; lương unknown.
5. **Hành động đề xuất**:
   - Với Job board: Apply qua link / Chuẩn bị hồ sơ.
   - Với Facebook Group: Nhắn tin trực tiếp qua Facebook / Zalo / gửi email cho người đăng kèm tóm tắt kinh nghiệm (dùng skill `application-assistant` để lấy tin nhắn mẫu).

## Tổng quan đầu báo cáo

- Bảng xếp hạng: rank | title | company | score | recommendation | lương | location | **link nộp CV / bài post**. **MỌI job trong bảng đều phải có link (url) bấm được** — không chỉ các job top. Dùng markdown link (vd `[Nộp CV](url)` hoặc `[FB Post](url)`).
- Nhận xét chung: xu hướng thị trường quan sát được, gap lặp lại nhiều lần (gợi ý kỹ năng nên học), có nên nới target không (vd lương kỳ vọng quá cao so với mặt bằng).

## Nguyên tắc

- Trung thực: nếu match yếu, nói thẳng; đừng thổi phồng.
- Ưu tiên hành động cụ thể hơn nhận xét chung chung.
- Song ngữ khi cần (thuật ngữ giữ tiếng Anh, giải thích tiếng Việt).
- Không tạo kỳ vọng sai về khả năng trúng tuyển.
