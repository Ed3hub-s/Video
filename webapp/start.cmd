@echo off
rem Local web app for the Course Video Generator.
rem Double-click this file, then open http://127.0.0.1:8000 in your browser.
cd /d "%~dp0.."
set "HF_HOME=%CD%\cache"
set "TMP=%CD%\.tmp"
set "TEMP=%CD%\.tmp"
if exist "%CD%\cache\hub\models--kyutai--pocket-tts-without-voice-cloning" set "HF_HUB_OFFLINE=1"
.venv\Scripts\python.exe -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
pause
