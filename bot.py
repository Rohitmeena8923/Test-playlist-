import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from downloader import YouTubePlaylistDownloader
from progress import ProgressHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YouTubeDownloaderBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.allowed_user_ids = [int(id) for id in os.getenv('ALLOWED_USER_IDS', '').split(',') if id]
        self.downloader = YouTubePlaylistDownloader()
        self.user_states = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_user_allowed(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        await update.message.reply_text(
            "🎬 YouTube Playlist Downloader Bot\n\n"
            "Send me a YouTube playlist URL to download videos"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_user_allowed(update):
            return

        text = update.message.text.strip()
        chat_id = update.message.chat_id

        if any(p in text for p in ['youtube.com/playlist?', 'youtu.be/playlist?']):
            self.user_states[chat_id] = {'playlist_url': text}
            await self._ask_quality(update, context)
        else:
            await update.message.reply_text("⚠️ Please send a valid YouTube playlist URL")

    async def _ask_quality(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        qualities = [
            ['144p', '240p', '360p'],
            ['480p', '720p', '1080p'],
            ['Best Quality', 'Audio Only']
        ]
        
        keyboard = [
            [InlineKeyboardButton(q, callback_data=q.split()[0].lower()) 
             for q in row] for row in qualities
        ]
        
        await update.message.reply_text(
            '📺 Select download quality:',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_quality_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id
        quality = query.data

        if chat_id not in self.user_states:
            await query.edit_message_text("❌ Session expired. Please start over.")
            return

        playlist_url = self.user_states[chat_id]['playlist_url']
        await query.edit_message_text(f"⏳ Starting download at {quality} quality...")

        progress_handler = ProgressHandler(chat_id, context.bot)
        
        try:
            success = await self.downloader.download_playlist(
                playlist_url,
                quality,
                progress_handler.update_progress,
                chat_id
            )
            
            if success:
                await context.bot.send_message(chat_id, "✅ All downloads completed!")
            else:
                await context.bot.send_message(
                    chat_id,
                    "⚠️ Some videos failed to download. Try again later."
                )
                
        except Exception as e:
            error_msg = self._format_error(e)
            await context.bot.send_message(chat_id, error_msg)
            logger.error(f"Download failed: {error_msg}")
        finally:
            self.user_states.pop(chat_id, None)

    def _format_error(self, error):
        error_str = str(error)
        if "Incomplete data" in error_str:
            return (
                "⚠️ Download failed - Network Error\n\n"
                "Possible solutions:\n"
                "1. Try again later\n"
                "2. Use a better network connection\n"
                "3. Try smaller playlists\n"
                "4. Contact support if persists"
            )
        elif "Unavailable" in error_str:
            return "❌ Video is unavailable or private"
        else:
            return f"⚠️ Error: {error_str[:200]}"

    def _is_user_allowed(self, update: Update):
        if not self.allowed_user_ids:
            return True
        return update.effective_user.id in self.allowed_user_ids

    def run(self):
        application = ApplicationBuilder().token(self.token).build()
        
        handlers = [
            CommandHandler('start', self.start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
            CallbackQueryHandler(self.handle_quality_selection)
        ]
        
        for handler in handlers:
            application.add_handler(handler)

        logger.info("Bot is running...")
        application.run_polling()

if __name__ == '__main__':
    YouTubeDownloaderBot().run()