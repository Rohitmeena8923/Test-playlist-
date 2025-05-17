import os
from yt_dlp import YoutubeDL
from typing import Callable, Optional
from utils import sanitize_filename

class YouTubePlaylistDownloader:
    def __init__(self):
        self.download_path = os.getenv('DOWNLOAD_PATH', './downloads')
        os.makedirs(self.download_path, exist_ok=True)

    async def download_playlist(
        self,
        playlist_url: str,
        quality: str,
        progress_callback: Optional[Callable],
        chat_id: int
    ):
        ydl_opts = self._get_ydl_options(quality, progress_callback)
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
            if 'entries' in info:
                playlist_title = sanitize_filename(info.get('title', 'playlist'))
                playlist_dir = os.path.join(self.download_path, playlist_title)
                os.makedirs(playlist_dir, exist_ok=True)
                
                ydl_opts['outtmpl'] = os.path.join(playlist_dir, '%(title)s.%(ext)s')
                
                with YoutubeDL(ydl_opts) as ydl_playlist:
                    ydl_playlist.download([playlist_url])

    def _get_ydl_options(self, quality: str, progress_callback: Optional[Callable]):
        opts = {
            'format': self._get_format_string(quality),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_callback] if progress_callback else [],
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        if quality == 'audio':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        return opts

    def _get_format_string(self, quality: str) -> str:
        if quality == 'best':
            return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality == 'audio':
            return 'bestaudio/best'
        else:
            return f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]/best'