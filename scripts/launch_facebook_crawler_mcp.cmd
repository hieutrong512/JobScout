@echo off
setlocal

if defined JOB_MATCHING_PYTHON (
  "%JOB_MATCHING_PYTHON%" "%~dp0..\mcp\facebook_crawler_server.py"
  exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import playwright" >nul 2>nul
  if not errorlevel 1 (
    py -3 "%~dp0..\mcp\facebook_crawler_server.py"
    exit /b %errorlevel%
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "import playwright" >nul 2>nul
  if not errorlevel 1 (
    python "%~dp0..\mcp\facebook_crawler_server.py"
    exit /b %errorlevel%
  )
)

echo JobMatching: no Python interpreter with Playwright was found. 1>&2
echo Install Playwright or set JOB_MATCHING_PYTHON to the correct python.exe. 1>&2
exit /b 1
