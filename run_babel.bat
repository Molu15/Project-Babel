@echo off
:: Check for permissions
NET SESSION >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    ECHO Administrator Privileges Detected! 
) ELSE (
    ECHO Requesting Administrative Privileges...
    PowerShell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    EXIT /B
)

:: Change to the script's directory
cd /d "%~dp0"

:: Run the application silently
start "" pythonw src/main.py
