---
name: application-assistant
description: Tùy chỉnh (tailor) nội dung CV và viết cover letter cho một job cụ thể dựa trên profile và JD. Dùng khi ứng viên đã chọn được job muốn apply và cần chuẩn bị hồ sơ.
---

# Application Assistant — tailor hồ sơ theo job

Đầu vào: `profile.json` + 1 job (từ jobs.json hoặc URL/JD dán vào) + (tùy chọn) MatchResult để biết gaps.
Đầu ra: bản nháp CV bullets đã điều chỉnh và/hoặc cover letter.

## Tailor CV bullets

- Chọn và viết lại các highlight kinh nghiệm sao cho khớp `must_have_skills` và trách nhiệm chính của JD.
- Dùng canonical skill name khớp với từ khóa JD (giúp qua ATS).
- Định lượng thành tích (số liệu) khi CV có dữ liệu; **không bịa** số hay kinh nghiệm không có.
- Nêu rõ chỗ nào là gap (missing must-have) và cách trình bày trung thực (vd "đang học", kinh nghiệm chuyển giao).

## Cover letter

- Cấu trúc: mở đầu (vì sao công ty/role này), thân (2–3 bằng chứng khớp yêu cầu), kết (call to action).
- Giọng văn phù hợp ngôn ngữ JD (vi/en/mixed). Ngắn gọn (~250–350 từ).
- Cá nhân hóa theo company (tránh mẫu chung chung).

## Ranh giới quan trọng

- **Không bịa** bằng cấp, kinh nghiệm, con số. Chỉ diễn đạt lại sự thật trong CV cho hấp dẫn hơn.
- Đây là bản nháp để ứng viên xem lại và tự chỉnh; nêu rõ điều đó.
- Không tự gửi email/nộp hồ sơ thay ứng viên.
