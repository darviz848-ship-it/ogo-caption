@echo off
title OgoCaption - Orqaga qaytarish
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update.ps1" -Restore
if errorlevel 1 (
  echo.
  echo Qaytarish tugamadi. Yuqoridagi xatoni oqing.
  pause
)
