#!/usr/bin/env python3
"""
PyQt5 GUI 界面
"""
import sys
import threading
import time
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QStatusBar, QMessageBox,
                             QGroupBox, QGridLayout, QProgressBar, QFileDialog, QComboBox,
                             QCheckBox, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QClipboard, QFont, QColor

from playlist_tracker import PlaylistTracker
from storage import get_storage

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(dict)
    status = pyqtSignal(str)

class PlaylistWorker(QThread):
    def __init__(self, tracker, storage, playlist_id, mode='fetch'):
        super().__init__()
        self.tracker = tracker
        self.storage = storage
        self.playlist_id = playlist_id
        self.mode = mode
        self.signals = WorkerSignals()
    
    def run(self):
        try:
            if self.mode == 'fetch':
                self.signals.status.emit("正在获取歌单信息...")
                playlist_info = self.tracker.get_playlist_info(self.playlist_id)
                if not playlist_info:
                    self.signals.error.emit("获取歌单信息失败")
                    return
                
                self.storage.update_playlist_history(self.playlist_id, playlist_info)
                tracks = self.tracker.get_playlist_tracks(self.playlist_id)
                albums = self.tracker.get_all_albums_from_playlist(self.playlist_id, tracks=tracks)
                
                # 为每个专辑添加链接信息
                for album in albums:
                    album['link'] = self.tracker.generate_album_link(album['album_id'])
                
                # 更新专辑快照并获取未读专辑
                album_ids = [album['album_id'] for album in albums]
                self.storage.update_album_snapshot(self.playlist_id, album_ids, albums)
                unread_album_ids = self.storage.get_unread_albums(self.playlist_id)
                
                result = {
                    'playlist_info': playlist_info,
                    'albums': albums,
                    'tracks_count': len(tracks),
                    'unread_album_ids': unread_album_ids
                }
                self.signals.result.emit(result)
                self.signals.status.emit("获取完成")
                
            elif self.mode == 'check_update':
                self.signals.status.emit("正在检查更新...")
                last_update_time = self.storage.get_last_update_time(self.playlist_id)
                update_result = self.tracker.check_for_updates(self.playlist_id, last_update_time)
                
                if update_result['has_update']:
                    playlist_info = self.tracker.get_playlist_info(self.playlist_id)
                    if playlist_info:
                        self.storage.update_playlist_history(self.playlist_id, playlist_info)
                        tracks = self.tracker.get_playlist_tracks(self.playlist_id)
                        albums = self.tracker.get_all_albums_from_playlist(self.playlist_id, tracks=tracks)
                        
                        # 为每个专辑添加链接信息
                        for album in albums:
                            album['link'] = self.tracker.generate_album_link(album['album_id'])
                        
                        # 更新专辑快照并获取未读专辑
                        album_ids = [album['album_id'] for album in albums]
                        self.storage.update_album_snapshot(self.playlist_id, album_ids, albums)
                        unread_album_ids = self.storage.get_unread_albums(self.playlist_id)
                        
                        result = {
                            'playlist_info': playlist_info,
                            'albums': albums,
                            'update_message': update_result['message'],
                            'tracks_count': len(tracks),
                            'unread_album_ids': unread_album_ids
                        }
                        self.signals.result.emit(result)
                    else:
                        self.signals.error.emit("获取更新信息失败")
                else:
                    self.signals.result.emit({'update_message': update_result['message']})
                
                self.signals.status.emit("检查完成")
        
        except Exception as e:
            self.signals.error.emit(str(e))

class PlaylistTrackerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tracker = PlaylistTracker()
        self.storage = get_storage()
        self.current_albums = []
        self.current_playlist_info = None
        self.current_playlist_id = None
        self.unread_album_ids = []
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("网易云歌单追踪器")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧边栏：历史歌单
        sidebar_group = QGroupBox("历史歌单")
        sidebar_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(2)
        self.history_table.setHorizontalHeaderLabels(["歌单名称", "专辑数"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 启用右键菜单
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_history_context_menu)
        # 连接选择变化信号
        self.history_table.itemSelectionChanged.connect(self.on_history_selection_changed)
        sidebar_layout.addWidget(self.history_table)
        
        # 历史歌单操作按钮
        history_button_layout = QHBoxLayout()
        self.refresh_history_button = QPushButton("刷新历史")
        self.refresh_history_button.clicked.connect(self.load_history_table)
        history_button_layout.addWidget(self.refresh_history_button)
        
        self.clear_all_history_button = QPushButton("清除所有历史")
        self.clear_all_history_button.clicked.connect(self.clear_all_history)
        history_button_layout.addWidget(self.clear_all_history_button)
        
        sidebar_layout.addLayout(history_button_layout)
        sidebar_group.setLayout(sidebar_layout)
        main_layout.addWidget(sidebar_group, 1)  # 左侧边栏占1份
        
        # 右侧主内容区域
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # 顶部控制区域
        control_group = QGroupBox("歌单控制")
        control_layout = QGridLayout()
        
        # 第0行：链接提取
        control_layout.addWidget(QLabel("歌单链接:"), 0, 0)
        self.playlist_link_input = QLineEdit()
        self.playlist_link_input.setPlaceholderText("粘贴网易云歌单链接，如: https://music.163.com/playlist?id=123456")
        control_layout.addWidget(self.playlist_link_input, 0, 1, 1, 3)  # 跨3列
        
        self.extract_button = QPushButton("提取ID")
        self.extract_button.clicked.connect(self.extract_playlist_id)
        control_layout.addWidget(self.extract_button, 0, 4)
        
        # 第1行：歌单ID和历史查询
        control_layout.addWidget(QLabel("歌单ID:"), 1, 0)
        self.playlist_id_input = QLineEdit()
        self.playlist_id_input.setText("3778678")
        control_layout.addWidget(self.playlist_id_input, 1, 1)
        
        # 历史记录下拉框（保留，便于快速选择）
        self.history_combo = QComboBox()
        self.history_combo.setPlaceholderText("历史查询记录")
        self.history_combo.currentIndexChanged.connect(self.on_history_selected)
        control_layout.addWidget(self.history_combo, 1, 2)
        
        self.fetch_button = QPushButton("获取歌单信息")
        self.fetch_button.clicked.connect(self.fetch_playlist)
        control_layout.addWidget(self.fetch_button, 1, 3)
        
        self.check_button = QPushButton("检查更新")
        self.check_button.clicked.connect(self.check_updates)
        control_layout.addWidget(self.check_button, 1, 4)
        
        self.clear_button = QPushButton("清除")
        self.clear_button.clicked.connect(self.clear_display)
        control_layout.addWidget(self.clear_button, 1, 5)
        
        control_group.setLayout(control_layout)
        right_layout.addWidget(control_group)
        
        # 歌单信息区域
        info_group = QGroupBox("歌单信息")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        # 专辑信息区域
        album_group = QGroupBox("专辑信息")
        album_layout = QVBoxLayout()
        
        self.album_table = QTableWidget()
        self.album_table.setColumnCount(3)
        self.album_table.setHorizontalHeaderLabels(["专辑名称", "艺术家", "链接"])
        self.album_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.album_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.album_table.itemClicked.connect(self.on_album_item_clicked)
        album_layout.addWidget(self.album_table)
        
        # 专辑操作按钮
        button_layout = QHBoxLayout()
        self.copy_button = QPushButton("复制选中链接")
        self.copy_button.clicked.connect(self.copy_selected_link)
        button_layout.addWidget(self.copy_button)
        
        self.open_button = QPushButton("打开选中链接")
        self.open_button.clicked.connect(self.open_selected_link)
        button_layout.addWidget(self.open_button)
        
        self.export_button = QPushButton("导出专辑列表")
        self.export_button.clicked.connect(self.export_album_list)
        button_layout.addWidget(self.export_button)
        
        self.mark_read_button = QPushButton("标记为已读")
        self.mark_read_button.clicked.connect(self.mark_all_as_read)
        self.mark_read_button.setEnabled(False)
        button_layout.addWidget(self.mark_read_button)
        
        album_layout.addLayout(button_layout)
        album_group.setLayout(album_layout)
        right_layout.addWidget(album_group)
        
        # 进度条（隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(right_widget, 3)  # 右侧内容占3份
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 加载历史记录
        self.load_history()
        self.load_history_table()
    
    def fetch_playlist(self):
        playlist_id = self.playlist_id_input.text().strip()
        if not playlist_id:
            QMessageBox.warning(self, "警告", "请输入歌单ID")
            return
        
        self.current_playlist_id = playlist_id
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        
        self.worker = PlaylistWorker(self.tracker, self.storage, playlist_id, 'fetch')
        self.worker.signals.result.connect(self.handle_fetch_result)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.status.connect(self.status_bar.showMessage)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()
    
    def check_updates(self):
        playlist_id = self.playlist_id_input.text().strip()
        if not playlist_id:
            QMessageBox.warning(self, "警告", "请输入歌单ID")
            return
        
        self.current_playlist_id = playlist_id
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        
        self.worker = PlaylistWorker(self.tracker, self.storage, playlist_id, 'check_update')
        self.worker.signals.result.connect(self.handle_check_result)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.status.connect(self.status_bar.showMessage)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()
    
    def handle_fetch_result(self, result):
        playlist_info = result['playlist_info']
        albums = result['albums']
        unread_album_ids = result.get('unread_album_ids', [])
        self.current_albums = albums
        self.current_playlist_info = playlist_info
        
        self.update_playlist_info_display(playlist_info)
        self.update_album_table(albums, unread_album_ids)
        
        # 更新"标记为已读"按钮状态
        has_unread = len(unread_album_ids) > 0
        self.mark_read_button.setEnabled(has_unread)
        
        self.status_bar.showMessage("获取完成")
        # 刷新历史记录列表
        self.load_history()
        self.load_history_table()
    
    def handle_check_result(self, result):
        if 'update_message' in result:
            QMessageBox.information(self, "检查结果", result['update_message'])
        
        if 'playlist_info' in result:
            playlist_info = result['playlist_info']
            albums = result['albums']
            unread_album_ids = result.get('unread_album_ids', [])
            self.current_albums = albums
            self.current_playlist_info = playlist_info
            
            self.update_playlist_info_display(playlist_info)
            self.update_album_table(albums, unread_album_ids)
            
            # 更新"标记为已读"按钮状态
            has_unread = len(unread_album_ids) > 0
            self.mark_read_button.setEnabled(has_unread)
        
        self.status_bar.showMessage("检查完成")
        # 刷新历史记录列表
        self.load_history()
        self.load_history_table()
    
    def handle_error(self, error_msg):
        QMessageBox.critical(self, "错误", error_msg)
        self.status_bar.showMessage("操作失败")
    
    def worker_finished(self):
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
    
    def set_ui_enabled(self, enabled):
        self.fetch_button.setEnabled(enabled)
        self.check_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.copy_button.setEnabled(enabled)
        self.open_button.setEnabled(enabled)
        self.export_button.setEnabled(enabled)
    
    def update_playlist_info_display(self, playlist_info):
        # 获取当前歌单ID（可能来自输入框或选择）
        playlist_id = self.current_playlist_id or playlist_info.get('id', '未知')
        info_text = f"""歌单ID: {playlist_id}
歌单名称: {playlist_info.get('name', '未知')}
歌单描述: {playlist_info.get('description', '无描述')}
歌曲数量: {playlist_info.get('trackCount', 0)}
播放次数: {playlist_info.get('playCount', 0)}
收藏数: {playlist_info.get('subscribedCount', 0)}
分享数: {playlist_info.get('shareCount', 0)}
评论数: {playlist_info.get('commentCount', 0)}
创建时间: {self.format_timestamp(playlist_info.get('createTime'))}
更新时间: {self.format_timestamp(playlist_info.get('updateTime'))}
创建者: {playlist_info.get('creator', {}).get('nickname', '未知')}
"""
        self.info_text.setText(info_text)
    
    def format_timestamp(self, timestamp):
        if not timestamp:
            return "未知"
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp/1000))
        except:
            return str(timestamp)
    
    def update_album_table(self, albums, unread_album_ids=None):
        self.album_table.setRowCount(len(albums))
        self.unread_album_ids = unread_album_ids or []
        
        # 创建字体样式
        unread_font = QFont()
        unread_font.setBold(True)
        unread_font.setWeight(QFont.Bold)
        
        # 已读颜色：灰色
        read_color = QColor('gray')
        
        for row, album in enumerate(albums):
            # 处理艺术家信息
            artists_list = album.get('artists', [])
            if artists_list and isinstance(artists_list[0], dict):
                # 格式: [{'name': '艺术家1'}, {'name': '艺术家2'}]
                artists = ", ".join([artist.get('name', '') for artist in artists_list])
            elif artists_list and isinstance(artists_list[0], str):
                # 格式: ['艺术家1', '艺术家2']
                artists = ", ".join(artists_list)
            else:
                artists = ""
            
            # 处理链接：优先使用存储的链接，否则生成
            link = album.get('link', '')
            if not link and 'album_id' in album:
                link = self.tracker.generate_album_link(album['album_id'])
            
            album_id = album['album_id']
            is_unread = album_id in self.unread_album_ids
            
            # 专辑名称
            name_item = QTableWidgetItem(album['album_name'])
            if is_unread:
                name_item.setFont(unread_font)
                # 未读：黑色加粗（默认黑色，只加粗）
            else:
                # 已读：灰色
                name_item.setForeground(read_color)
            self.album_table.setItem(row, 0, name_item)
            
            # 艺术家
            artist_item = QTableWidgetItem(artists)
            if is_unread:
                artist_item.setFont(unread_font)
            else:
                artist_item.setForeground(read_color)
            self.album_table.setItem(row, 1, artist_item)
            
            # 链接
            link_item = QTableWidgetItem(link)
            if is_unread:
                link_item.setFont(unread_font)
            else:
                link_item.setForeground(read_color)
            self.album_table.setItem(row, 2, link_item)
    
    def copy_selected_link(self):
        selected_items = self.album_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个专辑")
            return
        
        row = selected_items[0].row()
        link_item = self.album_table.item(row, 2)
        if link_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(link_item.text())
            self.status_bar.showMessage("链接已复制到剪贴板")
    
    def open_selected_link(self):
        selected_items = self.album_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个专辑")
            return
        
        row = selected_items[0].row()
        link_item = self.album_table.item(row, 2)
        if link_item:
            import webbrowser
            webbrowser.open(link_item.text())
            self.status_bar.showMessage("正在打开链接...")
    
    def export_album_list(self):
        if not self.current_albums:
            QMessageBox.warning(self, "警告", "没有专辑数据可导出")
            return
        
        # 生成默认文件名：歌单名_作者名.csv
        default_filename = "专辑列表.csv"
        if self.current_playlist_info:
            playlist_name = self.current_playlist_info.get('name', '未知歌单')
            creator_name = self.current_playlist_info.get('creator', {}).get('nickname', '未知作者')
            
            # 清理文件名中的非法字符
            def sanitize_filename(filename):
                # 替换Windows/Linux中不允许的文件名字符
                illegal_chars = r'[<>:"/\\|?*\n\r\t]'
                filename = re.sub(illegal_chars, '_', filename)
                # 移除首尾空格和点
                filename = filename.strip().strip('.')
                # 限制长度
                if len(filename) > 100:
                    filename = filename[:100]
                return filename
            
            safe_playlist_name = sanitize_filename(playlist_name)
            safe_creator_name = sanitize_filename(creator_name)
            
            if safe_playlist_name and safe_creator_name:
                default_filename = f"{safe_playlist_name}_{safe_creator_name}.csv"
            elif safe_playlist_name:
                default_filename = f"{safe_playlist_name}.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出专辑列表", default_filename, "CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            # 确保文件扩展名
            if not file_path.lower().endswith('.csv') and not file_path.lower().endswith('.txt'):
                file_path += '.csv'
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("专辑ID,专辑名称,艺术家,链接\n")
                    for album in self.current_albums:
                        artists = ", ".join([artist['name'] for artist in album.get('artists', [])])
                        link = self.tracker.generate_album_link(album['album_id'])
                        f.write(f"{album['album_id']},{album['album_name']},{artists},{link}\n")
                
                QMessageBox.information(self, "导出成功", f"专辑列表已导出到: {file_path}")
                self.status_bar.showMessage("导出完成")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出文件时发生错误: {e}")
    
    def clear_display(self):
        self.info_text.clear()
        self.album_table.setRowCount(0)
        self.current_albums = []
        self.current_playlist_info = None
        self.status_bar.showMessage("显示已清除")
    
    def extract_playlist_id(self):
        """从链接中提取歌单ID"""
        link = self.playlist_link_input.text().strip()
        if not link:
            QMessageBox.warning(self, "警告", "请输入歌单链接")
            return
        
        # 提取ID的模式（只匹配包含playlist的链接）
        patterns = [
            r'playlist\?id=(\d+)',    # music.163.com/playlist?id=123456
            r'/#/playlist\?id=(\d+)', # music.163.com/#/playlist?id=123456
            r'/playlist/(\d+)',       # 可能的其他格式
            r'playlist/(\d+)',        # 可能没有斜杠
        ]
        
        playlist_id = None
        for pattern in patterns:
            match = re.search(pattern, link)
            if match:
                playlist_id = match.group(1)
                break
        
        if playlist_id:
            self.playlist_id_input.setText(playlist_id)
            self.status_bar.showMessage(f"已提取歌单ID: {playlist_id}")
            # 可选：自动获取歌单信息
            # self.fetch_playlist()
        else:
            QMessageBox.warning(self, "警告", "无法从链接中提取歌单ID，请检查链接格式")
    
    def load_history(self):
        """加载历史查询记录到下拉框"""
        self.history_combo.clear()
        
        try:
            playlists = self.storage.get_all_playlists()
            if not playlists:
                self.history_combo.addItem("无历史记录")
                return
            
            # 添加一个空白选项
            self.history_combo.addItem("选择历史歌单...", None)
            
            for playlist in playlists:
                playlist_id = playlist.get('id', '')
                playlist_name = playlist.get('name', '未知歌单')
                track_count = playlist.get('track_count', 0)
                
                # 格式化显示：歌单名称 (ID: xxx, 歌曲数: xxx)
                display_text = f"{playlist_name} (ID: {playlist_id}, 歌曲数: {track_count})"
                self.history_combo.addItem(display_text, playlist_id)
        
        except Exception as e:
            print(f"加载历史记录失败: {e}")
            self.history_combo.addItem("加载历史记录失败")
    
    def on_history_selected(self, index):
        """历史记录下拉框选择事件"""
        if index <= 0:  # 第一个是空白选项或"无历史记录"
            return
        
        playlist_id = self.history_combo.itemData(index)
        if playlist_id:
            self.playlist_id_input.setText(str(playlist_id))
            # 可选：自动获取歌单信息
            # self.fetch_playlist()
    
    def load_history_table(self):
        """加载历史歌单到表格"""
        try:
            self.history_table.setRowCount(0)
            playlists = self.storage.get_all_playlists()
            
            if not playlists:
                self.history_table.setRowCount(1)
                no_data_item = QTableWidgetItem("无历史记录")
                no_data_item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(0, 0, no_data_item)
                self.history_table.setSpan(0, 0, 1, 2)  # 合并所有列
                return
            
            self.history_table.setRowCount(len(playlists))
            
            for row, playlist in enumerate(playlists):
                playlist_id = playlist.get('id', '')
                playlist_name = playlist.get('name', '未知歌单')
                track_count = playlist.get('track_count', 0)
                
                # 歌单名称列
                name_item = QTableWidgetItem(playlist_name)
                name_item.setData(Qt.UserRole, playlist_id)  # 存储歌单ID
                self.history_table.setItem(row, 0, name_item)
                
                # 专辑数列
                album_count = playlist.get('album_count', 0)
                count_item = QTableWidgetItem(str(album_count))
                count_item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row, 1, count_item)
        
        except Exception as e:
            print(f"加载历史表格失败: {e}")
            QMessageBox.warning(self, "加载失败", f"加载历史歌单失败: {e}")
    
    def toggle_pin_playlist(self, playlist_id: str):
        """切换歌单固定状态"""
        try:
            self.storage.toggle_pin_playlist(playlist_id)
            self.load_history_table()  # 刷新表格
            self.load_history()  # 刷新下拉框
        except Exception as e:
            QMessageBox.warning(self, "操作失败", f"切换固定状态失败: {e}")
    
    def delete_playlist(self, playlist_id: str):
        """删除歌单历史记录"""
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除歌单 {playlist_id} 的历史记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.storage.delete_playlist_history(playlist_id)
                self.load_history_table()  # 刷新表格
                self.load_history()  # 刷新下拉框
                # 如果当前输入框是该ID，清空
                if self.playlist_id_input.text() == playlist_id:
                    self.playlist_id_input.clear()
                QMessageBox.information(self, "删除成功", "歌单历史记录已删除")
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"删除歌单历史记录失败: {e}")
    
    def clear_all_history(self):
        """清除所有历史记录"""
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有历史记录吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 清空存储数据
                self.storage.data = {}
                self.storage._save_data()
                self.load_history_table()
                self.load_history()
                QMessageBox.information(self, "清除成功", "所有历史记录已清除")
            except Exception as e:
                QMessageBox.warning(self, "清除失败", f"清除历史记录失败: {e}")
    
    def mark_all_as_read(self):
        """标记所有专辑为已读"""
        if not self.current_playlist_id:
            QMessageBox.warning(self, "警告", "没有当前歌单")
            return
        
        try:
            # 调用存储方法标记为已读
            self.storage.mark_all_as_read(self.current_playlist_id)
            # 更新UI：清除未读样式
            self.update_album_table(self.current_albums, [])
            # 禁用"标记为已读"按钮
            self.mark_read_button.setEnabled(False)
            # 刷新历史记录列表（更新未读计数）
            self.load_history_table()
            
            QMessageBox.information(self, "标记成功", "所有专辑已标记为已读")
        except Exception as e:
            QMessageBox.warning(self, "标记失败", f"标记为已读失败: {e}")
    
    def show_history_context_menu(self, position):
        """显示历史歌单的右键菜单"""
        row = self.history_table.rowAt(position.y())
        if row < 0:
            return
        
        # 获取歌单ID
        playlist_id_item = self.history_table.item(row, 0)
        if not playlist_id_item:
            return
        
        playlist_id = playlist_id_item.data(Qt.UserRole)
        playlist_name_item = self.history_table.item(row, 0)
        playlist_name = playlist_name_item.text() if playlist_name_item else playlist_id
        
        # 创建右键菜单
        menu = QMenu()
        
        # 删除动作
        delete_action = QAction(f"删除歌单: {playlist_name}", self)
        delete_action.triggered.connect(lambda: self.delete_playlist(playlist_id))
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.history_table.viewport().mapToGlobal(position))
    
    def on_history_selection_changed(self):
        """历史歌单选择变化事件"""
        selected_rows = self.history_table.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        playlist_id_item = self.history_table.item(row, 0)
        if playlist_id_item:
            playlist_id = playlist_id_item.data(Qt.UserRole)
            if playlist_id:
                # 将歌单ID填入右侧输入框
                self.playlist_id_input.setText(str(playlist_id))
                
                # 设置当前歌单ID
                self.current_playlist_id = playlist_id
                
                # 尝试从缓存加载专辑数据
                try:
                    # 检查是否有缓存的专辑信息
                    if self.storage.has_album_details(playlist_id):
                        # 从存储加载专辑信息
                        albums = self.storage.get_album_details(playlist_id)
                        unread_album_ids = self.storage.get_unread_albums(playlist_id)
                        
                        # 更新专辑表格
                        self.current_albums = albums
                        self.update_album_table(albums, unread_album_ids)
                        
                        # 更新"标记为已读"按钮状态
                        has_unread = len(unread_album_ids) > 0
                        self.mark_read_button.setEnabled(has_unread)
                        
                        # 尝试获取歌单信息显示
                        playlist_data = self.storage.get_playlist_history(playlist_id)
                        if playlist_data and playlist_data.get('history'):
                            # 获取最新的历史记录
                            sorted_history = sorted(playlist_data['history'], 
                                                  key=lambda x: x.get('record_time', 0), 
                                                  reverse=True)
                            latest_history = sorted_history[0]
                            
                            # 创建伪playlist_info用于显示
                            playlist_info = {
                                'name': latest_history.get('name', '未知歌单'),
                                'description': latest_history.get('description', '无描述'),
                                'trackCount': latest_history.get('track_count', 0),
                                'playCount': 0,
                                'subscribedCount': 0,
                                'shareCount': 0,
                                'commentCount': 0,
                                'createTime': None,
                                'updateTime': latest_history.get('timestamp'),
                                'creator': {'nickname': '历史缓存'}
                            }
                            self.current_playlist_info = playlist_info
                            self.update_playlist_info_display(playlist_info)
                        
                        self.status_bar.showMessage(f"已加载缓存歌单: {playlist_id}")
                    else:
                        self.status_bar.showMessage(f"歌单 {playlist_id} 无缓存数据")
                        
                except Exception as e:
                    print(f"加载缓存数据失败: {e}")
                    self.status_bar.showMessage(f"加载缓存失败: {e}")
    
    def on_album_item_clicked(self, item):
        """专辑表格点击事件"""
        if not self.current_playlist_id:
            return
        
        row = item.row()
        if row < 0 or row >= len(self.current_albums):
            return
        
        album = self.current_albums[row]
        album_id = album['album_id']
        
        # 检查是否未读
        if album_id in self.unread_album_ids:
            # 标记为已读
            try:
                self.storage.mark_album_as_read(self.current_playlist_id, album_id)
                # 从本地未读列表中移除
                if album_id in self.unread_album_ids:
                    self.unread_album_ids.remove(album_id)
                
                # 更新该行样式
                # 已读颜色：灰色
                read_color = QColor('gray')
                
                # 更新该行所有单元格
                for col in range(self.album_table.columnCount()):
                    cell_item = self.album_table.item(row, col)
                    if cell_item:
                        # 清除加粗字体
                        normal_font = QFont()
                        cell_item.setFont(normal_font)
                        # 设置为灰色
                        cell_item.setForeground(read_color)
                
                # 更新"标记为已读"按钮状态
                has_unread = len(self.unread_album_ids) > 0
                self.mark_read_button.setEnabled(has_unread)
                
                # 刷新历史记录列表（更新未读计数）
                self.load_history_table()
                
                self.status_bar.showMessage(f"专辑已标记为已读: {album['album_name']}")
            except Exception as e:
                QMessageBox.warning(self, "标记失败", f"标记专辑为已读失败: {e}")

def main():
    app = QApplication(sys.argv)
    window = PlaylistTrackerWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()