import os
import logging

# Спростимо код - без імпортів на початку
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Спроба запуску бота...")
    
    # Спершу перевіримо чи бібліотеки встановлені
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        logger.info("✅ Бібліотеки завантажено!")
    except ImportError as e:
        logger.error(f"❌ Бібліотеки не встановлені: {e}")
        logger.info("📦 Перевірте requirements.txt")
        return
    
    # Тільки після успішного імпорту визначаємо функції
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"👋 Привіт, {user.first_name}! Бот працює на Railway! 🚀")
    
    # Отримуємо токен
    TOKEN = os.environ.get('BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ BOT_TOKEN не знайдено!")
        return
    
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        logger.info("✅ Бот запускається...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску: {e}")

if __name__ == '__main__':
    main()