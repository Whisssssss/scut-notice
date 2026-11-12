@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  华工通知抓取  %date% %time%
echo ============================================
python fetch.py %*
echo.
echo 完成。简报在 digest 文件夹里。
pause
