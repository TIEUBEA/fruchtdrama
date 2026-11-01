@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
if not exist ".installation-complete" goto missing
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 pause
exit /b
:missing
echo Lancez d'abord Installer.cmd. Consultez INSTALLATION.md.
pause
exit /b 1
