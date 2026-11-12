@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo ==== %date% %time% start ==== >> logs\task.log
python fetch.py --days 3 --once-per-day >> logs\task.log 2>&1
echo ==== %date% %time% exit=%errorlevel% ==== >> logs\task.log
