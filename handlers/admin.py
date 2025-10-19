from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import ADMIN_ID
from handlers.notifications import notification_system
import logging
import time

logger = logging.getLogger(__name__)

async def show_admin_panel(update: Update, context: CallbackContext):
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
    
    # Оновлена клавіатура з кнопкою скидання БД
    keyboard = [
        ['📊 Статистика', '👥 Користувачі'],
        ['📢 Розсилка', '🔄 Оновити базу'],
        ['🚫 Блокування', '📈 Детальна статистика'],
        ['🗑️ Скинути БД', '🔙 Головне меню']
    ]
    
    await update.message.reply_text(
        "👑 *Адмін панель*\nОберіть дію:", 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode='Markdown'
    )

async def handle_admin_actions(update: Update, context: CallbackContext):
    """Обробка дій адміністратора"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    logger.info(f"🔧 [ADMIN] {user.first_name}: '{text}'")
    
    if text == "👑 Адмін панель" or text == "📊 Статистика":
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
    
    elif text == "🗑️ Скинути БД":
        await reset_database(update, context)
    
    elif text == "🔙 Головне меню":
        await update.message.reply_text("👋 Повертаємось до головного меню", reply_markup=get_main_menu(user.id))
    
    # Обробка кнопок з меню користувачів
    elif text == "📋 Список користувачів":
        await show_users_list(update, context)
    elif text == "🔍 Пошук користувача":
        await start_user_search(update, context)
    elif text == "🚫 Заблокувати користувача":
        await start_ban_user(update, context)
    elif text == "✅ Розблокувати користувача":
        await start_unban_user(update, context)
    elif text == "📋 Список заблокованих":
        await show_banned_users(update, context)
    elif text == "🔙 Назад до адмін-панелі":
        await show_admin_panel(update, context)

async def reset_database(update: Update, context: CallbackContext):
    """Скинути базу даних"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    try:
        await update.message.reply_text("🔄 Скидання бази даних... Це може зайняти кілька секунд.")
        
        # Використовуємо метод з models.py
        success = db.reset_database()
        
        if success:
            await update.message.reply_text("✅ База даних скинута та перестворена!\n\n📝 Тепер потрібно заново заповнити профілі.")
            # Показуємо оновлену статистику
            await show_admin_panel(update, context)
        else:
            await update.message.reply_text("❌ Помилка скидання БД")
        
    except Exception as e:
        logger.error(f"❌ Помилка скидання БД: {e}")
        await update.message.reply_text("❌ Помилка скидання БД")

async def show_users_management(update: Update, context: CallbackContext):
    """Керування користувачами"""
    user = update.effective_user
    
    users_text = f"""👥 *Керування користувачами*

📊 Статистика:
• Загалом: {db.get_users_count()}
• Активних: {db.get_statistics()[2]}

⚙️ Доступні дії:"""
    
    keyboard = [
        ["📋 Список користувачів", "🔍 Пошук користувача"],
        ["🚫 Заблокувати користувача", "✅ Розблокувати користувача"],
        ["📋 Список заблокованих", "🔙 Назад до адмін-панелі"]
    ]
    
    await update.message.reply_text(
        users_text, 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode='Markdown'
    )

async def show_users_list(update: Update, context: CallbackContext):
    """Показати список користувачів"""
    user = update.effective_user
    users = db.get_all_active_users(user.id)
    
    if not users:
        await update.message.reply_text("😔 Користувачів не знайдено")
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

async def start_user_search(update: Update, context: CallbackContext):
    """Початок пошуку користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_SEARCH_USER
    await update.message.reply_text(
        "🔍 Введіть ID користувача або ім'я для пошуку:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def handle_user_search(update: Update, context: CallbackContext):
    """Обробка пошуку користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_SEARCH_USER:
        return
    
    search_query = update.message.text
    
    if search_query == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Пошук скасовано")
        return
    
    # Виконуємо пошук
    results = db.search_user(search_query)
    
    if results:
        search_text = f"🔍 *Результати пошуку для '{search_query}':*\n\n"
        for i, user_data in enumerate(results[:5], 1):
            user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
            user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
            is_banned = user_data[13] if len(user_data) > 13 else False
            
            status = "🚫" if is_banned else "✅"
            search_text += f"{i}. {status} {user_name} (ID: `{user_id}`)\n"
        
        if len(results) > 5:
            search_text += f"\n... та ще {len(results) - 5} користувачів"
        
        await update.message.reply_text(search_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Користувачів не знайдено")
    
    user_states[user.id] = States.START

async def start_broadcast(update: Update, context: CallbackContext):
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

async def handle_broadcast_message(update: Update, context: CallbackContext):
    """Обробка повідомлення для розсилки з сповіщенням"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.BROADCAST:
        return
    
    message_text = update.message.text
    
    if message_text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Розсилка скасована")
        return
    
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Немає користувачів для розсилки")
        user_states[user.id] = States.START
        return
    
    await update.message.reply_text(f"🔄 Розсилка повідомлення {len(users)} користувачам...")
    
    success_count = 0
    fail_count = 0
    
    for user_data in users:
        try:
            # Використовуємо функцію сповіщення для розсилки
            success = await notification_system.notify_broadcast_message(
                context, 
                user_data[1],  # telegram_id
                message_text
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                
            time.sleep(0.1)  # Затримка щоб не перевищити ліміти
        except Exception as e:
            logger.error(f"❌ Помилка відправки для {user_data[1]}: {e}")
            fail_count += 1
    
    # Сповіщаємо адміна про результат
    await update.message.reply_text(
        f"📊 *Результат розсилки:*\n\n"
        f"✅ Відправлено: {success_count}\n"
        f"❌ Не вдалося: {fail_count}",
        parse_mode='Markdown'
    )
    
    # Відправляємо сповіщення про успішну розсилку
    await notification_system.notify_broadcast_complete(context, user.id, success_count, len(users))
    
    user_states[user.id] = States.START

async def update_database(update: Update, context: CallbackContext):
    """Оновлення бази даних"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("🔄 Оновлення бази даних...")
    
    # Очищення старих даних
    db.cleanup_old_data()
    
    await update.message.reply_text("✅ База даних оновлена успішно!")

async def show_ban_management(update: Update, context: CallbackContext):
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

async def show_banned_users(update: Update, context: CallbackContext):
    """Показати заблокованих користувачів"""
    banned_users = db.get_banned_users()
    
    if not banned_users:
        await update.message.reply_text("😊 Немає заблокованих користувачів")
        return
    
    ban_text = "🚫 *Заблоковані користувачі:*\n\n"
    for i, user_data in enumerate(banned_users, 1):
        user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
        user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
        ban_text += f"{i}. {user_name} (ID: `{user_id}`)\n"
    
    await update.message.reply_text(ban_text, parse_mode='Markdown')

async def show_detailed_stats(update: Update, context: CallbackContext):
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

async def start_ban_user(update: Update, context: CallbackContext):
    """Початок блокування користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_BAN_USER
    await update.message.reply_text(
        "🚫 Введіть ID користувача для блокування:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def start_unban_user(update: Update, context: CallbackContext):
    """Початок розблокування користувача"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_UNBAN_USER
    await update.message.reply_text(
        "✅ Введіть ID користувача для розблокування:",
        reply_markup=ReplyKeyboardMarkup([['🔙 Скасувати']], resize_keyboard=True)
    )

async def handle_ban_user(update: Update, context: CallbackContext):
    """Обробка блокування користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_BAN_USER:
        return
    
    user_id_text = update.message.text
    
    if user_id_text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Блокування скасовано")
        return
    
    try:
        user_id = int(user_id_text)
        if db.ban_user(user_id):
            await update.message.reply_text(f"✅ Користувач `{user_id}` заблокований", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Користувача `{user_id}` не знайдено", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ Введіть коректний ID користувача")
    
    user_states[user.id] = States.START

async def handle_unban_user(update: Update, context: CallbackContext):
    """Обробка розблокування користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_UNBAN_USER:
        return
    
    user_id_text = update.message.text
    
    if user_id_text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Розблокування скасовано")
        return
    
    try:
        user_id = int(user_id_text)
        if db.unban_user(user_id):
            await update.message.reply_text(f"✅ Користувач `{user_id}` розблокований", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Користувача `{user_id}` не знайдено або вже розблоковано", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ Введіть коректний ID користувача")
    
    user_states[user.id] = States.START