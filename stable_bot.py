import os
import asyncio
import threading
from flask import Flask, request
from telegram.ext import Application, CommandHandler
from telegram import Update

app = Flask(__name__)
TOKEN = os.environ.get('BOT_TOKEN')

# Глобальний об'єкт бота
application = None

async def start(update: Update, context):
    """Стабільний старт"""
    user = update.effective_user
    print(f"🎯 Отримано /start від {user.id}")
    await update.message.reply_text(f"👋 Вітаю, {user.first_name}! Бот стабільно працює! 🎉")

async def init_bot():
    """Ініціалізація бота"""
    global application
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    await application.initialize()
    await application.bot.set_webhook("https://chatrix-bot-4m1p.onrender.com/webhook")
    await application.start()
    
    print("✅ Бот ініціалізовано")
    return application

def run_bot():
    """Запуск бота в потоці"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_bot())
        loop.run_forever()
    except Exception as e:
        print(f"❌ Помилка в потоці бота: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробник вебхука"""
    global application
    
    try:
        if not application:
            return "Bot not initialized", 500
            
        update_data = request.get_json()
        if not update_data:
            return "Empty update data", 400
        
        # Створюємо оновлення
        update = Update.de_json(update_data, application.bot)
        
        # Додаємо завдання в event loop бота
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update), 
            application._get_running_loop()
        )
        
        # Чекаємо результат
        try:
            future.result(timeout=10)
            return 'ok'
        except asyncio.TimeoutError:
            print("❌ Таймаут обробки оновлення")
            return "Timeout", 500
            
    except Exception as e:
        print(f"❌ Webhook помилка: {e}")
        return "Error", 500

@app.route('/')
def home():
    return "🤖 Bot is running STABLY! ✅", 200

if __name__ == '__main__':
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Чекаємо на ініціалізацію
    import time
    time.sleep(5)
    
    # Запускаємо Flask
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Запуск стабільного бота на порті {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)