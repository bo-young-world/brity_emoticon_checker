@echo off
rem ============================================================
rem  Emoticon checker - build single exe (run on online dev PC)
rem  Requires: pip install pyinstaller
rem  Output  : dist\emoticon_checker_v03.exe
rem ============================================================
cd /d "%~dp0"

set "PYINSTALLER=%~dp0.venv\Scripts\pyinstaller.exe"
if not exist "%PYINSTALLER%" (
    where pyinstaller >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] pyinstaller not found. Run: .venv\Scripts\python.exe -m pip install pyinstaller
        pause
        exit /b 1
    )
    set "PYINSTALLER=pyinstaller"
)

"%PYINSTALLER%" --clean --noconfirm emoticon_checker.spec
if errorlevel 1 (
    echo [ERROR] build failed.
    pause
    exit /b 1
)

echo.
echo [OK] build done: dist\emoticon_checker_v03.exe
pause
