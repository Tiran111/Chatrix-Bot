import asyncio
import os
import logging
from main import app, init_bot

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Головна функція запуску"""
    try:
        # Ініціалізація бота
        logger.info("🔧 Ініціалізація бота...")
        if init_bot():
            logger.info("✅ Бот успішно ініціалізовано")
        else:
            logger.error("❌ Помилка ініціалізації бота")
            return
        
        # Запуск Flask сервера
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"🌐 Запуск сервера на порті {port}")
        
        # Імпортуємо та запускаємо Flask
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску: {e}")
        raise

if __name__ == "__main__":
    # Запускаємо асинхронно
    asyncio.run(main())