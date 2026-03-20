#!/usr/bin/env python3
"""
数据存储模块
"""
import json
import os
import time
from typing import Dict, Any, Optional, List

# 缓存大小限制配置
MAX_ALBUMS_PER_PLAYLIST = 5000  # 每个歌单最多缓存专辑数量
MAX_PLAYLISTS = 100             # 最多保存歌单数量
MAX_HISTORY_PER_PLAYLIST = 10  # 每个歌单保留的历史记录数
CACHE_EXPIRE_DAYS = 90          # 缓存过期天数（90天未访问的歌单将被清理）

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
        
        # 只保留最近的历史记录
        if len(self.data[playlist_id]['history']) > MAX_HISTORY_PER_PLAYLIST:
            self.data[playlist_id]['history'] = self.data[playlist_id]['history'][-MAX_HISTORY_PER_PLAYLIST:]
        
        self._save_data()
        
        # 定期清理过期缓存（每10次操作或每次更新时）
        self._cleanup_counter = getattr(self, '_cleanup_counter', 0) + 1
        if self._cleanup_counter >= 10:
            self.cleanup_expired_cache()
            self._cleanup_counter = 0
    
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
        new_snapshot_set = set(album_ids)
        
        # 找出新增的专辑（在新快照中但不在旧快照中）
        new_albums = list(new_snapshot_set - old_snapshot)
        
        # 限制专辑数量：保留最新的（假设album_ids是按某种顺序的，取最新的）
        # 如果新快照超过限制，截断保留最新的
        if len(album_ids) > MAX_ALBUMS_PER_PLAYLIST:
            # 保留最新的专辑（列表末尾的是最新的）
            album_ids = album_ids[-MAX_ALBUMS_PER_PLAYLIST:]
            new_snapshot_set = set(album_ids)
            # 重新计算新增专辑
            new_albums = list(new_snapshot_set - old_snapshot)
        
        # 更新快照
        playlist_data['album_snapshot'] = album_ids
        
        # 更新未读列表：添加新增的专辑，但要保持唯一
        unread_set = set(playlist_data.get('unread_albums', []))
        unread_set.update(new_albums)
        # 同时清理不在快照中的未读专辑
        unread_set = unread_set.intersection(new_snapshot_set)
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
            # 清理不在快照中的详细信息
            valid_keys = set()
            for k in album_details_dict.keys():
                try:
                    if k.isdigit():
                        valid_keys.add(int(k))
                    else:
                        valid_keys.add(k)
                except (ValueError, TypeError):
                    pass
            
            playlist_data['album_details'] = {
                k: v for k, v in album_details_dict.items()
                if k in valid_keys and k in new_snapshot_set
            }
        
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
            # album_details 的 key 可能是 int 或 str，统一处理
            key = str(album_id) if isinstance(album_id, int) else album_id
            details = album_details.get(key, {})
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
    
    def cleanup_expired_cache(self):
        """清理过期缓存，限制存储大小"""
        current_time = int(time.time() * 1000)
        expire_millis = CACHE_EXPIRE_DAYS * 24 * 60 * 60 * 1000
        
        playlists_to_remove = []
        
        for playlist_id, playlist_data in self.data.items():
            # 检查是否过期（超过指定天数未访问）
            last_check = playlist_data.get('last_check', 0)
            if last_check > 0 and (current_time - last_check) > expire_millis:
                playlists_to_remove.append(playlist_id)
                continue
            
            # 限制每个歌单的专辑数量
            album_snapshot = playlist_data.get('album_snapshot', [])
            if len(album_snapshot) > MAX_ALBUMS_PER_PLAYLIST:
                # 只保留最新的专辑（假设专辑列表是按添加顺序的）
                playlist_data['album_snapshot'] = album_snapshot[-MAX_ALBUMS_PER_PLAYLIST:]
                
                # 同时清理album_details中不在snapshot的条目
                album_details = playlist_data.get('album_details', {})
                valid_album_ids = set(playlist_data['album_snapshot'])
                playlist_data['album_details'] = {
                    k: v for k, v in album_details.items() 
                    if int(k) in valid_album_ids
                }
                
                # 清理未读列表中不在snapshot的条目
                unread_albums = playlist_data.get('unread_albums', [])
                playlist_data['unread_albums'] = [
                    aid for aid in unread_albums 
                    if aid in valid_album_ids
                ]
        
        # 删除过期的歌单
        for playlist_id in playlists_to_remove:
            if playlist_id in self.data:
                del self.data[playlist_id]
        
        # 限制歌单总数量（按最后检查时间排序，删除最旧的）
        if len(self.data) > MAX_PLAYLISTS:
            # 按last_check时间排序，最旧的在前
            sorted_playlists = sorted(
                self.data.items(),
                key=lambda x: x[1].get('last_check', 0) if x[1].get('last_check') else 0
            )
            
            # 保留固定状态的歌单和最新的
            kept_playlists = []
            removed_count = 0
            excess = len(self.data) - MAX_PLAYLISTS
            
            for pid, pdata in sorted_playlists:
                if excess <= 0:
                    kept_playlists.append((pid, pdata))
                    continue
                
                # 不删除固定的歌单
                if pdata.get('pinned', False):
                    kept_playlists.append((pid, pdata))
                else:
                    removed_count += 1
                    excess -= 1
            
            # 重建data字典
            self.data = dict(kept_playlists)
        
        if playlists_to_remove or len(self.data) > MAX_PLAYLISTS:
            self._save_data()
        
        return len(playlists_to_remove)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_albums = 0
        total_playlists = len(self.data)
        
        for playlist_data in self.data.values():
            total_albums += len(playlist_data.get('album_snapshot', []))
        
        return {
            'total_playlists': total_playlists,
            'total_albums': total_albums,
            'max_playlists': MAX_PLAYLISTS,
            'max_albums_per_playlist': MAX_ALBUMS_PER_PLAYLIST,
            'cache_expire_days': CACHE_EXPIRE_DAYS
        }

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