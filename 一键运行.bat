@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================
echo   Forge Pulse - 开源星榜
echo   采集 =^> 算涨星 =^> 生成看板
echo ================================
echo.
python src\main.py --all
echo.
pause
