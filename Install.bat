@echo off
title Install

echo [*] Checking Python architecture...
python -c "import struct; print(struct.calcsize('P') * 8)" >nul 2>&1
python -c "import struct; print(struct.calcsize('P') * 8)" > arch.txt
set /p PYTHON_ARCH=<arch.txt
del arch.txt

if "%PYTHON_ARCH%"=="32" (
    echo [X] You have 32-bit Python installed!
    echo     pyMeow requires 64-bit Python.
    echo.
    echo [*] Installing 64-bit Python...
    echo     Downloading Python 3.13 64-bit...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe' -OutFile 'python_installer.exe'"
    echo [*] Running installer...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python_installer.exe
    echo [✔] Python 64-bit installed
    echo.
    echo [*] Please restart this script or run it again.
    pause
    exit /b 1
)

echo [✔] Python 64-bit found
echo.

echo [*] Installing required packages...
python -m pip install requests numpy pywin32 pymem --upgrade --quiet
echo [✔] Required packages installed

echo [*] Downloading pyMeow 64-bit...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/qb-0/pyMeow/releases/download/1.73.42/pyMeow-1.73.42.zip' -OutFile 'pyMeow-1.73.42.zip'" >nul 2>&1
echo [✔] Download complete

echo [*] Installing pyMeow...
python -m pip install pyMeow-1.73.42.zip --force-reinstall --no-deps --quiet
echo [✔] PyMeow installed

echo [*] Cleaning up...
del pyMeow-1.73.42.zip >nul 2>&1
echo [✔] Cleanup complete
pause
