# crawlers/ — script bóc job zero-dependency (hybrid tier 1)

Bóc tin tuyển dụng **ngoài vòng lặp của Claude** để tiết kiệm token: Python đọc JSON-LD/HTML,
trả về JSON đúng `schemas/job.schema.json`. Claude chỉ đọc JSON đã gọn thay vì HTML thô.

- **Chỉ dùng thư viện chuẩn (stdlib)** — không cần `pip install`. Chạy được với mọi Python 3.9+.
- **Hybrid:** board có adapter → dùng script (rẻ gần như 0 token). Board CHƯA có adapter →
  dispatcher trả `no_adapter` (exit 3) để agent **fallback `WebFetch`**.
- Tôn trọng robots/ToS, User-Agent thật, có nghỉ giữa request. **KHÔNG** vượt anti-bot/CAPTCHA.

## Board đã hỗ trợ
| Domain | Module | Cơ chế |
|---|---|---|
| `itviec.com` | `itviec.py` | JSON-LD `ItemList` (search) + `JobPosting` (JD) |

Thêm board: tạo `crawlers/<board>.py` expose `PLATFORM`, `DOMAINS`, `search(query, max_n, today)`,
`fetch_one(url, today)`; import vào `ADAPTERS` trong `run.py`; thêm test offline vào
`tests/test_crawlers.py`.

## Hợp đồng CLI (agent gọi qua Bash)

Điểm vào duy nhất: `crawlers/run.py`. Chạy được từ bất kỳ cwd nào.

### Pha search — gom URL ứng viên (một request, rẻ)
```bash
python crawlers/run.py --platform itviec.com --mode search --query "python developer" --max 20
```
stdout (một dòng JSON):
```json
{"platform":"itviec","mode":"search","count":20,
 "candidates":[{"url":"...","title":"...","platform":"itviec","relevance":1.0,"posted_days":"unknown"}]}
```
`relevance` là điểm lexical thô để cap top-K; agent vẫn re-rank ngữ nghĩa. `posted_days` ở
pha search = `unknown` (ngày chỉ có trên trang JD) — pha fetch điền chính xác.

### Pha fetch — bóc JD danh sách URL → job.schema
```bash
# URL từ file JSON:
python crawlers/run.py --platform itviec.com --mode fetch --urls-file urls.json \
  --out data/jobs/<run-id>.itviec.json
# hoặc URL từ stdin:
echo '["https://itviec.com/it-jobs/...-1536"]' | \
  python crawlers/run.py --platform itviec.com --mode fetch --urls-file - --out data/jobs/<run-id>.itviec.json
```
Ghi mảng job vào `--out`; stdout in tóm tắt:
```json
{"platform":"itviec","mode":"fetch","fetched":18,
 "dropped":[{"url":"...","reason":"Hết hạn ..."}],"out":"data/jobs/....json"}
```
Adapter tự loại job **hết hạn** (`validThrough` đã qua) và **tin cũ ≥ 30 ngày** (`datePosted`),
không có JSON-LD JobPosting, hoặc 404/410 — đưa vào `dropped` kèm lý do.

### Tham số chung
- `--today YYYY-MM-DD` — ghi đè "hôm nay" (dùng `<run-id>` date để kết quả ổn định).
- Exit code: `0` OK · `3` no_adapter (agent fallback WebFetch) · `4` search lỗi mạng.

## Test
```bash
cd job-matching-plugin
python -m unittest discover -s tests -v   # gồm test_crawlers.py (offline, không gọi mạng)
```
