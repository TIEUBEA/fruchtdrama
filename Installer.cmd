@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -m venv ".venv"
if errorlevel 1 goto failed
goto install
:python
where python >nul 2>nul
if errorlevel 1 goto missing
python -m venv ".venv"
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" installer.py
if errorlevel 1 goto failed
pause
exit /b 0
:missing
echo Installez Python 3.11 ou 3.12 64 bits depuis python.org, avec Add python.exe to PATH.
goto failed
:failed
echo Installation incomplete. Consultez le message ci-dessus et INSTALLATION.md.
pause
exit /b 1
