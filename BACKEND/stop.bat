@echo off
title NEXURA Scanner — To'xtatish
echo To'xtatilmoqda...
taskkill /f /im python.exe /fi "WINDOWTITLE eq NEXURA*" 2>nul
taskkill /f /im node.exe /fi "WINDOWTITLE eq NEXURA*" 2>nul
echo NEXURA to'xtatildi.
timeout /t 2 /nobreak >nul
