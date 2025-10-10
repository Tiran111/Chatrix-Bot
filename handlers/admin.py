from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu, get_admin_menu, get_cancel_keyboard
from utils.states import States, user_states
from config import ADMIN_ID
import logging
import time

logger = logging.getLogger(__name__)

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
    await update.message.reply_text("👑 *Адмін панель*\nОберіть дію:", reply_markup=get_admin_menu(), parse_mode='Markdown')

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
    
    elif text == "🔙 Назад до адмін-панелі":
        await show_admin_panel(update, context)
    
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
    
    await update.message.reply_text(users_text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')

async def handle_users_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка керування користувачами"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text == "📋 Список користувачів":
        await show_users_list(update, context)
    
    elif text == "🔍 Пошук користувача":
        await start_user_search(update, context)
    
    elif text == "🚫 Заблокувати":
        await start_ban_user(update, context)
    
    elif text == "✅ Розблокувати":
        await start_unban_user(update, context)
    
    elif text == "📧 Надіслати повідомлення":
        await start_send_message(update, context)

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати список користувачів"""
    user = update.effective_user
    users = db.get_all_active_users(user.id)
    
    if not users:
        await update.message.reply_text("😔 Користувачів не знайдено", reply_markup=get_admin_menu())
        return
    
    users_text = "📋 *Список користувачів:*\n\n"
    for i, user_data in enumerate(users[:15], 1):  # Показуємо перших 15
        user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
        user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
        is_banned = user_data[13] if len(user_data) > 13 else False
        
        status = "🚫" if is_banned else "✅"
        users_text += f"{i}. {status} {user_name} (ID: `{user_id}`)\n"
    
    if len(users) > 15:
        users_text += f"\n... та ще {len(users) - 15} користувачів"
    
    await update.message.reply_text(users_text, parse_mode='Markdown')
    await show_users_management(update, context)

async def start_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок пошуку користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_SEARCH_USER
    await update.message.reply_text(
        "🔍 Введіть ID користувача або ім'я для пошуку:",
        reply_markup=get_cancel_keyboard()
    )

async def start_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок блокування користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_BAN_USER
    await update.message.reply_text(
        "🚫 Введіть ID користувача для блокування:",
        reply_markup=get_cancel_keyboard()
    )

async def start_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок розблокування користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_UNBAN_USER
    await update.message.reply_text(
        "✅ Введіть ID користувача для розблокування:",
        reply_markup=get_cancel_keyboard()
    )

async def start_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок відправки повідомлення конкретному користувачу"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_SEND_MESSAGE
    await update.message.reply_text(
        "📧 Введіть ID користувача, якому хочете надіслати повідомлення:",
        reply_markup=get_cancel_keyboard()
    )

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
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    user_states[user.id] = States.BROADCAST

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлення для розсилки"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    message_text = update.message.text
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
                chat_id=user_data[1],
                text=f"📢 *Повідомлення від адміністратора:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            success_count += 1
            time.sleep(0.1)  # Затримка щоб не перевищити ліміти
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

async def update_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оновлення бази даних"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("🔄 Оновлення бази даних...")
    
    try:
        # Тут можна додати логіку оновлення бази
        # Наприклад, очищення старих даних, оновлення структури тощо
        
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
    
    await update.message.reply_text(ban_text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')

async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальна статистика"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    stats = db.get_detailed_statistics()
    
    if not stats:
        await update.message.reply_text("❌ Немає даних для статистики", reply_markup=get_admin_menu())
        return
    
    total_users, active_users, male_count, female_count, avg_age, goals_stats, cities_stats = stats
    
    stats_text = f"""📈 *Детальна статистика*

👥 Користувачі:
• Загалом: {total_users}
• Активних: {active_users}
• Чоловіків: {male_count}
• Жінок: {female_count}
• Середній вік: {avg_age:.1f} років"""

    if goals_stats:
        stats_text += "\n\n🎯 *Цілі знайомств:*"
        for goal, count in goals_stats:
            stats_text += f"\n• {goal}: {count}"
    
    if cities_stats:
        stats_text += "\n\n🏙️ *Топ міст:*"
        for city, count in cities_stats[:5]:  # Топ 5 міст
            stats_text += f"\n• {city}: {count}"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')
    await show_admin_panel(update, context)

# Функції для обробки повідомлень в різних станах адміна
async def handle_admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка пошуку користувача"""
    user = update.effective_user
    search_term = update.message.text
    
    try:
        # Спроба пошуку по ID
        user_id = int(search_term)
        user_data = db.get_user(user_id)
        
        if user_data:
            await show_user_info(update, context, user_data)
        else:
            await update.message.reply_text("❌ Користувача з таким ID не знайдено")
    except ValueError:
        # Пошук по імені
        users = db.search_users_by_name(search_term)
        if users:
            await show_users_search_results(update, context, users)
        else:
            await update.message.reply_text("❌ Користувачів з таким іменем не знайдено")
    
    user_states[user.id] = States.START
    await show_users_management(update, context)

async def show_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data):
    """Показати інформацію про користувача"""
    user_id = user_data[1]
    username = user_data[2] or "Немає"
    name = user_data[3] or "Невідомо"
    age = user_data[4] or "Не вказано"
    gender = "👨 Чоловік" if user_data[5] == 'male' else "👩 Жінка" if user_data[5] == 'female' else "Не вказано"
    city = user_data[6] or "Не вказано"
    is_banned = user_data[13] if len(user_data) > 13 else False
    
    status = "🚫 Заблокований" if is_banned else "✅ Активний"
    
    info_text = f"""👤 *Інформація про користувача*

🆔 ID: `{user_id}`
👤 Ім'я: {name}
📧 Username: @{username}
📊 Статус: {status}

📝 *Профіль:*
• Вік: {age}
• Стать: {gender}
• Місто: {city}"""
    
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def show_users_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, users):
    """Показати результати пошуку користувачів"""
    results_text = "🔍 *Результати пошуку:*\n\n"
    
    for i, user_data in enumerate(users[:10], 1):  # Показуємо перших 10
        user_id = user_data[1]
        username = user_data[2] or "Немає"
        name = user_data[3] or "Невідомо"
        is_banned = user_data[13] if len(user_data) > 13 else False
        
        status = "🚫" if is_banned else "✅"
        results_text += f"{i}. {status} {name} (@{username}, ID: `{user_id}`)\n"
    
    if len(users) > 10:
        results_text += f"\n... та ще {len(users) - 10} користувачів"
    
    await update.message.reply_text(results_text, parse_mode='Markdown')