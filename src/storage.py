#!/usr/bin/env python3
"""
数据存储模块
"""
import json
import os
import time
from typing import Dict, Any, Optional, List

class PlaylistStorage:
    def __init__(self, storage_file: str = 'data/playlist_history.json'):
        self.storage_file = storage_file
        dirname = os.path.dirname(storage_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """加载存储的数据"""
        if not os.path.exists(self.storage_file):
            return {}
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载存储文件失败: {e}")
            return {}
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存存储文件失败: {e}")
    
    def get_playlist_history(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """获取歌单的历史记录"""
        return self.data.get(playlist_id)
    
    def update_playlist_history(self, playlist_id: str, playlist_info: Dict[str, Any]):
        """更新歌单历史记录"""
        if playlist_id not in self.data:
            self.data[playlist_id] = {
                'history': [],
                'last_check': None,
                'last_update_time': None,
                'pinned': False,
                'album_snapshot': [],  # 专辑ID快照
                'album_details': {},   # 专辑详细信息 {album_id: {album_name, artists, link}}
                'unread_albums': []    # 未读专辑ID列表
            }
        
        history_entry = {
            'timestamp': playlist_info.get('updateTime'),
            'track_count': playlist_info.get('trackCount'),
            'name': playlist_info.get('name'),
            'description': playlist_info.get('description'),
            'record_time': int(time.time() * 1000)  # 当前时间戳，毫秒
        }
        
        # 添加到历史记录
        self.data[playlist_id]['history'].append(history_entry)
        
        # 更新最后检查时间和最后更新时间
        self.data[playlist_id]['last_check'] = int(time.time() * 1000)
        self.data[playlist_id]['last_update_time'] = playlist_info.get('updateTime')
        
        # 只保留最近10条历史记录
        if len(self.data[playlist_id]['history']) > 10:
            self.data[playlist_id]['history'] = self.data[playlist_id]['history'][-10:]
        
        self._save_data()
    
    def get_last_update_time(self, playlist_id: str) -> Optional[int]:
        """获取歌单的最后更新时间"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            return playlist_data.get('last_update_time')
        return None
    
    def pin_playlist(self, playlist_id: str):
        """固定歌单"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            playlist_data['pinned'] = True
            self._save_data()
    
    def unpin_playlist(self, playlist_id: str):
        """取消固定歌单"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            playlist_data['pinned'] = False
            self._save_data()
    
    def toggle_pin_playlist(self, playlist_id: str):
        """切换歌单固定状态"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            playlist_data['pinned'] = not playlist_data.get('pinned', False)
            self._save_data()
    
    def delete_playlist_history(self, playlist_id: str):
        """删除歌单历史记录"""
        if playlist_id in self.data:
            del self.data[playlist_id]
            self._save_data()
    
    def get_all_playlists(self) -> List[Dict[str, Any]]:
        """获取所有查询过的歌单列表（按固定状态和最后查询时间排序）"""
        playlists = []
        for playlist_id, playlist_data in self.data.items():
            if playlist_data.get('last_check'):
                # 获取最新的历史记录条目中的歌单名称
                latest_history = None
                if playlist_data.get('history'):
                    # 按record_time排序，获取最新的
                    sorted_history = sorted(playlist_data['history'], key=lambda x: x.get('record_time', 0), reverse=True)
                    latest_history = sorted_history[0]
                
                playlists.append({
                    'id': playlist_id,
                    'name': latest_history.get('name') if latest_history else '未知歌单',
                    'last_check': playlist_data.get('last_check'),
                    'last_update_time': playlist_data.get('last_update_time'),
                    'track_count': latest_history.get('track_count') if latest_history else 0,
                    'album_count': len(playlist_data.get('album_snapshot', [])),
                    'pinned': playlist_data.get('pinned', False)
                })
        
        # 排序：先按固定状态（固定的在前），再按最后检查时间倒序
        playlists.sort(key=lambda x: (not x.get('pinned', False), -x.get('last_check', 0)))
        return playlists
    
    def get_track_snapshot(self, playlist_id: str) -> Optional[List[int]]:
        """获取歌单的歌曲ID快照（用于检测歌曲变化）"""
        # 这个方法需要扩展，目前只记录更新时间
        # 可以存储歌曲ID列表来检测具体变化
        return None
    
    def update_album_snapshot(self, playlist_id: str, album_ids: List[int], album_details: Optional[List[Dict[str, Any]]] = None) -> List[int]:
        """更新专辑快照并返回新增专辑ID列表（未读）"""
        playlist_data = self.get_playlist_history(playlist_id)
        if not playlist_data:
            # 如果歌单记录不存在，先创建一个基本记录
            playlist_data = {
                'history': [],
                'last_check': None,
                'last_update_time': None,
                'pinned': False,
                'album_snapshot': [],
                'album_details': {},
                'unread_albums': []
            }
            self.data[playlist_id] = playlist_data
        
        old_snapshot = set(playlist_data.get('album_snapshot', []))
        new_snapshot = set(album_ids)
        
        # 找出新增的专辑（在新快照中但不在旧快照中）
        new_albums = list(new_snapshot - old_snapshot)
        
        # 更新快照
        playlist_data['album_snapshot'] = list(new_snapshot)
        
        # 更新未读列表：添新增的专辑，但要保持唯一
        unread_set = set(playlist_data.get('unread_albums', []))
        unread_set.update(new_albums)
        playlist_data['unread_albums'] = list(unread_set)
        
        # 更新专辑详细信息（如果提供）
        if album_details:
            album_details_dict = playlist_data.get('album_details', {})
            for album in album_details:
                album_id = album.get('album_id')
                if album_id:
                    album_details_dict[album_id] = {
                        'album_name': album.get('album_name'),
                        'artists': album.get('artists', []),
                        'link': album.get('link', '')
                    }
            playlist_data['album_details'] = album_details_dict
        
        self._save_data()
        return new_albums
    
    def get_unread_albums(self, playlist_id: str) -> List[int]:
        """获取未读专辑ID列表"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            return playlist_data.get('unread_albums', [])
        return []
    
    def get_unread_count(self, playlist_id: str) -> int:
        """获取未读专辑数量"""
        return len(self.get_unread_albums(playlist_id))
    
    def mark_all_as_read(self, playlist_id: str):
        """标记所有专辑为已读（清空未读列表）"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            # 清空未读列表，但保留当前快照
            playlist_data['unread_albums'] = []
            self._save_data()
    
    def mark_album_as_read(self, playlist_id: str, album_id: int):
        """标记单个专辑为已读"""
        playlist_data = self.get_playlist_history(playlist_id)
        if playlist_data:
            unread_albums = playlist_data.get('unread_albums', [])
            if album_id in unread_albums:
                unread_albums.remove(album_id)
                playlist_data['unread_albums'] = unread_albums
                self._save_data()
    
    def get_album_details(self, playlist_id: str) -> List[Dict[str, Any]]:
        """获取歌单的专辑详细信息列表"""
        playlist_data = self.get_playlist_history(playlist_id)
        if not playlist_data:
            return []
        
        album_details = playlist_data.get('album_details', {})
        album_snapshot = playlist_data.get('album_snapshot', [])
        unread_albums = set(playlist_data.get('unread_albums', []))
        
        # 构建专辑信息列表
        albums = []
        for album_id in album_snapshot:
            details = album_details.get(str(album_id) if isinstance(album_id, str) else album_id, {})
            albums.append({
                'album_id': album_id,
                'album_name': details.get('album_name', f'未知专辑 {album_id}'),
                'artists': details.get('artists', []),
                'link': details.get('link', '')
            })
        
        return albums
    
    def has_album_details(self, playlist_id: str) -> bool:
        """检查是否有缓存的专辑详细信息"""
        playlist_data = self.get_playlist_history(playlist_id)
        if not playlist_data:
            return False
        
        album_details = playlist_data.get('album_details', {})
        album_snapshot = playlist_data.get('album_snapshot', [])
        
        # 如果有专辑快照但详细信息不全，也视为有缓存
        return len(album_details) > 0 or len(album_snapshot) > 0

# 全局存储实例
_storage_instance = None

def get_storage(storage_file: str = 'data/playlist_history.json') -> PlaylistStorage:
    """获取存储实例（单例模式）"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = PlaylistStorage(storage_file)
    return _storage_instance

if __name__ == '__main__':
    import time
    storage = PlaylistStorage('test_storage.json')
    test_info = {
        'updateTime': 1773704789201,
        'trackCount': 200,
        'name': '热歌榜',
        'description': '测试描述'
    }
    storage.update_playlist_history('3778678', test_info)
    print("存储完成")