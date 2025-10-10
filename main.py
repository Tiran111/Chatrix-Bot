from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID
import logging
import os

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    user = update.effective_user
    
    logger.info(f"🆕 Користувач: {user.first_name} (ID: {user.id})")
    
    # Додаємо користувача в базу
    db.add_user(user.id, user.username, user.first_name)
    
    # Скидаємо стан
    user_states[user.id] = States.START
    
    # Вітання
    welcome_text = (
        f"👋 Вітаю, {user.first_name}!\n\n"
        f"💞 *Chatrix* — це бот для знайомств, де ти можеш:\n\n"
        f"• 📝 Створити свою анкету\n"
        f"• 💕 Знаходити цікавих людей\n"
        f"• ❤️ Ставити лайки та отримувати матчі\n"
        f"• 🏆 Переглядати топ користувачів\n"
        f"• 🏙️ Шукати за містом\n\n"
        f"🚀 *Бот працює на Render!*\n\n"
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
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Універсальний обробник повідомлень"""
    from utils.states import user_states, States
    from keyboards.main_menu import get_main_menu
    from database.models import db
    
    user = update.effective_user
    text = update.message.text if update.message.text else ""
    state = user_states.get(user.id, States.START)
    
    logger.info(f"📨 Повідомлення від {user.first_name}: '{text}', стан: {state}")

    # 1. Перевіряємо скасування для всіх станів
    if text == "🔙 Скасувати" or text == "🔙 Завершити":
        logger.info(f"🔍 Обробка скасування")
        user_states[user.id] = States.START
        context.user_data['waiting_for_city'] = False
        context.user_data['contact_admin'] = False
        await update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))
        return

    # 2. Перевіряємо додавання фото для профілю
    if state == States.ADD_MAIN_PHOTO:
        logger.info(f"📷 Користувач у стані ADD_MAIN_PHOTO")
        from handlers.profile import handle_main_photo
        await handle_main_photo(update, context)
        return

    # 3. Перевіряємо стани профілю
    if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                 States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
        logger.info(f"🔧 Передаємо обробку handle_profile_message, стан: {state}")
        from handlers.profile import handle_profile_message
        await handle_profile_message(update, context)
        return
    
    # 4. Перевіряємо введення міста для пошуку
    if context.user_data.get('waiting_for_city'):
        logger.info(f"🔧 Обробка пошуку за містом: '{text}'")
        
        from handlers.search import show_user_profile
        
        # Видаляємо емодзі з назви міста (якщо є)
        clean_city = text.replace('🏙️ ', '').strip()
        
        logger.info(f"🔍 Шукаємо в місті: {clean_city}")
        users = db.get_users_by_city(clean_city, user.id)
        logger.info(f"🔍 Знайдено користувачів: {len(users)}")
        
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
    
    # 5. Обробка звичайних команд користувача
    if text == "👨‍💼 Зв'язок з адміном":
        context.user_data['contact_admin'] = True
        await update.message.reply_text(
            "📧 Напишіть ваше повідомлення для адміністратора. Він отримає його в особисті повідомлення:",
            reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
        )
        return
    
    # 6. Обробка повідомлення для адміна
    if context.user_data.get('contact_admin'):
        # Відправляємо повідомлення адміну
        admin_message = f"📩 *Нове повідомлення від користувача:*\n\n" \
                       f"👤 Ім'я: {user.first_name}\n" \
                       f"🆔 ID: {user.id}\n" \
                       f"📧 Username: @{user.username if user.username else 'Немає'}\n\n" \
                       f"💬 *Повідомлення:*\n{text}"
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            await update.message.reply_text(
                "✅ Ваше повідомлення відправлено адміністратору! Він зв'яжеться з вами найближчим часом.",
                reply_markup=get_main_menu(user.id)
            )
        except Exception as e:
            await update.message.reply_text(
                "❌ Помилка відправки повідомлення. Спробуйте пізніше.",
                reply_markup=get_main_menu(user.id)
            )
        
        context.user_data['contact_admin'] = False
        return
    
    # 7. Обробка звичайних команд меню
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
    
    elif text == "🔙 Меню" or text == "🔙 Пошук":
        from handlers.search import handle_navigation
        await handle_navigation(update, context)
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
    
    # 8. Якщо нічого не підійшло
    await update.message.reply_text(
        "❌ Команда не розпізнана. Спробуйте обрати пункт з меню:",
        reply_markup=get_main_menu(user.id)
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"❌ Помилка: {context.error}")
    try:
        if update and update.effective_user:
            await update.message.reply_text(
                "❌ Сталася помилка. Спробуйте ще раз або використовуйте /start"
            )
    except Exception as e:
        logger.error(f"❌ Помилка в error_handler: {e}")

def main():
    """Головна функція"""
    logger.info("🚀 Запуск Chatrix Bot на Render...")
    
    try:
        # Створюємо додаток
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробник команди /start
        application.add_handler(CommandHandler("start", start))
        
        # Додаємо обробник команди /admin
        try:
            from handlers.admin import show_admin_panel
            application.add_handler(CommandHandler("admin", show_admin_panel))
            logger.info("✅ Обробник команди admin додано")
        except ImportError as e:
            logger.warning(f"ℹ️ Обробник admin не знайдено: {e}")
        
        # Обробники для профілю
        try:
            from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo
            application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
            application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
            application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
            logger.info("✅ Обробники профілю додані")
        except ImportError as e:
            logger.warning(f"ℹ️ Обробники профілю не знайдені: {e}")
        
        # Пошук
        try:
            from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, handle_navigation, show_top_users, show_matches, show_likes, handle_top_selection
            application.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
            application.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
            application.add_handler(MessageHandler(filters.Regex('^❤️ Лайк$'), handle_like))
            application.add_handler(MessageHandler(filters.Regex('^➡️ Далі$'), show_next_profile))
            application.add_handler(MessageHandler(filters.Regex('^(🔙 Пошук|🔙 Меню|🔙 Скасувати)$'), handle_navigation))
            
            # Топ та матчі
            application.add_handler(MessageHandler(filters.Regex('^🏆 Топ$'), show_top_users))
            application.add_handler(MessageHandler(filters.Regex('^💌 Мої матчі$'), show_matches))
            application.add_handler(MessageHandler(filters.Regex('^❤️ Хто мене лайкнув$'), show_likes))
            application.add_handler(MessageHandler(filters.Regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
            logger.info("✅ Обробники пошуку додані")
        except ImportError as e:
            logger.warning(f"ℹ️ Обробники пошуку не знайдені: {e}")
        
        # Універсальний обробник (ОСТАННІЙ!)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))
        application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, universal_handler))

        # Обробник помилок
        application.add_error_handler(error_handler)

        logger.info("✅ Всі обробники додані")
        logger.info("🤖 Бот запущено на Render!")
        
        # Запускаємо бота
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()