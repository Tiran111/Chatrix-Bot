import os
import logging
from flask import Flask, request, jsonify
import asyncio
from telegram.ext import Application, CommandHandler
from telegram import Update

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфігурація
TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

# Глобальні змінні
application = None

# ==================== TELEGRAM BOT ====================

async def start(update: Update, context):
    """Обробник команди /start"""
    user = update.effective_user
    await update.message.reply_text(f"👋 Вітаю, {user.first_name}! Бот працює! 🎉")

async def init_bot():
    """Ініціалізація бота"""
    global application
    try:
        logger.info("🔄 Ініціалізація бота...")
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        await application.initialize()
        await application.bot.set_webhook("https://chatrix-bot-4m1p.onrender.com/webhook")
        await application.start()
        
        logger.info("✅ Бот успішно ініціалізовано!")
        return application
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}")
        return None

# ==================== FLASK ROUTES ====================

@app.route('/')
def home():
    return jsonify({"status": "running", "service": "Chatrix Bot"}), 200

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    global application
    try:
        if not application:
            return "Bot not initialized", 500
            
        update_data = request.get_json()
        if not update_data:
            return "No data", 400
        
        # Створюємо оновлення
        update = Update.de_json(update_data, application.bot)
        
        # Обробляємо оновлення
        asyncio.create_task(application.process_update(update))
        
        return "ok", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "Error", 500

# ==================== ЗАПУСК ====================

def run_bot():
    """Запуск бота в окремому потоці"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_bot())
    
    # Запускаємо event loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == '__main__':
    # Запускаємо бота в окремому потоці
    import threading
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаємо Flask сервер
    logger.info(f"🚀 Запуск сервера на порті {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)