@echo off
setlocal enabledelayedexpansion

:: === CONFIGURATION ===
set APP_NAME=MyPointCards
set EXEC_FILE=%APP_NAME%.exe
set HTML_FILE=mypointcards-v1.html
set ICON_FILE=pc.ico
set PORT=8000

:: === BEGIN BUILD ===
echo ----------------------------------------
echo 🔄 Cleaning up old instance...
tasklist | find /i "%EXEC_FILE%" >nul 2>&1
if %errorlevel%==0 (
    taskkill /f /im "%EXEC_FILE%" >nul
    echo ✅ Killed old process: %EXEC_FILE%
) else (
    echo ℹ️  No running instance found
)

echo ----------------------------------------
echo 🗑 Deleting previous executable if it exists...
if exist "%EXEC_FILE%" (
    del /f "%EXEC_FILE%" >nul
    echo ✅ Deleted: %EXEC_FILE%
) else (
    echo ℹ️  No existing executable to delete
)

echo ----------------------------------------
echo ⚙️  Building new executable...

:: Validate input files
if not exist "%HTML_FILE%" (
    echo ❌ HTML file not found: %HTML_FILE%
    exit /b 1
)

if not exist "%ICON_FILE%" (
    echo ❌ Icon file not found: %ICON_FILE%
    exit /b 1
)

python make_windows_exe.py --html "%HTML_FILE%" --exec "%EXEC_FILE%" --port %PORT% --icon "%ICON_FILE%"
if %errorlevel% neq 0 (
    echo ❌ Build failed.
    exit /b 1
)

echo ----------------------------------------
echo ✅ Build complete: %EXEC_FILE%
echo ----------------------------------------

:: Optional: pause for user to see results
:: pause

