# Job Matching Plugin

Plugin Claude Code giúp **tìm và xếp hạng job phù hợp nhất với target + CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua Search Engine + Web scraping (không cần API key).

## Cài đặt

Thêm marketplace rồi cài plugin (trong phiên `claude` tương tác):

```bash
/plugin marketplace add <đường-dẫn-hoặc-git-repo-này>
```

```bash
/plugin install jobscout
```

> Marketplace nằm ở `.claude-plugin/marketplace.json` tại gốc repo; plugin nằm trong `job-matching-plugin/`.

## Cách dùng

Nhanh nhất — chạy full pipeline bằng slash command:

```bash
/find-jobs D:\path\to\CV.pdf
```

Hoặc gọi từng bước bằng ngôn ngữ tự nhiên (skill tự kích hoạt): "parse CV này", "tìm job cho tôi", "chấm điểm các job", "làm báo cáo fit".

## Pipeline

```
CV + Target
   │  candidate-intake (skill)
   ▼  → data/profiles/<slug>.json
job-collector (subagent)        ← Job boards (tối đa 20)
   ▼  → data/jobs/<run-id>.json
job-matcher (subagent)          ← chấm điểm theo scoring-rubric
   ▼  → data/results/<run-id>.shortlist.json
fit-analyzer (skill)            ← báo cáo fit/gap, mọi job có link nộp CV
   ▼  → data/results/<run-id>.fit_report.md
application-assistant (skill, tùy chọn) ← tailor CV/cover letter & tin nhắn tiếp cận HR
```

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `find-jobs` | Command | Điều phối toàn bộ pipeline |
| `candidate-intake` | Skill | Parse CV + target → profile.json |
| `job-collector` | Agent | Search + scrape từ Job boards → jobs.json |
| `job-matcher` | Agent | Chấm điểm & rank → shortlist.json |
| `fit-analyzer` | Skill | Báo cáo fit/gap (link nộp CV cho mọi job) |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR |
| `scoring-rubric` | Skill | Công thức tính điểm (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job (kèm contact) |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh |

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ Ứng viên override được qua `target.priorities` trong profile.

## Yêu cầu môi trường

`WebSearch` / `WebFetch` cho Job boards là tool sẵn có của Claude Code — không cần cấu hình.

## Dữ liệu

- **Định nghĩa** (agents/skills/schemas) nằm trong plugin.
- **Dữ liệu chạy** (`data/profiles`, `data/jobs`, `data/results`) ghi trong thư mục làm việc của người dùng, không nằm trong plugin.

## Kiểm tra

```bash
cd job-matching-plugin
python -m unittest discover -s tests -v
python -m compileall -q -f tests
```

## Ghi chú vận hành

- **Tiêu chuẩn thu thập**: Quét từ các trang tuyển dụng chính thống (ITviec, TopCV, VietnamWorks, LinkedIn), chỉ giữ job xem được full JD và còn hạn.
- Giữ nguyên đơn vị lương gốc theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; không vượt anti-bot/CAPTCHA; không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
