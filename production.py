from waitress import serve
from main import app, init_bot
import os
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Запуск у продакшен режимі"""
    try:
        # Ініціалізація бота
        logger.info("🔧 Ініціалізація бота...")
        if init_bot():
            logger.info("✅ Бот успішно ініціалізовано")
        else:
            logger.error("❌ Помилка ініціалізації бота")
        
        # Запуск сервера
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"🌐 Запуск сервера на порті {port}")
        
        serve(app, host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску: {e}")
        raise

if __name__ == "__main__":
    main()