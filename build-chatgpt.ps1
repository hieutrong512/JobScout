# build-chatgpt.ps1 — gom bộ file "Knowledge" để upload vào Custom GPT / ChatGPT Project.
#   Flatten skills/*/SKILL.md và copy schemas + orchestrator vào dist/chatgpt-knowledge/.
# Cách chạy:  powershell -ExecutionPolicy Bypass -File .\build-chatgpt.ps1

$ErrorActionPreference = "Stop"

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$plugin = "job-matching-plugin"
$out    = "dist/chatgpt-knowledge"

if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force -Path $out | Out-Null

# Orchestrator (cũng dùng làm knowledge để GPT tham chiếu).
Copy-Item "chatgpt/GPT-INSTRUCTIONS.md" "$out/00-orchestrator.md"

# Flatten từng skill: skills/<name>/SKILL.md -> skill-<name>.md
Get-ChildItem "$plugin/skills" -Directory | ForEach-Object {
  Copy-Item "$($_.FullName)/SKILL.md" "$out/skill-$($_.Name).md"
}

# Data contracts.
Copy-Item "$plugin/schemas/*.json" $out

$count = (Get-ChildItem $out -File).Count
Write-Host ""
Write-Host "OK  Bộ knowledge ($count file): $((Resolve-Path $out).Path)" -ForegroundColor Green
Write-Host "    Kéo-thả TẤT CẢ file vào mục Knowledge cua Custom GPT (nhớ bật Web Search)."
