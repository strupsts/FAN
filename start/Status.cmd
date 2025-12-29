@echo off
cd /d "%USERPROFILE%"
wsl -d Ubuntu -- bash -lc "cd ~/FAN && ./scripts/manage.sh status"
pause