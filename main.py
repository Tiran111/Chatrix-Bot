from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
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
    
    update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def universal_handler(update: Update, context: CallbackContext):
    from utils.states import user_states, States
    from keyboards.main_menu import get_main_menu
    from database.models import db
    
    user = update.effective_user
    text = update.message.text
    state = user_states.get(user.id, States.START)
    
    print(f"🔍 [UNIVERSAL] {user.first_name}: текст='{text}', стан={state}")

    # 0. ПЕРЕВІРКА НА БЛОКУВАННЯ
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        update.message.reply_text(
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
        update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))
        return

    # 2. Перевіряємо додавання фото для профілю
    if state == States.ADD_MAIN_PHOTO:
        print(f"📷 [UNIVERSAL] Користувач у стані ADD_MAIN_PHOTO, обробляємо фото")
        from handlers.profile import handle_main_photo
        handle_main_photo(update, context)
        return

    # 3. Перевіряємо стани профілю
    if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                 States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
        print(f"🔧 [UNIVERSAL] Передаємо обробку handle_profile_message, стан: {state}")
        from handlers.profile import handle_profile_message
        handle_profile_message(update, context)
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
    
    # 5. СПОЧАТКУ ПЕРЕВІРЯЄМО ПІДТВЕРДЖЕННЯ РОЗСИЛКИ
    if user.id == ADMIN_ID:
        if text in ["✅ Так, відправити", "❌ Ні, скасувати"] and 'broadcast_message' in context.user_data:
            print(f"🔧 [UNIVERSAL] Підтвердження розсилки: {text}")
            from handlers.admin import confirm_broadcast
            confirm_broadcast(update, context)
            return
        
        # Перевіряємо інші адмін-стани
        elif state == States.ADMIN_SEARCH_USER:
            from handlers.admin import handle_user_search
            handle_user_search(update, context)
            return
        elif state == States.ADMIN_BAN_USER:
            from handlers.admin import handle_ban_user
            handle_ban_user(update, context)
            return
        elif state == States.ADMIN_UNBAN_USER:
            from handlers.admin import handle_unban_user
            handle_unban_user(update, context)
            return
        elif state == States.ADMIN_BAN_BY_ID:
            from handlers.admin import handle_ban_by_id
            handle_ban_by_id(update, context)
            return
        elif state == States.ADMIN_BAN_BY_MESSAGE:
            from handlers.admin import handle_ban_by_message
            handle_ban_by_message(update, context)
            return
        elif state == States.ADMIN_SEND_MESSAGE:
            from handlers.admin import handle_send_message
            handle_send_message(update, context)
            return
    
    # 6. Обробка адмін-меню
    if user.id == ADMIN_ID:
        if text in ["📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування", "📈 Детальна статистика"]:
            from handlers.admin import handle_admin_actions
            handle_admin_actions(update, context)
            return
        elif text in ["📋 Список користувачів", "🔍 Пошук користувача", "🚫 Заблокувати", "✅ Розблокувати", "📧 Надіслати повідомлення"]:
            from handlers.admin import handle_users_management
            handle_users_management(update, context)
            return
        elif text in ["🔍 Список заблокованих", "🆔 Заблокувати за ID", "📧 Заблокувати за повідомленням", "✅ Розблокувати всіх"]:
            from handlers.admin import handle_ban_management
            handle_ban_management(update, context)
            return
    
    # 7. Обробка звичайних команд користувача
    if text == "👨‍💼 Зв'язок з адміном":
        context.user_data['contact_admin'] = True
        update.message.reply_text(
            "📧 Напишіть ваше повідомлення для адміністратора. Він отримає його в особисті повідомлення:",
            reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
        )
        return
    
    # 8. Обробка повідомлення для адміна
    if context.user_data.get('contact_admin'):
        # Відправляємо повідомлення адміну
        admin_message = f"📩 *Нове повідомлення від користувача:*\n\n" \
                       f"👤 Ім'я: {user.first_name}\n" \
                       f"🆔 ID: {user.id}\n" \
                       f"📧 Username: @{user.username if user.username else 'Немає'}\n\n" \
                       f"💬 *Повідомлення:*\n{text}"
        
        try:
            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            update.message.reply_text(
                "✅ Ваше повідомлення відправлено адміністратору! Він зв'яжеться з вами найближчим часом.",
                reply_markup=get_main_menu(user.id)
            )
        except Exception as e:
            update.message.reply_text(
                "❌ Помилка відправки повідомлення. Спробуйте пізніше.",
                reply_markup=get_main_menu(user.id)
            )
        
        context.user_data['contact_admin'] = False
        return
    
    # 9. Обробка звичайних команд меню
    if text == "📝 Заповнити профіль" or text == "✏️ Редагувати профіль":
        from handlers.profile import start_profile_creation
        start_profile_creation(update, context)
        return
    
    elif text == "👤 Мій профіль":
        from handlers.profile import show_my_profile
        show_my_profile(update, context)
        return
    
    elif text == "💕 Пошук анкет":
        from handlers.search import search_profiles
        search_profiles(update, context)
        return
    
    elif text == "🏙️ По місту":
        from handlers.search import search_by_city
        search_by_city(update, context)
        return
    
    elif text == "❤️ Лайк":
        from handlers.search import handle_like
        handle_like(update, context)
        return
    
    elif text == "➡️ Далі":
        from handlers.search import show_next_profile
        show_next_profile(update, context)
        return
    
    elif text == "🔙 Меню" or text == "🔙 Пошук":
        from handlers.search import handle_navigation
        handle_navigation(update, context)
        return
    
    elif text == "🏆 Топ":
        from handlers.search import show_top_users
        show_top_users(update, context)
        return
    
    elif text == "💌 Мої матчі":
        from handlers.search import show_matches
        show_matches(update, context)
        return
    
    elif text == "❤️ Хто мене лайкнув":
        from handlers.search import show_likes
        show_likes(update, context)
        return
    
    elif text in ["👨 Топ чоловіків", "👩 Топ жінок", "🏆 Загальний топ"]:
        from handlers.search import handle_top_selection
        handle_top_selection(update, context)
        return
    
    # 10. Обробка розсилки (без стану BROADCAST)
    if user.id == ADMIN_ID and text and 'broadcast_message' not in context.user_data:
        from handlers.admin import handle_broadcast_message
        handle_broadcast_message(update, context)
        return
    
    # 11. Якщо нічого не підійшло
    update.message.reply_text(
        "❌ Команда не розпізнана. Спробуйте обрати пункт з меню:",
        reply_markup=get_main_menu(user.id)
    )

def main():
    try:
        print("🚀 Запуск бота...")
        
        # Створюємо Updater для версії 20.7
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        print("✅ Updater створено")
        
        # Додаємо обробник команди /start
        dispatcher.add_handler(CommandHandler("start", start))
        print("✅ Обробник команди start додано")
        
        # Додаємо обробник команди /admin
        from handlers.admin import show_admin_panel
        dispatcher.add_handler(CommandHandler("admin", show_admin_panel))
        print("✅ Обробник команди admin додано")
        
        # Обробники для профілю
        from handlers.profile import start_profile_creation, show_my_profile
        dispatcher.add_handler(MessageHandler(Filters.regex('^(📝 Заповнити профіль|✏️ Редагувати профіль)$'), start_profile_creation))
        dispatcher.add_handler(MessageHandler(Filters.regex('^👤 Мій профіль$'), show_my_profile))
        
        # Обробник фото (для реєстрації)
        from handlers.profile import handle_main_photo
        dispatcher.add_handler(MessageHandler(Filters.photo, handle_main_photo))
        
        # Пошук
        from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, handle_navigation, show_top_users, show_matches, show_likes, handle_top_selection
        dispatcher.add_handler(MessageHandler(Filters.regex('^💕 Пошук анкет$'), search_profiles))
        dispatcher.add_handler(MessageHandler(Filters.regex('^🏙️ По місту$'), search_by_city))
        dispatcher.add_handler(MessageHandler(Filters.regex('^❤️ Лайк$'), handle_like))
        dispatcher.add_handler(MessageHandler(Filters.regex('^➡️ Далі$'), show_next_profile))
        dispatcher.add_handler(MessageHandler(Filters.regex('^(🔙 Пошук|🔙 Меню|🔙 Скасувати)$'), handle_navigation))
        
        # Топ та матчі
        dispatcher.add_handler(MessageHandler(Filters.regex('^🏆 Топ$'), show_top_users))
        dispatcher.add_handler(MessageHandler(Filters.regex('^💌 Мої матчі$'), show_matches))
        dispatcher.add_handler(MessageHandler(Filters.regex('^❤️ Хто мене лайкнув$'), show_likes))
        dispatcher.add_handler(MessageHandler(Filters.regex('^(👨 Топ чоловіків|👩 Топ жінок|🏆 Загальний топ)$'), handle_top_selection))
        
        # Універсальний обробник (ОСТАННІЙ!)
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, universal_handler))
        dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.command, universal_handler))

        print("✅ Всі обробники додані")
        print("🤖 Бот запущено!")
        
        # Запускаємо бота
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Помилка запуску бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()