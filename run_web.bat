@echo off
title QForge Quantum Studio Web
echo Launching QForge Web Studio on http://localhost:8501 ...
.\.venv\Scripts\streamlit.exe run app_web.py --server.port 8501 --server.headless false
pause
