@echo off
setlocal
cd /d %~dp0
if "%BOOTSTRAP_ADMIN_USERNAME%"=="" (
  echo Configure BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD first.
  echo See README.md for the secure setup instructions.
  pause
  exit /b 1
)
if "%BOOTSTRAP_ADMIN_PASSWORD%"=="" (
  echo Configure BOOTSTRAP_ADMIN_PASSWORD first.
  echo See README.md for the secure setup instructions.
  pause
  exit /b 1
)
python server.py
