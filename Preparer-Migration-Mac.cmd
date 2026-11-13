@echo off
setlocal
cd /d "%~dp0"
echo Preparation des archives pour le Mac (le PC n est pas modifie)...
".venv\Scripts\python.exe" preparer_migration_mac.py %*
if errorlevel 1 echo Preparation incomplete : voir le message ci-dessus.
pause
