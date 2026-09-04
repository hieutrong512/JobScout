#!/usr/bin/env python3
"""Dispatcher crawler — điểm vào DUY NHẤT cho agent job-collector gọi qua Bash.

Route theo `--platform` (domain) tới adapter tương ứng. Board CHƯA có adapter → thoát mã 3
và in {"error":"no_adapter"} để agent tự fallback sang WebFetch (đây chính là phần "hybrid").

Chỉ dùng stdlib — không cần pip install. Xem crawlers/README.md cho hợp đồng CLI đầy đủ.

Ví dụ:
  python run.py --platform itviec.com --mode search --query "python developer" --max 20
  python run.py --platform itviec.com --mode fetch --urls-file urls.json --out data/jobs/run.itviec.json
  echo '["https://itviec.com/it-jobs/....-2114"]' | python run.py --platform itviec.com --mode fetch --urls-file -
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime

# Cho phép chạy từ bất kỳ cwd nào: thêm thư mục script vào sys.path để import base + adapter.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import itviec  # noqa: E402
from base import FetchError, dedupe_by, now_iso  # noqa: E402

# Registry adapter. Thêm board mới: import module rồi thêm vào đây.
ADAPTERS = [itviec]


def _find_adapter(platform: str):
    domain = platform.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    for mod in ADAPTERS:
        if any(d in domain for d in mod.DOMAINS):
            return mod
    return None


def _parse_today(s: str | None) -> date | None:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def _load_urls(spec: str) -> list[str]:
    """--urls-file: đường dẫn file JSON (mảng URL) hoặc '-' để đọc từ stdin."""
    text = sys.stdin.read() if spec == "-" else open(spec, encoding="utf-8").read()
    data = json.loads(text)
    if isinstance(data, list):
        return [str(x) for x in data if x]
    raise ValueError("--urls-file phải là JSON mảng URL")


def main() -> int:
    ap = argparse.ArgumentParser(description="Crawler dispatcher cho job-collector")
    ap.add_argument("--platform", required=True, help="Domain nền tảng, vd itviec.com")
    ap.add_argument("--mode", required=True, choices=["search", "fetch"])
    ap.add_argument("--query", help="(search) chuỗi tìm kiếm song ngữ")
    ap.add_argument("--max", type=int, default=20, help="(search) cận trên số candidate")
    ap.add_argument("--urls-file", help="(fetch) file JSON mảng URL, hoặc '-' cho stdin")
    ap.add_argument("--out", help="(fetch) đường dẫn ghi mảng job JSON")
    ap.add_argument("--today", help="YYYY-MM-DD ghi đè ngày hôm nay (mặc định = hệ thống)")
    args = ap.parse_args()

    today = _parse_today(args.today)
    adapter = _find_adapter(args.platform)
    if adapter is None:
        # Không có adapter → agent fallback WebFetch.
        json.dump({"error": "no_adapter", "platform": args.platform}, sys.stdout, ensure_ascii=False)
        print()
        return 3

    if args.mode == "search":
        if not args.query:
            ap.error("--mode search cần --query")
        try:
            candidates = adapter.search(args.query, args.max, today)
        except FetchError as e:
            json.dump({"error": "fetch_failed", "detail": str(e), "platform": adapter.PLATFORM},
                      sys.stdout, ensure_ascii=False)
            print()
            return 4
        candidates = dedupe_by(candidates, "url")
        json.dump({"platform": adapter.PLATFORM, "mode": "search",
                   "count": len(candidates), "candidates": candidates},
                  sys.stdout, ensure_ascii=False)
        print()
        return 0

    # mode == fetch
    if not args.urls_file:
        ap.error("--mode fetch cần --urls-file")
    urls = _load_urls(args.urls_file)
    jobs: list[dict] = []
    dropped: list[dict] = []
    for u in urls:
        try:
            jobs.append(adapter.fetch_one(u, today))
        except FetchError as e:
            dropped.append({"url": u, "reason": str(e)})
        except Exception as e:  # noqa: BLE001 — không để một URL hỏng làm gãy cả batch
            dropped.append({"url": u, "reason": f"{type(e).__name__}: {e}"})
    jobs = dedupe_by(jobs, "id")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)

    json.dump({"platform": adapter.PLATFORM, "mode": "fetch", "fetched": len(jobs),
               "dropped": dropped, "out": args.out, "collected_at": now_iso()},
              sys.stdout, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
