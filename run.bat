@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 goto failed
py app.py
if errorlevel 1 goto failed
exit /b
:failed
echo Khong chay duoc. Can cai Python 3.11+ va Python Launcher.
pause
