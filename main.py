import os
import logging
import asyncio
from flask import Flask

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

def setup_telegram_bot():
    """Налаштування та запуск Telegram бота"""
    try:
        # Імпортуємо все всередині функції щоб уникнути конфліктів
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
        from telegram import Update, ReplyKeyboardMarkup
        from database.models import db
        from keyboards.main_menu import get_main_menu
        from utils.states import user_states, States
        from config import TOKEN, ADMIN_ID
        
        # Імпорт всіх необхідних функцій
        from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
        from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile
        
        logger.info("🚀 Ініціалізація Telegram Bot...")
        
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

        async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Показати адмін панель"""
            try:
                user = update.effective_user
                if user.id != ADMIN_ID:
                    await update.message.reply_text("❌ Доступ заборонено", reply_markup=get_main_menu(user.id))
                    return
                
                stats = db.get_statistics()
                male, female, total_active, goals_stats = stats
                
                # Додаткова статистика
                total_users = db.get_users_count()
                banned_users = len(db.get_banned_users())
                
                stats_text = f"""📊 *Статистика бота*

👥 Загалом користувачів: {total_users}
✅ Активних анкет: {total_active}
🚫 Заблокованих: {banned_users}
👨 Чоловіків: {male}
👩 Жінок: {female}"""

                if goals_stats:
                    stats_text += "\n\n🎯 *Цілі знайомств:*"
                    for goal, count in goals_stats:
                        stats_text += f"\n• {goal}: {count}"
                
                await update.message.reply_text(stats_text, parse_mode='Markdown')
                
                # Адмін меню
                keyboard = [
                    ['📊 Статистика', '👥 Користувачі'],
                    ['📢 Розсилка', '🔄 Оновити базу'],
                    ['🚫 Блокування', '📈 Детальна статистика'],
                    ['🔙 Головне меню']
                ]
                
                await update.message.reply_text(
                    "👑 *Адмін панель*\nОберіть дію:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Помилка в show_admin_panel: {e}")
                await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

        async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Обробка дій адміністратора"""
            try:
                user = update.effective_user
                if user.id != ADMIN_ID:
                    return
                
                text = update.message.text
                
                logger.info(f"🔧 [ADMIN] {user.first_name}: '{text}'")
                
                if text == "👑 Адмін панель" or text == "📊 Статистика":
                    await show_admin_panel(update, context)
                
                elif text == "👥 Користувачі":
                    from handlers.admin import show_users_management
                    await show_users_management(update, context)
                
                elif text == "📢 Розсилка":
                    from handlers.admin import start_broadcast
                    await start_broadcast(update, context)
                
                elif text == "🔄 Оновити базу":
                    from handlers.admin import update_database
                    await update_database(update, context)
                
                elif text == "🚫 Блокування":
                    from handlers.admin import show_ban_management
                    await show_ban_management(update, context)
                
                elif text == "📈 Детальна статистика":
                    from handlers.admin import show_detailed_stats
                    await show_detailed_stats(update, context)
                
                elif text == "🔙 Головне меню":
                    await update.message.reply_text("👋 Повертаємось до головного меню", reply_markup=get_main_menu(user.id))
            except Exception as e:
                logger.error(f"❌ Помилка в handle_admin_actions: {e}")
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
                    return

                # 2. Обробка зв'язку з адміном
                if state == States.CONTACT_ADMIN:
                    logger.info(f"🔧 Обробка повідомлення для адміна від {user.id}")
                    await handle_contact_message(update, context)
                    return

                # 3. Перевіряємо додавання фото
                if state == States.ADD_MAIN_PHOTO:
                    await handle_main_photo(update, context)
                    return

                # 4. Перевіряємо стани профілю
                if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                             States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
                    await handle_profile_message(update, context)
                    return
                
                # 5. Перевіряємо введення міста для пошуку
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
                
                # 6. Обробка станів адміна
                if user.id == ADMIN_ID:
                    state = user_states.get(user.id)
                    if state == States.ADMIN_BAN_USER:
                        from handlers.admin import handle_ban_user
                        await handle_ban_user(update, context)
                        return
                    elif state == States.ADMIN_UNBAN_USER:
                        from handlers.admin import handle_unban_user
                        await handle_unban_user(update, context)
                        return
                    elif state == States.BROADCAST:
                        from handlers.admin import handle_broadcast_message
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
                            from handlers.admin import show_users_list
                            await show_users_list(update, context)
                        elif text == "🚫 Заблокувати користувача":
                            from handlers.admin import start_ban_user
                            await start_ban_user(update, context)
                        elif text == "✅ Розблокувати користувача":
                            from handlers.admin import start_unban_user
                            await start_unban_user(update, context)
                        elif text == "📋 Список заблокованих":
                            from handlers.admin import show_banned_users
                            await show_banned_users(update, context)
                        elif text == "🔙 Назад до адмін-панелі":
                            await show_admin_panel(update, context)
                        return
                
                # 8. Обробка команд меню
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
                
                # 9. Обробка кнопки зв'язку з адміном
                elif text == "👨‍💼 Зв'язок з адміном":
                    await contact_admin(update, context)
                    return
                
                # 10. Якщо нічого не підійшло
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

        def setup_handlers(application):
            """Налаштування обробників"""
            application.add_handler(CommandHandler("start", start))
            
            # Обробники кнопок
            application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
            application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
            application.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
            application.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
            application.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), handle_like))
            application.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
            application.add_handler(MessageHandler(filters.Regex('^🔙 Меню$'), lambda u, c: u.message.reply_text("👋 Повертаємось до меню", reply_markup=get_main_menu(u.effective_user.id))))
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

        # Створюємо application
        application = Application.builder().token(TOKEN).build()
        
        # Налаштовуємо обробники
        setup_handlers(application)
        
        return application
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}")
        return None

async def run_bot():
    """Запуск бота"""
    application = setup_telegram_bot()
    if application:
        logger.info("✅ Бот запущено!")
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    else:
        logger.error("❌ Не вдалося ініціалізувати бота")

def start_bot():
    """Запуск бота в окремому потоці"""
    asyncio.run(run_bot())

def start_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Запуск Flask сервера на порті {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Визначаємо тип запуску через змінну оточення
    run_type = os.environ.get("RUN_TYPE", "web")
    
    if run_type == "bot":
        logger.info("🚀 Запуск Telegram Bot...")
        start_bot()
    else:
        logger.info("🚀 Запуск Flask Web Server...")
        start_flask()