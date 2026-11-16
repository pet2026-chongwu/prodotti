@echo off
cd /d "%~dp0"
py aggiorna_catalogo.py
if errorlevel 1 echo Update failed. Check Python, Pillow and the selected files.
pause
