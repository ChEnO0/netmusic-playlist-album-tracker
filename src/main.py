#!/usr/bin/env python3
"""
网易云歌单追踪器 - 主入口点
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 优先使用 PyQt5 版本
from gui_qt import main

if __name__ == '__main__':
    main()