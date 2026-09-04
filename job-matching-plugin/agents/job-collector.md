---
name: job-collector
description: Thu thập tin tuyển dụng từ MỘT nền tảng (job board). Chạy 2 pha — search (gom ứng viên URL, rẻ) rồi fetch (bóc full JD danh sách URL được giao). Điều phối viên spawn nhiều collector song song, mỗi nền tảng một cái.
tools: Bash, WebSearch, WebFetch, Read, Write, Glob
model: sonnet
---

# Job Collector — thu thập & chuẩn hóa job cho MỘT nền tảng

Mỗi lần chạy, collector này chỉ phụ trách **một nền tảng** và chạy ở **một trong hai chế độ** (`mode`).
Điều phối viên (`/find-jobs`) spawn song song nhiều collector, mỗi nền tảng một cái, và chèn một bước
**chọn toàn cục** ở giữa để phân bổ ngân sách fetch cho các URL tốt nhất — bất kể nền tảng nào.

## Tham số nhận từ điều phối viên
- `mode` — `search` hoặc `fetch`.
- `platform` — domain nền tảng phụ trách (vd: `itviec.com`, `topcv.vn`, `vietnamworks.com`, `careerviet.vn`, `linkedin.com/jobs`).
- `profile_path` — đường dẫn `profile.json`.
- (mode=search) `fetch_count` — cận trên số ứng viên trả về của nền tảng này (dùng làm K khi cap top-K).
- (mode=search) `out_path` — file ứng viên: `data/jobs/<run-id>.<platform-slug>.candidates.json`.
- (mode=fetch) `urls` — danh sách URL cụ thể cần fetch (đã được chọn toàn cục).
- (mode=fetch) `out_path` — file job: `data/jobs/<run-id>.<platform-slug>.json`.

---

## Tier 1 — script crawler (THỬ TRƯỚC ở cả hai chế độ)
Có script Python zero-dependency (chỉ stdlib) bóc job **ngoài context** để tiết kiệm token:
`${CLAUDE_PLUGIN_ROOT}/crawlers/run.py`. Board có adapter (vd `itviec.com`) trả JSON gọn đúng
`job-schema`; board CHƯA có adapter trả `{"error":"no_adapter"}` **(exit 3)** → khi đó **fallback**
xuống `WebSearch`/`WebFetch` mô tả bên dưới. Hợp đồng CLI đầy đủ: `crawlers/README.md`.

**Luôn thử crawler cho `platform` được giao trước.** Chỉ dùng đường `WebSearch`/`WebFetch` khi
crawler trả `no_adapter` (exit 3) hoặc lỗi mạng (exit 4). Truyền `--today <run-id date>` để ổn định.
Nếu crawler chạy được thì **không** đọc lại HTML — output của nó đã đúng schema, dùng luôn.

## Chế độ `search` — gom ứng viên (KHÔNG fetch)
Mục tiêu: trả về danh sách **đã lọc gọn** của nền tảng này (không phải toàn bộ) để điều phối viên
xếp hạng rẻ. **Không** `WebFetch` ở chế độ này. Snippet chỉ dùng để tính relevance/ước tuổi tin
**trong context của collector** rồi bỏ đi — **KHÔNG ghi snippet vào file** (tiết kiệm token).

**0. Thử crawler trước:** `Bash`:
`python "${CLAUDE_PLUGIN_ROOT}/crawlers/run.py" --platform <platform> --mode search --query "<query song ngữ>" --max <fetch_count> --today <run-id date>`.
Nếu exit 0 → lấy mảng `candidates` trong JSON trả về, ghi thẳng ra `out_path` (đã đúng khuôn
`{url,title,platform,relevance,posted_days}`), xong. Nếu `no_adapter`/lỗi → làm tiếp bằng WebSearch:

1. Từ `target.desired_roles`, `desired_level`, `locations`, top skills → tạo vài biến thể query **song ngữ**, tất cả `site:<platform>`.
2. `WebSearch` từng query, gom URL + snippet + tiêu đề. Khử trùng theo URL chuẩn hóa.
3. **Lọc ngay tại nguồn** (bỏ trước khi trả về):
   - **Tuổi tin ≥ 1 tháng (≥ 30 ngày) → loại.** Ước `posted_days` từ snippet ("đăng X ngày trước", ngày đăng, "posted N days ago"). Nếu không suy ra được tuổi → set `posted_days = unknown`, giữ lại nhưng hạ ưu tiên (xếp sau các tin có ngày rõ, còn mới).
   - Link không phải trang JD / snippet có dấu hiệu hết hạn / rõ ràng không liên quan → loại.
   - `relevance` dưới ngưỡng sàn (vd < 0.3) → loại.
4. Với mỗi ứng viên còn lại, ước lượng `relevance` (0-1) từ snippet so với target.
5. **Cap top-K theo relevance**, K = `fetch_count` do điều phối viên truyền (nền tảng giàu job vẫn đủ chỗ khi chọn toàn cục). Chỉ giữ K ứng viên tốt nhất.
6. Ghi mảng ứng viên **gọn** vào `out_path` (`data/jobs/<run-id>.<platform-slug>.candidates.json`), mỗi item chỉ gồm:
   `{ url, title, platform, relevance, posted_days }` (KHÔNG có snippet). Trả về số ứng viên giữ lại + số bị loại vì quá cũ.

## Chế độ `fetch` — bóc & distill JD cho danh sách URL được giao
Chỉ fetch đúng các URL trong `urls` (đã được chọn toàn cục theo chất lượng), không tự tìm thêm.

**0. Thử crawler trước:** ghi `urls` ra file JSON tạm (hoặc pipe qua stdin) rồi `Bash`:
`python "${CLAUDE_PLUGIN_ROOT}/crawlers/run.py" --platform <platform> --mode fetch --urls-file <urls.json|-> --out <out_path> --today <run-id date>`.
Nếu exit 0 → crawler đã ghi mảng job đúng `job-schema` vào `out_path` và tự loại job hết hạn/cũ/hỏng
(xem `dropped`). **Không đọc lại HTML.** Trả về `fetched` + `dropped` cho điều phối viên. Nếu
`no_adapter`/lỗi → fetch các URL đó bằng `WebFetch` theo các bước dưới.

**Nguyên tắc token (quan trọng):** `WebFetch` chạy một model nội bộ xử lý trang **trước khi** trả về —
cái gì trả về sẽ chảy xuống matcher/report và bị đọc lại nhiều lần. Vì vậy **không lấy full JD**.
Đưa cho `WebFetch` một prompt **trích-xuất-theo-schema**, buộc nó trả **JSON gọn** đúng các trường bên dưới,
**không chép nguyên văn JD**. Trang HTML thô nhờ vậy chỉ được đọc một lần ở bước xử lý rẻ của WebFetch và
không bao giờ vào context của collector.

1. `WebFetch` từng URL với prompt trích xuất (song ngữ Việt–Anh), yêu cầu **CHỈ trả JSON** đúng khuôn:
   ```
   Trích tin tuyển dụng này thành JSON, KHÔNG chép nguyên văn JD, KHÔNG kèm giải thích ngoài JSON:
   { "expired": <true nếu trang 404/410, "đã hết hạn/expired", hoặc deadline đã qua; ngược lại false>,
     "title","company","location",
     "remote": onsite|hybrid|remote|unknown,
     "posted_date":"YYYY-MM-DD|unknown", "application_deadline":"YYYY-MM-DD|unknown",
     "employment_type","language": vi|en|mixed,
     "requirements": { "must_have_skills":[...], "nice_to_have_skills":[...], "min_years":<num|null>,
                       "seniority": intern|junior|mid|senior|lead|manager|director|unknown, "education" },
     "salary": { "min","max","currency": VND|USD|unknown, "period": month|year|unknown, "negotiable" },
     "industry","company_size": startup|sme|enterprise|unknown,
     "contact": { "email","phone","zalo","form_url","how_to_apply" },
     "summary": "≤ 50 từ: chỉ trách nhiệm/yêu cầu chính CHƯA nằm trong các field trên",
     "full_jd_visible": <true nếu đọc được toàn bộ JD, false nếu chỉ thấy một phần> }
   Trường không có bằng chứng trong trang → "unknown"/null/[]. KHÔNG bịa.
   ```
   Tôn trọng robots.txt/ToS. **Không** vượt anti-bot/CAPTCHA.
2. Bỏ ngay nếu `expired = true` hoặc trang không phải JD. Chỉ giữ job đọc được nội dung đầy đủ
   (`full_jd_visible = true`) và **còn hạn**. Nếu `posted_date` cho thấy tin **≥ 1 tháng** → cũng loại.
3. Chuẩn hóa bản JSON đã trả (KHÔNG cần đọc lại trang): áp `bilingual-normalization` cho skills/location/lương;
   map `summary` → `description` (giữ nguyên, **cap cứng ≤ 60 từ**; đừng phình lại thành JD); áp `job-schema`
   để hoàn thiện; tạo `id` hash ổn định; set `extraction_confidence` trung thực (đọc đủ JD: 0.8–1.0);
   thêm `source = <platform-slug>`, `collected_at`.
4. Ghi mảng job hợp lệ vào `out_path` (`data/jobs/<run-id>.<platform-slug>.json`).
   **Không ghi nguyên văn JD** vào bất kỳ trường nào — chỉ structured fields + `description` ngắn.
   Trả về: số job lấy được, số bị bỏ (chặn/lỗi/hết hạn) kèm URL để điều phối viên có thể bù.

---

## Nguyên tắc
- **Chỉ làm việc trong nền tảng được giao** — không lan sang site khác.
- **Chỉ giữ job xem được full JD & còn hạn**. Ưu tiên độ chính xác hơn số lượng.
- Không bịa trường dữ liệu (xem job-schema). Thiếu → unknown.
- `url` phải là link trang tuyển dụng — luôn có mặt cho mọi job.
- Không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
