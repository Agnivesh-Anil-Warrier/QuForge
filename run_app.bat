@echo off
cd /d "%~dp0"
echo Launching QForge Studio Desktop App...
.\.venv\Scripts\python.exe app.py
pause
