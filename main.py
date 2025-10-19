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

# ДЕТАЛЬНЕ ЛОГУВАННЯ БАЗИ ДАНИХ
print("🔧 Перевірка бази даних...")
try:
    from database_postgres import db
    print("✅ Використовується PostgreSQL база даних")
    print(f"🔗 DATABASE_URL: {os.environ.get('DATABASE_URL', 'Не встановлено')}")
    
    # Тестуємо підключення
    try:
        test_user = db.get_user(1)  # Тестовий запит
        print("✅ Підключення до PostgreSQL успішне")
    except Exception as e:
        print(f"❌ Помилка підключення до PostgreSQL: {e}")
        
except ImportError as e:
    print(f"⚠️ PostgreSQL не доступний: {e}")
    from database_postgres import db  # Використовуємо PostgreSQL як основну
    print("ℹ️ Використовується PostgreSQL база даних")

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

# Додаємо необхідні імпорти
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import ADMIN_ID

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
                if isinstance(random_user, dict):
                    user_name = random_user.get('first_name', 'Користувач')
                else:
                    user_name = random_user[3] if len(random_user) > 3 else 'Користувач'
                message += f"🔍 *Пошук:* ✅ Знайдено {user_name}\n"
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
            
        # Тест матчів
        try:
            matches = db.get_user_matches(user.id)
            message += f"💌 *Матчі:* {len(matches)} знайдено\n"
        except Exception as e:
            message += f"💌 *Матчі:* ❌ Помилка - {str(e)[:100]}\n"
            
        # Тест фото
        try:
            photos = db.get_profile_photos(user.id)
            message += f"📷 *Фото:* {len(photos)} додано\n"
        except Exception as e:
            message += f"📷 *Фото:* ❌ Помилка - {str(e)[:100]}\n"
            
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
        
        from handlers.notifications import notification_system
        await notification_system.notify_contact_admin(context, user.id, message_text)
        
        await update.message.reply_text(
            "✅ Ваше повідомлення відправлено адміністратору!",
            reply_markup=get_main_menu(user.id)
        )
        
        user_states[user.id] = States.START
        
    except Exception as e:
        logger.error(f"❌ Помилка в handle_contact_message: {e}")
        await update.message.reply_text("❌ Сталася помилка.")

# Додаємо прості версії функцій, які відсутні
async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія створення профілю"""
    try:
        from handlers.profile import start_profile_creation as real_start_profile
        await real_start_profile(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція створення профілю тимчасово недоступна")

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія показу профілю"""
    try:
        from handlers.profile import show_my_profile as real_show_profile
        await real_show_profile(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція перегляду профілю тимчасово недоступна")

async def search_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія пошуку профілів"""
    try:
        from handlers.search import search_profiles as real_search
        await real_search(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція пошуку тимчасово недоступна")

async def search_by_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія пошуку за містом"""
    try:
        from handlers.search import search_by_city as real_search_city
        await real_search_city(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція пошуку за містом тимчасово недоступна")

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія наступного профілю"""
    try:
        from handlers.search import show_next_profile as real_next_profile
        await real_next_profile(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція наступного профілю тимчасово недоступна")

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія лайку"""
    try:
        from handlers.search import handle_like as real_handle_like
        await real_handle_like(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція лайку тимчасово недоступна")

async def handle_like_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія взаємного лайку"""
    try:
        from handlers.search import handle_like_back as real_handle_like_back
        await real_handle_like_back(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція взаємного лайку тимчасово недоступна")

async def show_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія топу користувачів"""
    try:
        from handlers.search import show_top_users as real_show_top
        await real_show_top(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція топу користувачів тимчасово недоступна")

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія матчів"""
    try:
        from handlers.search import show_matches as real_show_matches
        await real_show_matches(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція матчів тимчасово недоступна")

async def show_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія лайків"""
    try:
        from handlers.search import show_likes as real_show_likes
        await real_show_likes(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція перегляду лайків тимчасово недоступна")

async def handle_top_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія вибору топу"""
    try:
        from handlers.search import handle_top_selection as real_handle_top
        await real_handle_top(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція вибору топу тимчасово недоступна")

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія адмін дій"""
    try:
        from handlers.admin import handle_admin_actions as real_admin_actions
        await real_admin_actions(update, context)
    except ImportError:
        await update.message.reply_text("❌ Адмін функції тимчасово недоступні")

async def handle_main_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проста версія обробки фото"""
    try:
        from handlers.profile import handle_main_photo as real_handle_photo
        await real_handle_photo(update, context)
    except ImportError:
        await update.message.reply_text("❌ Функція обробки фото тимчасово недоступна")

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

        if state == States.ADD_MAIN_PHOTO:
            await handle_main_photo(update, context)
            return

        if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                     States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
            try:
                from handlers.profile import handle_profile_message
                await handle_profile_message(update, context)
            except ImportError:
                await update.message.reply_text("❌ Функція редагування профілю тимчасово недоступна")
            return
        
        if context.user_data.get('waiting_for_city'):
            clean_city = text.replace('🏙️ ', '').strip()
            users = db.get_users_by_city(clean_city, user.id)
            
            if users:
                try:
                    from handlers.search import show_user_profile
                    user_data = users[0]
                    await show_user_profile(update, context, user_data, f"🏙️ Місто: {clean_city}")
                    context.user_data['search_users'] = users
                    context.user_data['current_index'] = 0
                    context.user_data['search_type'] = 'city'
                except ImportError:
                    await update.message.reply_text("❌ Функція пошуку тимчасово недоступна")
            else:
                await update.message.reply_text(
                    f"😔 Не знайдено анкет у місті {clean_city}",
                    reply_markup=get_main_menu(user.id)
                )
            
            context.user_data['waiting_for_city'] = False
            return
        
        if user.id == ADMIN_ID:
            admin_state = user_states.get(user.id)
            if admin_state == States.ADMIN_BAN_USER:
                try:
                    from handlers.admin import handle_ban_user
                    await handle_ban_user(update, context)
                except ImportError:
                    await update.message.reply_text("❌ Адмін функції тимчасово недоступні")
                return
            elif admin_state == States.ADMIN_UNBAN_USER:
                try:
                    from handlers.admin import handle_unban_user
                    await handle_unban_user(update, context)
                except ImportError:
                    await update.message.reply_text("❌ Адмін функції тимчасово недоступні")
                return
            elif admin_state == States.BROADCAST:
                try:
                    from handlers.admin import handle_broadcast_message
                    await handle_broadcast_message(update, context)
                except ImportError:
                    await update.message.reply_text("❌ Адмін функції тимчасово недоступні")
                return
            elif admin_state == States.ADMIN_SEARCH_USER:
                try:
                    from handlers.admin import handle_user_search
                    await handle_user_search(update, context)
                except ImportError:
                    await update.message.reply_text("❌ Адмін функції тимчасово недоступні")
                return
        
        # Обробка кнопок меню
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
        
        elif text == "➡️ Далі":
            await show_next_profile(update, context)
            return
        
        elif text == "❤️ Лайк":
            await handle_like(update, context)
            return
        
        elif text == "❤️ Взаємний лайк":
            await handle_like_back(update, context)
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
        
        elif user.id == ADMIN_ID:
            if text in ["👑 Адмін панель", "📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування"]:
                await handle_admin_actions(update, context)
                return
            
            if text in ["📋 Список користувачів", "🚫 Заблокувати користувача", "✅ Розблокувати користувача", "📋 Список заблокованих", "🔙 Назад до адмін-панелі"]:
                try:
                    from handlers.admin import show_users_list, show_banned_users, start_ban_user, start_unban_user, show_admin_panel
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
                except ImportError:
                    await update.message.reply_text("❌ Адмін функції тимчасово недоступні")
                return
        
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
        
        from config import initialize_config
        initialize_config()
        from config import TOKEN
        
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application створено")
        
        setup_handlers(application)
        logger.info("✅ Обробники налаштовано")
        
        await application.initialize()
        logger.info("✅ Бот ініціалізовано")
        
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
        
        bot_initialized = True
        logger.info("🤖 Бот успішно ініціалізовано та готовий до роботи!")
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}", exc_info=True)

def setup_handlers(application):
    """Налаштування обробників повідомлень"""
    logger.info("🔄 Налаштування обробників...")
    
    # Додаємо debug команду
    application.add_handler(CommandHandler("debug", debug_bot))
    print("✅ Debug команда додана")
    
    # Решта ваших обробників залишається без змін...
    application.add_handler(CommandHandler("start", start))
    
    # Обробники кнопок
    application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
    application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
    application.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
    application.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
    application.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
    application.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), handle_like))
    application.add_handler(MessageHandler(filters.Regex('^❤️ Взаємний лайк$'), handle_like_back))
    application.add_handler(MessageHandler(filters.Regex('^🔙 Меню$'), lambda update, context: update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(update.effective_user.id))))
    application.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
    application.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
    application.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
    application.add_handler(MessageHandler(filters.Regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
    application.add_handler(MessageHandler(filters.Regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    
    # Адмін обробники
    application.add_handler(MessageHandler(filters.Regex('^(👑 Адмін панель|📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування)$'), handle_admin_actions))
    application.add_handler(MessageHandler(filters.Regex('^(📋 Список користувачів|🚫 Заблокувати користувача|✅ Розблокувати користувача|📋 Список заблокованих|🔙 Назад до адмін-панелі)$'), universal_handler))
    
    # Фото та універсальний обробник
    application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    application.add_error_handler(error_handler)
    logger.info("✅ Всі обробники налаштовано")

def init_bot():
    """Ініціалізація бота"""
    global event_loop, bot_initialization_started
    
    if bot_initialization_started:
        return
        
    bot_initialization_started = True
    
    try:
        validate_environment()
        
        max_wait_time = 10
        start_time = time.time()
        
        while event_loop is None and (time.time() - start_time) < max_wait_time:
            time.sleep(0.1)
            logger.info("⏳ Чекаємо на ініціалізацію event loop...")
        
        if event_loop is None:
            logger.error("❌ Event loop не ініціалізований протягом 10 секунд")
            return
        
        logger.info("🔄 Запускаємо ініціалізацію бота через event loop...")
        
        future = asyncio.run_coroutine_threadsafe(initialize_bot_async(), event_loop)
        future.result(timeout=30)
        logger.info("✅ Бот успішно ініціалізовано")
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}", exc_info=True)

@app.route('/')
def home():
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

@app.route('/keepalive')
def keepalive():
    """Спеціальний ендпоінт для keep-alive"""
    return "ALIVE", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logger.info("📨 Отримано webhook запит від Telegram")
        
        if not bot_initialized or application is None:
            logger.warning("⚠️ Бот ще не ініціалізований, спробуємо ініціалізувати...")
            init_bot()
            
            time.sleep(2)
            
            if not bot_initialized or application is None:
                logger.error("❌ Бот все ще не ініціалізований")
                return "Bot not initialized", 500
            
        update_data = request.get_json()
        
        if update_data is None:
            logger.error("❌ Порожні дані оновлення")
            return "Empty update data", 400
            
        update = Update.de_json(update_data, application.bot)
        
        asyncio.run_coroutine_threadsafe(process_update(update), event_loop)
        logger.info("✅ Оновлення успішно додано в чергу обробки")
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Критична помилка в webhook: {e}", exc_info=True)
        return "Error", 500

@app.route('/set_webhook')
def set_webhook_route():
    logger.info("🔄 Запит на встановлення webhook")
    try:
        if not bot_initialized:
            init_bot()
            return "🔄 Бот ініціалізується... Спробуйте ще раз через кілька секунд."
        
        future = asyncio.run_coroutine_threadsafe(application.bot.get_webhook_info(), event_loop)
        webhook_info = future.result(timeout=30)
        
        result = f"✅ Webhook встановлено: {WEBHOOK_URL}<br>Pending updates: {webhook_info.pending_update_count}"
        logger.info(f"✅ Результат перевірки webhook: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки webhook: {e}", exc_info=True)
        return f"❌ Помилка: {e}"

# ==================== ДЕТАЛЬНА ВІДЛАДКА БАЗИ ДАНИХ ====================
print("=" * 60)
print("🔧 ДЕТАЛЬНА ІНФОРМАЦІЯ ПРО БАЗУ ДАНИХ")
print("=" * 60)

# Перевірка типу бази даних
if 'postgres' in str(type(db)).lower():
    print("✅ АКТИВНА БАЗА: PostgreSQL")
    db_type = "PostgreSQL"
else:
    print("ℹ️ АКТИВНА БАЗА: SQLite")
    db_type = "SQLite"

# Тест базових функцій
try:
    user_count = db.get_users_count()
    print(f"📊 Кількість користувачів: {user_count}")
    
    stats = db.get_statistics()
    male, female, total_active, goals_stats = stats
    print(f"📈 Статистика: {male} чол., {female} жін., {total_active} актив.")
    
    print("✅ Тест бази даних пройдено успішно")
except Exception as e:
    print(f"❌ Помилка тесту бази даних: {e}")

print("=" * 60)
print("🚀 Бот повністю готовий до роботи!")
print("=" * 60)

if __name__ == '__main__':
    # Запуск сервера
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Запуск Flask сервера на порті {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)