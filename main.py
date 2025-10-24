import logging
import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from handlers.profile import start_edit_profile

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
    raise

try:
    from config import ADMIN_ID
    from config import TOKEN
except ImportError as e:
    logger.error(f"❌ Помилка імпорту конфігурації: {e}")
    raise

try:
    from keyboards.main_menu import get_main_menu
    from utils.states import user_states, States
except ImportError as e:
    logger.error(f"❌ Помилка імпорту утиліт: {e}")

# Глобальні змінні
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
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

        elif text == "👀 Хто переглядав":
            from handlers.search import show_profile_views
            await show_profile_views(update, context)
            return

        elif text == "❤️ Лайк":  # Для лайків з топу
            from handlers.search import handle_top_like
            await handle_top_like(update, context)
            return

        elif text == "❤️ Лайкнути":  # Для лайків з переглядів
            from handlers.search import handle_like
            await handle_like(update, context)
            return

        elif text == "➡️ Наступний перегляд":
            from handlers.search import show_next_profile_view
            await show_next_profile_view(update, context)
            return

        elif text == "➡️ Наступний у топі":
            from handlers.search import handle_top_navigation
            await handle_top_navigation(update, context)
            return 

        elif text == "📈 Детальна статистика":
            from handlers.admin import show_detailed_stats
            await show_detailed_stats(update, context)
            return     

        elif text == "🔙 Меню":
            await update.message.reply_text(
                "👋 Повертаємось до головного меню",
                reply_markup=get_main_menu(user.id)
            )
            return

        elif text == "🔍 Пошук користувача":
            from handlers.admin import start_user_search
            await start_user_search(update, context)
            return  

        elif text == "📊 Статистика":
            from handlers.admin import show_admin_panel
            await show_admin_panel(update, context)
            return

        elif text == "👥 Користувачі":
            from handlers.admin import show_users_management
            await show_users_management(update, context)
            return

        elif text == "📢 Розсилка":
            from handlers.admin import start_broadcast
            await start_broadcast(update, context)
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

def init_bot():
    """Ініціалізація бота"""
    global application, bot_initialized
    
    if bot_initialized:
        logger.info("✅ Бот вже ініціалізовано")
        return True
        
    try:
        logger.info("🔄 Ініціалізація бота...")
        
        # Створюємо додаток
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        setup_handlers(application)
        
        # Ініціалізуємо
        application.initialize()
        
        # Встановлюємо вебхук
        application.bot.set_webhook(WEBHOOK_URL)
        
        bot_initialized = True
        logger.info("✅ Бот успішно ініціалізовано!")
        logger.info(f"🌐 Вебхук встановлено: {WEBHOOK_URL}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}")
        return False

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
    
    # Фото та універсальний обробник
    application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
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
            if not init_bot():
                return "Bot initialization failed", 500
            
        update_data = request.get_json()
        if update_data is None:
            return "Empty update data", 400
            
        # Обробляємо оновлення
        update = Update.de_json(update_data, application.bot)
        application.update_queue.put(update)
        
        return 'ok'
        
    except Exception as e:
        logger.error(f"❌ Webhook помилка: {e}")
        return "Error", 200

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
print("🚀 СЕРВЕР ГОТОВИЙ ДО РОБОТИ!")
print(f"🌐 Порт: {PORT}")
print("📱 Бот ініціалізується при першому запиті")
print("=" * 60)

# ==================== SERVER STARTUP ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск Chatrix Bot...")
    print("=" * 50)
    
    # Ініціалізація бота
    print("🔧 Ініціалізація бота...")
    if init_bot():
        print("✅ Бот успішно ініціалізовано")
    else:
        print("❌ Помилка ініціалізації бота")
    
    # Запуск сервера
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Запуск сервера на порті {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)