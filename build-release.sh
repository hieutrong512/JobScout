#!/usr/bin/env bash
# build-release.sh — đóng gói plugin JobMatching thành 1 file .zip tải-về-là-dùng
#   (dùng được ở CẢ Claude Code lẫn Codex).
# Cách chạy:  bash build-release.sh
# Yêu cầu: chạy trong repo git; đóng gói theo HEAD đã commit (git archive).
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

manifest="job-matching-plugin/.claude-plugin/plugin.json"
version="$(grep -m1 '"version"' "$manifest" | sed -E 's/.*"version"\s*:\s*"([^"]+)".*/\1/')"
name="$(grep -m1 '"name"' "$manifest" | sed -E 's/.*"name"\s*:\s*"([^"]+)".*/\1/')"

mkdir -p dist
out="dist/${name}-v${version}.zip"

# git archive: chỉ gồm file đã tracked ở HEAD (tự loại data/profiles, .auth, __pycache__...).
git archive --format=zip --prefix="${name}-v${version}/" -o "$out" HEAD

size="$(du -h "$out" | cut -f1)"
echo ""
echo "OK  Đã tạo package: $repo_root/$out ($size)"
echo "    - Claude Code : giải nén, rồi /plugin marketplace add <thư-mục-giải-nén>"
echo "    - Codex       : trỏ plugin tới <thư-mục-giải-nén>/job-matching-plugin"
