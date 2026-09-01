@echo off
set PYTHON_EXE=p:\dev\misc\android\TVBox\FongMiTV\mypathon\python\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo ============================================================
echo Running Dm84 Crawler Validator...
echo ============================================================
"%PYTHON_EXE%" "%~dp0validate_crawler.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Crawler validation failed!
    echo Running self-healing diagnostics...
    echo ============================================================
    "%PYTHON_EXE%" "%~dp0self_heal.py"
) else (
    echo.
    echo [SUCCESS] Dm84 crawler validation passed successfully.
)
echo.
pause
