import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста команда /start"""
    user = update.effective_user
    await update.message.reply_text(f"👋 Привіт, {user.first_name}! Бот працює! 🚀")

def main():
    logger.info("🚀 Запуск бота на Railway...")
    
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ BOT_TOKEN не знайдено!")
        return
    
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        logger.info("✅ Бот запущено!")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")

if __name__ == '__main__':
    main()