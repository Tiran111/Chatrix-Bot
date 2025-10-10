import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Запуск бота...")
    
    # Список бібліотек для перевірки
    libraries = ['telegram', 'aiohttp']
    
    for lib in libraries:
        try:
            __import__(lib)
            logger.info(f"✅ {lib} завантажено")
        except ImportError as e:
            logger.error(f"❌ {lib} не встановлено: {e}")
            return
    
    # Якщо всі бібліотеки встановлені - запускаємо бота
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            await update.message.reply_text(f"👋 Привіт, {user.first_name}! Бот працює! 🚀")
        
        TOKEN = os.environ.get('BOT_TOKEN')
        if not TOKEN:
            logger.error("❌ BOT_TOKEN не знайдено!")
            return
        
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        logger.info("✅ Бот запускається...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")

if __name__ == '__main__':
    main()