@echo off
rem JoJo Eyes of Heaven Korean patch v{{VERSION}} - runs install.ps1 (menu + folder picker)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
pause
