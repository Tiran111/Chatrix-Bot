import logging
import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

# Імпорт модулів
try:
    from database_postgres import db
    logger.info("✅ Використовується PostgreSQL база даних")
except ImportError as e:
    logger.error(f"❌ Помилка імпорту бази даних: {e}")
    # Створюємо просту заглушку для тестування
    class DatabaseStub:
        def get_user(self, user_id): return None
        def add_user(self, user_id, username, first_name): return True
        def get_users_count(self): return 0
        def get_statistics(self): return (0, 0, 0, [])
        def get_random_user(self, exclude_id): return None
        def can_like_today(self, user_id): return (True, "Тест")
        def get_user_matches(self, user_id): return []
        def get_profile_photos(self, user_id): return []
        def get_user_profile(self, user_id): return (None, False)
        def get_users_by_city(self, city, exclude_id): return []
    db = DatabaseStub()

# Спрощена конфігурація
try:
    TOKEN = os.environ.get('BOT_TOKEN', 'test_token')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', '1385645772'))
    logger.info("✅ Конфігурація завантажена з змінних середовища")
except Exception as e:
    logger.error(f"❌ Помилка конфігурації: {e}")
    TOKEN = 'test_token'
    ADMIN_ID = 1385645772

# Спрощені утиліти
class States:
    START = 0
    PROFILE_AGE = 1
    PROFILE_GENDER = 2
    PROFILE_CITY = 3
    PROFILE_SEEKING_GENDER = 4
    PROFILE_GOAL = 5
    PROFILE_BIO = 6
    ADD_MAIN_PHOTO = 7
    CONTACT_ADMIN = 10
    ADMIN_BAN_USER = 100
    ADMIN_UNBAN_USER = 101
    BROADCAST = 102
    ADMIN_SEARCH_USER = 103

user_states = {}

def get_main_menu(user_id):
    """Спрощена версія головного меню"""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ['💕 Пошук анкет', '🏙️ По місту'],
        ['👤 Мій профіль', '📝 Редагувати'],
        ['❤️ Хто мене лайкнув', '💌 Мої матчі'],
        ['🏆 Топ', "👨‍💼 Зв'язок з адміном"]
    ]
    if user_id == ADMIN_ID:
        keyboard.append(['👑 Адмін панель'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Глобальні змінні
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', "https://chatrix-bot-4m1p.onrender.com/webhook")
PORT = int(os.environ.get('PORT', 10000))
application = None
bot_initialized = False

async def debug_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальна відладка бота"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        user_count = db.get_users_count()
        stats = db.get_statistics()
        male, female, total_active, goals_stats = stats
        
        message = f"""
🔧 *ДЕТАЛЬНА ВІДЛАДКА БОТА*

📊 *База даних:* PostgreSQL ✅
👤 *Ваш ID:* `{user.id}`
📛 *Ваше ім'я:* {user.first_name}
📈 *Користувачів всього:* {user_count}
👥 *Статистика:* {male} чол., {female} жін., {total_active} актив.

*Тестування функцій:*
"""
        
        # Тест пошуку
        try:
            random_user = db.get_random_user(user.id)
            if random_user:
                message += f"🔍 *Пошук:* ✅ Знайдено користувача\n"
            else:
                message += f"🔍 *Пошук:* ⚠️ Не знайдено користувачів\n"
        except Exception as e:
            message += f"🔍 *Пошук:* ❌ Помилка - {str(e)[:100]}\n"
            
        # Тест лайків
        try:
            can_like, like_msg = db.can_like_today(user.id)
            message += f"❤️ *Лайки:* {like_msg}\n"
        except Exception as e:
            message += f"❤️ *Лайки:* ❌ Помилка - {str(e)[:100]}\n"
            
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Критична помилка: {str(e)[:200]}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    try:
        user = update.effective_user
        
        logger.info(f"🆕 Користувач: {user.first_name} (ID: {user.id}) викликав /start")
        
        db.add_user(user.id, user.username, user.first_name)
        logger.info(f"✅ Користувач {user.id} доданий в базу")
        
        user_states[user.id] = States.START
        
        welcome_text = (
            f"👋 Вітаю, {user.first_name}!\n\n"
            f"💞 *Chatrix* — це бот для знайомств!\n\n"
            f"🎯 *Почнімо знайомство!*"
        )
        
        user_data, is_complete = db.get_user_profile(user.id)
        
        if not is_complete:
            welcome_text += "\n\n📝 *Для початку заповни свою анкету*"
            keyboard = [['📝 Заповнити профіль']]
        else:
            keyboard = [
                ['💕 Пошук анкет', '🏙️ По місту'],
                ['👤 Мій профіль', '📝 Редагувати'],
                ['❤️ Хто мене лайкнув', '💌 Мої матчі'],
                ['🏆 Топ', "👨‍💼 Зв'язок з адміном"]
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
        
        # Спрощене сповіщення адміна
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📩 Нове повідомлення від {user.first_name} (ID: {user.id}):\n\n{message_text}"
            )
        except Exception as e:
            logger.error(f"❌ Не вдалося сповістити адміна: {e}")
        
        await update.message.reply_text(
            "✅ Ваше повідомлення відправлено адміністратору!",
            reply_markup=get_main_menu(user.id)
        )
        
        user_states[user.id] = States.START
        
    except Exception as e:
        logger.error(f"❌ Помилка в handle_contact_message: {e}")
        await update.message.reply_text("❌ Сталася помилка.")

async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія створення профілю"""
    await update.message.reply_text("📝 Функція створення профілю тимчасово недоступна")

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія показу профілю"""
    await update.message.reply_text("👤 Функція перегляду профілю тимчасово недоступна")

async def search_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія пошуку профілів"""
    await update.message.reply_text("💕 Функція пошуку тимчасово недоступна")

async def search_by_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія пошуку за містом"""
    await update.message.reply_text("🏙️ Функція пошуку за містом тимчасово недоступна")

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія наступного профілю"""
    await update.message.reply_text("➡️ Функція наступного профілю тимчасово недоступна")

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія лайку"""
    await update.message.reply_text("❤️ Функція лайку тимчасово недоступна")

async def handle_like_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія взаємного лайку"""
    await update.message.reply_text("❤️ Функція взаємного лайку тимчасово недоступна")

async def show_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія топу користувачів"""
    await update.message.reply_text("🏆 Функція топу користувачів тимчасово недоступна")

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія матчів"""
    await update.message.reply_text("💌 Функція матчів тимчасово недоступна")

async def show_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія лайків"""
    await update.message.reply_text("❤️ Функція перегляду лайків тимчасово недоступна")

async def handle_top_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія вибору топу"""
    await update.message.reply_text("🏆 Функція вибору топу тимчасово недоступна")

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія адмін дій"""
    await update.message.reply_text("👑 Адмін функції тимчасово недоступні")

async def handle_main_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія обробки фото"""
    await update.message.reply_text("📷 Функція обробки фото тимчасово недоступна")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скасування поточної дії"""
    user = update.effective_user
    user_states[user.id] = States.START
    await update.message.reply_text(
        "✅ Всі дії скасовано. Повертаємось до головного меню.",
        reply_markup=get_main_menu(user.id)
    )

async def reset_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Примусове скидання стану"""
    user = update.effective_user
    user_states[user.id] = States.START
    await update.message.reply_text(
        "✅ Стан скинуто. Повертаємось до головного меню.",
        reply_markup=get_main_menu(user.id)
    )

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Універсальний обробник повідомлень"""
    try:
        user = update.effective_user
        text = update.message.text if update.message.text else ""
        
        state = user_states.get(user.id, States.START)

        if text == "🔙 Скасувати":
            user_states[user.id] = States.START
            await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
            return

        if state == States.CONTACT_ADMIN:
            await handle_contact_message(update, context)
            return

        # Обробка кнопок меню
        if text == "📝 Заповнити профіль" or text == "📝 Редагувати":
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
        
        elif text == "❤️ Хто мене лайкнув":
            await show_likes(update, context)
            return
        
        elif text == "💌 Мої матчі":
            await show_matches(update, context)
            return
        
        elif text == "🏆 Топ":
            await show_top_users(update, context)
            return
        
        elif text == "👨‍💼 Зв'язок з адміном":
            await contact_admin(update, context)
            return

        elif user.id == ADMIN_ID and text == "👑 Адмін панель":
            await handle_admin_actions(update, context)
            return
        
        await update.message.reply_text(
            "❌ Команда не розпізнана. Оберіть пункт з меню:",
            reply_markup=get_main_menu(user.id)
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка в universal_handler: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Сталася помилка: {str(e)[:100]}\n\n"
            f"Спробуйте ще раз або зверніться до адміністратора.",
            reply_markup=get_main_menu(user.id)
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    try:
        logger.error(f"❌ Помилка в боті: {context.error}", exc_info=True)
        if update and update.effective_user:
            await update.message.reply_text("❌ Сталася помилка.")
    except Exception as e:
        logger.error(f"❌ Помилка в error_handler: {e}")

def setup_handlers(application):
    """Налаштування обробників"""
    logger.info("🔄 Налаштування обробників...")
    
    # Основні команди
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("debug", debug_bot))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("reset_state", reset_state))
    
    # Основні обробники кнопок
    application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|📝 Редагувати)$'), start_profile_creation))
    application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
    application.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
    application.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
    application.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
    application.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
    application.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
    application.add_handler(MessageHandler(filters.Regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    application.add_handler(MessageHandler(filters.Regex('^👑 Адмін панель$'), handle_admin_actions))
    
    # Універсальний обробник
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    application.add_error_handler(error_handler)
    logger.info("✅ Обробники налаштовано")

# ==================== FLASK ROUTES ====================

@app.route('/')
def home():
    return "🤖 Chatrix Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    global application, bot_initialized
    
    try:
        # Ініціалізуємо бота при першому запиті, якщо ще не ініціалізовано
        if not bot_initialized:
            logger.info("🔄 Ініціалізація бота при першому запиті...")
            application = Application.builder().token(TOKEN).build()
            setup_handlers(application)
            
            # Ініціалізуємо бота
            application.initialize()
            
            # Встановлюємо вебхук
            application.bot.set_webhook(WEBHOOK_URL)
            
            bot_initialized = True
            logger.info("✅ Бот успішно ініціалізовано!")
            logger.info(f"🌐 Вебхук встановлено: {WEBHOOK_URL}")
            
        update_data = request.get_json()
        if update_data is None:
            return "Empty update data", 400
            
        # Обробляємо оновлення
        update = Update.de_json(update_data, application.bot)
        application.process_update(update)
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Webhook помилка: {e}")
        return "Error", 500

# ==================== СЕРВЕР ====================

print("=" * 60)
print("🚀 СЕРВЕР ГОТОВИЙ ДО РОБОТИ!")
print(f"🌐 Порт: {PORT}")
print("📱 Бот ініціалізується при першому запиті")
print("=" * 60)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    print("=" * 50)
    print(f"🌐 Запуск сервера на порті {port}...")
    print("🤖 Сервер готовий до роботи!")
    print("=" * 50)
    
    # Запускаємо Flask сервер
    app.run(host='0.0.0.0', port=port, debug=False)