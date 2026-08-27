#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convenience entrypoint for scripts/fb_crawler.py
Cho phép chạy trực tiếp: python fb_crawler.py ...
"""
import sys
from pathlib import Path

# Thêm thư mục scripts vào sys.path
scripts_dir = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from fb_crawler import main

if __name__ == "__main__":
    main()
