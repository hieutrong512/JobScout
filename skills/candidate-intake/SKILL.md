---
name: candidate-intake
description: Parse CV của ứng viên (PDF/DOCX/text) và thu thập target/mong muốn để tạo profile.json chuẩn. Dùng khi bắt đầu một phiên tìm việc, khi người dùng cung cấp CV mới, hoặc muốn cập nhật mục tiêu nghề nghiệp.
---

# Candidate Intake — tạo profile ứng viên

Đầu ra: một file `data/profiles/<slug>.json` tuân theo `schemas/profile.schema.json`.

## Bước 1 — Đọc CV

- Trích text từ CV:
  - **PDF** → dùng CLI có sẵn trong sandbox: `pdftotext cv.pdf -` (poppler), hoặc `python -c "import pypdf; ..."`. Nếu không có tool, yêu cầu người dùng dán nội dung CV.
  - **DOCX** → `python -c "import docx; ..."` (python-docx), hoặc unzip đọc `word/document.xml`.
  - **Text/Markdown** → đọc trực tiếp.
- Trích: thông tin cá nhân tối thiểu (tên, headline, location), kỹ năng, kinh nghiệm (title/công ty/thời gian/highlights), học vấn, ngôn ngữ.
- Suy `total_years` và `seniority` từ tổng thời gian + phạm vi trách nhiệm.

## Bước 2 — Chuẩn hóa (song ngữ)

- Áp skill `bilingual-normalization`: đưa skills & chức danh về canonical name, chuẩn hóa location.
- Với mỗi skill, cố gắng gắn `years`/`level`/`evidence` từ CV (không bịa — thiếu thì để trống).

## Bước 3 — Thu thập target

Hỏi ứng viên (gộp câu hỏi, đừng hỏi lẻ tẻ). Nếu người dùng đã nêu sẵn trong hội thoại thì dùng luôn, chỉ hỏi phần còn thiếu:

1. **Vai trò mong muốn** (desired_roles) + cấp bậc (desired_level).
2. **Địa điểm** + hình thức (onsite/hybrid/remote/any).
3. **Lương kỳ vọng** (min & target, VND hay USD, tháng/năm).
4. **Ngành** ưu tiên + **quy mô công ty**.
5. **Dealbreakers** — điều tuyệt đối không chấp nhận.
6. **Ưu tiên** (priorities): cái gì quan trọng nhất? (lương / kỹ năng phù hợp / địa điểm / ngành / văn hóa). Chuyển thành trọng số 0–1 cho `target.priorities` (tổng ~1) — đây là dữ liệu quan trọng cho skill `scoring-rubric`.

## Bước 4 — Ghi file & Xác nhận nguồn tìm kiếm

- Ghi `profile.json` đúng schema. Đặt tên slug từ tên ứng viên (không dấu, kebab-case).
- Tóm tắt lại cho người dùng xác nhận: seniority suy ra, top skills, target, và trọng số priorities. Cho phép chỉnh trước khi sang bước collector.
- **Hỏi xác nhận nguồn tìm kiếm Facebook (Minh bạch & Nhập link động)**:
  - Hỏi người dùng: *"Bạn có muốn tìm kiếm thêm tin tuyển dụng từ các Hội nhóm Facebook IT/AI không?"*
  - *(Cảnh báo: Nếu chọn Có và phiên đăng nhập chưa có sẵn, trình duyệt sẽ mở lên để bạn đăng nhập lấy cookie session — được lưu bảo mật cục bộ tại `data/.auth/`, không bao giờ chia sẻ ra ngoài).*
  - **Nếu người dùng chọn Có**: Yêu cầu người dùng gửi link các Group Facebook công khai mục tiêu. Ghi danh sách link này vào `data/config/facebook_groups.json`.

## Nguyên tắc

- Không bịa kỹ năng/kinh nghiệm không có trong CV.
- Nếu CV thiếu năm tháng cụ thể, ước lượng và ghi rõ là ước lượng.
- Tôn trọng riêng tư: chỉ lưu thông tin cần cho matching; không đưa dữ liệu cá nhân ra ngoài.
