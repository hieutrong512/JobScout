# Job Collector — thu thập & chuẩn hóa job (phase)

Nhiệm vụ: từ `profile.json`, tìm và chuẩn hóa danh sách job → `data/jobs/<run-id>.json`
(mảng object theo `schemas/job.schema.json`).

> Trong Codex không có subagent — phase này chạy ngay trong luồng chính. Vì tốn nhiều
> lượt search/fetch, làm gọn: dừng khi đã đủ ~20 job hợp lệ.

## Công cụ search (giữ nguyên tinh thần: Search Engine + scraping, không cần API key)

Dùng tool **`web_search`** của Codex cho cả hai việc:
1. **Search**: tìm danh sách URL + snippet theo query.
2. **Fetch full JD**: mở URL job để đọc **toàn bộ** nội dung (không chỉ snippet).

> Cần bật web search: chạy `codex --search`, hoặc đặt `tools.web_search = true` trong
> `~/.codex/config.toml`. Nếu chưa bật, dừng và báo người dùng bật trước.

## Quy trình

### 1. Sinh truy vấn tìm kiếm
Từ `target.desired_roles`, `desired_level`, `locations`, top skills, tạo nhiều biến thể query **song ngữ**:
- EN + VN: vd "Senior React Developer Ho Chi Minh", "tuyển Frontend React senior TP.HCM".
- Kèm site filter cho các nguồn VN: `site:itviec.com`, `site:topcv.vn`, `site:vietnamworks.com`, `site:careerviet.vn`, và `site:linkedin.com/jobs`.
- Biến thể theo từng desired_role và location.

### 2. Search
- Dùng `web_search` cho từng query, gom URL + snippet.
- Khử trùng theo URL chuẩn hóa. Ưu tiên tin còn hạn / mới đăng nếu nhận biết được.

### 3. Fetch & extract — CHỈ GIỮ JOB XEM ĐƯỢC & CÒN HẠN
Đây là bộ lọc cứng. Một job chỉ được đưa vào kết quả khi thỏa **CẢ HAI** điều kiện:

**(a) Xem được nội dung đầy đủ:**
- Mở URL job (qua `web_search`) để lấy **full JD** (không chỉ snippet). Tôn trọng robots.txt/ToS.
- Nếu vẫn không lấy được full JD (chỉ có snippet, bị chặn, cần đăng nhập mới xem được nội dung) → **BỎ QUA job đó**. KHÔNG giữ job chỉ dựa trên snippet. `extraction_confidence` phải ≥ 0.5 mới được giữ.

**(b) Còn hạn ứng tuyển:**
- Kiểm tra tín hiệu hết hạn/đóng tuyển → **BỎ QUA** nếu gặp: HTTP 404/410 Gone, "job đã hết hạn / expired", "no longer accepting applications", "không còn nhận đơn", deadline đã qua so với ngày hiện tại, redirect về trang danh sách/tuyển dụng chung.
- Nếu trang có ghi hạn nộp → điền vào `application_deadline` (YYYY-MM-DD) và chỉ giữ khi hạn ≥ ngày hiện tại.
- Nếu không có tín hiệu hết hạn rõ ràng và JD hiển thị bình thường → coi là còn mở.

- **Không** vượt anti-bot/CAPTCHA. Trang chặn không mở được → bỏ qua và ghi chú (không đoán nội dung).

### 4. Chuẩn hóa
- Theo `codex/reference/job-schema.md` để map vào schema; theo `codex/reference/bilingual-normalization.md` cho skills/location/lương.
- Tạo `id` hash ổn định để khử trùng across nguồn.
- Set `extraction_confidence` trung thực (full JD cao, chỉ snippet thấp).

### 5. Ghi kết quả
- Ghi mảng job hợp lệ vào `data/jobs/<run-id>.json`.
- Tóm tắt: số job thu được / theo nguồn, số bị bỏ (chặn), cảnh báo dữ liệu thiếu.

## Nguyên tắc
- **Chỉ giữ job xem được full JD VÀ còn hạn** (xem bước 3). Thà ít mà chắc còn hơn nhồi job hết hạn/không xem được.
- Ưu tiên độ chính xác hơn số lượng; không nhồi job không liên quan.
- Không bịa trường dữ liệu (xem job-schema). Thiếu → unknown.
- `url` phải là link trang tuyển dụng còn truy cập được (nơi ứng viên bấm nộp CV) — luôn có mặt cho mọi job.
- **Mục tiêu số lượng: tối đa 20 job** hợp lệ (đã lọc). Nếu sau khi lọc còn dư, mở rộng query để đủ ~20; nếu ít hơn, nêu rõ lý do.
