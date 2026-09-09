@echo off
REM Start VaaniSetu. Double click this file, or run it from the project folder.
cd /d "%~dp0"

if not exist "vaanisetu_env\Scripts\activate.bat" (
  echo Could not find vaanisetu_env. Create it first:
  echo     python -m venv vaanisetu_env
  echo     vaanisetu_env\Scripts\activate
  echo     pip install -r requirements.txt
  pause
  exit /b 1
)

call vaanisetu_env\Scripts\activate.bat

if "%1"=="verify" (
  echo Verifying the models. This loads them, so give it a minute.
  python verify_models.py
  pause
  exit /b %errorlevel%
)

echo Starting VaaniSetu. The first run loads the models, which takes a minute.
echo When it says Running on http://127.0.0.1:5000, open that in your browser.
echo.
python app.py
pause
