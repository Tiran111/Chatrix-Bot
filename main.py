import os
import logging
from telegram.ext import Updater, CommandHandler

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update, context):
    user = update.message.from_user
    update.message.reply_text(f'Привіт {user.first_name}! Бот запущений! ✅')

def main():
    try:
        logger.info("🚀 Запуск бота...")
        
        # Отримуємо токен
        TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not TOKEN:
            logger.error("❌ Токен не знайдено!")
            # Виведемо всі змінні для дебагу
            for key, value in os.environ.items():
                if 'BOT' in key or 'TOKEN' in key:
                    logger.info(f"🔍 {key}: {value}")
            return
            
        logger.info(f"✅ Токен отримано, довжина: {len(TOKEN)}")
        
        # Створюємо Updater
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Додаємо обробники
        dispatcher.add_handler(CommandHandler("start", start))
        
        logger.info("✅ Бот запускається...")
        
        # Запускаємо бота
        updater.start_polling()
        logger.info("🤖 Бот працює!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()