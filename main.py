from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID
import logging
import os
from flask import Flask, request

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Вимкнути логи Flask/Werkzeug
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('gunicorn').setLevel(logging.WARNING)

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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint для Telegram"""
    try:
        if application is None:
            logger.error("❌ Application не ініціалізовано")
            return "Bot not initialized", 500
            
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        application.update_queue.put_nowait(update)
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

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопки зв'язку з адміном"""
    try:
        user = update.effective_user
        
        contact_text = f"""👨‍💼 *Зв'язок з адміністратором*

📧 Для зв'язку з адміністратором напишіть повідомлення з описом вашої проблеми або питання.

🆔 Ваш ID: `{user.id}`
👤 Ваше ім'я: {user.first_name}

💬 *Напишіть ваше повідомлення:*"""

        # Встановлюємо стан очікування повідомлення для адміна
        user_states[user.id] = States.CONTACT_ADMIN
        
        await update.message.reply_text(
            contact_text,
            reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Помилка в contact_admin: {e}")
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def handle_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлення для адміна"""
    try:
        user = update.effective_user
        
        # Перевіряємо стан
        if user_states.get(user.id) != States.CONTACT_ADMIN:
            logger.info(f"❌ Неправильний стан для обробки повідомлення адміну: {user_states.get(user.id)}")
            return
        
        message_text = update.message.text
        
        if message_text == "🔙 Скасувати":
            user_states[user.id] = States.START
            await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
            return
        
        # Відправляємо повідомлення адміну
        try:
            admin_message = f"""📩 *Нове повідомлення від користувача*

👤 *Користувач:* {user.first_name}
🆔 *ID:* `{user.id}`
📝 *Повідомлення:*
{message_text}"""

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            # Підтверджуємо користувачу
            await update.message.reply_text(
                "✅ Ваше повідомлення відправлено адміністратору! Він зв'яжеться з вами найближчим часом.",
                reply_markup=get_main_menu(user.id)
            )
            
        except Exception as e:
            logger.error(f"❌ Помилка відправки повідомлення адміну: {e}")
            await update.message.reply_text(
                "❌ Помилка відправки повідомлення. Спробуйте пізніше.",
                reply_markup=get_main_menu(user.id)
            )
        
        # Скидаємо стан після обробки
        user_states[user.id] = States.START
        logger.info(f"✅ Стан скинуто для користувача {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Помилка в handle_contact_message: {e}")
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

# ... (всі інші функції залишаються незмінними з попереднього коду)

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Універсальний обробник повідомлень"""
    try:
        user = update.effective_user
        text = update.message.text if update.message.text else ""
        state = user_states.get(user.id, States.START)
        
        logger.info(f"📨 Повідомлення від {user.first_name}: '{text}', стан: {state}")

        # 1. Перевіряємо скасування
        if text == "🔙 Скасувати" or text == "🔙 Завершити":
            user_states[user.id] = States.START
            context.user_data.pop('waiting_for_city', None)
            context.user_data.pop('contact_admin', None)
            await update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))
            return

        # 2. Обробка зв'язку з адміном
        if state == States.CONTACT_ADMIN:
            logger.info(f"🔧 Обробка повідомлення для адміна від {user.id}")
            await handle_contact_message(update, context)
            return

        # 3. Перевіряємо додавання фото
        if state == States.ADD_MAIN_PHOTO:
            from handlers.profile import handle_main_photo
            await handle_main_photo(update, context)
            return

        # 4. Перевіряємо стани профілю
        if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                     States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
            from handlers.profile import handle_profile_message
            await handle_profile_message(update, context)
            return
        
        # 5. Перевіряємо введення міста для пошуку
        if context.user_data.get('waiting_for_city'):
            from handlers.search import show_user_profile
            
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
        
        # 6. Обробка станів адміна
        if user.id == ADMIN_ID:
            state = user_states.get(user.id)
            if state == States.ADMIN_BAN_USER:
                await handle_ban_user(update, context)
                return
            elif state == States.ADMIN_UNBAN_USER:
                await handle_unban_user(update, context)
                return
            elif state == States.BROADCAST:
                await handle_broadcast_message(update, context)
                return
        
        # 7. Адмін-меню
        if user.id == ADMIN_ID:
            if text in ["👑 Адмін панель", "📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування", "📈 Детальна статистика"]:
                await handle_admin_actions(update, context)
                return
            
            # Обробка адмін-кнопок керування користувачами
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
        
        # 8. Обробка команд меню
        if text == "📝 Заповнити профіль" or text == "✏️ Редагувати профіль":
            from handlers.profile import start_profile_creation
            await start_profile_creation(update, context)
            return
        
        elif text == "👤 Мій профіль":
            from handlers.profile import show_my_profile
            await show_my_profile(update, context)
            return
        
        elif text == "💕 Пошук анкет":
            from handlers.search import search_profiles
            await search_profiles(update, context)
            return
        
        elif text == "🏙️ По місту":
            from handlers.search import search_by_city
            await search_by_city(update, context)
            return
        
        elif text == "❤️ Лайк":
            from handlers.search import handle_like
            await handle_like(update, context)
            return
        
        elif text == "➡️ Далі":
            from handlers.search import show_next_profile
            await show_next_profile(update, context)
            return
        
        elif text == "🔙 Меню":
            await update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(user.id))
            return
        
        elif text == "🏆 Топ":
            from handlers.search import show_top_users
            await show_top_users(update, context)
            return
        
        elif text == "💌 Мої матчі":
            from handlers.search import show_matches
            await show_matches(update, context)
            return
        
        elif text == "❤️ Хто мене лайкнув":
            from handlers.search import show_likes
            await show_likes(update, context)
            return
        
        elif text in ["👨 Топ чоловіків", "👩 Топ жінок", "🏆 Загальний топ"]:
            from handlers.search import handle_top_selection
            await handle_top_selection(update, context)
            return
        
        # 9. Обробка кнопки зв'язку з адміном
        elif text == "👨‍💼 Зв'язок з адміном":
            await contact_admin(update, context)
            return
        
        # 10. Команда дебагу
        elif text == "/debug_search":
            await debug_search(update, context)
            return
        
        # 11. Якщо нічого не підійшло
        await update.message.reply_text(
            "❌ Команда не розпізнана. Оберіть пункт з меню:",
            reply_markup=get_main_menu(user.id)
        )
        
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
    
    # Обробники для станів блокування
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^🚫 Заблокувати$'), start_ban_user))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^✅ Розблокувати$'), start_unban_user))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^🚫 Заблокувати користувача$'), start_ban_user))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^✅ Розблокувати користувача$'), start_unban_user))
    
    # Фото та універсальний обробник
    app.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # Обробник помилок
    app.add_error_handler(error_handler)

def init_bot():
    """Ініціалізація бота"""
    global application
    
    # Створюємо application
    application = Application.builder().token(TOKEN).build()
    
    # Налаштовуємо обробники
    setup_handlers(application)
    
    # Отримуємо URL для Render
    render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://chatrix-bot.onrender.com')
    webhook_url = f"{render_url}/webhook"
    
    logger.info(f"🌐 Налаштування webhook: {webhook_url}")
    
    # Ініціалізуємо бота
    application.initialize()
    
    # Встановлюємо webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path=TOKEN,
        webhook_url=webhook_url,
        secret_token='WEBHOOK_SECRET'
    )
    
    logger.info("✅ Webhook налаштовано!")
    logger.info("🤖 Бот готовий до роботи!")

# Імпорт функцій
from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile
from main import handle_contact_message, handle_admin_actions, debug_search, start_ban_user, start_unban_user, handle_ban_user, handle_unban_user, show_users_management, show_users_list, start_broadcast, update_database, show_ban_management, show_banned_users, show_detailed_stats, handle_broadcast_message

if __name__ == "__main__":
    # Ініціалізуємо бота
    init_bot()