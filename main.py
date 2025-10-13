import logging
import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import Conflict, TelegramError

# Імпорт ваших модулів
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID

# Імпорт обробників
from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile
from handlers.admin import show_admin_panel, handle_admin_actions, show_users_management, show_users_list, start_broadcast, update_database, show_ban_management, show_banned_users, show_detailed_stats, handle_broadcast_message, start_ban_user, start_unban_user, handle_ban_user, handle_unban_user

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
bot_initialized = False

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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    try:
        logger.info("📨 Отримано webhook запит від Telegram")
        
        if application is None:
            logger.error("❌ Бот не ініціалізований")
            return "Bot not initialized", 500
            
        # Отримуємо оновлення від Telegram
        update_data = request.get_json()
        
        if update_data is None:
            logger.error("❌ Порожні дані оновлення")
            return "Empty update data", 400
            
        update = Update.de_json(update_data, application.bot)
        
        # Обробляємо оновлення
        asyncio.create_task(process_update(update))
        logger.info("✅ Оновлення успішно додано в чергу обробки")
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Критична помилка в webhook: {e}", exc_info=True)
        return "Error", 500

async def process_update(update):
    """Обробка оновлення"""
    try:
        await application.process_update(update)
        logger.info(f"✅ Оновлення успішно оброблено: {update.update_id}")
    except Exception as e:
        logger.error(f"❌ Помилка обробки оновлення: {e}")

@app.route('/set_webhook')
def set_webhook_route():
    """Встановити webhook через HTTP запит"""
    logger.info("🔄 Запит на встановлення webhook")
    try:
        result = asyncio.run(set_webhook())
        logger.info(f"✅ Результат встановлення webhook: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Помилка встановлення webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

async def set_webhook():
    """Асинхронна функція для встановлення webhook"""
    global application, bot_initialized
    
    try:
        if not bot_initialized:
            await initialize_bot()
        
        logger.info(f"🌐 Встановлення webhook на URL: {WEBHOOK_URL}")
        await application.bot.set_webhook(WEBHOOK_URL)
        
        # Перевіряємо webhook
        webhook_info = await application.bot.get_webhook_info()
        logger.info(f"📊 Інформація про webhook: {webhook_info.url}, pending: {webhook_info.pending_update_count}")
        
        logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
        logger.info("🤖 Бот готовий до роботи!")
        
        return f"✅ Webhook встановлено: {WEBHOOK_URL}<br>Pending updates: {webhook_info.pending_update_count}"
        
    except Exception as e:
        logger.error(f"❌ Помилка встановлення webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

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
        logger.info(f"✅ Стан скинуто для {user.id}")
        
        # Вітання
        welcome_text = (
            f"👋 Вітаю, {user.first_name}!\n\n"
            f"💞 *Chatrix* — це бот для знайомств!\n\n"
            f"🎯 *Почнімо знайомство!*"
        )
        
        # Перевіряємо чи заповнений профіль
        user_data, is_complete = db.get_user_profile(user.id)
        logger.info(f"📊 Профіль користувача {user.id}: complete={is_complete}")
        
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

# ... (інші обробники залишаються незмінними)

async def initialize_bot():
    """Ініціалізація бота"""
    global application, bot_initialized
    
    try:
        logger.info("🚀 Початок ініціалізації бота...")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application створено")
        
        # Налаштовуємо обробники
        setup_handlers(application)
        
        # Ініціалізуємо бота
        await application.initialize()
        await application.start()
        logger.info("✅ Бот ініціалізовано та запущено")
        
        bot_initialized = True
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}", exc_info=True)
        raise

def setup_handlers(application):
    """Налаштування обробників"""
    logger.info("🔄 Налаштування обробників...")
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("debug_search", debug_search))
    
    # Обробники кнопок
    application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
    application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
    application.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
    application.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
    application.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), handle_like))
    application.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
    application.add_handler(MessageHandler(filters.Regex('^🔙 Меню$'), lambda update, context: update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(update.effective_user.id))))
    application.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
    application.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
    application.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
    application.add_handler(MessageHandler(filters.Regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
    application.add_handler(MessageHandler(filters.Regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    
    # Адмін обробники
    application.add_handler(MessageHandler(filters.Regex('^(👑 Адмін панель|📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування|📈 Детальна статистика)$'), handle_admin_actions))
    application.add_handler(MessageHandler(filters.Regex('^(📋 Список користувачів|🚫 Заблокувати користувача|✅ Розблокувати користувача|📋 Список заблокованих|🔙 Назад до адмін-панелі)$'), universal_handler))
    
    # Фото та універсальний обробник
    application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # Обробник помилок
    application.add_error_handler(error_handler)
    logger.info("✅ Всі обробники налаштовано")

async def main():
    """Головна асинхронна функція"""
    await initialize_bot()

if __name__ == "__main__":
    # Запускаємо ініціалізацію бота
    asyncio.run(main())
    
    # Запускаємо Flask сервер
    logger.info(f"🚀 Запуск Flask сервера на порті {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)