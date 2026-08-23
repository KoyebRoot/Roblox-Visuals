@echo off
title Install

echo [*] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found! Please install Python 3.8+
    echo     Download from: https://python.org/downloads
    pause
    exit /b 1
)
echo [✔] Python found

echo [*] Installing requests...
python -m pip install requests --quiet
echo [✔] Requests installed

echo [*] Installing numpy...
python -m pip install numpy --quiet
echo [✔] Numpy installed

echo [*] Installing pywin32...
python -m pip install pywin32 --quiet
echo [✔] PyWin32 installed

echo [*] Installing pymem...
python -m pip install pymem --quiet
echo [✔] PyMem installed

echo [*] Downloading pyMeow...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/qb-0/pyMeow/releases/download/1.73.42/pyMeow-1.73.42.zip' -OutFile 'pyMeow-1.73.42.zip'" >nul 2>&1
echo [✔] Download complete

echo [*] Installing pyMeow...
python -m pip install pyMeow-1.73.42.zip --quiet
echo [✔] PyMeow installed

echo [*] Cleaning up...
del pyMeow-1.73.42.zip >nul 2>&1
echo [✔] Cleanup complete