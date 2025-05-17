import os
import asyncio
from yt_dlp import YoutubeDL
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

class YouTubePlaylistDownloader:
    def __init__(self):
        self.download_path = os.getenv('DOWNLOAD_PATH', './downloads')
        os.makedirs(self.download_path, exist_ok=True)
        self.max_retries = 3
        self.retry_delay = 10  # Increased delay

    async def download_playlist(
        self,
        url: str,
        quality: str,
        progress_callback: Optional[Callable],
        chat_id: int
    ) -> bool:
        opts = self._get_options(quality, progress_callback)
        
        try:
            return await self._download_with_retries(url, opts)
        except Exception as e:
            logger.error(f"Final download attempt failed: {e}")
            raise

    async def _download_with_retries(self, url, opts):
        for attempt in range(1, self.max_retries + 1):
            try:
                with YoutubeDL(opts) as ydl:
                    await self._run_in_executor(ydl.download, [url])
                    return True
                    
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                
                logger.warning(f"Attempt {attempt} failed, retrying... Error: {e}")
                await asyncio.sleep(self.retry_delay * attempt)  # Exponential backoff

    async def _run_in_executor(self, func, args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    def _get_options(self, quality, progress_callback):
        opts = {
            'format': self._get_format(quality),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_callback] if progress_callback else [],
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'extractor_args': {'youtube': {'skip': ['dash', 'hls']}},
            'socket_timeout': 30,
            'noprogress': True,
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
        }

        if quality == 'audio':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            })
        else:
            opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]

        return opts

    def _get_format(self, quality):
        if quality == 'best':
            return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
        elif quality == 'audio':
            return 'bestaudio'
        else:
            return f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'