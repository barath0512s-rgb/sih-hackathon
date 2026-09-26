@echo off
REM Start Nijbhasha (formerly VaaniSetu). Double click this file, or run it from the project folder.
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

if "%1"=="https" (
  echo Starting the laptop hub over HTTPS, so tablets on this Wi-Fi can use the microphone.
  echo The first run loads the models, which takes a minute.
  echo On the tablet, open the https address printed below. See README, "Laptop hub".
  echo.
  python app.py --https
  pause
  exit /b %errorlevel%
)

echo Starting Nijbhasha. The first run loads the models, which takes a minute.
echo When it says Running on http://127.0.0.1:5000, open that in your browser.
echo.
python app.py
pause
