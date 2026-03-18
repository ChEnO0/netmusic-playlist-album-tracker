#!/usr/bin/env python3
"""
Tkinter GUI 界面
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from typing import Optional

from playlist_tracker import PlaylistTracker
from storage import get_storage

class PlaylistTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("网易云歌单追踪器")
        self.root.geometry("900x700")
        
        self.tracker = PlaylistTracker()
        self.storage = get_storage()
        
        self.setup_ui()
        
    def setup_ui(self):
        # 顶部框架：输入歌单ID和按钮
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, sticky="we")
        
        ttk.Label(top_frame, text="歌单ID:").grid(row=0, column=0, padx=5)
        self.playlist_id_var = tk.StringVar()
        self.playlist_id_entry = ttk.Entry(top_frame, textvariable=self.playlist_id_var, width=40)
        self.playlist_id_entry.grid(row=0, column=1, padx=5)
        self.playlist_id_var.set("3778678")  # 默认值
        
        ttk.Button(top_frame, text="获取歌单信息", command=self.fetch_playlist_info).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="检查更新", command=self.check_updates).grid(row=0, column=3, padx=5)
        ttk.Button(top_frame, text="清除", command=self.clear_display).grid(row=0, column=4, padx=5)
        
        # 歌单信息框架
        info_frame = ttk.LabelFrame(self.root, text="歌单信息", padding="10")
        info_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, width=100)
        self.info_text.grid(row=0, column=0, sticky="we")
        
        # 专辑信息框架
        album_frame = ttk.LabelFrame(self.root, text="专辑信息", padding="10")
        album_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        # 创建树状视图显示专辑
        columns = ('album_id', 'album_name', 'artists', 'link')
        self.album_tree = ttk.Treeview(album_frame, columns=columns, show='headings', height=12)
        
        self.album_tree.heading('album_id', text='专辑ID')
        self.album_tree.heading('album_name', text='专辑名称')
        self.album_tree.heading('artists', text='艺术家')
        self.album_tree.heading('link', text='链接')
        
        self.album_tree.column('album_id', width=80)
        self.album_tree.column('album_name', width=200)
        self.album_tree.column('artists', width=150)
        self.album_tree.column('link', width=300)
        
        self.album_tree.grid(row=0, column=0, sticky="nsew")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(album_frame, orient=tk.VERTICAL, command=self.album_tree.yview)
        self.album_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 底部按钮框架
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.grid(row=3, column=0, sticky="we")
        
        ttk.Button(bottom_frame, text="复制选中链接", command=self.copy_selected_link).grid(row=0, column=0, padx=5)
        ttk.Button(bottom_frame, text="打开选中链接", command=self.open_selected_link).grid(row=0, column=1, padx=5)
        ttk.Button(bottom_frame, text="导出专辑列表", command=self.export_album_list).grid(row=0, column=2, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, sticky="we", padx=10, pady=5)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=1)
        
        info_frame.columnconfigure(0, weight=1)
        album_frame.columnconfigure(0, weight=1)
        album_frame.rowconfigure(0, weight=1)
        
    def fetch_playlist_info(self):
        playlist_id = self.playlist_id_var.get().strip()
        if not playlist_id:
            messagebox.showerror("错误", "请输入歌单ID")
            return
        
        self.status_var.set("正在获取歌单信息...")
        self.root.update()
        
        # 在新线程中执行网络请求
        thread = threading.Thread(target=self._fetch_playlist_info_thread, args=(playlist_id,))
        thread.daemon = True
        thread.start()
    
    def _fetch_playlist_info_thread(self, playlist_id):
        try:
            playlist_info = self.tracker.get_playlist_info(playlist_id)
            if not playlist_info:
                self.root.after(0, lambda: messagebox.showerror("错误", "获取歌单信息失败"))
                self.root.after(0, lambda: self.status_var.set("获取失败"))
                return
            
            # 更新存储
            self.storage.update_playlist_history(playlist_id, playlist_info)
            
            # 获取歌曲列表
            tracks = self.tracker.get_playlist_tracks(playlist_id)
            # 获取专辑信息
            albums = self.tracker.get_all_albums_from_playlist(playlist_id, tracks=tracks)
            
            # 在主线程中更新UI
            self.root.after(0, self._update_playlist_info_display, playlist_info, albums, len(tracks))
            self.root.after(0, lambda: self.status_var.set("获取完成"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"获取过程中发生异常: {e}"))
            self.root.after(0, lambda: self.status_var.set("错误"))
    
    def _update_playlist_info_display(self, playlist_info, albums, tracks_count):
        # 清空信息文本框
        self.info_text.delete(1.0, tk.END)
        
        # 显示歌单信息
        info_text = f"""歌单名称: {playlist_info.get('name', '未知')}
歌单描述: {playlist_info.get('description', '无描述')}
歌曲数量: {playlist_info.get('trackCount', 0)} (已获取: {tracks_count})
播放次数: {playlist_info.get('playCount', 0)}
收藏数: {playlist_info.get('subscribedCount', 0)}
分享数: {playlist_info.get('shareCount', 0)}
评论数: {playlist_info.get('commentCount', 0)}
创建时间: {self._format_timestamp(playlist_info.get('createTime'))}
更新时间: {self._format_timestamp(playlist_info.get('updateTime'))}
创建者: {playlist_info.get('creator', {}).get('nickname', '未知')}
"""
        self.info_text.insert(1.0, info_text)
        
        # 更新专辑树状视图
        self._update_album_tree(albums)
    
    def _format_timestamp(self, timestamp):
        if not timestamp:
            return "未知"
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp/1000))
        except:
            return str(timestamp)
    
    def _update_album_tree(self, albums):
        # 清空树状视图
        for item in self.album_tree.get_children():
            self.album_tree.delete(item)
        
        # 插入新数据
        for album in albums:
            artists = ", ".join([artist['name'] for artist in album.get('artists', [])])
            link = self.tracker.generate_album_link(album['album_id'])
            self.album_tree.insert('', 'end', values=(
                album['album_id'],
                album['album_name'],
                artists,
                link
            ))
    
    def check_updates(self):
        playlist_id = self.playlist_id_var.get().strip()
        if not playlist_id:
            messagebox.showerror("错误", "请输入歌单ID")
            return
        
        self.status_var.set("正在检查更新...")
        self.root.update()
        
        thread = threading.Thread(target=self._check_updates_thread, args=(playlist_id,))
        thread.daemon = True
        thread.start()
    
    def _check_updates_thread(self, playlist_id):
        try:
            last_update_time = self.storage.get_last_update_time(playlist_id)
            update_result = self.tracker.check_for_updates(playlist_id, last_update_time)
            
            if update_result['has_update']:
                # 如果有更新，重新获取歌单信息
                playlist_info = self.tracker.get_playlist_info(playlist_id)
                if playlist_info:
                    self.storage.update_playlist_history(playlist_id, playlist_info)
                    tracks = self.tracker.get_playlist_tracks(playlist_id)
                    albums = self.tracker.get_all_albums_from_playlist(playlist_id, tracks=tracks)
                    
                    self.root.after(0, self._update_playlist_info_display, playlist_info, albums, len(tracks))
                    self.root.after(0, lambda: messagebox.showinfo("更新", update_result['message']))
            else:
                self.root.after(0, lambda: messagebox.showinfo("无更新", update_result['message']))
            
            self.root.after(0, lambda: self.status_var.set("检查完成"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"检查更新过程中发生异常: {e}"))
            self.root.after(0, lambda: self.status_var.set("错误"))
    
    def copy_selected_link(self):
        selected = self.album_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个专辑")
            return
        
        item = self.album_tree.item(selected[0])
        link = item['values'][3]  # 链接在第四列
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        self.status_var.set("链接已复制到剪贴板")
    
    def open_selected_link(self):
        selected = self.album_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个专辑")
            return
        
        item = self.album_tree.item(selected[0])
        link = item['values'][3]
        import webbrowser
        webbrowser.open(link)
        self.status_var.set("正在打开链接...")
    
    def export_album_list(self):
        # 获取所有专辑数据
        albums = []
        for item in self.album_tree.get_children():
            item_data = self.album_tree.item(item)
            albums.append(item_data['values'])
        
        if not albums:
            messagebox.showwarning("警告", "没有专辑数据可导出")
            return
        
        # 生成导出内容
        export_content = "专辑ID,专辑名称,艺术家,链接\n"
        for album in albums:
            export_content += f"{album[0]},{album[1]},{album[2]},{album[3]}\n"
        
        # 弹出保存文件对话框
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_content)
                messagebox.showinfo("导出成功", f"专辑列表已导出到: {file_path}")
                self.status_var.set("导出完成")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出文件时发生错误: {e}")
    
    def clear_display(self):
        self.info_text.delete(1.0, tk.END)
        for item in self.album_tree.get_children():
            self.album_tree.delete(item)
        self.status_var.set("显示已清除")

def main():
    root = tk.Tk()
    app = PlaylistTrackerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()