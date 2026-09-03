---
description: Chạy full pipeline tìm việc — parse CV, thu thập job, chấm điểm, xuất báo cáo fit/gap.
argument-hint: [đường dẫn CV hoặc tên profile]
---

# /find-jobs — Điều phối pipeline tìm việc

Chạy tuần tự 4 bước. `$ARGUMENTS` là đường dẫn CV (PDF/DOCX/text) hoặc tên profile đã có.

Dùng `<run-id>` duy nhất theo mẫu `<candidate-slug>-<YYYYMMDD-HHMMSS>-<suffix>` và giữ nguyên ID này xuyên suốt pipeline. Tạo thư mục `data/profiles`, `data/jobs`, `data/results` trong thư mục làm việc nếu chưa có.

## Bước 1 — Intake (skill `candidate-intake`)
- Nếu `$ARGUMENTS` là file CV → parse và tạo `data/profiles/<slug>.json`.
- Nếu là tên profile đã tồn tại → dùng lại, hỏi xem có cập nhật target không.
- Thu thập/ xác nhận target: vai trò, cấp bậc, địa điểm/remote, lương, ưu tiên (priorities → trọng số), dealbreakers.
- **Hỏi số lượng job muốn thu thập** (`fetch_count`): người dùng nhập một số. Mặc định 20 nếu bỏ trống. **Giới hạn tối đa 20** — nếu nhập lớn hơn thì kẹp về 20; nếu ≤ 0 thì hỏi lại.
- **Hỏi danh sách nền tảng** (`platforms`): mặc định 5 nền tảng (`itviec.com`, `topcv.vn`, `vietnamworks.com`, `careerviet.vn`, `linkedin.com/jobs`). Người dùng có thể **thay bằng cách gửi link/domain nền tảng muốn crawl**; khi đó dùng đúng danh sách người dùng đưa (chuẩn hóa mỗi link về domain, khử trùng). **Giới hạn tối đa 7 nền tảng** — nếu đưa nhiều hơn thì giữ 7 cái đầu và báo cho người dùng.
- Tóm tắt cho người dùng xác nhận (kèm `fetch_count` và danh sách `platforms`).

## Bước 2 — Collector (2 pha: search song song → chọn toàn cục → fetch song song)
Mục tiêu: **chỉ tốn tối đa `fetch_count` (≤20) lần fetch** nhưng ngân sách fetch được dồn cho các URL **tốt nhất trên toàn bộ nền tảng**, không chia đều — để không bỏ sót nền tảng giàu job.

**Pha 2a — Search (rẻ, song song).** Với mỗi nền tảng trong `platforms` (đã chốt ở Bước 1), **spawn một `job-collector` `mode=search` song song trong CÙNG một message**. Mỗi cái chỉ `WebSearch` (không fetch), ghi ứng viên ra `data/jobs/<run-id>.<platform-slug>.candidates.json` (`{url, title, snippet, platform, relevance, fresh_hint}`).

**Pha 2b — Chọn toàn cục (điều phối viên, không spawn).** Đọc tất cả file `*.candidates.json`, gộp, khử trùng theo URL chuẩn hóa, **xếp hạng toàn cục theo `relevance` + tin mới/còn hạn** — KHÔNG giới hạn theo nền tảng. Chọn **top `fetch_count` URL** làm danh sách fetch (một nền tảng giàu job có thể chiếm phần lớn slot). Lấy dư một ít (buffer ~30%, nhưng tổng ≤ 20 + buffer) để bù URL hỏng/hết hạn.

**Pha 2c — Fetch (song song).** Nhóm danh sách URL đã chọn **theo nền tảng**; với mỗi nhóm không rỗng, **spawn một `job-collector` `mode=fetch` song song**, truyền `urls` của nhóm đó, ghi `data/jobs/<run-id>.<platform-slug>.json`. Mỗi cái chỉ fetch đúng URL được giao.

**Pha 2d — Gộp pool.** Đọc mọi file `data/jobs/<run-id>.<platform-slug>.json`, gộp, **khử trùng theo `id`/URL**, ghi `data/jobs/<run-id>.json`. Nếu sau khi bỏ job hỏng/hết hạn mà còn thiếu nhiều so với `fetch_count`, chọn thêm URL từ danh sách dự phòng (pha 2b) và fetch bù trước khi sang Bước 3. Xếp hạng/chọn 20 cuối cùng do Bước 3 (matcher) lo.
- Chuẩn thu thập không đổi: chỉ giữ job xem được full JD & còn hạn.

## Bước 3 — Matcher (subagent `job-matcher`)
- Truyền `profile.json` + `data/jobs/<run-id>.json`.
- Chấm điểm theo skill `scoring-rubric`, dùng trọng số từ `target.priorities`.
- Ghi `data/results/<run-id>.shortlist.json`.

## Bước 4 — Fit report (skill `fit-analyzer`)
- Đọc shortlist → tạo `data/results/<run-id>.fit_report.md`.
- **Phân tích chi tiết TẤT CẢ job trong shortlist** (nếu >20 thì chi tiết 20 job điểm cao nhất, phần còn lại vẫn liệt kê đủ trong bảng). **KHÔNG rút gọn báo cáo chỉ còn top 3.**
- Có thể đánh dấu thêm nhóm "Ưu tiên apply ngay" ở đầu, nhưng đó là phần bổ sung — không thay thế phần phân tích chi tiết từng job bên dưới.
- **Mọi job trong bảng xếp hạng đều có link nộp CV / bài post bấm được.**
- Gửi file báo cáo cho người dùng.

## Sau khi xong
Đề xuất bước tiếp: tailor hồ sơ cho job top (skill `application-assistant`), hoặc mở rộng nguồn (remote quốc tế / thành phố khác).

## Nguyên tắc
- Không bịa dữ liệu job/CV. Thiếu → unknown, hạ confidence.
- Tôn trọng robots/ToS khi scrape; không vượt anti-bot/CAPTCHA.
- Không tự nộp hồ sơ thay người dùng.
