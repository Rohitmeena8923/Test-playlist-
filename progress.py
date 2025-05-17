import time
from typing import Optional, Dict
from tqdm import tqdm

class ProgressHandler:
    def __init__(self, chat_id: int, bot):
        self.chat_id = chat_id
        self.bot = bot
        self.last_update_time = 0
        self.progress_messages = {}  # video_id: message_id
        self.pbar_cache = {}  # video_id: tqdm instance

    async def update_progress(self, d):
        if d['status'] == 'downloading':
            video_id = d['info_dict'].get('id')
            filename = d['info_dict'].get('_filename', 'Unknown')
            
            if video_id not in self.pbar_cache:
                self.pbar_cache[video_id] = tqdm(
                    total=d.get('total_bytes') or d.get('total_bytes_estimate'),
                    desc=filename[:20],
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                )
            
            pbar = self.pbar_cache[video_id]
            pbar.n = d['downloaded_bytes']
            pbar.refresh()
            
            # Only update Telegram every 5 seconds to avoid spamming
            current_time = time.time()
            if current_time - self.last_update_time >= 5:
                self.last_update_time = current_time
                
                percent = d.get('percent', 0)
                speed = d.get('speed', 0) / 1024  # KB/s
                eta = d.get('eta', 0)
                
                progress_bar = self._create_progress_bar(percent)
                speed_str = f"{speed:.1f} KB/s" if speed < 1024 else f"{speed/1024:.1f} MB/s"
                eta_str = self._format_eta(eta)
                
                message = (
                    f"Downloading: {filename[:50]}...\n\n"
                    f"{progress_bar} {percent:.1f}%\n"
                    f"Speed: {speed_str} | ETA: {eta_str}"
                )
                
                if video_id in self.progress_messages:
                    try:
                        await self.bot.edit_message_text(
                            chat_id=self.chat_id,
                            message_id=self.progress_messages[video_id],
                            text=message
                        )
                    except:
                        pass  # Message wasn't modified or wasn't found
                else:
                    sent_message = await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message
                    )
                    self.progress_messages[video_id] = sent_message.message_id
        
        elif d['status'] == 'finished':
            video_id = d['info_dict'].get('id')
            if video_id in self.pbar_cache:
                self.pbar_cache[video_id].close()
                del self.pbar_cache[video_id]
            
            if video_id in self.progress_messages:
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=self.progress_messages[video_id],
                        text=f"Download complete: {d['info_dict'].get('_filename', 'Unknown')}"
                    )
                except:
                    pass
                del self.progress_messages[video_id]

    def _create_progress_bar(self, percent: float) -> str:
        filled = '█' * int(percent / 5)
        empty = '░' * (20 - len(filled))
        return filled + empty

    def _format_eta(self, seconds: int) -> str:
        if seconds < 0:
            return "Unknown"
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"