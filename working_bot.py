from flask import Flask, request, jsonify
import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Налаштування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
app = Flask(__name__)

# Глобальні змінні
application = None

async def init_bot():
    """Ініціалізація бота"""
    global application
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Ініціалізуємо
        await application.initialize()
        
        logger.info("✅ Бот ініціалізовано")
        return True
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}")
        return False

async def start(update: Update, context):
    """Обробник /start"""
    user = update.effective_user
    logger.info(f"🎯 Отримано /start від {user.id}")
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n"
        f"🆔 Ваш ID: {user.id}\n"
        "✅ Бот працює!\n\n"
        "🎉 Повідомлення отримано та оброблено!"
    )

async def echo(update: Update, context):
    """Ехо-обробник"""
    await update.message.reply_text(f"📝 Ви написали: {update.message.text}")

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Обробник вебхука"""
    try:
        if request.method == 'GET':
            return jsonify({"status": "webhook is ready"})
            
        # Обробляємо POST запит
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        
        logger.info(f"📨 Отримано вебхук: {data}")
        
        # Створюємо оновлення
        update = Update.de_json(data, application.bot)
        
        # Обробляємо асинхронно
        async def process_update():
            await application.process_update(update)
        
        # Запускаємо обробку
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_update())
        loop.close()
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ Помилка вебхука: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return "🤖 Chatrix Bot is RUNNING! ✅", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/test')
def test():
    return "🚀 Сервер працює! Вебхук готовий до роботи.", 200

@app.route('/set_webhook')
def set_webhook_route():
    """Встановити вебхук вручну"""
    try:
        import requests
        webhook_url = "https://chatrix-bot-4m1p.onrender.com/webhook"
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook",
            data={"url": webhook_url}
        )
        return f"✅ Вебхук встановлено! Відповідь: {response.json()}"
    except Exception as e:
        return f"❌ Помилка: {e}"

def main():
    """Запуск програми"""
    # Ініціалізація бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(init_bot())
    
    if not success:
        logger.error("❌ Не вдалося ініціалізувати бота")
        return
    
    # Запуск Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск сервера на порті {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()