import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("🚀 Запуск бота...")
        
        # Перевірка токена
        TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        if not TOKEN:
            logger.error("❌ Токен не знайдено!")
            # Виводимо всі змінні
            for key in os.environ:
                if 'TOKEN' in key or 'BOT' in key:
                    logger.info(f"🔍 {key}: {os.environ[key][:10]}...")
            return
        
        logger.info(f"✅ Токен отримано: {TOKEN[:10]}...")
        
        # Спроба імпорту після встановлення бібліотеки
        try:
            from telegram.ext import Updater, CommandHandler
        except ImportError as e:
            logger.error(f"❌ Помилка імпорту бібліотеки: {e}")
            return
        
        # Створення бота
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        def start(update, context):
            update.message.reply_text('✅ Бот працює!')
        
        dispatcher.add_handler(CommandHandler("start", start))
        
        logger.info("🤖 Бот запускається...")
        updater.start_polling()
        logger.info("🎉 Бот успішно запущений!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"💥 Критична помилка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()