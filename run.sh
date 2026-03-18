#!/bin/bash
# 网易云歌单追踪器启动脚本（macOS/Linux）

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "错误：虚拟环境不存在。请先运行 setup.sh 或手动创建虚拟环境。"
    echo "运行：python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    # Windows (Git Bash)
    source venv/Scripts/activate
else
    echo "错误：找不到虚拟环境激活脚本。"
    exit 1
fi

# 检查依赖是否安装
if ! python -c "import PyQt5" 2>/dev/null; then
    echo "警告：PyQt5 未安装。正在安装依赖..."
    pip install -r requirements.txt
fi

# 运行主程序
python src/main.py

# 程序结束后停用虚拟环境（可选）
deactivate 2>/dev/null || true