# 网易云歌单追踪器 - 快速开始

## 问题解决

如果您遇到以下错误：
```
ModuleNotFoundError: No module named 'src'
```
或
```
ModuleNotFoundError: No module named 'PyQt5'
```

请按照以下步骤操作：

## 解决方案

### 方法1：使用启动脚本（最简单）
```bash
# macOS/Linux
./run.sh

# Windows
双击 run.bat
```

### 方法2：手动运行（正确方式）
```bash
# 1. 进入项目目录
cd /path/to/wyy

# 2. 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 3. 运行程序
python src/main.py

# 4. 完成后退出虚拟环境（可选）
deactivate
```

### 方法3：直接使用虚拟环境的Python
```bash
# macOS/Linux
./venv/bin/python src/main.py

# Windows
venv\Scripts\python src\main.py
```

## 错误原因

程序依赖包安装在虚拟环境（`venv/` 目录）中，但您使用了系统Python运行程序：
```bash
python3 src/main.py  # 错误：使用系统Python
```

系统Python找不到虚拟环境中的包，因此报错。

## 验证安装

检查依赖是否正确安装：
```bash
./venv/bin/python -c "import PyQt5, pyncm; print('所有依赖已安装')"
```

如果显示错误，重新安装依赖：
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## 常用命令

- **安装程序**：`./setup.sh` (macOS/Linux) 或 双击 `setup.bat` (Windows)
- **运行程序**：`./run.sh` (macOS/Linux) 或 双击 `run.bat` (Windows)
- **查看版本**：`./venv/bin/python --version`

## 新功能提示

### RSS式已读/未读管理
1. **新专辑自动标记为未读**（黑色加粗显示）
2. **点击专辑行标记为已读**（变为灰色）
3. **一键标记所有为已读**（使用"标记为已读"按钮）

### 快捷操作
1. **点击左侧历史歌单**：自动加载缓存数据并填入ID
2. **右键点击歌单**：删除历史记录
3. **粘贴链接**：自动提取歌单ID

### 离线查看
即使没有网络，也可以查看之前缓存的历史歌单数据。

## 获取帮助

如问题仍未解决：
1. 查看 README.md 中的详细说明
2. 检查虚拟环境是否存在：
   ```bash
   ls -la venv/
   ```
3. 确保已安装所有依赖：
   ```bash
   pip list | grep -E "(PyQt5|pyncm|requests)"
   ```

---

**记住：始终使用启动脚本或先激活虚拟环境再运行程序！**