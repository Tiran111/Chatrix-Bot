from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID
import logging
import sys

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    print(f"🆕 Новий користувач: {user.first_name} (ID: {user.id})")
    
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
    from utils.states import user_states, States
    from keyboards.main_menu import get_main_menu
    from database.models import db
    
    user = update.effective_user
    text = update.message.text if update.message.text else ""
    state = user_states.get(user.id, States.START)
    
    print(f"🔍 [UNIVERSAL] {user.first_name}: текст='{text}', стан={state}")

    # 0. ПЕРЕВІРКА НА БЛОКУВАННЯ
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text(
            "🚫 Ваш акаунт заблоковано адміністратором.\n"
            "Зв'яжіться з адміністратором для отримання додаткової інформації."
        )
        return

    # 1. Перевіряємо скасування для всіх станів
    if text == "🔙 Скасувати" or text == "🔙 Завершити":
        print(f"🔍 [UNIVERSAL] Обробка скасування")
        user_states[user.id] = States.START
        context.user_data['waiting_for_city'] = False
        context.user_data['contact_admin'] = False
        await update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))
        return

    # 2. Перевіряємо додавання фото для профілю
    if state == States.ADD_MAIN_PHOTO:
        print(f"📷 [UNIVERSAL] Користувач у стані ADD_MAIN_PHOTO, обробляємо фото")
        from handlers.profile import handle_main_photo
        await handle_main_photo(update, context)
        return

    # 3. Перевіряємо стани профілю
    if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                 States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
        print(f"🔧 [UNIVERSAL] Передаємо обробку handle_profile_message, стан: {state}")
        from handlers.profile import handle_profile_message
        await handle_profile_message(update, context)
        return
    
    # 4. Перевіряємо введення міста для пошуку
    if context.user_data.get('waiting_for_city'):
        print(f"🔧 [UNIVERSAL] Обробка пошуку за містом: '{text}'")
        
        from handlers.search import show_user_profile
        
        # Видаляємо емодзі з назви міста (якщо є)
        clean_city = text.replace('🏙️ ', '').strip()
        
        print(f"🔍 Шукаємо в місті: {clean_city}")
        users = db.get_users_by_city(clean_city, user.id)
        print(f"🔍 Знайдено користувачів: {len(users)}")
        
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
    
    # 5. Обробка звичайних команд меню
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
    
    # 6. Якщо нічого не підійшло
    await update.message.reply_text(
        "❌ Команда не розпізнана. Спробуйте обрати пункт з меню:",
        reply_markup=get_main_menu(user.id)
    )

def main():
    try:
        print("🚀 Запуск бота...")
        
        # Перевірка токена перед створенням додатка
        if not TOKEN:
            print("❌ КРИТИЧНА ПОМИЛКА: TELEGRAM_BOT_TOKEN не встановлено!")
            print("📝 Інструкція:")
            print("1. Перейдіть до @BotFather в Telegram")
            print("2. Створіть нового бота командою /newbot")
            print("3. Отримайте токен")
            print("4. Додайте токен як змінну оточення TELEGRAM_BOT_TOKEN на Railway")
            print("5. Перезапустіть додаток")
            sys.exit(1)
        
        # Перевірка формату токена
        if ':' not in TOKEN:
            print("❌ НЕВІРНИЙ ФОРМАТ ТОКЕНА!")
            print("Токен повинен мати формат: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
            sys.exit(1)
            
        print(f"✅ Токен отримано, починаю запуск...")
        
        application = Application.builder().token(TOKEN).build()
        print("✅ Додаток створено")
        
        # Додаємо обробник команди /start
        application.add_handler(CommandHandler("start", start))
        print("✅ Обробник команди start додано")
        
        # Додаємо обробник команди /admin
        from handlers.admin import show_admin_panel
        application.add_handler(CommandHandler("admin", show_admin_panel))
        print("✅ Обробник команди admin додано")
        
        # Обробники для профілю
        from handlers.profile import start_profile_creation, show_my_profile
        application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
        application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
        
        # Обробник фото (для реєстрації)
        from handlers.profile import handle_main_photo
        application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
        
        # Пошук
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
        
        # Універсальний обробник (ОСТАННІЙ!)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))
        application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, universal_handler))

        print("✅ Всі обробники додані")
        print("🤖 Бот запущено!")
        
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Помилка запуску бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()