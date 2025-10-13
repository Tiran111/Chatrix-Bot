import logging
import os
import asyncio
from flask import Flask
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ReplyKeyboardMarkup
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

def start(update: Update, context: CallbackContext):
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
        
        update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Помилка в /start: {e}")
        update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

def contact_admin(update: Update, context: CallbackContext):
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
        
        update.message.reply_text(
            contact_text,
            reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Помилка в contact_admin: {e}")
        update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

def handle_contact_message(update: Update, context: CallbackContext):
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
            update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
            return
        
        # Відправляємо повідомлення адміну
        try:
            admin_message = f"""📩 *Нове повідомлення від користувача*

👤 *Користувач:* {user.first_name}
🆔 *ID:* `{user.id}`
📝 *Повідомлення:*
{message_text}"""

            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            # Підтверджуємо користувачу
            update.message.reply_text(
                "✅ Ваше повідомлення відправлено адміністратору! Він зв'яжеться з вами найближчим часом.",
                reply_markup=get_main_menu(user.id)
            )
            
        except Exception as e:
            logger.error(f"❌ Помилка відправки повідомлення адміну: {e}")
            update.message.reply_text(
                "❌ Помилка відправки повідомлення. Спробуйте пізніше.",
                reply_markup=get_main_menu(user.id)
            )
        
        # Скидаємо стан після обробки
        user_states[user.id] = States.START
        logger.info(f"✅ Стан скинуто для користувача {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Помилка в handle_contact_message: {e}")
        update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

def debug_search(update: Update, context: CallbackContext):
    """Команда для дебагу пошуку"""
    try:
        user = update.effective_user
        logger.info(f"🔧 [DEBUG COMMAND] Для користувача {user.id}")
        
        # Отримуємо дані поточного користувача
        current_user = db.get_user(user.id)
        
        if not current_user:
            update.message.reply_text("❌ Вашого профілю не знайдено")
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
        
        update.message.reply_text(debug_info, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ Помилка в debug_search: {e}")
        update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

def universal_handler(update: Update, context: CallbackContext):
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
            update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))
            return

        # 2. Обробка зв'язку з адміном
        if state == States.CONTACT_ADMIN:
            logger.info(f"🔧 Обробка повідомлення для адміна від {user.id}")
            handle_contact_message(update, context)
            return

        # 3. Перевіряємо додавання фото
        if state == States.ADD_MAIN_PHOTO:
            handle_main_photo(update, context)
            return

        # 4. Перевіряємо стани профілю
        if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                     States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
            handle_profile_message(update, context)
            return
        
        # 5. Перевіряємо введення міста для пошуку
        if context.user_data.get('waiting_for_city'):
            clean_city = text.replace('🏙️ ', '').strip()
            users = db.get_users_by_city(clean_city, user.id)
            
            if users:
                user_data = users[0]
                show_user_profile(update, context, user_data, f"🏙️ Місто: {clean_city}")
                context.user_data['search_users'] = users
                context.user_data['current_index'] = 0
                context.user_data['search_type'] = 'city'
            else:
                update.message.reply_text(
                    f"😔 Не знайдено анкет у місті {clean_city}",
                    reply_markup=get_main_menu(user.id)
                )
            
            context.user_data['waiting_for_city'] = False
            return
        
        # 6. Обробка станів адміна
        if user.id == ADMIN_ID:
            state = user_states.get(user.id)
            if state == States.ADMIN_BAN_USER:
                handle_ban_user(update, context)
                return
            elif state == States.ADMIN_UNBAN_USER:
                handle_unban_user(update, context)
                return
            elif state == States.BROADCAST:
                handle_broadcast_message(update, context)
                return
        
        # 7. Адмін-меню
        if user.id == ADMIN_ID:
            if text in ["👑 Адмін панель", "📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування", "📈 Детальна статистика"]:
                handle_admin_actions(update, context)
                return
            
            # Обробка адмін-кнопок керування користувачами
            if text in ["📋 Список користувачів", "🚫 Заблокувати користувача", "✅ Розблокувати користувача", "📋 Список заблокованих", "🔙 Назад до адмін-панелі"]:
                if text == "📋 Список користувачів":
                    show_users_list(update, context)
                elif text == "🚫 Заблокувати користувача":
                    start_ban_user(update, context)
                elif text == "✅ Розблокувати користувача":
                    start_unban_user(update, context)
                elif text == "📋 Список заблокованих":
                    show_banned_users(update, context)
                elif text == "🔙 Назад до адмін-панелі":
                    show_admin_panel(update, context)
                return
        
        # 8. Обробка команд меню
        if text == "📝 Заповнити профіль" or text == "✏️ Редагувати профіль":
            start_profile_creation(update, context)
            return
        
        elif text == "👤 Мій профіль":
            show_my_profile(update, context)
            return
        
        elif text == "💕 Пошук анкет":
            search_profiles(update, context)
            return
        
        elif text == "🏙️ По місту":
            search_by_city(update, context)
            return
        
        elif text == "❤️ Лайк":
            handle_like(update, context)
            return
        
        elif text == "➡️ Далі":
            show_next_profile(update, context)
            return
        
        elif text == "🔙 Меню":
            update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(user.id))
            return
        
        elif text == "🏆 Топ":
            show_top_users(update, context)
            return
        
        elif text == "💌 Мої матчі":
            show_matches(update, context)
            return
        
        elif text == "❤️ Хто мене лайкнув":
            show_likes(update, context)
            return
        
        elif text in ["👨 Топ чоловіків", "👩 Топ жінок", "🏆 Загальний топ"]:
            handle_top_selection(update, context)
            return
        
        # 9. Обробка кнопки зв'язку з адміном
        elif text == "👨‍💼 Зв'язок з адміном":
            contact_admin(update, context)
            return
        
        # 10. Команда дебагу
        elif text == "/debug_search":
            debug_search(update, context)
            return
        
        # 11. Якщо нічого не підійшло
        update.message.reply_text(
            "❌ Команда не розпізнана. Оберіть пункт з меню:",
            reply_markup=get_main_menu(user.id)
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка в universal_handler: {e}")
        update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

def error_handler(update: Update, context: CallbackContext):
    """Обробник помилок"""
    try:
        logger.error(f"❌ Помилка: {context.error}", exc_info=True)
        if update and update.effective_user:
            update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")
    except Exception as e:
        logger.error(f"❌ Помилка в error_handler: {e}")

def setup_handlers(updater):
    """Налаштування обробників"""
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("debug_search", debug_search))
    
    # Обробники кнопок
    dispatcher.add_handler(MessageHandler(Filters.regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
    dispatcher.add_handler(MessageHandler(Filters.regex('^👤 Мій профіль$'), show_my_profile))
    dispatcher.add_handler(MessageHandler(Filters.regex('^💕 Пошук анкет$'), search_profiles))
    dispatcher.add_handler(MessageHandler(Filters.regex('^🏙️ По місту$'), search_by_city))
    dispatcher.add_handler(MessageHandler(Filters.regex('^❤️ Лайк$'), handle_like))
    dispatcher.add_handler(MessageHandler(Filters.regex('^➡️ Далі$'), show_next_profile))
    dispatcher.add_handler(MessageHandler(Filters.regex('^🔙 Меню$'), lambda update, context: update.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(update.effective_user.id))))
    dispatcher.add_handler(MessageHandler(Filters.regex('^🏆 Топ$'), show_top_users))
    dispatcher.add_handler(MessageHandler(Filters.regex('^💌 Мої матчі$'), show_matches))
    dispatcher.add_handler(MessageHandler(Filters.regex('^❤️ Хто мене лайкнув$'), show_likes))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
    dispatcher.add_handler(MessageHandler(Filters.regex("^👨‍💼 Зв'язок з адміном$"), contact_admin))
    
    # Адмін обробники
    dispatcher.add_handler(MessageHandler(Filters.regex('^(👑 Адмін панель|📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування|📈 Детальна статистика)$'), handle_admin_actions))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(📋 Список користувачів|🚫 Заблокувати користувача|✅ Розблокувати користувача|📋 Список заблокованих|🔙 Назад до адмін-панелі)$'), universal_handler))
    
    # Обробники для станів блокування
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^🚫 Заблокувати$'), start_ban_user))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^✅ Розблокувати$'), start_unban_user))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^🚫 Заблокувати користувача$'), start_ban_user))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^✅ Розблокувати користувача$'), start_unban_user))
    
    # Фото та універсальний обробник
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_main_photo))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, universal_handler))

    # Обробник помилок
    dispatcher.add_error_handler(error_handler)

def start_telegram_bot():
    """Запуск Telegram бота"""
    try:
        logger.info("🚀 Запуск Telegram Bot...")
        
        # Створюємо updater
        updater = Updater(TOKEN, use_context=True)
        
        # Налаштовуємо обробники
        setup_handlers(updater)
        
        logger.info("✅ Бот запущено!")
        
        # Запускаємо polling БЕЗ idle()
        updater.start_polling()
        
        # Простий нескінченний цикл
        import time
        while True:
            time.sleep(10)
            
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}")

def start_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Запуск Flask сервера на порті {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def main():
    """Головна функція запуску"""
    # Визначаємо тип запуску через змінну оточення
    run_type = os.environ.get("RUN_TYPE", "web")
    
    if run_type == "bot":
        logger.info("🚀 Запуск Telegram Bot...")
        start_telegram_bot()
    else:
        logger.info("🚀 Запуск Flask Web Server...")
        start_flask()

if __name__ == "__main__":
    main()