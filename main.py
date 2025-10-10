from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import TOKEN, ADMIN_ID
import logging
import time
import asyncio

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
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати адмін панель"""
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

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка дій адміністратора"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    logger.info(f"🔧 [ADMIN] {user.first_name}: '{text}'")
    
    if text == "📊 Статистика":
        await show_admin_panel(update, context)
    
    elif text == "👥 Користувачі":
        await show_users_management(update, context)
    
    elif text == "📢 Розсилка":
        await start_broadcast(update, context)
    
    elif text == "🔄 Оновити базу":
        await update_database(update, context)
    
    elif text == "🚫 Блокування":
        await show_ban_management(update, context)
    
    elif text == "📈 Детальна статистика":
        await show_detailed_stats(update, context)
    
    elif text == "🔙 Головне меню":
        await update.message.reply_text("👋 Повертаємось до головного меню", reply_markup=get_main_menu(user.id))

async def show_users_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Керування користувачами"""
    user = update.effective_user
    stats = db.get_statistics()
    male, female, total_active, goals_stats = stats
    
    users_text = f"""👥 *Керування користувачами*

📊 Статистика:
• Загалом: {db.get_users_count()}
• Активних: {total_active}
• Чоловіків: {male}
• Жінок: {female}

⚙️ Доступні дії:"""
    
    keyboard = [
        ["📋 Список користувачів", "🔍 Пошук користувача"],
        ["🚫 Заблокувати", "✅ Розблокувати"],
        ["📧 Надіслати повідомлення", "🔙 Назад до адмін-панелі"]
    ]
    
    await update.message.reply_text(
        users_text, 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode='Markdown'
    )

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати список користувачів"""
    user = update.effective_user
    users = db.get_all_active_users(user.id)
    
    if not users:
        await update.message.reply_text("😔 Користувачів не знайдено", reply_markup=get_admin_menu())
        return
    
    users_text = "📋 *Список користувачів:*\n\n"
    for i, user_data in enumerate(users[:10], 1):
        user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
        user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
        is_banned = user_data[13] if len(user_data) > 13 else False
        
        status = "🚫" if is_banned else "✅"
        users_text += f"{i}. {status} {user_name} (ID: `{user_id}`)\n"
    
    if len(users) > 10:
        users_text += f"\n... та ще {len(users) - 10} користувачів"
    
    await update.message.reply_text(users_text, parse_mode='Markdown')
    await show_users_management(update, context)

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок розсилки"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    total_users = db.get_users_count()
    
    await update.message.reply_text(
        f"📢 *Розсилка повідомлень*\n\n"
        f"Кількість одержувачів: {total_users}\n\n"
        f"Введіть повідомлення для розсилки:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True),
        parse_mode='Markdown'
    )
    user_states[user.id] = States.BROADCAST

async def update_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оновлення бази даних"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("🔄 Оновлення бази даних...")
    
    try:
        # Очищення старих даних
        db.cleanup_old_data()
        
        await update.message.reply_text(
            "✅ База даних оновлена успішно!",
            reply_markup=get_admin_menu()
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Помилка оновлення бази: {e}",
            reply_markup=get_admin_menu()
        )

async def show_ban_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Керування блокуванням"""
    user = update.effective_user
    banned_users = db.get_banned_users()
    
    ban_text = f"""🚫 *Керування блокуванням*

Заблоковано користувачів: {len(banned_users)}

Доступні дії:"""
    
    keyboard = [
        ["🚫 Заблокувати користувача", "✅ Розблокувати користувача"],
        ["📋 Список заблокованих", "🔙 Назад до адмін-панелі"]
    ]
    
    await update.message.reply_text(
        ban_text, 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode='Markdown'
    )

async def show_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати заблокованих користувачів"""
    banned_users = db.get_banned_users()
    
    if not banned_users:
        await update.message.reply_text("😊 Немає заблокованих користувачів", reply_markup=get_admin_menu())
        return
    
    ban_text = "🚫 *Заблоковані користувачі:*\n\n"
    for i, user_data in enumerate(banned_users, 1):
        user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
        user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
        ban_text += f"{i}. {user_name} (ID: `{user_id}`)\n"
    
    await update.message.reply_text(ban_text, parse_mode='Markdown')
    await show_ban_management(update, context)

async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальна статистика"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    stats = db.get_statistics()
    male, female, total_active, goals_stats = stats
    total_users = db.get_users_count()
    banned_users = len(db.get_banned_users())
    
    stats_text = f"""📈 *Детальна статистика*

👥 *Користувачі:*
• Загалом: {total_users}
• Активних: {total_active}
• Заблокованих: {banned_users}
• Чоловіків: {male}
• Жінок: {female}"""

    if goals_stats:
        stats_text += "\n\n🎯 *Цілі знайомств:*"
        for goal, count in goals_stats:
            percentage = (count/total_active*100) if total_active > 0 else 0
            stats_text += f"\n• {goal}: {count} ({percentage:.1f}%)"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')
    await show_admin_panel(update, context)

def get_admin_menu():
    """Меню адміністратора"""
    keyboard = [
        ['📊 Статистика', '👥 Користувачі'],
        ['📢 Розсилка', '🔄 Оновити базу'],
        ['🚫 Блокування', '📈 Детальна статистика'],
        ['🔙 Головне меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def handle_admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка пошуку користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_SEARCH_USER:
        return
    
    query = update.message.text
    
    if query == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Пошук скасовано", reply_markup=get_admin_menu())
        return
    
    # Пошук користувача
    found_users = db.search_user(query)
    
    if not found_users:
        await update.message.reply_text(
            f"❌ Користувача '{query}' не знайдено",
            reply_markup=get_admin_menu()
        )
        user_states[user.id] = States.START
        return
    
    user_data = found_users[0]
    user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
    user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
    is_banned = user_data[13] if len(user_data) > 13 else False
    
    status = "🚫 Заблокований" if is_banned else "✅ Активний"
    
    user_info = f"""🔍 *Результати пошуку:*

👤 Ім'я: {user_name}
🆔 ID: `{user_id}`
📊 Статус: {status}"""

    keyboard = []
    if is_banned:
        keyboard.append(["✅ Розблокувати"])
    else:
        keyboard.append(["🚫 Заблокувати"])
    keyboard.append(["📧 Надіслати повідомлення"])
    keyboard.append(["🔙 Назад"])
    
    context.user_data['searched_user_id'] = user_id
    
    await update.message.reply_text(
        user_info,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )
    user_states[user.id] = States.START

async def handle_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка блокування користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_BAN_USER:
        return
    
    user_id_text = update.message.text
    
    if user_id_text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Блокування скасовано", reply_markup=get_admin_menu())
        return
    
    try:
        user_id = int(user_id_text)
        if db.ban_user(user_id):
            await update.message.reply_text(
                f"✅ Користувач `{user_id}` заблокований",
                reply_markup=get_admin_menu(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Користувача `{user_id}` не знайдено",
                reply_markup=get_admin_menu(),
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text("❌ Введіть коректний ID користувача")
    
    user_states[user.id] = States.START

async def handle_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка розблокування користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_UNBAN_USER:
        return
    
    user_id_text = update.message.text
    
    if user_id_text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Розблокування скасовано", reply_markup=get_admin_menu())
        return
    
    try:
        user_id = int(user_id_text)
        if db.unban_user(user_id):
            await update.message.reply_text(
                f"✅ Користувач `{user_id}` розблокований",
                reply_markup=get_admin_menu(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Користувача `{user_id}` не знайдено або вже розблоковано",
                reply_markup=get_admin_menu(),
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text("❌ Введіть коректний ID користувача")
    
    user_states[user.id] = States.START

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлення для розсилки"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.BROADCAST:
        return
    
    message_text = update.message.text
    
    if message_text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Розсилка скасована", reply_markup=get_admin_menu())
        return
    
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Немає користувачів для розсилки", reply_markup=get_admin_menu())
        user_states[user.id] = States.START
        return
    
    await update.message.reply_text(f"🔄 Розсилка повідомлення {len(users)} користувачам...")
    
    success_count = 0
    fail_count = 0
    
    for user_data in users:
        try:
            await context.bot.send_message(
                chat_id=user_data[1],  # telegram_id
                text=f"📢 *Повідомлення від адміністратора:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            success_count += 1
            # Невелика затримка щоб не перевищити ліміти
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"❌ Помилка відправки для {user_data[1]}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"📊 *Результат розсилки:*\n\n"
        f"✅ Відправлено: {success_count}\n"
        f"❌ Не вдалося: {fail_count}",
        reply_markup=get_admin_menu(),
        parse_mode='Markdown'
    )
    user_states[user.id] = States.START

async def handle_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка відправки повідомлення конкретному користувачу"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_SEND_MESSAGE:
        return
    
    text = update.message.text
    
    if text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Відправка скасована", reply_markup=get_admin_menu())
        return
    
    # Якщо це перше повідомлення - зберігаємо ID користувача
    if 'target_user_id' not in context.user_data:
        try:
            target_user_id = int(text)
            context.user_data['target_user_id'] = target_user_id
            await update.message.reply_text(
                f"👤 Отримувач: `{target_user_id}`\n\nВведіть повідомлення:",
                reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True),
                parse_mode='Markdown'
            )
        except ValueError:
            await update.message.reply_text("❌ Введіть коректний ID користувача")
    else:
        # Це повідомлення для відправки
        target_user_id = context.user_data['target_user_id']
        message_text = text
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"📩 *Повідомлення від адміністратора:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            await update.message.reply_text(
                f"✅ Повідомлення відправлено користувачу `{target_user_id}`",
                reply_markup=get_admin_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Не вдалося відправити повідомлення користувачу `{target_user_id}`\n\nПомилка: {e}",
                reply_markup=get_admin_menu(),
                parse_mode='Markdown'
            )
        
        # Очищаємо дані
        context.user_data.pop('target_user_id', None)
        user_states[user.id] = States.START

async def handle_users_management_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопок керування користувачами"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text == "📋 Список користувачів":
        await show_users_list(update, context)
    elif text == "🔍 Пошук користувача":
        await start_user_search(update, context)
    elif text == "🚫 Заблокувати" or text == "🚫 Заблокувати користувача":
        await start_ban_user(update, context)
    elif text == "✅ Розблокувати" or text == "✅ Розблокувати користувача":
        await start_unban_user(update, context)
    elif text == "📧 Надіслати повідомлення":
        await start_send_message(update, context)
    elif text == "📋 Список заблокованих":
        await show_banned_users(update, context)
    elif text == "🔙 Назад до адмін-панелі":
        await show_admin_panel(update, context)

async def start_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок пошуку користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_SEARCH_USER
    await update.message.reply_text(
        "🔍 Введіть ID користувача або ім'я для пошуку:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def start_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок блокування користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_BAN_USER
    await update.message.reply_text(
        "🚫 Введіть ID користувача для блокування:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def start_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок розблокування користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_UNBAN_USER
    await update.message.reply_text(
        "✅ Введіть ID користувача для розблокування:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def start_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок відправки повідомлення конкретному користувачу"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_SEND_MESSAGE
    await update.message.reply_text(
        "📧 Введіть ID користувача, якому хочете надіслати повідомлення:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Універсальний обробник повідомлень"""
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

    # 2. Перевіряємо додавання фото
    if state == States.ADD_MAIN_PHOTO:
        from handlers.profile import handle_main_photo
        await handle_main_photo(update, context)
        return

    # 3. Перевіряємо стани профілю
    if state in [States.PROFILE_AGE, States.PROFILE_GENDER, States.PROFILE_SEEKING_GENDER, 
                 States.PROFILE_CITY, States.PROFILE_GOAL, States.PROFILE_BIO]:
        from handlers.profile import handle_profile_message
        await handle_profile_message(update, context)
        return
    
    # 4. Перевіряємо введення міста для пошуку
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
    
    # 5. Обробка станів адміна
    if user.id == ADMIN_ID:
        state = user_states.get(user.id)
        if state == States.ADMIN_SEARCH_USER:
            await handle_admin_search_user(update, context)
            return
        elif state == States.ADMIN_BAN_USER:
            await handle_ban_user(update, context)
            return
        elif state == States.ADMIN_UNBAN_USER:
            await handle_unban_user(update, context)
            return
        elif state == States.BROADCAST:
            await handle_broadcast_message(update, context)
            return
        elif state == States.ADMIN_SEND_MESSAGE:
            await handle_send_message(update, context)
            return
    
    # 6. Адмін-меню
    if user.id == ADMIN_ID:
        if text in ["📊 Статистика", "👥 Користувачі", "📢 Розсилка", "🔄 Оновити базу", "🚫 Блокування", "📈 Детальна статистика"]:
            await handle_admin_actions(update, context)
            return
        
        # Обробка адмін-кнопок керування користувачами
        if text in ["📋 Список користувачів", "🔍 Пошук користувача", "🚫 Заблокувати", 
                   "✅ Розблокувати", "📧 Надіслати повідомлення", "📋 Список заблокованих",
                   "🚫 Заблокувати користувача", "✅ Розблокувати користувача", "🔙 Назад до адмін-панелі"]:
            await handle_users_management_buttons(update, context)
            return
    
    # 7. Зв'язок з адміном
    if text == "👨‍💼 Зв'язок з адміном":
        context.user_data['contact_admin'] = True
        await update.message.reply_text(
            "📧 Напишіть ваше повідомлення для адміністратора:",
            reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
        )
        return
    
    # 8. Обробка повідомлення для адміна
    if context.user_data.get('contact_admin'):
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
                "✅ Ваше повідомлення відправлено адміністратору!",
                reply_markup=get_main_menu(user.id)
            )
        except Exception as e:
            await update.message.reply_text(
                "❌ Помилка відправки повідомлення.",
                reply_markup=get_main_menu(user.id)
            )
        
        context.user_data['contact_admin'] = False
        return
    
    # 9. Обробка команд меню
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
    
    # 10. Якщо нічого не підійшло
    await update.message.reply_text(
        "❌ Команда не розпізнана. Оберіть пункт з меню:",
        reply_markup=get_main_menu(user.id)
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"❌ Помилка: {context.error}")
    try:
        if update and update.effective_user:
            await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")
    except:
        pass

# Імпорт функцій
from handlers.profile import start_profile_creation, show_my_profile, handle_main_photo, handle_profile_message
from handlers.search import search_profiles, search_by_city, handle_like, show_next_profile, show_top_users, show_matches, show_likes, handle_top_selection, show_user_profile

def main():
    """Головна функція запуску"""
    logger.info("🚀 Запуск Chatrix Bot...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Обробники команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", show_admin_panel))
        
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
        
        # Адмін обробники
        application.add_handler(MessageHandler(filters.Regex('^(📊 Статистика|👥 Користувачі|📢 Розсилка|🔄 Оновити базу|🚫 Блокування|📈 Детальна статистика)$'), handle_admin_actions))
        
        # Обробники керування користувачами
        application.add_handler(MessageHandler(filters.Regex('^(📋 Список користувачів|🔍 Пошук користувача|🚫 Заблокувати|✅ Розблокувати|📧 Надіслати повідомлення|📋 Список заблокованих|🚫 Заблокувати користувача|✅ Розблокувати користувача|🔙 Назад до адмін-панелі)$'), handle_users_management_buttons))
        
        # Фото та універсальний обробник
        application.add_handler(MessageHandler(filters.PHOTO, handle_main_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

        # Обробник помилок
        application.add_error_handler(error_handler)

        logger.info("✅ Бот запущено!")
        
        # Запуск бота
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску: {e}")

if __name__ == "__main__":
    main()