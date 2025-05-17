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
        self.user_states = {}  # To track user's current state

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_user_allowed(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        await update.message.reply_text(
            "Welcome to YouTube Playlist Downloader Bot!\n\n"
            "Send me a YouTube playlist URL to get started."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_user_allowed(update):
            return

        text = update.message.text
        chat_id = update.message.chat_id

        if 'youtube.com/playlist?' in text or 'youtu.be/playlist?' in text:
            self.user_states[chat_id] = {'playlist_url': text}
            await self._ask_quality(update, context)
        else:
            await update.message.reply_text("Please send a valid YouTube playlist URL.")

    async def _ask_quality(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        keyboard = [
            [
                InlineKeyboardButton("144p", callback_data='144'),
                InlineKeyboardButton("240p", callback_data='240'),
                InlineKeyboardButton("360p", callback_data='360'),
            ],
            [
                InlineKeyboardButton("480p", callback_data='480'),
                InlineKeyboardButton("720p", callback_data='720'),
                InlineKeyboardButton("1080p", callback_data='1080'),
            ],
            [
                InlineKeyboardButton("Best Available", callback_data='best'),
                InlineKeyboardButton("Audio Only", callback_data='audio'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            'Please choose the download quality:',
            reply_markup=reply_markup
        )

    async def handle_quality_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id
        quality = query.data

        if chat_id not in self.user_states or 'playlist_url' not in self.user_states[chat_id]:
            await query.edit_message_text("Error: No playlist URL found. Please start over.")
            return

        playlist_url = self.user_states[chat_id]['playlist_url']
        await query.edit_message_text(f"Starting download for playlist at {quality}p quality...")

        # Initialize progress handler
        progress_handler = ProgressHandler(chat_id, context.bot)
        
        try:
            success = await self.downloader.download_playlist(
                playlist_url,
                quality,
                progress_handler.update_progress,
                chat_id
            )
            if success:
                await context.bot.send_message(chat_id, "All videos downloaded successfully!")
            else:
                await context.bot.send_message(chat_id, "Some videos failed to download. Please try again.")
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}")
            error_msg = str(e)
            
            if "Incomplete data received" in error_msg:
                error_msg = (
                    "Download failed due to incomplete data received from YouTube.\n\n"
                    "This is usually a temporary issue. Please try again later."
                )
            elif "Unsupported URL" in error_msg:
                error_msg = "Invalid YouTube playlist URL. Please check the URL and try again."
            else:
                error_msg = f"Download failed: {error_msg}"
            
            await context.bot.send_message(chat_id, error_msg)
        finally:
            if chat_id in self.user_states:
                del self.user_states[chat_id]

    def _is_user_allowed(self, update: Update):
        if not self.allowed_user_ids:  # If no restrictions
            return True
        return update.effective_user.id in self.allowed_user_ids

    def run(self):
        application = ApplicationBuilder().token(self.token).build()

        # Add handlers
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_quality_selection))

        # Run the bot
        application.run_polling()

if __name__ == '__main__':
    bot = YouTubeDownloaderBot()
    bot.run()