@echo off
REM 网易云歌单追踪器启动脚本（Windows）

REM 进入脚本所在目录
cd /d "%~dp0"

REM 检查虚拟环境是否存在
if not exist "venv\" (
    echo 错误：虚拟环境不存在。请先运行 setup.bat 或手动创建虚拟环境。
    echo 运行：python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 错误：激活虚拟环境失败。
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import PyQt5" 2>nul
if errorlevel 1 (
    echo 警告：PyQt5 未安装。正在安装依赖...
    pip install -r requirements.txt
)

REM 运行主程序
python src\main.py

REM 程序结束后停用虚拟环境
call venv\Scripts\deactivate.bat 2>nul