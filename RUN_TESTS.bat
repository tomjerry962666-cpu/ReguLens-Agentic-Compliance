@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run START_REGULENS.bat once first.& pause & exit /b 1)
call ".venv\Scripts\activate.bat"
python -m unittest discover -s tests -v
pause
