import os
import logging
from main import app, init_bot
rint(f"🔧 PORT змінна: {os.environ.get('PORT')}")
print(f"🔧 Поточний каталог: {os.getcwd()}")
print(f"🔧 Файли в каталозі: {os.listdir('.')}")

port = int(os.environ.get("PORT", 10000))
print(f"🌐 Використовуємо порт: {port}")

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Отримуємо порт для Render
    port = int(os.environ.get("PORT", 10000))
    
    print("=" * 50)
    print(f"🚀 Запуск Chatrix Bot на порті {port}")
    print("=" * 50)
    
    # Ініціалізація бота
    logger.info("🔧 Ініціалізація бота...")
    if init_bot():
        logger.info("✅ Бот успішно ініціалізовано")
    else:
        logger.error("❌ Помилка ініціалізації бота")
    
    # Явно вказуємо порт для Flask
    logger.info(f"🌐 Запуск Flask сервера на 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)