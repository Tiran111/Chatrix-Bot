from flask import Flask, request
import threading
import asyncio
import os
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Створюємо новий Flask додаток (не імпортуємо з main.py)
app = Flask(__name__)

WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
application = None

def setup_bot():
    """Налаштування бота в окремому потоці"""
    global application
    
    try:
        logger.info("🔧 Налаштування бота...")
        
        # Імпортуємо все необхідне
        from config import TOKEN
        from telegram.ext import Application
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        
        # Налаштовуємо обробники з main.py
        try:
            # Імпортуємо функцію setup_handlers з main.py
            import sys
            sys.path.append('/opt/render/project/src')
            from main import setup_handlers
            setup_handlers(application)
            logger.info("✅ Всі обробники завантажено")
            
        except Exception as e:
            logger.error(f"❌ Помилка завантаження обробників: {e}")
            # Запасний варіант - простий обробник
            from telegram.ext import CommandHandler
            from telegram import Update
            
            async def start(update: Update, context):
                await update.message.reply_text("👋 Привіт! Chatrix Bot працює! 🎉")
            
            application.add_handler(CommandHandler("start", start))
            logger.info("✅ Простий обробник завантажено")
        
        # Встановлюємо вебхук
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def init_webhook():
            await application.initialize()
            await application.bot.set_webhook(WEBHOOK_URL)
            await application.start()
            logger.info("✅ Бот запущено та вебхук встановлено!")
            logger.info("🎯 Функціонал бота готовий до роботи!")
        
        loop.run_until_complete(init_webhook())
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ Помилка налаштування бота: {e}")
        import traceback
        traceback.print_exc()

# Запускаємо бота в окремому потоці
logger.info("🚀 Запуск бота...")
bot_thread = threading.Thread(target=setup_bot, daemon=True)
bot_thread.start()

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Обробник вебхука для Telegram"""
    try:
        if not application:
            return "Bot not initialized", 500
            
        update_data = request.get_json()
        if not update_data:
            return "Empty update data", 400
            
        # Обробляємо оновлення
        from telegram import Update
        update = Update.de_json(update_data, application.bot)
        
        # Використовуємо основний event loop бота
        if hasattr(application, 'update_queue'):
            async def put_update():
                await application.update_queue.put(update)
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(put_update())
                else:
                    loop.run_until_complete(put_update())
            except RuntimeError:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(put_update())
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Webhook помилка: {e}")
        return 'error', 500

# Додаємо унікальні маршрути (без конфліктів з main.py)
@app.route('/')
def home():
    return "🤖 Chatrix Bot is running with full functionality!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/test-bot')
def test_bot():
    """Тестовий маршрут для перевірки стану бота"""
    if application and application.bot:
        return f"✅ Bot is running. Webhook: {WEBHOOK_URL}"
    return "❌ Bot not initialized", 500

@app.route('/status')
def status():
    """Статус бота"""
    bot_status = "running" if application else "not initialized"
    return f"Bot status: {bot_status}", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Запуск сервера на порті {port}")
    app.run(host='0.0.0.0', port=port, debug=False)