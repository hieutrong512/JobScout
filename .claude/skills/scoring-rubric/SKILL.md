---
name: scoring-rubric
description: Công thức chấm điểm mức độ khớp giữa 1 job và profile ứng viên. Dùng bởi job-matcher và bất kỳ nơi nào cần đánh giá độ phù hợp job/CV. Định nghĩa trọng số, cách tính từng chiều, hard filter (dealbreakers), và cách xử lý dữ liệu thiếu.
---

# Scoring Rubric — chấm điểm khớp job ↔ profile

Đây là "bộ não" quyết định chất lượng match. Kết quả tuân theo `schemas/match.schema.json`.

## Nguyên tắc

1. Điểm mỗi chiều thang **0–100**, độc lập.
2. `overall_score` = tổng có trọng số của các chiều, **trừ** khi có dealbreaker (→ excluded).
3. Minh bạch: luôn ghi `weights_used`, `matched_skills`, `missing_must_have`, `rationale`.
4. Dữ liệu thiếu KHÔNG bị chấm 0 một cách mù quáng — xem mục "Xử lý dữ liệu thiếu".

## Bước 0 — Hard filter (dealbreakers)

Trước khi chấm điểm, kiểm tra `profile.target.dealbreakers` và các ràng buộc cứng:

- Vi phạm bất kỳ dealbreaker → `recommendation = "excluded"`, `overall_score = 0`, ghi vào `dealbreaker_violations`. **Không** tính tiếp.
- Ví dụ dealbreaker cứng thường gặp: location ngoài vùng chấp nhận (khi remote=onsite), loại hình công ty bị loại (outsource), lương max < salary.min của ứng viên (khi có đủ dữ liệu).
- Nếu dữ liệu không đủ để khẳng định vi phạm (vd lương "unknown") → KHÔNG loại, hạ `confidence` thay vì exclude.

## Trọng số mặc định

| Chiều | Mặc định | Ý nghĩa |
|---|---|---|
| skills | 0.35 | Khớp kỹ năng must-have / nice-to-have |
| seniority | 0.20 | Cấp bậc & số năm kinh nghiệm |
| domain | 0.15 | Ngành/lĩnh vực |
| location | 0.05 | Địa điểm & hình thức remote |
| compensation | 0.15 | Lương so với kỳ vọng |
| culture | 0.05 | Quy mô/loại hình công ty, tín hiệu văn hóa |

**Override:** nếu `profile.target.priorities` có giá trị, dùng chúng thay cho mặc định. Chuẩn hóa lại để tổng = 1 (chia mỗi trọng số cho tổng). Luôn ghi kết quả vào `weights_used`.

## Cách tính từng chiều

### skills (0–100)
- Chuẩn hóa mọi skill về canonical name (dùng skill `bilingual-normalization`) trước khi so khớp.
- `must_cover` = tỉ lệ must-have của job mà profile đáp ứng.
- `nice_cover` = tỉ lệ nice-to-have đáp ứng.
- `skills_score = 100 * (0.75 * must_cover + 0.25 * nice_cover)`.
- Cộng thưởng nhẹ nếu ứng viên có skill level `advanced/expert` cho must-have chính (tối đa +10, cap 100).
- Nếu job không nêu must-have (`must_have_skills` rỗng) → suy từ title + description; hạ `confidence`.
- Ghi `matched_skills` và `missing_must_have`.

### seniority (0–100)
- So `profile.seniority` với `job.requirements.seniority` (map thang: intern<junior<mid<senior<lead<manager<director).
- Khoảng cách 0 bậc → 100; 1 bậc → 75; 2 bậc → 45; ≥3 bậc → 15.
- **Overqualified** (ứng viên cao hơn job ≥2 bậc) cũng bị trừ (dễ bị loại/chán việc): áp cùng thang khoảng cách.
- Điều chỉnh bằng `min_years`: nếu `total_years < min_years` → nhân 0.6; nếu thừa nhiều năm → không thưởng.
- Nếu job seniority = unknown → suy từ min_years/title; hạ confidence.

### domain (0–100)
- Trùng ngành trong `profile.domains`/`target.industries` với `job.industry` → 100.
- Ngành liền kề/chuyển giao được (adjacent) → 60.
- Không liên quan → 30 (không phải 0, vì kỹ năng có thể chuyển ngành).

### location (0–100)
- remote=remote và ứng viên chấp nhận remote/any → 100.
- Job location nằm trong `target.locations` → 100.
- hybrid + cùng thành phố → 85.
- onsite khác thành phố nhưng ứng viên để "any" → 60.
- onsite ngoài vùng chấp nhận (chưa tới mức dealbreaker) → 25.

### compensation (0–100)
- Cần đưa về cùng đơn vị (VND/tháng) — dùng `bilingual-normalization` để quy đổi USD↔VND & year↔month.
- job_mid = trung bình (min,max). So với `target.salary.target` (hoặc min).
- job_mid ≥ target → 100; trong khoảng [min, target] → nội suy 70–100; dưới min nhưng ≥ 90% min → 50; thấp hơn → 20.
- Lương unknown → điểm neutral 60, hạ confidence (KHÔNG chấm 0).

### culture (0–100)
- Khớp `target.company_size` → +40 baseline lên; tín hiệu tích cực trong JD (đãi ngộ, lộ trình, tech stack hiện đại) cộng thêm.
- Ít dữ liệu → 60 neutral.

## Xử lý dữ liệu thiếu

- Không bao giờ chấm 0 vì "thiếu thông tin" — dùng điểm **neutral** (55–60) và **giảm `confidence`**.
- **Với tin tuyển dụng Facebook Groups ngắn** (chỉ có title, vị trí, vài tech keywords, lương ngắn gọn và contact):
  - Chấm `skills` dựa trên các keywords công nghệ trích được từ bài post.
  - Các chiều thiếu (culture, domain chi tiết) chấm điểm neutral (60) và gán `confidence` khoảng 0.55–0.65.
  - Trong `rationale`: nêu rõ `"Tin từ Facebook Group: Cần inbox/Zalo người đăng để nhận full JD"`.
- `confidence` tổng của match ≈ trung bình có trọng số của `job.extraction_confidence` và độ đầy đủ dữ liệu các chiều.
- Match có confidence < 0.4 nên được đánh dấu "cần xác minh JD" trong rationale.

## Tổng hợp & khuyến nghị

```
overall = Σ (dimension_score[d] * weight[d])   với d ∈ 6 chiều
```

Map sang `recommendation`:

| overall | recommendation |
|---|---|
| ≥ 80 | strong |
| 65–79 | good |
| 50–64 | maybe |
| < 50 | weak |
| (dealbreaker) | excluded |

## Đầu ra

Trả về đúng `schemas/match.schema.json`: overall_score, recommendation, dimension_scores, weights_used, matched_skills, missing_must_have, gaps[], dealbreaker_violations[], rationale, confidence.

`rationale` viết ngắn, cụ thể, song ngữ nếu cần — nêu 1–2 lý do mạnh nhất và 1 gap lớn nhất.
