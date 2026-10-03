@echo off
setlocal
cd /d "%~dp0"
title 云枢 (YunShu) - Web 控制中心

echo ====================================================================
echo   云枢 (YunShu) - 多品牌服务器温控与集群监控 Web 版
echo ====================================================================
echo.

python -c "import bottle" >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Python 运行环境已就绪，正在启动 Web 控制中心...
    python run_web.py %*
    goto finish
)

py -3.11 -c "import bottle" >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Python 3.11 运行环境已就绪，正在启动 Web 控制中心...
    py -3.11 run_web.py %*
    goto finish
)

py run_web.py %*
if %errorlevel% equ 0 goto finish

echo.
echo ====================================================================
echo [错误] 启动失败，未检测到完整的 Python 运行依赖库！
echo 请在命令行中执行依赖安装：
echo   pip install bottle paramiko cryptography bcrypt
echo ====================================================================

:finish
echo.
pause
