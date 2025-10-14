import logging
import os
import asyncio
import threading
import time
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

# Імпорт ваших модулів
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID

# Імпорт обробників
from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile, handle_like_back
from handlers.admin import show_admin_panel, handle_admin_actions, show_users_list, show_banned_users, handle_broadcast_message, start_ban_user, start_unban_user, handle_ban_user, handle_unban_user, handle_user_search
from handlers.notifications import notification_system

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Вимкнути логи Flask/Werkzeug
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Flask app для Render
app = Flask(__name__)

# Конфігурація
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
PORT = int(os.environ.get('PORT', 10000))

# Глобальна змінна для бота
application = None
event_loop = None
bot_initialized = False
bot_initialization_started = False

def run_async_tasks():
    """Запуск асинхронних завдань в окремому потоці"""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()

# Запускаємо event loop в окремому потоці
async_thread = threading.Thread(target=run_async_tasks, daemon=True)
async_thread.start()

def setup_handlers(app_instance):
    """Налаштування обробників"""
    logger.info("🔄 Налаштування обробників...")
    
    # Команди
    app_instance.add_handler(CommandHandler("start", start))
    
    # Обробники кнопок
    app_instance.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
    app_instance.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
    app_instance.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
    app_instance.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
    app_instance.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), handle_like))
    app_instance.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
    app_instance.add_handler(MessageHandler(filters.Regex('^🔙 Меню$'), lambda update, context: update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(update.effective_user.id))))
    app_instance.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
    app_instance.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
    app_instance.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
    app_instance.add_handler(MessageHandler(filters.Regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
    app_instance.add_handler(MessageHandler(filters.Regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    
    # Адмін обробники
    app_instance.add_handler(MessageHandler(filters.Regex('^(👑 Адмін панель|📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування)$'), handle_admin_actions))
    app_instance.add_handler(MessageHandler(filters.Regex('^(📋 Список користувачів|🚫 Заблокувати користувача|✅ Розблокувати користувача|📋 Список заблокованих|🔙 Назад до адмін-панелі)$'), universal_handler))
    
    # Callback обробники
    app_instance.add_handler(CallbackQueryHandler(handle_like_back, pattern='^like_back_'))
    
    # Фото та універсальний обробник
    app_instance.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # Обробник помилок
    app_instance.add_error_handler(error_handler)
    logger.info("✅ Всі обробники налаштовано")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    try:
        user = update.effective_user
        
        logger.info(f"🆕 Користувач: {user.first_name} (ID: {user.id}) викликав /start")
        
        # Додаємо користувача в базу
        db.add_user(user.id, user.username, user.first_name)
        logger.info(f"✅ Користувач {user.id} доданий в базу")
        
        # Скидаємо стан
        user_states[user.id] = States.START
        
        # Вітання
        welcome_text = (
            f"👋 Вітаю, {user.first_name}!\n\n"
            f"💞 *Chatrix* — це бот для знайомств!\n\n"
            f"🎯 *Почнімо знайомство!*"
        )
        
        # Перевіряємо чи заповнений профіль
        user_data, is_complete = db.get_user_profile(user.id)
        
        if not is_complete:
            welcome_text += "\n\n📝 *Для початку заповни свою анкету*"
            keyboard = [['📝 Заповнити профіль']]
        else:
            keyboard = [
                ['💕 Пошук анкет', '🏙️ По місту'],
                ['👤 Мій профіль', '❤️ Хто мене лайкнув'],
                ['💌 Мої матчі', '🏆 Топ'],
                ["👨‍💼 Зв'язок з адміном"]
            ]
        
        if user.id == ADMIN_ID:
            keyboard.append(['👑 Адмін панель'])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Відправлено вітальне повідомлення для {user.first_name}")
        
    except Exception as e:
        logger.error(f"❌ Помилка в /start: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопки зв'язку з адміном"""
    try:
        user = update.effective_user
        user_states[user.id] = States.CONTACT_ADMIN
        
        contact_text = f"""👨‍💼 *Зв'язок з адміністратором*

📧 Для зв'язку з адміністратором напишіть повідомлення з описом вашої проблеми або питання.

🆔 Ваш ID: `{user.id}`
👤 Ваше ім'я: {user.first_name}

💬 *Напишіть ваше повідомлення:*"""

        await update.message.reply_text(
            contact_text,
            reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка в contact_admin: {e}")
        await update.message.reply_text("❌ Сталася помилка.")

async def handle_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлення для адміна з сповіщенням"""
    try:
        user = update.effective_user
        
        if user_states.get(user.id) != States.CONTACT_ADMIN:
            return
        
        message_text = update.message.text
        
        if message_text == "🔙 Скасувати":
            user_states[user.id] = States.START
            await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
            return
        
        # Відправляємо сповіщення адміну
        await notification_system.notify_contact_admin(context, user.id, message_text)
        
        await update.message.reply_text(
            "✅ Ваше повідомлення відправлено адміністратору!",
            reply_markup=get_main_menu(user.id)
        )
        
        user_states[user.id] = States.START
        
    except Exception as e:
        logger.error(f"❌ Помилка в handle_contact_message: {e}")
        await update.message.reply_text("❌ Сталася помилка.")

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Універсальний обробник повідомлень"""
    try:
        user = update.effective_user
        text = update.message.text if update.message.text else ""
        state = user_states.get(user.id, States.START)

        # Скасування
        if text == "🔙 Скасувати":
            user_states[user.id] = States.START
            await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
            return

        # Зв'язок з адміном
        if state == States.CONTACT_ADMIN:
            await handle_contact_message(update, context)
            return

        # Додавання фото
        if state == States.ADD_MAIN_PHOTO:
            await handle_main_photo(update, context)
            return

        # Стани профілю
        if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                     States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
            await handle_profile_message(update, context)
            return
        
        # Пошук по місту
        if context.user_data.get('waiting_for_city'):
            clean_city = text.replace('🏙️ ', '').strip()
            users = db.get_users_by_city(clean_city, user.id)
            
            if users:
                user_data = users[0]
                await show_user_profile(update, context, user_data, f"🏙️ Місто: {clean_city}")
                context.user_data['search_users'] = users
                context.user_data['current_index'] = 0
                context.user_data['search_type'] = 'city'
            else:
                await update.message.reply_text(
                    f"😔 Не знайдено анкет у місті {clean_city}",
                    reply_markup=get_main_menu(user.id)
                )
            
            context.user_data['waiting_for_city'] = False
            return
        
        # Обробка станів адміна
        if user.id == ADMIN_ID:
            admin_state = user_states.get(user.id)
            if admin_state == States.ADMIN_BAN_USER:
                await handle_ban_user(update, context)
                return
            elif admin_state == States.ADMIN_UNBAN_USER:
                await handle_unban_user(update, context)
                return
            elif admin_state == States.BROADCAST:
                await handle_broadcast_message(update, context)
                return
            elif admin_state == States.ADMIN_SEARCH_USER:
                await handle_user_search(update, context)
                return
        
        # Адмін-меню
        if user.id == ADMIN_ID:
            if text in ["👑 Адмін панель", "📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування"]:
                await handle_admin_actions(update, context)
                return
            
            if text in ["📋 Список користувачів", "🚫 Заблокувати користувача", "✅ Розблокувати користувача", "📋 Список заблокованих", "🔙 Назад до адмін-панелі"]:
                if text == "📋 Список користувачів":
                    await show_users_list(update, context)
                elif text == "🚫 Заблокувати користувача":
                    await start_ban_user(update, context)
                elif text == "✅ Розблокувати користувача":
                    await start_unban_user(update, context)
                elif text == "📋 Список заблокованих":
                    await show_banned_users(update, context)
                elif text == "🔙 Назад до адмін-панелі":
                    await show_admin_panel(update, context)
                return
        
        # Обробка команд меню
        if text == "📝 Заповнити профіль" or text == "✏️ Редагувати профіль":
            await start_profile_creation(update, context)
            return
        
        elif text == "👤 Мій профіль":
            await show_my_profile(update, context)
            return
        
        elif text == "💕 Пошук анкет":
            await search_profiles(update, context)
            return
        
        elif text == "🏙️ По місту":
            await search_by_city(update, context)
            return
        
        elif text == "❤️ Лайк":
            await handle_like(update, context)
            return
        
        elif text == "➡️ Далі":
            await show_next_profile(update, context)
            return
        
        elif text == "🔙 Меню":
            await update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(user.id))
            return
        
        elif text == "🏆 Топ":
            await show_top_users(update, context)
            return
        
        elif text == "💌 Мої матчі":
            await show_matches(update, context)
            return
        
        elif text == "❤️ Хто мене лайкнув":
            await show_likes(update, context)
            return
        
        elif text in ["👨 Топ чоловіків", "👩 Топ жінок", "🏆 Загальний топ"]:
            await handle_top_selection(update, context)
            return
        
        elif text == "👨‍💼 Зв'язок з адміном":
            await contact_admin(update, context)
            return
        
        # Якщо нічого не підійшло
        await update.message.reply_text(
            "❌ Команда не розпізнана. Оберіть пункт з меню:",
            reply_markup=get_main_menu(user.id)
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка в universal_handler: {e}")
        await update.message.reply_text("❌ Сталася помилка.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    try:
        logger.error(f"❌ Помилка в боті: {context.error}", exc_info=True)
        if update and update.effective_user:
            await update.message.reply_text("❌ Сталася помилка.")
    except Exception as e:
        logger.error(f"❌ Помилка в error_handler: {e}")

async def process_update(update):
    """Обробка оновлення"""
    try:
        await application.process_update(update)
        logger.info(f"✅ Оновлення успішно оброблено: {update.update_id}")
    except Exception as e:
        logger.error(f"❌ Помилка обробки оновлення: {e}")

async def initialize_bot_async():
    """Асинхронна ініціалізація бота"""
    global application, bot_initialized
    
    try:
        logger.info("🚀 Асинхронна ініціалізація бота...")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application створено")
        
        # Налаштовуємо обробники
        setup_handlers(application)
        logger.info("✅ Обробники налаштовано")
        
        # Ініціалізуємо бота
        await application.initialize()
        logger.info("✅ Бот ініціалізовано")
        
        # Встановлюємо webhook
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
        
        bot_initialized = True
        logger.info("🤖 Бот успішно ініціалізовано та готовий до роботи!")
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}", exc_info=True)

def init_bot():
    """Ініціалізація бота"""
    global event_loop, bot_initialization_started
    
    if bot_initialization_started:
        return
        
    bot_initialization_started = True
    
    try:
        # Чекаємо поки event loop буде готовий
        max_wait_time = 10  # секунд
        start_time = time.time()
        
        while event_loop is None and (time.time() - start_time) < max_wait_time:
            time.sleep(0.1)
            logger.info("⏳ Чекаємо на ініціалізацію event loop...")
        
        if event_loop is None:
            logger.error("❌ Event loop не ініціалізований протягом 10 секунд")
            return
        
        logger.info("🔄 Запускаємо ініціалізацію бота через event loop...")
        
        # Запускаємо асинхронну ініціалізацію через event loop
        future = asyncio.run_coroutine_threadsafe(initialize_bot_async(), event_loop)
        future.result(timeout=30)  # Чекаємо до 30 секунд
        logger.info("✅ Бот успішно ініціалізовано")
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}", exc_info=True)

# ========== FLASK ROUTES ==========

@app.route('/')
def home():
    # Ініціалізуємо бота при першому запиті
    if not bot_initialization_started:
        init_bot()
    return "🤖 Chatrix Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/healthz')
def healthz():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    try:
        logger.info("📨 Отримано webhook запит від Telegram")
        
        # Якщо бот ще не ініціалізований, спробуємо ініціалізувати
        if not bot_initialized or application is None:
            logger.warning("⚠️ Бот ще не ініціалізований, спробуємо ініціалізувати...")
            init_bot()
            
            # Чекаємо трохи на ініціалізацію
            time.sleep(2)
            
            if not bot_initialized or application is None:
                logger.error("❌ Бот все ще не ініціалізований")
                return "Bot not initialized", 500
            
        # Отримуємо оновлення від Telegram
        update_data = request.get_json()
        
        if update_data is None:
            logger.error("❌ Порожні дані оновлення")
            return "Empty update data", 400
            
        update = Update.de_json(update_data, application.bot)
        
        # Обробляємо оновлення через event loop
        asyncio.run_coroutine_threadsafe(process_update(update), event_loop)
        logger.info("✅ Оновлення успішно додано в чергу обробки")
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Критична помилка в webhook: {e}", exc_info=True)
        return "Error", 500

@app.route('/set_webhook')
def set_webhook_route():
    """Встановити webhook через HTTP запит"""
    logger.info("🔄 Запит на встановлення webhook")
    try:
        if not bot_initialized:
            init_bot()
            return "🔄 Бот ініціалізується... Спробуйте ще раз через кілька секунд."
        
        # Перевіряємо стан webhook
        future = asyncio.run_coroutine_threadsafe(application.bot.get_webhook_info(), event_loop)
        webhook_info = future.result(timeout=30)
        
        result = f"✅ Webhook встановлено: {WEBHOOK_URL}<br>Pending updates: {webhook_info.pending_update_count}"
        logger.info(f"✅ Результат перевірки webhook: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

# ========== ЗАПУСК СЕРВЕРА ==========

if __name__ == "__main__":
    # Ініціалізуємо бота
    logger.info("🚀 Запуск додатку...")
    init_bot()
    
    # Запускаємо Flask сервер
    logger.info(f"🚀 Запуск Flask сервера на порті {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)