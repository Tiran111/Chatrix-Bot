import os
import logging
from main import app, init_bot

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Ініціалізація бота
    logger.info("🔧 Ініціалізація бота...")
    if init_bot():
        logger.info("✅ Бот успішно ініціалізовано")
    else:
        logger.error("❌ Помилка ініціалізації бота")
    
    # Запуск сервера
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Запуск сервера на порті {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)