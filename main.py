import os
import logging
from telegram.ext import Application, CommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    user = update.effective_user
    await update.message.reply_text(f"👋 Привіт, {user.first_name}! Бот працює на Render! 🚀")

def main():
    logger.info("🚀 Запуск бота на Render...")
    
    TOKEN = os.environ.get('BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ BOT_TOKEN не знайдено!")
        return
    
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start_command))
        
        logger.info("✅ Бот запускається...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")

if __name__ == '__main__':
    main()