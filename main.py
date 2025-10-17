import logging
import os
import asyncio
import threading
import time
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import urllib.request
import json

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
PORT = int(os.environ.get('PORT', 10000))

application = None
event_loop = None
bot_initialized = False
bot_initialization_started = False

def keep_alive():
    """Функція для підтримки активності додатку без requests"""
    while True:
        try:
            # Використовуємо urllib замість requests
            with urllib.request.urlopen('https://chatrix-bot-4m1p.onrender.com/health', timeout=10) as response:
                logger.info(f"🔄 Keep-alive: {response.getcode()}")
        except Exception as e:
            logger.error(f"❌ Keep-alive помилка: {e}")
        
        # Чекаємо 4 хвилини між запитами
        time.sleep(240)

# Запускаємо keep-alive в окремому потоці
keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

def validate_environment():
    """Перевірка змінних середовища"""
    required_vars = ['BOT_TOKEN', 'ADMIN_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"❌ Відсутні обов'язкові змінні середовища: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    token = os.environ.get('BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        error_msg = "❌ Ви використовуєте тестовий токен. Встановіть реальний токен бота."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        admin_id = int(os.environ.get('ADMIN_ID', 0))
        if admin_id == 0:
            raise ValueError("ADMIN_ID не встановлено")
    except ValueError:
        raise ValueError("❌ ADMIN_ID має бути числовим значенням")
    
    logger.info("✅ Змінні середовища перевірені успішно")

def run_async_tasks():
    """Запуск асинхронних завдань в окремому потоці"""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()

async_thread = threading.Thread(target=run_async_tasks, daemon=True)
async_thread.start()

def setup_handlers(app_instance):
    """Налаштування обробників"""
    logger.info("🔄 Налаштування обробників...")
    
    from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
    from handlers.search import search_profiles, search_by_city, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile
    from handlers.admin import show_admin_panel, handle_admin_actions, show_users_list, show_banned_users, handle_broadcast_message, start_ban_user, start_unban_user, handle_ban_user, handle_unban_user, handle_user_search
    from keyboards.main_menu import get_main_menu
    
    # Команди
    app_instance.add_handler(CommandHandler("start", start))
    
    # Обробники кнопок
    app_instance.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
    app_instance.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
    app_instance.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
    app_instance.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
    app_instance.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
    app_instance.add_handler(MessageHandler(filters.Regex('^🔙 Меню$'), lambda update, context: update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(update.effective_user.id))))
    app_instance.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
    app_instance.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
    app_instance.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
    app_instance.add_handler(MessageHandler(filters.Regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
    app_instance.add_handler(MessageHandler(filters.Regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    app_instance.add_handler(CallbackQueryHandler(handle_like_callback, pattern='^like_'))

    # ДОДАЄМО ОБРОБНИКИ ДЛЯ НОВИХ КНОПОК - ВИКОРИСТОВУЄМО ЛЯМБДА
    app_instance.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), lambda update, context: handle_like_button(update, context)))
    app_instance.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), lambda update, context: handle_next_button(update, context)))

    # Адмін обробники
    app_instance.add_handler(MessageHandler(filters.Regex('^(👑 Адмін панель|📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування|🗑️ Скинути БД)$'), handle_admin_actions))
    app_instance.add_handler(MessageHandler(filters.Regex('^(📋 Список користувачів|🔍 Пошук користувача|🚫 Заблокувати користувача|✅ Розблокувати користувача|📋 Список заблокованих|🔙 Назад до адмін-панелі)$'), universal_handler))
    
    # Фото та універсальний обробник
    app_instance.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    app_instance.add_error_handler(error_handler)
    logger.info("✅ Всі обробники налаштовано")

if __name__ == "__main__":
    logger.info("🚀 Запуск додатку...")
    init_bot()
    
    logger.info(f"🚀 Запуск Flask сервера на порті {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)