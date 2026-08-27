# Job Matching Plugin

Plugin Claude Code giúp **tìm và xếp hạng job phù hợp nhất với target + CV** của ứng viên. Xử lý song ngữ Việt–Anh, lấy dữ liệu job qua Search Engine + Web scraping (không cần API key).

## Cài đặt

Thêm marketplace rồi cài plugin (trong phiên `claude` tương tác):

```bash
/plugin marketplace add <đường-dẫn-hoặc-git-repo-này>
```

```bash
/plugin install job-matching
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
   ▼  → data/profiles/<slug>.json (kèm hỏi người dùng xác nhận bật nguồn Facebook)
job-collector (subagent)        ← Job boards + Tùy chọn: In-Group Facebook Crawler (tối đa 20)
   ▼  → data/jobs/<run-id>.json
job-matcher (subagent)          ← chấm điểm theo scoring-rubric
   ▼  → data/results/<run-id>.shortlist.json
fit-analyzer (skill)            ← báo cáo fit/gap, mọi job có link nộp CV / bài post
   ▼  → data/results/<run-id>.fit_report.md
application-assistant (skill, tùy chọn) ← tailor CV/cover letter & tin nhắn tiếp cận HR (Zalo/FB)
```

## Thành phần

| Thành phần | Loại | Vai trò |
|---|---|---|
| `find-jobs` | Command | Điều phối toàn bộ pipeline (hỏi bật nguồn Facebook minh bạch) |
| `candidate-intake` | Skill | Parse CV + target → profile.json |
| `job-collector` | Agent | Search + scrape từ Job boards (và FB Groups nếu được bật) → jobs.json |
| `job-matcher` | Agent | Chấm điểm & rank → shortlist.json |
| `fit-analyzer` | Skill | Báo cáo fit/gap (link nộp CV / bài post cho mọi job) |
| `application-assistant` | Skill | Tailor CV / cover letter / tin nhắn tiếp cận HR (Zalo/FB) |
| `scoring-rubric` | Skill | Công thức tính điểm (nền tảng) |
| `job-schema` | Skill | Schema chuẩn cho job (kèm contact & FB posts) |
| `bilingual-normalization` | Skill | Chuẩn hóa skill/chức danh/lương Việt–Anh & văn phong MXH |

## Trọng số chấm điểm (mặc định)

skills 35% · seniority 20% · domain 15% · compensation 15% · location 5% · culture 5%
→ Ứng viên override được qua `target.priorities` trong profile.

## Dữ liệu

- **Định nghĩa** (agents/skills/schemas) nằm trong plugin.
- **Dữ liệu chạy** (`data/profiles`, `data/jobs`, `data/results`) ghi trong thư mục làm việc của người dùng, không nằm trong plugin.

## Ghi chú vận hành

- **Tiêu chuẩn thu thập theo nguồn**:
  - *Job boards truyền thống* (ITviec, TopCV, VietnamWorks, LinkedIn): Luôn được quét chính thống, chỉ giữ job xem được full JD và còn hạn.
  - *Hội nhóm Facebook (Tùy chọn)*: Quét qua In-Group Search trực tiếp với từ khóa chuyên môn. Cần người dùng xác nhận bật và đăng nhập lấy session cookie (lưu bảo mật tại `data/.auth/`).
- Giữ nguyên đơn vị lương gốc theo JD; chỉ quy đổi khi so sánh (tỉ giá $1 = 26.100 VND).
- Tôn trọng robots.txt/ToS; không vượt anti-bot/CAPTCHA; không tự nộp hồ sơ / gửi tin nhắn thay người dùng.
