@echo off
setlocal
cd /d "%~dp0"
title ReguLens - Regulatory Impact and Evidence Lab

echo ========================================================
echo ReguLens - Regulatory Impact and Evidence Lab
echo ========================================================
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  set "PY=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating a local Python environment...
  %PY% -m venv .venv
  if errorlevel 1 goto error
)
call ".venv\Scripts\activate.bat"
echo [2/3] Installing / checking free dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto error
echo [3/3] Starting ReguLens. Keep this window open while using the app.
echo If the browser does not open automatically, visit http://localhost:8501
python -m streamlit run app.py
if errorlevel 1 goto error
goto end
:error
echo.
echo ReguLens could not start. Check the error above.
echo Ensure Python 3.10-3.13 (64-bit) is installed and this computer can reach the Python package index for first-time setup.
echo If your network uses a proxy, configure pip for that network and rerun this file.
pause
:end
endlocal
