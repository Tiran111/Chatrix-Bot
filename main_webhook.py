from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID
import logging
import os
import asyncio
from flask import Flask, request
import threading

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app для Render
app = Flask(__name__)

# Глобальна змінна для бота
application = None

@app.route('/')
def home():
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

@app.route('/' + TOKEN, methods=['POST'])
async def webhook():
    """Webhook endpoint для Telegram"""
    try:
        if application is None:
            return "Bot not initialized", 500
            
        update = Update.de_json(await request.get_json(), application.bot)
        await application.update_queue.put(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"❌ Помилка в webhook: {e}")
        return "Error", 500

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    try:
        user = update.effective_user
        
        logger.info(f"🆕 Користувач: {user.first_name} (ID: {user.id})")
        
        # Додаємо користувача в базу
        db.add_user(user.id, user.username, user.first_name)
        
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
    except Exception as e:
        logger.error(f"❌ Помилка в /start: {e}")
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

# ... (всі інші функції залишаються незмінними з попереднього коду)

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Універсальний обробник повідомлень"""
    try:
        user = update.effective_user
        text = update.message.text if update.message.text else ""
        state = user_states.get(user.id, States.START)
        
        logger.info(f"📨 Повідомлення від {user.first_name}: '{text}', стан: {state}")

        # Обробка скасування
        if text == "🔙 Скасувати" or text == "🔙 Завершити":
            user_states[user.id] = States.START
            context.user_data.pop('waiting_for_city', None)
            context.user_data.pop('contact_admin', None)
            await update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))
            return

        # Обробка зв'язку з адміном
        if state == States.CONTACT_ADMIN:
            from main import handle_contact_message
            await handle_contact_message(update, context)
            return

        # Інша логіка обробки...
        # ... (решта коду universal_handler)

    except Exception as e:
        logger.error(f"❌ Помилка в universal_handler: {e}")
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    try:
        logger.error(f"❌ Помилка: {context.error}", exc_info=True)
        if update and update.effective_user:
            await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")
    except Exception as e:
        logger.error(f"❌ Помилка в error_handler: {e}")

def setup_handlers(app):
    """Налаштування обробників"""
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug_search", debug_search))
    
    # Обробники кнопок
    app.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
    app.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
    app.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
    app.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
    app.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), handle_like))
    app.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
    app.add_handler(MessageHandler(filters.Regex('^🔙 Меню$'), lambda u, c: u.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(u.effective_user.id))))
    app.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
    app.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
    app.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
    app.add_handler(MessageHandler(filters.Regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
    app.add_handler(MessageHandler(filters.Regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    
    # Адмін обробники
    app.add_handler(MessageHandler(filters.Regex('^(👑 Адмін панель|📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування|📈 Детальна статистика)$'), handle_admin_actions))
    app.add_handler(MessageHandler(filters.Regex('^(📋 Список користувачів|🚫 Заблокувати користувача|✅ Розблокувати користувача|📋 Список заблокованих|🔙 Назад до адмін-панелі)$'), universal_handler))
    
    # Фото та універсальний обробник
    app.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # Обробник помилок
    app.add_error_handler(error_handler)

async def setup_webhook():
    """Налаштування webhook"""
    global application
    
    # Створюємо application
    application = Application.builder().token(TOKEN).build()
    
    # Налаштовуємо обробники
    setup_handlers(application)
    
    # Отримуємо URL для Render
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not render_url:
        # Якщо не на Render, використовуємо polling
        logger.info("🚀 Запуск бота в режимі polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        return True
    else:
        # Налаштовуємо webhook для Render
        webhook_url = f"{render_url}/{TOKEN}"
        logger.info(f"🌐 Налаштування webhook: {webhook_url}")
        
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(webhook_url)
        
        logger.info("✅ Webhook налаштовано!")
        return False

def run_bot():
    """Запуск бота"""
    asyncio.run(setup_webhook())

if __name__ == "__main__":
    # Імпорт функцій
    from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
    from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile
    from main import handle_contact_message, handle_admin_actions, debug_search, start_ban_user, start_unban_user, handle_ban_user, handle_unban_user, show_users_management, show_users_list, start_broadcast, update_database, show_ban_management, show_banned_users, show_detailed_stats, handle_broadcast_message
    
    # Запускаємо Flask
    port = int(os.environ.get("PORT", 10000))
    
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    logger.info("🚀 Запуск Flask сервера...")
    app.run(host='0.0.0.0', port=port, debug=False)