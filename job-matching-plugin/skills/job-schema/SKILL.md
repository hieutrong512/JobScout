---
name: job-schema
description: Schema chuẩn cho một tin tuyển dụng (job) và cách map dữ liệu thô từ search/scrape vào schema đó. Dùng bởi job-collector khi chuẩn hóa JD, và job-matcher khi đọc job.
---

# Job Schema — chuẩn hóa tin tuyển dụng

Schema chính: `./schemas/job.schema.json`. Skill này hướng dẫn cách điền cho nhất quán.

## Quy tắc bắt buộc

- `id`: tạo hash ổn định. Ưu tiên chuẩn hóa URL (bỏ query tracking) rồi hash; nếu không có URL sạch, hash chuỗi `company|title|location` (lowercase, bỏ dấu). Dùng để **khử trùng lặp** giữa các nguồn.
- `source`: định danh nguồn ngắn gọn: `itviec`, `topcv`, `vietnamworks`, `linkedin`, `careerviet`, `facebook_group`, `facebook`, `google`, ...
- `collected_at`: ISO timestamp.
- `extraction_confidence` (0–1):
  - **Cao** (0.8–1.0): đọc được full JD từ trang tuyển dụng chính thống hoặc link JD mở.
  - **Khá** (0.5–0.7): bài post ngắn trên Facebook Groups công khai có đủ Title, Vị trí, Địa điểm, Tech stack chính và Kênh liên hệ.
  - **Thấp** (≤0.4): chỉ có snippet rời rạc từ kết quả tìm kiếm không đủ thông tin liên hệ.

## Chuẩn hóa các trường

- **skills** (`must_have_skills`, `nice_to_have_skills`): đưa về canonical name qua skill `bilingual-normalization` (vd "ReactJS", "React.js" → "React"). Với bài post FB ngắn, trích xuất các keywords công nghệ được nhắc tới vào `must_have_skills`.
- **salary**: parse cả tiếng Việt ("15-20 triệu", "thỏa thuận", "Up to $2000", "2x-3x tr", "range 30-50m") → {min, max, currency, period, negotiable}. "Thỏa thuận"/"Negotiable" → currency=unknown, negotiable=true.
- **remote**: nhận diện "remote", "làm việc từ xa", "hybrid", "onsite", "tại văn phòng".
- **seniority**: suy từ title/JD ("Junior", "Senior", "Trưởng nhóm"→lead, "Fresher"→junior).
- **company**: Nếu bài post Facebook không nêu rõ tên cty (stealth startup, headhunter tuyển hộ) → ghi `Confidential (<lĩnh vực>)` hoặc tên agency (vd `Confidential (Fintech HCM)`).
- **contact**: Trích xuất kênh liên hệ trực tiếp từ bài post:
  - `email`: email nhận CV (vd `hr@company.com`).
  - `zalo`: số điện thoại / link Zalo.
  - `telegram`: handle Telegram (@recruiter).
  - `facebook_author`: tên/link profile người đăng bài.
  - `how_to_apply`: tóm tắt ngắn (vd `"Inbox FB / Zalo để nhận JD chi tiết"`, `"Gửi CV qua email hr@..."`).
- **language**: `vi`/`en`/`mixed` tùy JD.
- **min_years**: parse "2+ năm kinh nghiệm", "at least 3 years".

## Nguyên tắc chống bịa

- Chỉ điền trường khi có bằng chứng trong dữ liệu nguồn. Không suy đoán lương/quy mô công ty nếu JD không nói → để `unknown`.
- Với bài post Facebook, giữ nguyên link bài viết làm `url` để người dùng có thể bấm vào comment/inbox trực tiếp cho người đăng.
- Rút gọn `description` nếu quá dài (giữ phần requirements + trách nhiệm chính hoặc trích toàn văn bài post ngắn).

## Ví dụ tin tuyển dụng chuẩn

### 1. Nguồn Job Board (Full JD)
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

### 2. Nguồn Facebook Group (Bài post ngắn / Teaser post)
```json
{
  "id": "fb_9f8e7d",
  "title": "Senior AI Engineer (CV & LLM)",
  "company": "Confidential (Fintech / AI Startup)",
  "location": "Ho Chi Minh City",
  "remote": "onsite",
  "url": "https://www.facebook.com/groups/vietnam.ai.community/posts/123456789/",
  "source": "facebook_group",
  "language": "vi",
  "description": "[HCM/Onsite] Cần tuyển Senior AI Engineer làm về Computer Vision & LLM RAG. Lương 35-50M. Anh em quan tâm inbox hoặc gửi CV qua zalo 0901234567 nhé!",
  "contact": {
    "zalo": "0901234567",
    "facebook_author": "Lan Nguyen (HR)",
    "how_to_apply": "Inbox FB người đăng hoặc liên hệ Zalo 0901234567 để nhận JD chi tiết"
  },
  "requirements": {
    "must_have_skills": ["Computer Vision", "LLM", "RAG", "Python"],
    "seniority": "senior"
  },
  "salary": { "min": 35000000, "max": 50000000, "currency": "VND", "period": "month" },
  "collected_at": "2026-08-25T10:00:00Z",
  "extraction_confidence": 0.65
}
```
