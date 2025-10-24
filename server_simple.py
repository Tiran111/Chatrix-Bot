from flask import Flask, request
import threading
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальні змінні
TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
application = None

async def start(update: Update, context):
    await update.message.reply_text("👋 Привіт! Бот працює!")

def setup_bot():
    """Налаштування бота в окремому потоці"""
    global application
    
    try:
        logger.info("🔧 Налаштування бота...")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                            lambda u, c: u.message.reply_text("Отримано повідомлення!")))
        
        # Встановлюємо вебхук
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def init_webhook():
            await application.initialize()
            await application.bot.set_webhook(WEBHOOK_URL)
            await application.start()
            logger.info("✅ Бот запущено!")
        
        loop.run_until_complete(init_webhook())
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ Помилка налаштування бота: {e}")

# Запускаємо бота в окремому потоці
bot_thread = threading.Thread(target=setup_bot, daemon=True)
bot_thread.start()

@app.route('/')
def home():
    return "🤖 Chatrix Bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        update_data = request.get_json()
        if application and update_data:
            update = Update.de_json(update_data, application.bot)
            
            # Обробляємо оновлення
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.process_update(update))
            
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)