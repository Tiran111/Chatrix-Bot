import os
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Тестуємо імпорт бібліотек
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    logger.info("✅ Бібліотеки завантажено успішно!")
    TELEGRAM_LOADED = True
except ImportError as e:
    logger.error(f"❌ Помилка завантаження бібліотек: {e}")
    TELEGRAM_LOADED = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста команда /start для тесту"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привіт, {user.first_name}!\n"
        f"🤖 Бот працює на Railway!\n"
        f"✅ Бібліотеки завантажені: {TELEGRAM_LOADED}"
    )

def main():
    logger.info("🚀 Запуск тестового бота на Railway...")
    
    # Отримуємо токен з змінних середовища Railway
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ BOT_TOKEN не знайдено в змінних середовища!")
        return
    
    if not TELEGRAM_LOADED:
        logger.error("❌ Бібліотеки не завантажено!")
        return
    
    try:
        # Створюємо додаток
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        logger.info("✅ Бот запускається...")
        
        # Запускаємо бота
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()