@echo off
wsl -d Ubuntu -- bash -lc "cd ~/CategoryBrain && ./scripts/manage.sh status"
pause