---
name: job-schema
description: Schema chuẩn cho một tin tuyển dụng (job) và cách map dữ liệu thô từ search/scrape vào schema đó. Dùng bởi job-collector khi chuẩn hóa JD, và job-matcher khi đọc job.
---

# Job Schema — chuẩn hóa tin tuyển dụng

Schema chính: `./schemas/job.schema.json`. Skill này hướng dẫn cách điền cho nhất quán.

## Quy tắc bắt buộc

- `id`: tạo hash ổn định. Ưu tiên chuẩn hóa URL (bỏ query tracking) rồi hash; nếu không có URL sạch, hash chuỗi `company|title|location` (lowercase, bỏ dấu). Dùng để **khử trùng lặp** giữa các nguồn.
- `source`: định danh nguồn ngắn gọn: `itviec`, `topcv`, `vietnamworks`, `linkedin`, `careerviet`, `google`, ...
- `collected_at`: ISO timestamp.
- `extraction_confidence` (0–1):
  - **Cao** (0.8–1.0): đọc được full JD từ trang tuyển dụng chính thống hoặc link JD mở.
  - **Thấp** (≤0.4): chỉ có snippet rời rạc từ kết quả tìm kiếm không đủ thông tin.

## Chuẩn hóa các trường

- **skills** (`must_have_skills`, `nice_to_have_skills`): đưa về canonical name qua skill `bilingual-normalization` (vd "ReactJS", "React.js" → "React").
- **salary**: parse cả tiếng Việt ("15-20 triệu", "thỏa thuận", "Up to $2000", "range 30-50m") → {min, max, currency, period, negotiable}. "Thỏa thuận"/"Negotiable" → currency=unknown, negotiable=true.
- **remote**: nhận diện "remote", "làm việc từ xa", "hybrid", "onsite", "tại văn phòng".
- **seniority**: suy từ title/JD ("Junior", "Senior", "Trưởng nhóm"→lead, "Fresher"→junior).
- **company**: Nếu JD không nêu rõ tên cty (stealth startup, headhunter tuyển hộ) → ghi `Confidential (<lĩnh vực>)` hoặc tên agency (vd `Confidential (Fintech HCM)`).
- **contact**: Trích xuất kênh liên hệ ứng tuyển nếu JD có:
  - `email`: email nhận CV (vd `hr@company.com`).
  - `phone`: số điện thoại liên hệ.
  - `form_url`: link Google Form / Typeform nộp hồ sơ.
  - `how_to_apply`: tóm tắt ngắn (vd `"Gửi CV qua email hr@..."`, `"Apply qua link"`).
- **language**: `vi`/`en`/`mixed` tùy JD.
- **min_years**: parse "2+ năm kinh nghiệm", "at least 3 years".

## Nguyên tắc chống bịa

- Chỉ điền trường khi có bằng chứng trong dữ liệu nguồn. Không suy đoán lương/quy mô công ty nếu JD không nói → để `unknown`.
- `url` luôn là link trang tuyển dụng gốc để người dùng bấm vào apply.
- Rút gọn `description` nếu quá dài (giữ phần requirements + trách nhiệm chính).

## Ví dụ tin tuyển dụng chuẩn (Full JD)

```json
{
  "id": "a1b2c3",
  "title": "Senior Frontend Developer (ReactJS)",
  "company": "ABC Tech",
  "location": "Ho Chi Minh City",
  "remote": "hybrid",
  "url": "https://itviec.com/it-jobs/senior-frontend-abc",
  "source": "itviec",
  "language": "mixed",
  "requirements": {
    "must_have_skills": ["React", "TypeScript"],
    "nice_to_have_skills": ["Next.js"],
    "min_years": 3,
    "seniority": "senior"
  },
  "salary": { "min": 30000000, "max": 45000000, "currency": "VND", "period": "month" },
  "collected_at": "2026-08-25T10:00:00Z",
  "extraction_confidence": 0.9
}
```
