---
name: bilingual-normalization
description: Chuẩn hóa kỹ năng, chức danh, địa điểm và lương giữa tiếng Việt và tiếng Anh về dạng canonical, phục vụ so khớp job/CV chính xác. Dùng khi parse CV, chuẩn hóa JD, hoặc so khớp skills/lương trong scoring.
---

# Bilingual Normalization — chuẩn hóa Việt–Anh

Mục tiêu: mọi so khớp diễn ra trên **canonical name** thống nhất, tránh trượt vì khác ngôn ngữ/cách viết.

## Skills — canonical name

- Canonical ưu tiên tên tiếng Anh phổ biến của công nghệ: `React`, `Node.js`, `Java`, `Python`, `Kubernetes`...
- Gộp biến thể: `ReactJS`/`React.js`/`Reactjs` → `React`; `NodeJS` → `Node.js`; `K8s` → `Kubernetes`; `.NET`/`dotnet` → `.NET`.
- Chức năng mô tả bằng tiếng Việt → canonical EN:
  - "Lập trình viên" / "Kỹ sư phần mềm" → Software Engineer
  - "Trưởng nhóm" → Lead ; "Quản lý dự án" → Project Manager
  - "Kiểm thử" / "QC" → QA ; "Phân tích nghiệp vụ" → Business Analyst
  - "Khoa học dữ liệu" → Data Science ; "Kỹ sư dữ liệu" → Data Engineer
- Giữ `aliases[]` trong profile/job để truy vết.

## Chức danh & cấp bậc (seniority)

- Map cấp bậc VN → thang chuẩn: Fresher→junior, "Chuyên viên"→mid, "Senior/Kỹ sư cao cấp"→senior, "Trưởng nhóm/Team Lead"→lead, "Trưởng phòng"→manager, "Giám đốc"→director.
- Cẩn thận với "Senior" gắn năm kinh nghiệm khác nhau giữa công ty — ưu tiên `min_years` nếu có.

## Địa điểm

- Chuẩn hóa: "TP.HCM"/"Sài Gòn"/"HCMC"/"Ho Chi Minh" → "Ho Chi Minh City"; "HN"/"Hà Nội" → "Hanoi"; "ĐN"/"Đà Nẵng" → "Da Nang".
- Nhận diện remote: "làm việc từ xa"/"remote" → remote; "linh hoạt"/"hybrid" → hybrid.

## Lương — giữ nguyên gốc, chỉ quy đổi khi cần so sánh

- **Luôn giữ nguyên đơn vị & giá trị gốc** trong `job.salary` (currency đúng như JD). Ví dụ JD ghi "$1000" → lưu USD 1000; ghi "26 triệu" → lưu VND 26,000,000. Không tự đổi khi lưu trữ hay hiển thị.
- Đơn vị Việt: "15 triệu"/"15tr" → 15,000,000 VND; "15-20 triệu" → min 15tr, max 20tr.
- "Thỏa thuận"/"Cạnh tranh"/"Negotiable" → không set số, `negotiable=true`, currency=unknown.
- USD: "$1500"/"1500 USD" → USD. "Up to $2000" → max=2000, currency=USD.
- **Chỉ khi cần so sánh** (chấm điểm compensation, so hai job khác đơn vị): quy đổi tạm về VND/tháng bằng tỉ giá cố định **$1 = 26,100 VND**; year→month chia 12. Giá trị quy đổi này chỉ dùng nội bộ lúc tính toán, KHÔNG ghi đè giá trị gốc.

## Nguyên tắc

- Chỉ map khi chắc chắn; nếu không rõ, giữ nguyên và ghi vào aliases để không mất thông tin.
- Không "dịch" tên riêng công ty.
