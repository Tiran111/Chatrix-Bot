from flask import Flask, request
import threading
import asyncio
import os
import logging
from main import app as flask_app, setup_handlers
from config import TOKEN, ADMIN_ID
from telegram.ext import Application
from telegram import Update
import importlib

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
application = None

def setup_bot():
    """Налаштування бота в окремому потоці"""
    global application
    
    try:
        logger.info("🔧 Налаштування бота...")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        
        # Імпортуємо та налаштовуємо ваші обробники
        try:
            # Імпортуємо всі необхідні модулі
            from handlers.profile import start_profile_creation, show_my_profile, handle_profile_message, handle_main_photo
            from handlers.search import search_profiles, search_by_city, show_next_profile, handle_like
            from handlers.admin import handle_admin_actions, show_admin_panel
            from handlers.notifications import notification_system
            
            # Налаштовуємо обробники з main.py
            setup_handlers(application)
            
            logger.info("✅ Всі обробники завантажено")
            
        except ImportError as e:
            logger.error(f"❌ Помилка імпорту обробників: {e}")
            # Використовуємо простий обробник як запасний варіант
            from telegram.ext import CommandHandler, MessageHandler, filters
            
            async def start(update: Update, context):
                await update.message.reply_text("👋 Привіт! Основний функціонал завантажується...")
            
            async def echo(update: Update, context):
                await update.message.reply_text("🔧 Бот в режимі обслуговування. Спробуйте пізніше.")
            
            application.add_handler(CommandHandler("start", start))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
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

@flask_app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Обробник вебхука для Telegram"""
    try:
        if not application:
            return "Bot not initialized", 500
            
        update_data = request.get_json()
        if not update_data:
            return "Empty update data", 400
            
        # Обробляємо оновлення в тому ж потоці, де працює бот
        update = Update.de_json(update_data, application.bot)
        
        # Використовуємо основний event loop бота для обробки
        if hasattr(application, 'update_queue'):
            # Додаємо оновлення в чергу бота
            async def put_update():
                await application.update_queue.put(update)
            
            # Запускаємо в потоці бота
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(put_update())
                else:
                    loop.run_until_complete(put_update())
            except RuntimeError:
                # Якщо немає event loop, створюємо новий
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(put_update())
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Webhook помилка: {e}")
        return 'error', 500

# Додаємо тестові маршрути
@flask_app.route('/')
def home():
    return "🤖 Chatrix Bot is running with full functionality!", 200

@flask_app.route('/health')
def health():
    return "OK", 200

@flask_app.route('/test-bot')
def test_bot():
    """Тестовий маршрут для перевірки стану бота"""
    if application and application.bot:
        return f"✅ Bot is running. Webhook: {WEBHOOK_URL}"
    return "❌ Bot not initialized", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Запуск сервера на порті {port}")
    flask_app.run(host='0.0.0.0', port=port, debug=False)