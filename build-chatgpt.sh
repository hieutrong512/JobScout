#!/usr/bin/env bash
# build-chatgpt.sh — gom bộ file "Knowledge" để upload vào Custom GPT / ChatGPT Project.
#   Flatten skills/*/SKILL.md và copy schemas + orchestrator vào dist/chatgpt-knowledge/.
# Cách chạy:  bash build-chatgpt.sh
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

plugin="job-matching-plugin"
out="dist/chatgpt-knowledge"

rm -rf "$out"
mkdir -p "$out"

# Orchestrator (cũng dùng làm knowledge để GPT tham chiếu).
cp chatgpt/GPT-INSTRUCTIONS.md "$out/00-orchestrator.md"

# Flatten từng skill: skills/<name>/SKILL.md -> skill-<name>.md
for d in "$plugin"/skills/*/; do
  name="$(basename "$d")"
  cp "$d/SKILL.md" "$out/skill-${name}.md"
done

# Data contracts.
cp "$plugin"/schemas/*.json "$out/"

count="$(find "$out" -type f | wc -l | tr -d ' ')"
echo ""
echo "OK  Bộ knowledge ($count file): $repo_root/$out"
echo "    Kéo-thả TẤT CẢ file vào mục Knowledge của Custom GPT (nhớ bật Web Search)."
