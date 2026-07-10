@echo off
setlocal
cd /d "%~dp0\frontend"
call npm run dev -- --host 127.0.0.1
