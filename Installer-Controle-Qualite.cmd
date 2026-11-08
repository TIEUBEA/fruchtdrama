@echo off
python -m pip install --upgrade --target "%~dp0.qc-runtime" -r "%~dp0requirements-quality.txt"
if errorlevel 1 exit /b 1
python "%~dp0quality_setup.py"
pause
