@echo off
REM 网易云歌单追踪器安装脚本（Windows）

echo === 网易云歌单追踪器安装程序 ===
echo.

REM 检查Python
where python >nul 2>nul
if errorlevel 1 (
    echo 错误：未找到 Python。请先安装 Python 3.8 或更高版本。
    echo 访问 https://www.python.org/downloads/ 下载安装程序。
    echo 安装时请勾选 "Add Python to PATH"。
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>nul') do set python_version=%%i
echo 检测到 Python 版本: %python_version%

REM 进入脚本所在目录
cd /d "%~dp0"
echo 工作目录: %cd%

REM 创建虚拟环境
echo.
echo 正在创建虚拟环境...
if not exist "venv\" (
    python -m venv venv
    if errorlevel 1 (
        echo 错误：创建虚拟环境失败。
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功。
) else (
    echo 虚拟环境已存在，跳过创建。
)

REM 激活虚拟环境
echo.
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 错误：激活虚拟环境失败。
    pause
    exit /b 1
)
echo 虚拟环境已激活。

REM 升级pip
echo.
echo 正在升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
echo.
echo 正在安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误：安装依赖失败。
    pause
    exit /b 1
)
echo 依赖包安装成功。

REM 验证安装
echo.
echo 正在验证安装...
python -c "import PyQt5, pyncm, requests, customtkinter; print('所有依赖验证通过')" 2>nul
if errorlevel 1 (
    echo ❌ 依赖验证失败。
    pause
    exit /b 1
) else (
    echo ✅ 所有依赖验证通过。
)

REM 创建数据目录
echo.
echo 正在创建数据目录...
if not exist "data\" mkdir data
echo 数据目录创建成功。

echo.
echo === 安装完成！ ===
echo.
echo 启动程序：
echo  双击 run.bat          # Windows
echo  或
echo  打开命令提示符，切换到本目录，运行 run.bat
echo.
echo 如需卸载，删除整个文件夹即可。
echo.
pause