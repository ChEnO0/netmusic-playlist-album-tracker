#!/usr/bin/env python3
"""
CustomTkinter GUI 界面 - 现代化美观界面
"""
import sys
import threading
import time
import os
import re
import customtkinter as ctk
from tkinter import filedialog

from playlist_tracker import PlaylistTracker
from storage import get_storage

# 设置 CustomTkinter 外观
ctk.set_appearance_mode("light")  # 可选: "light", "dark", "system"
ctk.set_default_color_theme("blue")  # 可选: "blue", "green", "dark-blue"

class PlaylistTrackerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.tracker = PlaylistTracker()
        self.storage = get_storage()
        self.current_albums = []
        self.current_playlist_info = None
        self.current_playlist_id = None
        self.unread_album_ids = []
        
        # 启动时清理过期缓存
        cleaned = self.storage.cleanup_expired_cache()
        if cleaned > 0:
            print(f"已清理 {cleaned} 个过期歌单缓存")
        
        self.title("网易云歌单追踪器")
        self.geometry("1500x900")
        
        # 设置网格权重
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== 左侧边栏 ==========
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # 标题
        title_label = ctk.CTkLabel(
            self.sidebar, 
            text="📚 历史歌单", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # 历史歌单列表框
        self.history_listbox = ctk.CTkScrollableFrame(self.sidebar, height=400)
        self.history_listbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.history_listbox.grid_columnconfigure(0, weight=1)
        
        # 历史歌单按钮
        button_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=10, pady=(5, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        
        self.refresh_btn = ctk.CTkButton(
            button_frame, 
            text="🔄 刷新历史",
            command=self.load_history_table,
            height=32,
            fg_color="#3B8ED0",
            hover_color="#36719F"
        )
        self.refresh_btn.grid(row=0, column=0, padx=2, sticky="ew")
        
        self.clear_all_btn = ctk.CTkButton(
            button_frame, 
            text="🗑️ 清除所有",
            command=self.clear_all_history,
            height=32,
            fg_color="#D33B3B",
            hover_color="#B02A2A"
        )
        self.clear_all_btn.grid(row=0, column=1, padx=2, sticky="ew")
        
        # ========== 右侧主区域 ==========
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#F5F5F5")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)  # 让专辑区域可扩展
        
        # 顶部控制区域
        self.control_frame = ctk.CTkFrame(self.main_frame, height=100)
        self.control_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        self.control_frame.grid_columnconfigure(1, weight=1)
        
        # 歌单链接输入
        self.link_label = ctk.CTkLabel(self.control_frame, text="歌单链接:", font=ctk.CTkFont(weight="bold"))
        self.link_label.grid(row=0, column=0, padx=(15, 5), pady=(15, 5), sticky="w")
        
        self.link_input = ctk.CTkEntry(
            self.control_frame, 
            placeholder_text="粘贴网易云歌单链接，如: https://music.163.com/playlist?id=123456",
            height=35
        )
        self.link_input.grid(row=0, column=1, columnspan=2, padx=5, pady=(15, 5), sticky="ew")
        
        self.extract_btn = ctk.CTkButton(
            self.control_frame, 
            text="提取ID",
            command=self.extract_playlist_id,
            width=80,
            height=35
        )
        self.extract_btn.grid(row=0, column=3, padx=(5, 15), pady=(15, 5))
        
        # 歌单ID输入和按钮
        self.id_label = ctk.CTkLabel(self.control_frame, text="歌单ID:", font=ctk.CTkFont(weight="bold"))
        self.id_label.grid(row=1, column=0, padx=(15, 5), pady=5, sticky="w")
        
        self.id_input = ctk.CTkEntry(
            self.control_frame, 
            placeholder_text="输入歌单ID",
            height=35
        )
        self.id_input.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.id_input.insert(0, "3778678")
        
        self.fetch_btn = ctk.CTkButton(
            self.control_frame, 
            text="📥 获取歌单",
            command=self.fetch_playlist,
            height=35,
            fg_color="#2FA335",
            hover_color="#248A2C"
        )
        self.fetch_btn.grid(row=1, column=2, padx=5, pady=5)
        
        self.check_btn = ctk.CTkButton(
            self.control_frame, 
            text="🔍 检查更新",
            command=self.check_updates,
            height=35,
            fg_color="#E07B39",
            hover_color="#C66A2E"
        )
        self.check_btn.grid(row=1, column=3, padx=5, pady=5)
        
        self.clear_btn = ctk.CTkButton(
            self.control_frame, 
            text="🧹 清除",
            command=self.clear_display,
            height=35,
            fg_color="#666666",
            hover_color="#4D4D4D"
        )
        self.clear_btn.grid(row=1, column=4, padx=(5, 15), pady=5)
        
        # 歌单信息区域
        self.info_frame = ctk.CTkFrame(self.main_frame, height=160)
        self.info_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        
        self.info_label = ctk.CTkLabel(
            self.info_frame, 
            text="📋 歌单信息", 
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        self.info_label.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        self.info_text = ctk.CTkTextbox(self.info_frame, height=100, font=ctk.CTkFont(size=12))
        self.info_text.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.info_text.configure(state="disabled")
        
        # 专辑信息区域
        self.album_frame = ctk.CTkFrame(self.main_frame)
        self.album_frame.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        self.album_frame.grid_columnconfigure(0, weight=1)
        self.album_frame.grid_rowconfigure(1, weight=1)  # 让列表框可扩展
        
        self.album_label = ctk.CTkLabel(
            self.album_frame, 
            text="💿 专辑信息", 
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        self.album_label.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        # 专辑列表框 - 不设固定高度，让它自适应
        self.album_listbox = ctk.CTkScrollableFrame(self.album_frame)
        self.album_listbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.album_listbox.grid_columnconfigure(0, weight=1)
        
        # 专辑操作按钮 - 放在main_frame中，不在album_frame中
        self.album_btn_frame = ctk.CTkFrame(self.main_frame, height=50)
        self.album_btn_frame.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.album_btn_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        self.copy_btn = ctk.CTkButton(
            self.album_btn_frame, 
            text="📋 复制链接",
            command=self.copy_selected_link,
            height=36,
            fg_color="#3B8ED0"
        )
        self.copy_btn.grid(row=0, column=0, padx=3, sticky="ew")
        
        self.copy_name_btn = ctk.CTkButton(
            self.album_btn_frame, 
            text="📝 复制专辑名",
            command=self.copy_selected_album_name,
            height=36,
            fg_color="#3B8ED0"
        )
        self.copy_name_btn.grid(row=0, column=1, padx=3, sticky="ew")
        
        self.open_btn = ctk.CTkButton(
            self.album_btn_frame, 
            text="🌐 打开链接",
            command=self.open_selected_link,
            height=36,
            fg_color="#3B8ED0"
        )
        self.open_btn.grid(row=0, column=2, padx=3, sticky="ew")
        
        self.export_btn = ctk.CTkButton(
            self.album_btn_frame, 
            text="📥 导出列表",
            command=self.export_album_list,
            height=36,
            fg_color="#3B8ED0"
        )
        self.export_btn.grid(row=0, column=3, padx=3, sticky="ew")
        
        self.mark_read_btn = ctk.CTkButton(
            self.album_btn_frame, 
            text="✓ 全部已读",
            command=self.mark_all_as_read,
            height=36,
            fg_color="#2FA335",
            state="disabled"
        )
        self.mark_read_btn.grid(row=0, column=4, padx=3, sticky="ew")
        
        # 状态栏
        self.status_bar = ctk.CTkLabel(
            self.main_frame, 
            text="就绪", 
            anchor="w",
            text_color="#666666",
            font=ctk.CTkFont(size=11)
        )
        self.status_bar.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="ew")
        
        # 加载历史记录
        self.load_history_table()
    
    def fetch_playlist(self):
        playlist_id = self.id_input.get().strip()
        if not playlist_id:
            self.show_warning("请输入歌单ID")
            return
        
        self.current_playlist_id = playlist_id
        self.set_ui_enabled(False)
        self.status_bar.configure(text="正在获取歌单信息...")
        
        thread = threading.Thread(target=self._fetch_thread, args=(playlist_id, 'fetch'))
        thread.daemon = True
        thread.start()
    
    def check_updates(self):
        playlist_id = self.id_input.get().strip()
        if not playlist_id:
            self.show_warning("请输入歌单ID")
            return
        
        self.current_playlist_id = playlist_id
        self.set_ui_enabled(False)
        self.status_bar.configure(text="正在检查更新...")
        
        thread = threading.Thread(target=self._fetch_thread, args=(playlist_id, 'check_update'))
        thread.daemon = True
        thread.start()
    
    def _fetch_thread(self, playlist_id, mode):
        try:
            if mode == 'fetch':
                self.after(0, lambda: self.status_bar.configure(text="正在获取歌单信息..."))
                playlist_info = self.tracker.get_playlist_info(playlist_id)
                if not playlist_info:
                    self.after(0, lambda: self.show_error("获取歌单信息失败"))
                    self.after(0, lambda: self.status_bar.configure(text="获取失败"))
                    self.after(0, lambda: self.set_ui_enabled(True))
                    return
                
                self.storage.update_playlist_history(playlist_id, playlist_info)
                tracks = self.tracker.get_playlist_tracks(playlist_id)
                albums = self.tracker.get_all_albums_from_playlist(playlist_id, tracks=tracks)
                
                for album in albums:
                    album['link'] = self.tracker.generate_album_link(album['album_id'])
                
                album_ids = [album['album_id'] for album in albums]
                self.storage.update_album_snapshot(playlist_id, album_ids, albums)
                unread_album_ids = self.storage.get_unread_albums(playlist_id)
                
                self.after(0, lambda: self._update_display(playlist_info, albums, unread_album_ids))
                self.after(0, lambda: self.status_bar.configure(text="获取完成"))
                
            elif mode == 'check_update':
                self.after(0, lambda: self.status_bar.configure(text="正在检查更新..."))
                last_update_time = self.storage.get_last_update_time(playlist_id)
                update_result = self.tracker.check_for_updates(playlist_id, last_update_time)
                
                if update_result['has_update']:
                    playlist_info = self.tracker.get_playlist_info(playlist_id)
                    if playlist_info:
                        self.storage.update_playlist_history(playlist_id, playlist_info)
                        tracks = self.tracker.get_playlist_tracks(playlist_id)
                        albums = self.tracker.get_all_albums_from_playlist(playlist_id, tracks=tracks)
                        
                        for album in albums:
                            album['link'] = self.tracker.generate_album_link(album['album_id'])
                        
                        album_ids = [album['album_id'] for album in albums]
                        self.storage.update_album_snapshot(playlist_id, album_ids, albums)
                        unread_album_ids = self.storage.get_unread_albums(playlist_id)
                        
                        self.after(0, lambda: self._update_display(playlist_info, albums, unread_album_ids))
                        self.after(0, lambda: self.show_info(update_result['message']))
                    else:
                        self.after(0, lambda: self.show_error("获取更新信息失败"))
                else:
                    self.after(0, lambda: self.show_info(update_result['message']))
                
                self.after(0, lambda: self.status_bar.configure(text="检查完成"))
            
            self.after(0, lambda: self.set_ui_enabled(True))
            self.after(0, lambda: self.load_history_table())
            
        except Exception as e:
            self.after(0, lambda: self.show_error(f"发生错误: {e}"))
            self.after(0, lambda: self.status_bar.configure(text="错误"))
            self.after(0, lambda: self.set_ui_enabled(True))
    
    def _update_display(self, playlist_info, albums, unread_album_ids):
        self.current_albums = albums
        self.current_playlist_info = playlist_info
        self.unread_album_ids = unread_album_ids or []
        
        self.update_playlist_info_display(playlist_info)
        self.update_album_table(albums, unread_album_ids)
        
        has_unread = len(unread_album_ids) > 0
        self.mark_read_btn.configure(state="normal" if has_unread else "disabled")
    
    def update_playlist_info_display(self, playlist_info):
        playlist_id = self.current_playlist_id or playlist_info.get('id', '未知')
        info_text = f"""歌单ID: {playlist_id}
歌单名称: {playlist_info.get('name', '未知')}
歌曲数量: {playlist_info.get('trackCount', 0)}
播放次数: {playlist_info.get('playCount', 0)}
收藏数: {playlist_info.get('subscribedCount', 0)}
分享数: {playlist_info.get('shareCount', 0)}
评论数: {playlist_info.get('commentCount', 0)}
创建时间: {self.format_timestamp(playlist_info.get('createTime'))}
更新时间: {self.format_timestamp(playlist_info.get('updateTime'))}
创建者: {playlist_info.get('creator', {}).get('nickname', '未知')}"""
        
        self.info_text.configure(state="normal")
        self.info_text.delete("0.0", "end")
        self.info_text.insert("0.0", info_text)
        self.info_text.configure(state="disabled")
    
    def format_timestamp(self, timestamp):
        if not timestamp:
            return "未知"
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp/1000))
        except:
            return str(timestamp)
    
    def update_album_table(self, albums, unread_album_ids=None):
        # 清除现有项
        for widget in self.album_listbox.winfo_children():
            widget.destroy()
        
        self.unread_album_ids = unread_album_ids or []
        unread_set = set(self.unread_album_ids)
        
        # 表头
        header_frame = ctk.CTkFrame(self.album_listbox, fg_color="#E0E0E0")
        header_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(header_frame, text="专辑名称", font=ctk.CTkFont(weight="bold"), width=200).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="艺术家", font=ctk.CTkFont(weight="bold"), width=150).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="链接", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        # 专辑行
        for row, album in enumerate(albums):
            album_id = album['album_id']
            is_unread = album_id in unread_set
            
            artists = ", ".join([artist.get('name', '') for artist in album.get('artists', [])])
            link = album.get('link', '') or self.tracker.generate_album_link(album_id)
            
            # 根据是否未读选择颜色
            if is_unread:
                fg_color = "#FFFFFF"
                text_color = "#000000"
                font = ctk.CTkFont(weight="bold")
            else:
                fg_color = "#F8F8F8"
                text_color = "#888888"
                font = ctk.CTkFont()
            
            row_frame = ctk.CTkFrame(self.album_listbox, fg_color=fg_color, height=40)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            # 点击事件
            row_frame.bind("<Button-1>", lambda e, aid=album_id: self.on_album_click(aid))
            
            name_label = ctk.CTkLabel(
                row_frame, 
                text=album.get('album_name', '未知'), 
                text_color=text_color,
                font=font,
                width=200,
                anchor="w"
            )
            name_label.pack(side="left", padx=5)
            name_label.bind("<Button-1>", lambda e, aid=album_id: self.on_album_click(aid))
            
            artist_label = ctk.CTkLabel(
                row_frame, 
                text=artists, 
                text_color=text_color,
                font=font,
                width=150,
                anchor="w"
            )
            artist_label.pack(side="left", padx=5)
            artist_label.bind("<Button-1>", lambda e, aid=album_id: self.on_album_click(aid))
            
            link_label = ctk.CTkLabel(
                row_frame, 
                text=link, 
                text_color="#3B8ED0" if is_unread else "#888888",
                font=font,
                anchor="w"
            )
            link_label.pack(side="left", padx=5, fill="x", expand=True)
            link_label.bind("<Button-1>", lambda e, aid=album_id: self.on_album_click(aid))
    
    def on_album_click(self, album_id):
        if not self.current_playlist_id:
            return
        
        if album_id in self.unread_album_ids:
            self.storage.mark_album_as_read(self.current_playlist_id, album_id)
            self.unread_album_ids.remove(album_id)
            self.update_album_table(self.current_albums, self.unread_album_ids)
            
            has_unread = len(self.unread_album_ids) > 0
            self.mark_read_btn.configure(state="normal" if has_unread else "disabled")
            self.status_bar.configure(text=f"已标记为已读")
            self.load_history_table()
    
    def set_ui_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.fetch_btn.configure(state=state)
        self.check_btn.configure(state=state)
        self.clear_btn.configure(state=state)
        self.extract_btn.configure(state=state)
        self.copy_btn.configure(state=state)
        self.copy_name_btn.configure(state=state)
        self.open_btn.configure(state=state)
        self.export_btn.configure(state=state)
    
    def load_history_table(self):
        # 清除现有项
        for widget in self.history_listbox.winfo_children():
            widget.destroy()
        
        playlists = self.storage.get_all_playlists()
        
        if not playlists:
            ctk.CTkLabel(
                self.history_listbox, 
                text="暂无历史记录", 
                text_color="#888888"
            ).pack(pady=20)
            return
        
        for playlist in playlists:
            playlist_id = playlist.get('id', '')
            playlist_name = playlist.get('name', '未知歌单')
            album_count = playlist.get('album_count', 0)
            unread_count = self.storage.get_unread_count(playlist_id)
            
            # 歌单项
            item_frame = ctk.CTkFrame(self.history_listbox, fg_color="#FFFFFF", height=50)
            item_frame.pack(fill="x", pady=3, ipady=5)
            item_frame.pack_propagate(False)
            
            # 左键点击加载缓存
            item_frame.bind("<Button-1>", lambda e, pid=playlist_id: self.on_history_select(pid))
            
            # 歌单名称
            name_label = ctk.CTkLabel(
                item_frame, 
                text=f"📁 {playlist_name}", 
                font=ctk.CTkFont(weight="bold"),
                anchor="w"
            )
            name_label.pack(side="left", padx=(10, 5), fill="x", expand=True)
            name_label.bind("<Button-1>", lambda e, pid=playlist_id: self.on_history_select(pid))
            
            # 未读数量徽章
            if unread_count > 0:
                badge = ctk.CTkLabel(
                    item_frame, 
                    text=f" {unread_count} ",
                    font=ctk.CTkFont(size=10),
                    text_color="white",
                    fg_color="#E07B39",
                    corner_radius=10
                )
                badge.pack(side="right", padx=5)
                badge.bind("<Button-1>", lambda e, pid=playlist_id: self.on_history_select(pid))
            
            # 专辑数
            count_label = ctk.CTkLabel(
                item_frame, 
                text=f"💿 {album_count}",
                text_color="#888888"
            )
            count_label.pack(side="right", padx=5)
            count_label.bind("<Button-1>", lambda e, pid=playlist_id: self.on_history_select(pid))
            
            # 右键菜单
            item_frame.bind("<Button-3>", lambda e, pid=playlist_id, pname=playlist_name: self.show_context_menu(e, pid, pname))
            name_label.bind("<Button-3>", lambda e, pid=playlist_id, pname=playlist_name: self.show_context_menu(e, pid, pname))
    
    def on_history_select(self, playlist_id):
        self.id_input.delete(0, "end")
        self.id_input.insert(0, str(playlist_id))
        self.current_playlist_id = playlist_id
        
        if self.storage.has_album_details(playlist_id):
            albums = self.storage.get_album_details(playlist_id)
            unread_album_ids = self.storage.get_unread_albums(playlist_id)
            
            self.current_albums = albums
            self.update_album_table(albums, unread_album_ids)
            
            # 获取歌单信息用于显示
            playlist_data = self.storage.get_playlist_history(playlist_id)
            if playlist_data and playlist_data.get('history'):
                sorted_history = sorted(
                    playlist_data['history'], 
                    key=lambda x: x.get('record_time', 0), 
                    reverse=True
                )
                latest = sorted_history[0]
                
                playlist_info = {
                    'name': latest.get('name', '未知歌单'),
                    'description': latest.get('description', ''),
                    'trackCount': latest.get('track_count', 0),
                    'updateTime': latest.get('timestamp'),
                    'creator': {'nickname': '历史缓存'}
                }
                self.current_playlist_info = playlist_info
                self.update_playlist_info_display(playlist_info)
            
            has_unread = len(unread_album_ids) > 0
            self.mark_read_btn.configure(state="normal" if has_unread else "disabled")
            
            self.status_bar.configure(text=f"已加载缓存: {playlist_id}")
        else:
            self.status_bar.configure(text=f"歌单 {playlist_id} 无缓存数据")
    
    def show_context_menu(self, event, playlist_id, playlist_name):
        menu = ctk.CTkMenu(self, fg_color="#FFFFFF")
        
        delete_action = ctk.CTkMenu(menu, fg_color="#FFFFFF")
        menu.add_cascade(label=f"🗑️ 删除: {playlist_name}", menu=delete_action)
        delete_action.add_command(label="确认删除", command=lambda: self.delete_playlist(playlist_id))
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def delete_playlist(self, playlist_id):
        from tkinter import messagebox
        reply = messagebox.askyesno("确认删除", f"确定要删除歌单 {playlist_id} 的历史记录吗？")
        if reply:
            self.storage.delete_playlist_history(playlist_id)
            self.load_history_table()
            if self.id_input.get().strip() == playlist_id:
                self.id_input.delete(0, "end")
            self.show_info("删除成功")
    
    def clear_all_history(self):
        from tkinter import messagebox
        reply = messagebox.askyesno("确认清除", "确定要清除所有历史记录吗？此操作不可恢复！")
        if reply:
            self.storage.data = {}
            self.storage._save_data()
            self.load_history_table()
            self.show_info("所有历史记录已清除")
    
    def mark_all_as_read(self):
        if not self.current_playlist_id:
            self.show_warning("没有当前歌单")
            return
        
        self.storage.mark_all_as_read(self.current_playlist_id)
        self.update_album_table(self.current_albums, [])
        self.mark_read_btn.configure(state="disabled")
        self.load_history_table()
        self.show_info("所有专辑已标记为已读")
    
    def extract_playlist_id(self):
        link = self.link_input.get().strip()
        if not link:
            self.show_warning("请输入歌单链接")
            return
        
        patterns = [
            r'playlist\?id=(\d+)',
            r'/#/playlist\?id=(\d+)',
            r'/playlist/(\d+)',
            r'playlist/(\d+)',
        ]
        
        playlist_id = None
        for pattern in patterns:
            match = re.search(pattern, link)
            if match:
                playlist_id = match.group(1)
                break
        
        if playlist_id:
            self.id_input.delete(0, "end")
            self.id_input.insert(0, playlist_id)
            self.status_bar.configure(text=f"已提取歌单ID: {playlist_id}")
        else:
            self.show_warning("无法从链接中提取歌单ID")
    
    def copy_selected_link(self):
        if not self.current_albums:
            self.show_warning("没有专辑数据")
            return
        
        # 获取选中的链接
        for widget in self.album_listbox.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                labels = widget.winfo_children()
                if len(labels) >= 3:
                    link = labels[2].cget("text")
                    if link and link.startswith("http"):
                        self.clipboard_clear()
                        self.clipboard_append(link)
                        self.status_bar.configure(text="链接已复制到剪贴板")
                        return
        
        self.show_warning("请先选择一个专辑")
    
    def copy_selected_album_name(self):
        if not self.current_albums:
            self.show_warning("没有专辑数据")
            return
        
        # 获取选中的专辑名
        for widget in self.album_listbox.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                labels = widget.winfo_children()
                if len(labels) >= 3:
                    album_name = labels[0].cget("text")
                    if album_name and not album_name.startswith("http"):
                        self.clipboard_clear()
                        self.clipboard_append(album_name)
                        self.status_bar.configure(text="专辑名已复制到剪贴板")
                        return
        
        self.show_warning("请先选择一个专辑")
    
    def open_selected_link(self):
        if not self.current_albums:
            self.show_warning("没有专辑数据")
            return
        
        import webbrowser
        
        for widget in self.album_listbox.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                labels = widget.winfo_children()
                if len(labels) >= 3:
                    link = labels[2].cget("text")
                    if link and link.startswith("http"):
                        webbrowser.open(link)
                        self.status_bar.configure(text="正在打开链接...")
                        return
        
        self.show_warning("请先选择一个专辑")
    
    def export_album_list(self):
        if not self.current_albums:
            self.show_warning("没有专辑数据可导出")
            return
        
        default_filename = "专辑列表.csv"
        if self.current_playlist_info:
            name = self.current_playlist_info.get('name', '未知歌单')
            creator = self.current_playlist_info.get('creator', {}).get('nickname', '未知')
            safe_name = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)[:50]
            safe_creator = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', creator)[:50]
            if safe_name and safe_creator:
                default_filename = f"{safe_name}_{safe_creator}.csv"
            elif safe_name:
                default_filename = f"{safe_name}.csv"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=default_filename
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("专辑ID,专辑名称,艺术家,链接\n")
                    for album in self.current_albums:
                        artists = ", ".join([artist.get('name', '') for artist in album.get('artists', [])])
                        link = album.get('link', '') or self.tracker.generate_album_link(album['album_id'])
                        f.write(f"{album['album_id']},{album.get('album_name', '')},{artists},{link}\n")
                
                self.show_info(f"专辑列表已导出到:\n{file_path}")
                self.status_bar.configure(text="导出完成")
            except Exception as e:
                self.show_error(f"导出文件时发生错误:\n{e}")
    
    def clear_display(self):
        self.info_text.configure(state="normal")
        self.info_text.delete("0.0", "end")
        self.info_text.configure(state="disabled")
        
        for widget in self.album_listbox.winfo_children():
            widget.destroy()
        
        self.current_albums = []
        self.current_playlist_info = None
        self.status_bar.configure(text="显示已清除")
    
    def show_error(self, message):
        from tkinter import messagebox
        messagebox.showerror("错误", message)
    
    def show_warning(self, message):
        from tkinter import messagebox
        messagebox.showwarning("警告", message)
    
    def show_info(self, message):
        from tkinter import messagebox
        messagebox.showinfo("提示", message)

def main():
    app = PlaylistTrackerWindow()
    app.mainloop()

if __name__ == '__main__':
    main()