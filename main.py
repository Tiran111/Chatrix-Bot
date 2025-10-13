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
        logger.info(f"📊 Заголовки: {dict(request.headers)}")
        
        if application is None:
            logger.error("❌ Бот не ініціалізований")
            return "Bot not initialized", 500
            
        # Отримуємо оновлення від Telegram
        update_data = request.get_json()
        logger.info(f"📦 Дані оновлення отримано, тип: {type(update_data)}")
        
        if update_data is None:
            logger.error("❌ Порожні дані оновлення")
            return "Empty update data", 400
            
        logger.info(f"🔍 Ключі в оновленні: {list(update_data.keys()) if update_data else 'None'}")
        
        update = Update.de_json(update_data, application.bot)
        logger.info(f"✅ Оновлення створено, тип: {type(update)}")
        
        # Логуємо деталі оновлення
        if update.message:
            logger.info(f"💬 Повідомлення: {update.message.text if update.message.text else 'No text'}")
            logger.info(f"👤 Користувач: {update.message.from_user.first_name if update.message.from_user else 'No user'}")
        elif update.callback_query:
            logger.info(f"🔄 Callback query: {update.callback_query.data}")
        
        # Додаємо оновлення в чергу
        application.update_queue.put_nowait(update)
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
        result = asyncio.run(set_webhook())
        logger.info(f"✅ Результат встановлення webhook: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Помилка встановлення webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

async def set_webhook():
    """Асинхронна функція для встановлення webhook"""
    global application
    try:
        logger.info("🚀 Початок ініціалізації бота...")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application створено")
        
        # Налаштовуємо обробники
        setup_handlers(application)
        logger.info("✅ Обробники налаштовано")
        
        # Встановлюємо webhook (з await!)
        logger.info(f"🌐 Встановлення webhook на URL: {WEBHOOK_URL}")
        await application.bot.set_webhook(WEBHOOK_URL)
        
        # Перевіряємо webhook
        webhook_info = await application.bot.get_webhook_info()
        logger.info(f"📊 Інформація про webhook: {webhook_info.url}, pending: {webhook_info.pending_update_count}")
        
        logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
        logger.info("🤖 Бот готовий до роботи!")
        
        return f"✅ Webhook встановлено: {WEBHOOK_URL}\nPending updates: {webhook_info.pending_update_count}"
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

@app.route('/delete_webhook')
def delete_webhook_route():
    """Видалити webhook через HTTP запит"""
    logger.info("🔄 Запит на видалення webhook")
    try:
        result = asyncio.run(delete_webhook())
        logger.info(f"✅ Результат видалення webhook: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Помилка видалення webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

async def delete_webhook():
    """Асинхронна функція для видалення webhook"""
    try:
        if application and application.bot:
            await application.bot.delete_webhook()
            logger.info("✅ Webhook видалено")
            return "✅ Webhook видалено"
        logger.warning("❌ Бот не ініціалізований для видалення webhook")
        return "❌ Бот не ініціалізований"
    except Exception as e:
        logger.error(f"❌ Помилка видалення webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

@app.route('/webhook_info')
def webhook_info_route():
    """Отримати інформацію про webhook"""
    try:
        result = asyncio.run(get_webhook_info())
        return result
    except Exception as e:
        return f"❌ Помилка: {e}"

async def get_webhook_info():
    """Отримати інформацію про webhook"""
    try:
        if application and application.bot:
            webhook_info = await application.bot.get_webhook_info()
            return f"""
            📊 Webhook Info:
            URL: {webhook_info.url}
            Has custom certificate: {webhook_info.has_custom_certificate}
            Pending update count: {webhook_info.pending_update_count}
            Last error date: {webhook_info.last_error_date}
            Last error message: {webhook_info.last_error_message}
            Max connections: {webhook_info.max_connections}
            Allowed updates: {webhook_info.allowed_updates}
            """
        return "❌ Бот не ініціалізований"
    except Exception as e:
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

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопки зв'язку з адміном"""
    try:
        user = update.effective_user
        logger.info(f"👨‍💼 Користувач {user.first_name} запитує зв'язок з адміном")
        
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
        logger.info(f"✅ Запит на зв'язок з адміном оброблено для {user.first_name}")
        
    except Exception as e:
        logger.error(f"❌ Помилка в contact_admin: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def handle_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлення для адміна"""
    try:
        user = update.effective_user
        logger.info(f"📩 Обробка повідомлення для адміна від {user.first_name}")
        
        # Перевіряємо стан
        if user_states.get(user.id) != States.CONTACT_ADMIN:
            logger.info(f"❌ Неправильний стан для обробки повідомлення адміну: {user_states.get(user.id)}")
            return
        
        message_text = update.message.text
        
        if message_text == "🔙 Скасувати":
            user_states[user.id] = States.START
            await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
            logger.info(f"✅ Скасовано зв'язок з адміном для {user.first_name}")
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
            logger.info(f"✅ Повідомлення від {user.first_name} відправлено адміну")
            
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
        logger.error(f"❌ Помилка в handle_contact_message: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def debug_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для дебагу пошуку"""
    try:
        user = update.effective_user
        logger.info(f"🔧 [DEBUG COMMAND] Для користувача {user.id}")
        
        # Отримуємо дані поточного користувача
        current_user = db.get_user(user.id)
        
        if not current_user:
            await update.message.reply_text("❌ Вашого профілю не знайдено")
            return
        
        # Дебаг пошуку
        seeking_gender = current_user.get('seeking_gender', 'all')
        current_gender = current_user.get('gender')
        
        # Спроба знайти користувачів
        random_user = db.get_random_user(user.id)
        
        debug_info = f"""🔧 *ДЕБАГ ПОШУКУ*

👤 *Ваш профіль:*
• ID: `{user.id}`
• Стать: {current_gender}
• Шукаєте: {seeking_gender}

🔍 *Результат пошуку:*
• Знайдено анкет: {'1' if random_user else '0'}
• Статус: {'✅ УСПІШНО' if random_user else '❌ НЕ ЗНАЙДЕНО'}

📊 *База даних:*
• Всього користувачів: {db.get_users_count()}
• Активних анкет: {db.get_statistics()[2]}"""

        if random_user:
            debug_info += f"\n\n👤 *Знайдений користувач:*\n• ID: `{random_user[1]}`\n• Стать: {random_user[5]}"
        
        await update.message.reply_text(debug_info, parse_mode='Markdown')
        logger.info(f"✅ Дебаг інформація відправлена для {user.first_name}")
        
    except Exception as e:
        logger.error(f"❌ Помилка в debug_search: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def safe_await_handler(handler_func, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Безпечний виклик обробника з перевіркою на корутину"""
    try:
        logger.info(f"🔄 Виклик обробника: {handler_func.__name__}")
        result = handler_func(update, context)
        if hasattr(result, '__await__'):
            await result
            logger.info(f"✅ Обробник {handler_func.__name__} завершено")
        else:
            logger.info(f"ℹ️ Обробник {handler_func.__name__} не асинхронний")
    except Exception as e:
        logger.error(f"❌ Помилка в {handler_func.__name__}: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

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
            logger.info(f"✅ Дію скасовано для {user.first_name}")
            return

        # 2. Обробка зв'язку з адміном
        if state == States.CONTACT_ADMIN:
            logger.info(f"🔧 Обробка повідомлення для адміна від {user.id}")
            await safe_await_handler(handle_contact_message, update, context)
            return

        # 3. Перевіряємо додавання фото
        if state == States.ADD_MAIN_PHOTO:
            await safe_await_handler(handle_main_photo, update, context)
            return

        # 4. Перевіряємо стани профілю
        if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                     States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
            await safe_await_handler(handle_profile_message, update, context)
            return
        
        # 5. Перевіряємо введення міста для пошуку
        if context.user_data.get('waiting_for_city'):
            clean_city = text.replace('🏙️ ', '').strip()
            users = db.get_users_by_city(clean_city, user.id)
            
            if users:
                user_data = users[0]
                try:
                    result = show_user_profile(update, context, user_data, f"🏙️ Місто: {clean_city}")
                    if hasattr(result, '__await__'):
                        await result
                    context.user_data['search_users'] = users
                    context.user_data['current_index'] = 0
                    context.user_data['search_type'] = 'city'
                except Exception as e:
                    logger.error(f"❌ Помилка в show_user_profile: {e}")
            else:
                await update.message.reply_text(
                    f"😔 Не знайдено анкет у місті {clean_city}",
                    reply_markup=get_main_menu(user.id)
                )
            
            context.user_data['waiting_for_city'] = False
            return
        
        # 6. Обробка станів адміна
        if user.id == ADMIN_ID:
            admin_state = user_states.get(user.id)
            if admin_state == States.ADMIN_BAN_USER:
                await safe_await_handler(handle_ban_user, update, context)
                return
            elif admin_state == States.ADMIN_UNBAN_USER:
                await safe_await_handler(handle_unban_user, update, context)
                return
            elif admin_state == States.BROADCAST:
                await safe_await_handler(handle_broadcast_message, update, context)
                return
        
        # 7. Адмін-меню
        if user.id == ADMIN_ID:
            if text in ["👑 Адмін панель", "📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування", "📈 Детальна статистика"]:
                await safe_await_handler(handle_admin_actions, update, context)
                return
            
            # Обробка адмін-кнопок керування користувачами
            if text in ["📋 Список користувачів", "🚫 Заблокувати користувача", "✅ Розблокувати користувача", "📋 Список заблокованих", "🔙 Назад до адмін-панелі"]:
                if text == "📋 Список користувачів":
                    await safe_await_handler(show_users_list, update, context)
                elif text == "🚫 Заблокувати користувача":
                    await safe_await_handler(start_ban_user, update, context)
                elif text == "✅ Розблокувати користувача":
                    await safe_await_handler(start_unban_user, update, context)
                elif text == "📋 Список заблокованих":
                    await safe_await_handler(show_banned_users, update, context)
                elif text == "🔙 Назад до адмін-панелі":
                    await safe_await_handler(show_admin_panel, update, context)
                return
        
        # 8. Обробка команд меню
        if text == "📝 Заповнити профіль" or text == "✏️ Редагувати профіль":
            await safe_await_handler(start_profile_creation, update, context)
            return
        
        elif text == "👤 Мій профіль":
            await safe_await_handler(show_my_profile, update, context)
            return
        
        elif text == "💕 Пошук анкет":
            await safe_await_handler(search_profiles, update, context)
            return
        
        elif text == "🏙️ По місту":
            await safe_await_handler(search_by_city, update, context)
            return
        
        elif text == "❤️ Лайк":
            await safe_await_handler(handle_like, update, context)
            return
        
        elif text == "➡️ Далі":
            await safe_await_handler(show_next_profile, update, context)
            return
        
        elif text == "🔙 Меню":
            await update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(user.id))
            return
        
        elif text == "🏆 Топ":
            await safe_await_handler(show_top_users, update, context)
            return
        
        elif text == "💌 Мої матчі":
            await safe_await_handler(show_matches, update, context)
            return
        
        elif text == "❤️ Хто мене лайкнув":
            await safe_await_handler(show_likes, update, context)
            return
        
        elif text in ["👨 Топ чоловіків", "👩 Топ жінок", "🏆 Загальний топ"]:
            await safe_await_handler(handle_top_selection, update, context)
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
        logger.info(f"❌ Нерозпізнана команда від {user.first_name}: {text}")
        
    except Exception as e:
        logger.error(f"❌ Помилка в universal_handler: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    try:
        logger.error(f"❌ Помилка в боті: {context.error}", exc_info=True)
        if update and update.effective_user:
            await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")
    except Exception as e:
        logger.error(f"❌ Помилка в error_handler: {e}")

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
    
    # Обробники для станів блокування
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^🚫 Заблокувати$'), start_ban_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^✅ Розблокувати$'), start_unban_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^🚫 Заблокувати користувача$'), start_ban_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^✅ Розблокувати користувача$'), start_unban_user))
    
    # Фото та універсальний обробник
    application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # Обробник помилок
    application.add_error_handler(error_handler)
    logger.info("✅ Всі обробники налаштовано")

async def initialize_bot():
    """Ініціалізація бота при старті"""
    global application
    try:
        logger.info("🚀 Початок ініціалізації бота...")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application створено")
        
        # Налаштовуємо обробники
        setup_handlers(application)
        
        # Встановлюємо webhook
        logger.info(f"🌐 Встановлення webhook на URL: {WEBHOOK_URL}")
        await application.bot.set_webhook(WEBHOOK_URL)
        
        # Перевіряємо webhook
        webhook_info = await application.bot.get_webhook_info()
        logger.info(f"📊 Інформація про webhook: {webhook_info.url}, pending: {webhook_info.pending_update_count}")
        
        logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
        logger.info("🤖 Бот готовий до роботи!")
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}", exc_info=True)

def run_async_init():
    """Запуск асинхронної ініціалізації"""
    asyncio.run(initialize_bot())

if __name__ == "__main__":
    # Ініціалізуємо бота при старті
    run_async_init()
    
    # Запускаємо Flask сервер
    logger.info(f"🚀 Запуск Flask сервера на порті {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)