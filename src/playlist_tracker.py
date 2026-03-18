#!/usr/bin/env python3
"""
网易云歌单追踪模块
"""
import time
from typing import List, Dict, Any, Optional
from pyncm import GetCurrentSession, apis

class PlaylistTracker:
    def __init__(self):
        self.session = GetCurrentSession()
        # 设置用户代理，避免被屏蔽
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_playlist_info(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """获取歌单基本信息"""
        try:
            resp = apis.playlist.GetPlaylistInfo(playlist_id)
            if resp.get('code') == 200:
                return resp.get('playlist')
            else:
                print(f"获取歌单信息失败，错误码: {resp.get('code')}")
                return None
        except Exception as e:
            print(f"获取歌单信息时发生异常: {e}")
            return None
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """获取歌单所有歌曲列表（支持分页）"""
        # 首先获取歌单基本信息，得到总歌曲数
        playlist = self.get_playlist_info(playlist_id)
        if not playlist:
            return []
        
        total_tracks = playlist.get('trackCount', 0)
        if total_tracks == 0:
            return []
        
        all_tracks = []
        page_size = 500  # 每次获取500首，API限制最大1000
        max_retries = 3
        
        for offset in range(0, total_tracks, page_size):
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    resp = apis.playlist.GetPlaylistAllTracks(
                        playlist_id, 
                        offset=offset, 
                        limit=min(page_size, total_tracks - offset)
                    )
                    if resp.get('code') == 200:
                        tracks = resp.get('songs', [])
                        all_tracks.extend(tracks)
                        success = True
                        # 输出进度
                        print(f"已获取 {len(all_tracks)}/{total_tracks} 首歌曲")
                        # 添加短暂延迟，避免触发API限制
                        time.sleep(0.1)
                    else:
                        print(f"获取失败，错误码: {resp.get('code')}")
                        retry_count += 1
                except Exception as e:
                    print(f"获取异常: {e}")
                    retry_count += 1
            
            if not success:
                print(f"经过 {max_retries} 次重试后仍失败，停止获取")
                break
        
        return all_tracks
    
    def extract_album_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        """从歌曲信息中提取专辑信息"""
        album = track.get('al', {})
        artists = track.get('ar', [])
        return {
            'track_id': track.get('id'),
            'track_name': track.get('name'),
            'album_id': album.get('id'),
            'album_name': album.get('name'),
            'album_pic_url': album.get('picUrl'),
            'artists': [{'id': ar.get('id'), 'name': ar.get('name')} for ar in artists],
            'duration': track.get('dt', 0)  # 歌曲时长，毫秒
        }
    
    def get_all_albums_from_playlist(self, playlist_id: str, tracks: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """从歌单中提取所有专辑信息（去重）
        
        Args:
            playlist_id: 歌单ID
            tracks: 可选的歌曲列表，如果提供则直接使用，否则会调用get_playlist_tracks获取
        """
        if tracks is None:
            tracks = self.get_playlist_tracks(playlist_id)
        albums_dict = {}
        
        for track in tracks:
            album_info = self.extract_album_info(track)
            album_id = album_info['album_id']
            if album_id not in albums_dict:
                albums_dict[album_id] = album_info
            # 如果同一专辑有多首歌曲，可以记录歌曲数量
            # 暂时只保留第一个出现的
        
        return list(albums_dict.values())
    
    def generate_album_link(self, album_id: int) -> str:
        """生成网易云音乐专辑链接"""
        return f"https://music.163.com/#/album?id={album_id}"
    
    def generate_track_link(self, track_id: int) -> str:
        """生成歌曲链接"""
        return f"https://music.163.com/#/song?id={track_id}"
    
    def check_for_updates(self, playlist_id: str, last_update_time: Optional[int] = None) -> Dict[str, Any]:
        """检查歌单是否有更新"""
        playlist = self.get_playlist_info(playlist_id)
        if not playlist:
            return {'has_update': False, 'message': '获取歌单失败'}
        
        current_update_time = playlist.get('updateTime')
        track_count = playlist.get('trackCount')
        
        if last_update_time is None:
            return {
                'has_update': True,
                'message': '首次获取歌单信息',
                'current_update_time': current_update_time,
                'track_count': track_count
            }
        
        if current_update_time != last_update_time:
            if current_update_time:
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_update_time/1000))
            else:
                time_str = "未知时间"
            return {
                'has_update': True,
                'message': f'歌单已更新，更新时间: {time_str}',
                'current_update_time': current_update_time,
                'previous_update_time': last_update_time,
                'track_count': track_count
            }
        else:
            return {
                'has_update': False,
                'message': '歌单未更新',
                'current_update_time': current_update_time,
                'track_count': track_count
            }

if __name__ == '__main__':
    # 测试代码
    tracker = PlaylistTracker()
    playlist_id = '3778678'
    info = tracker.get_playlist_info(playlist_id)
    if info:
        print(f"歌单名称: {info.get('name')}")
        print(f"描述: {info.get('description')}")
        print(f"歌曲数量: {info.get('trackCount')}")
        print(f"更新时间: {info.get('updateTime')}")
        
        albums = tracker.get_all_albums_from_playlist(playlist_id)
        print(f"专辑数量: {len(albums)}")
        for album in albums[:3]:
            print(f"专辑: {album['album_name']} (ID: {album['album_id']})")
            print(f"链接: {tracker.generate_album_link(album['album_id'])}")