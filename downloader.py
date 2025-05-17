import os
import asyncio
from yt_dlp import YoutubeDL, DownloadError
from typing import Callable, Optional
from utils import sanitize_filename
import logging

logger = logging.getLogger(__name__)

class YouTubePlaylistDownloader:
    def __init__(self):
        self.download_path = os.getenv('DOWNLOAD_PATH', './downloads')
        os.makedirs(self.download_path, exist_ok=True)
        self.max_retries = 3
        self.retry_delay = 5  # seconds

    async def download_playlist(
        self,
        playlist_url: str,
        quality: str,
        progress_callback: Optional[Callable],
        chat_id: int
    ) -> bool:
        ydl_opts = self._get_ydl_options(quality, progress_callback)
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                # First extract info without downloading
                info = await self._run_async(ydl.extract_info, playlist_url, download=False)
                
                if 'entries' in info:
                    playlist_title = sanitize_filename(info.get('title', 'playlist'))
                    playlist_dir = os.path.join(self.download_path, playlist_title)
                    os.makedirs(playlist_dir, exist_ok=True)
                    
                    # Now download with the proper output template
                    ydl_opts['outtmpl'] = os.path.join(playlist_dir, '%(title)s.%(ext)s')
                    await self._download_with_retries(ydl_opts, playlist_url)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}")
            raise

    async def _download_with_retries(self, ydl_opts, url):
        for attempt in range(self.max_retries + 1):
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    await self._run_async(ydl.download, [url])
                return True
            except DownloadError as e:
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
            except Exception as e:
                logger.error(f"Unexpected error during download: {e}")
                raise

    async def _run_async(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _get_ydl_options(self, quality: str, progress_callback: Optional[Callable]):
        opts = {
            'format': self._get_format_string(quality),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_callback] if progress_callback else [],
            'merge_output_format': 'mp4',
            'retries': self.max_retries,
            'fragment_retries': self.max_retries,
            'skip_unavailable_fragments': True,
            'extract_flat': False,
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
        else:
            opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
        
        return opts

    def _get_format_string(self, quality: str) -> str:
        if quality == 'best':
            return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality == 'audio':
            return 'bestaudio/best'
        else:
            return f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]/best'