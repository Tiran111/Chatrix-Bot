import logging
import os
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Імпорт модулів
try:
    from database_postgres import db
    logger.info("✅ Використовується PostgreSQL база даних")
except ImportError as e:
    logger.error(f"❌ Помилка імпорту бази даних: {e}")
    raise

try:
    from config import ADMIN_ID, TOKEN
except ImportError as e:
    logger.error(f"❌ Помилка імпорту конфігурації: {e}")
    raise

# Глобальні змінні
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
PORT = int(os.environ.get('PORT', 10000))

# Глобальний об'єкт бота
application = None

# ==================== ПРОСТІ ФУНКЦІЇ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія команди /start"""
    user = update.effective_user
    await update.message.reply_text(f"👋 Вітаю, {user.first_name}! Бот працює! 🎉")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"❌ Помилка в боті: {context.error}", exc_info=True)

def setup_handlers(app):
    """Налаштування обробників"""
    app.add_handler(CommandHandler("start", start))
    app.add_error_handler(error_handler)

async def init_bot():
    """Ініціалізація бота"""
    global application
    
    try:
        logger.info("🔄 Ініціалізація бота...")
        
        # Створюємо додаток
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        setup_handlers(application)
        
        # Ініціалізуємо
        await application.initialize()
        
        # Встановлюємо вебхук
        await application.bot.set_webhook(WEBHOOK_URL)
        
        logger.info("✅ Бот успішно ініціалізовано!")
        logger.info(f"🌐 Вебхук встановлено: {WEBHOOK_URL}")
        return application
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}")
        return None

def run_bot():
    """Запуск бота в окремому потоці"""
    try:
        # Створюємо новий event loop для цього потоку
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ініціалізація бота
        bot_app = loop.run_until_complete(init_bot())
        
        if not bot_app:
            logger.error("❌ Не вдалося ініціалізувати бота")
            return
        
        logger.info("🔄 Бот запущено в потоці")
        
        # Запускаємо event loop
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ Помилка в потоці бота: {e}")

def process_update_safe(update_data):
    """Безпечна обробка оновлення"""
    global application
    
    try:
        if not application:
            logger.error("❌ Бот не ініціалізований")
            return False
            
        # Створюємо оновлення
        update = Update.de_json(update_data, application.bot)
        
        # Використовуємо event loop бота
        if hasattr(application, '_get_running_loop'):
            loop = application._get_running_loop()
        else:
            # Альтернативний спосіб отримати loop
            import asyncio
            loop = asyncio.get_event_loop()
        
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update), 
            loop
        )
        
        # Чекаємо результат
        try:
            future.result(timeout=10)
            logger.info("✅ Оновлення успішно оброблено")
            return True
        except asyncio.TimeoutError:
            logger.error("❌ Таймаут обробки оновлення")
            return False
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки оновлення: {e}")
        return False

# ==================== FLASK ROUTES ====================

@app.route('/')
def home():
    return "🤖 Chatrix Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/status')
def status():
    """Перевірка статусу"""
    global application
    return jsonify({
        'status': 'running',
        'bot_initialized': application is not None,
        'port': PORT
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    try:
        update_data = request.get_json()
        if update_data is None:
            return "Empty update data", 400
            
        logger.info(f"📨 Отримано вебхук від Telegram")
        
        # Обробляємо оновлення
        success = process_update_safe(update_data)
        
        if success:
            return 'ok'
        else:
            return "Error processing update", 500
        
    except Exception as e:
        logger.error(f"❌ Webhook помилка: {e}")
        return "Error", 200

# ==================== ЗАПУСК СЕРВЕРА ====================

def main():
    """Запуск програми"""
    
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Чекаємо трохи на ініціалізацію бота
    import time
    time.sleep(3)
    
    # Запуск Flask сервера
    logger.info(f"🚀 Запуск сервера на порті {PORT}")
    logger.info(f"🌐 URL: https://chatrix-bot-4m1p.onrender.com")
    
    # Важливо: використовуємо правильний хост і порт
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()