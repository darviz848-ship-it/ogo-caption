@echo off
title OgoCaption - Ornatuvchi
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo Ornatish tugamadi. Yuqoridagi xatoni oqing.
  pause
)
