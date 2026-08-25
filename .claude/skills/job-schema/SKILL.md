---
name: job-schema
description: Schema chuẩn cho một tin tuyển dụng (job) và cách map dữ liệu thô từ search/scrape vào schema đó. Dùng bởi job-collector khi chuẩn hóa JD, và job-matcher khi đọc job.
---

# Job Schema — chuẩn hóa tin tuyển dụng

Schema chính: `schemas/job.schema.json`. Skill này hướng dẫn cách điền cho nhất quán.

## Quy tắc bắt buộc

- `id`: tạo hash ổn định. Ưu tiên chuẩn hóa URL (bỏ query tracking) rồi hash; nếu không có URL sạch, hash chuỗi `company|title|location` (lowercase, bỏ dấu). Dùng để **khử trùng lặp** giữa các nguồn.
- `source`: định danh nguồn ngắn gọn: `itviec`, `topcv`, `vietnamworks`, `linkedin`, `careerviet`, `google`, ...
- `collected_at`: ISO timestamp.
- `extraction_confidence` (0–1): **cao** khi fetch được full JD; **thấp** (≤0.4) khi chỉ có snippet từ search.

## Chuẩn hóa các trường

- **skills** (`must_have_skills`, `nice_to_have_skills`): đưa về canonical name qua skill `bilingual-normalization` (vd "ReactJS", "React.js" → "React").
- **salary**: parse cả tiếng Việt ("15-20 triệu", "thỏa thuận", "Up to $2000") → {min, max, currency, period, negotiable}. "Thỏa thuận"/"Negotiable" → currency=unknown, negotiable=true.
- **remote**: nhận diện "remote", "làm việc từ xa", "hybrid", "onsite", "tại văn phòng".
- **seniority**: suy từ title/JD ("Junior", "Senior", "Trưởng nhóm"→lead, "Fresher"→junior).
- **language**: `vi`/`en`/`mixed` tùy JD.
- **min_years**: parse "2+ năm kinh nghiệm", "at least 3 years".

## Nguyên tắc chống bịa

- Chỉ điền trường khi có bằng chứng trong dữ liệu nguồn. Không suy đoán lương/quy mô công ty nếu JD không nói → để `unknown`.
- Nếu chỉ có snippet, điền những gì chắc chắn (title, company, url, source) và đặt `extraction_confidence` thấp; các trường suy đoán để unknown/rỗng.
- Rút gọn `description` nếu quá dài (giữ phần requirements + trách nhiệm chính).

## Ví dụ tối thiểu hợp lệ

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
