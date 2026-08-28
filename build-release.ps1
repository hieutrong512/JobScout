# build-release.ps1 — đóng gói plugin JobMatching thành 1 file .zip tải-về-là-dùng
#   (dùng được ở CẢ Claude Code lẫn Codex).
# Cách chạy:  powershell -ExecutionPolicy Bypass -File .\build-release.ps1
# Yêu cầu: chạy trong repo git; đóng gói theo HEAD đã commit (git archive).

$ErrorActionPreference = "Stop"

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$manifest = Get-Content "job-matching-plugin/.claude-plugin/plugin.json" -Raw | ConvertFrom-Json
$version  = $manifest.version
$name     = $manifest.name

New-Item -ItemType Directory -Force -Path "dist" | Out-Null
$outFile = "dist/$name-v$version.zip"

# git archive: chỉ gồm file đã tracked ở HEAD (tự loại data/profiles, .auth, __pycache__...).
git archive --format=zip --prefix="$name-v$version/" -o $outFile HEAD

$full = (Resolve-Path $outFile).Path
$size = "{0:N1} KB" -f ((Get-Item $outFile).Length / 1KB)
Write-Host ""
Write-Host "OK  Đã tạo package: $full ($size)" -ForegroundColor Green
Write-Host "    - Claude Code : giải nén, rồi /plugin marketplace add <thư-mục-giải-nén>"
Write-Host "    - Codex       : trỏ plugin tới <thư-mục-giải-nén>/job-matching-plugin"
