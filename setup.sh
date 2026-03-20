#!/bin/bash
# 网易云歌单追踪器安装脚本（macOS/Linux）

echo "=== 网易云歌单追踪器安装程序 ==="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 Python3。请先安装 Python 3.8 或更高版本。"
    echo "macOS: brew install python@3.13"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
echo "检测到 Python 版本: $python_version"

# 进入脚本所在目录
cd "$(dirname "$0")"
echo "工作目录: $(pwd)"

# 创建虚拟环境
echo ""
echo "正在创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误：创建虚拟环境失败。"
        exit 1
    fi
    echo "虚拟环境创建成功。"
else
    echo "虚拟环境已存在，跳过创建。"
fi

# 激活虚拟环境
echo ""
echo "正在激活虚拟环境..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "错误：激活虚拟环境失败。"
    exit 1
fi
echo "虚拟环境已激活。"

# 升级pip
echo ""
echo "正在升级 pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "正在安装依赖包..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误：安装依赖失败。"
    exit 1
fi
echo "依赖包安装成功。"

# 验证安装
echo ""
echo "正在验证安装..."
if python -c "import PyQt5, pyncm, requests; print('所有依赖验证通过')" 2>/dev/null; then
    echo "✅ 所有依赖验证通过。"
else
    echo "❌ 依赖验证失败。请检查上方输出。"
    exit 1
fi

# 创建数据目录
echo ""
echo "正在创建数据目录..."
mkdir -p data
echo "数据目录创建成功。"

echo ""
echo "=== 安装完成！ ==="
echo ""
echo "启动程序："
echo "  ./run.sh           # macOS/Linux"
echo "  或"
echo "  source venv/bin/activate && python src/main.py"
echo ""
echo "如需卸载，删除整个文件夹即可。"
echo ""