from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
import logging
from datetime import datetime
from database.models import db

logger = logging.getLogger(__name__)

# ID адміністратора (замініть на ваш)
ADMIN_ID = 8330660486  # Ваш Telegram ID

async def admin_panel(update: Update, context: CallbackContext):
    """Панель адміністратора"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас немає доступу до цієї команди.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Користувачі", callback_data="admin_users")],
        [InlineKeyboardButton("🚫 Заблоковані", callback_data="admin_banned")],
        [InlineKeyboardButton("🔄 Оновити БД", callback_data="admin_update_db")],
        [InlineKeyboardButton("🗑️ Скинути БД", callback_data="admin_reset_db")],
        [InlineKeyboardButton("🔍 Пошук", callback_data="admin_search")],
        [InlineKeyboardButton("🔄 Розблокувати всіх", callback_data="admin_unban_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💻 *Панель адміністратора*\n\n"
        "Оберіть дію:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_button_handler(update: Update, context: CallbackContext):
    """Обробник кнопок адмін-панелі"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.edit_message_text("❌ У вас немає доступу.")
        return
    
    data = query.data
    
    if data == "admin_stats":
        await show_statistics(query, context)
    elif data == "admin_users":
        await show_users_list(query, context)
    elif data == "admin_banned":
        await show_banned_users(query, context)
    elif data == "admin_update_db":
        await update_database(query, context)
    elif data == "admin_reset_db":
        await confirm_reset_database(query, context)
    elif data == "admin_search":
        await start_search(query, context)
    elif data == "admin_unban_all":
        await unban_all_users(query, context)
    elif data.startswith("user_detail_"):
        user_id = int(data.split("_")[2])
        await show_user_detail(query, context, user_id)
    elif data.startswith("ban_user_"):
        user_id = int(data.split("_")[2])
        await ban_user_action(query, context, user_id)
    elif data.startswith("unban_user_"):
        user_id = int(data.split("_")[2])
        await unban_user_action(query, context, user_id)
    elif data == "confirm_reset":
        await reset_database(query, context)
    elif data == "cancel_reset":
        await query.edit_message_text("❌ Скидання БД скасовано.")

async def show_statistics(query, context):
    """Показати статистику"""
    male, female, total_active, goals_stats = db.get_statistics()
    total_users = db.get_users_count()
    
    stats_text = f"""📊 *Статистика бота*

👥 *Користувачі:*
• Всього: {total_users}
• Активних: {total_active}
• Чоловіків: {male}
• Жінок: {female}

🎯 *Цілі знайомств:*
"""
    
    for goal, count in goals_stats:
        if goal:
            stats_text += f"• {goal}: {count}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_users_list(query, context, page=0):
    """Показати список користувачів"""
    users = db.get_all_active_users()
    users_per_page = 10
    total_pages = (len(users) + users_per_page - 1) // users_per_page
    
    if not users:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Користувачів не знайдено.", reply_markup=reply_markup)
        return
    
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    page_users = users[start_idx:end_idx]
    
    text = f"👥 *Список користувачів* (стор. {page + 1}/{total_pages})\n\n"
    
    keyboard = []
    for user in page_users:
        user_info = f"{user[3]} (ID: {user[1]})"
        if user[2]:  # username
            user_info += f" @{user[2]}"
        
        keyboard.append([InlineKeyboardButton(
            user_info, 
            callback_data=f"user_detail_{user[1]}"
        )])
    
    # Навігація по сторінкам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Попередня", callback_data=f"users_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Наступна ➡️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_banned_users(query, context):
    """Показати заблокованих користувачів"""
    users = db.get_banned_users()
    
    if not users:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("✅ Немає заблокованих користувачів.", reply_markup=reply_markup)
        return
    
    text = "🚫 *Заблоковані користувачі:*\n\n"
    
    keyboard = []
    for user in users:
        user_info = f"{user[3]} (ID: {user[1]})"
        if user[2]:
            user_info += f" @{user[2]}"
        
        keyboard.append([InlineKeyboardButton(
            f"🔓 {user_info}", 
            callback_data=f"unban_user_{user[1]}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_detail(query, context, user_id):
    """Показати детальну інформацію про користувача"""
    user = db.get_user_by_id(user_id)
    
    if not user:
        await query.answer("❌ Користувача не знайдено.", show_alert=True)
        return
    
    text = f"""👤 *Детальна інформація*

🆔 ID: `{user['telegram_id']}`
👤 Ім'я: {user['first_name']}
🔗 Username: @{user['username'] if user['username'] else 'Немає'}
👁️ Стать: {user['gender'] if user['gender'] else 'Не вказано'}
🎂 Вік: {user['age'] if user['age'] else 'Не вказано'}
🏙️ Місто: {user['city'] if user['city'] else 'Не вказано'}
🎯 Ціль: {user['goal'] if user['goal'] else 'Не вказано'}
❤️ Лайків: {user['likes_count']}
⭐ Рейтинг: {user['rating']}
📸 Фото: {'✅' if user['has_photo'] else '❌'}
🚫 Статус: {'Заблокований' if user['is_banned'] else 'Активний'}
📅 Реєстрація: {user['created_at']}
🕐 Остання активність: {user['last_active'] if user['last_active'] else 'Не вказано'}
"""
    
    keyboard = []
    if not user['is_banned']:
        keyboard.append([InlineKeyboardButton("🚫 Заблокувати", callback_data=f"ban_user_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🔓 Розблокувати", callback_data=f"unban_user_{user_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_users")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def ban_user_action(query, context, user_id):
    """Заблокувати користувача"""
    if db.ban_user(user_id):
        await query.answer("✅ Користувача заблоковано!", show_alert=True)
        await show_user_detail(query, context, user_id)
    else:
        await query.answer("❌ Помилка блокування!", show_alert=True)

async def unban_user_action(query, context, user_id):
    """Розблокувати користувача"""
    if db.unban_user(user_id):
        await query.answer("✅ Користувача розблоковано!", show_alert=True)
        if query.data.startswith("unban_user_"):
            # Оновлюємо список заблокованих
            await show_banned_users(query, context)
        else:
            await show_user_detail(query, context, user_id)
    else:
        await query.answer("❌ Помилка розблокування!", show_alert=True)

async def unban_all_users(query, context):
    """Розблокувати всіх користувачів"""
    if db.unban_all_users():
        await query.answer("✅ Всі користувачі розблоковані!", show_alert=True)
        await admin_panel(update=Update(update_id=query.update_id, message=query.message), context=context)
    else:
        await query.answer("❌ Помилка розблокування!", show_alert=True)

async def update_database(query, context):
    """Оновлення бази даних"""
    await query.edit_message_text("🔄 Оновлення бази даних...")
    
    # Очищення старих даних з отриманням результатів
    result = db.cleanup_old_data()
    
    if result:
        stats_text = f"""✅ *База даних оновлена успішно!*

🗑️ *Видалено:*
• Неповних профілів: {result['deleted_incomplete']}
• Старих лайків: {result['deleted_likes']}

📈 *Оновлено:*
• Рейтингів користувачів: {result['updated_ratings']}"""

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Помилка оновлення бази даних", reply_markup=reply_markup)

async def confirm_reset_database(query, context):
    """Підтвердження скидання бази даних"""
    keyboard = [
        [InlineKeyboardButton("✅ Так, скинути", callback_data="confirm_reset")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel_reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚠️ *УВАГА!*\n\n"
        "Ви дійсно хочете повністю скинути базу даних?\n"
        "Ця дія:\n"
        "• Видалить ВСІХ користувачів\n"
        "• Видалить ВСІ лайки та матчі\n"
        "• Видалить ВСІ фото\n"
        "• Створить нову чисту базу даних\n\n"
        "Цю дію НЕМОЖЛИВО скасувати!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def reset_database(query, context):
    """Скидання бази даних"""
    await query.edit_message_text("🔄 Скидання бази даних...")
    
    if db.reset_database():
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("✅ База даних успішно скинута!", reply_markup=reply_markup)
    else:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Помилка скидання бази даних!", reply_markup=reply_markup)

async def start_search(query, context):
    """Початок пошуку користувача"""
    context.user_data['awaiting_search'] = True
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔍 *Пошук користувача*\n\n"
        "Введіть ID користувача або ім'я для пошуку:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_search(update: Update, context: CallbackContext):
    """Обробник пошукового запиту"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    if not context.user_data.get('awaiting_search'):
        return
    
    search_query = update.message.text.strip()
    context.user_data['awaiting_search'] = False
    
    results = db.search_user(search_query)
    
    if not results:
        await update.message.reply_text("❌ Користувачів не знайдено.")
        await admin_panel(update, context)
        return
    
    if len(results) == 1:
        # Якщо знайдено одного користувача - показуємо деталі
        user_id = results[0][1]
        await show_user_detail_simple(update, context, user_id)
    else:
        # Якщо знайдено кілька користувачів - показуємо список
        text = f"🔍 *Результати пошуку для '{search_query}':*\n\n"
        
        keyboard = []
        for user in results[:10]:  # Обмежуємо до 10 результатів
            user_info = f"{user[3]} (ID: {user[1]})"
            if user[2]:
                user_info += f" @{user[2]}"
            
            keyboard.append([InlineKeyboardButton(
                user_info, 
                callback_data=f"user_detail_{user[1]}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_detail_simple(update: Update, context: CallbackContext, user_id: int):
    """Показати деталі користувача (проста версія для пошуку)"""
    user = db.get_user_by_id(user_id)
    
    if not user:
        await update.message.reply_text("❌ Користувача не знайдено.")
        return
    
    text = f"""👤 *Результат пошуку*

🆔 ID: `{user['telegram_id']}`
👤 Ім'я: {user['first_name']}
🔗 Username: @{user['username'] if user['username'] else 'Немає'}
👁️ Стать: {user['gender'] if user['gender'] else 'Не вказано'}
🎂 Вік: {user['age'] if user['age'] else 'Не вказано'}
🏙️ Місто: {user['city'] if user['city'] else 'Не вказано'}
🎯 Ціль: {user['goal'] if user['goal'] else 'Не вказано'}
❤️ Лайків: {user['likes_count']}
⭐ Рейтинг: {user['rating']}
📸 Фото: {'✅' if user['has_photo'] else '❌'}
🚫 Статус: {'Заблокований' if user['is_banned'] else 'Активний'}
"""
    
    keyboard = []
    if not user['is_banned']:
        keyboard.append([InlineKeyboardButton("🚫 Заблокувати", callback_data=f"ban_user_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🔓 Розблокувати", callback_data=f"unban_user_{user_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Обробники для навігації
async def handle_navigation(update: Update, context: CallbackContext):
    """Обробник навігації по сторінках"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("users_page_"):
        page = int(data.split("_")[2])
        await show_users_list(query, context, page)
    elif data == "admin_back":
        await admin_panel(update=Update(update_id=query.update_id, message=query.message), context=context)

def setup_admin_handlers(application):
    """Налаштування обробників для адмін-панелі"""
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_navigation, pattern="^(users_page_|admin_back)"))
    application.add_handler(CallbackQueryHandler(ban_user_action, pattern="^ban_user_"))
    application.add_handler(CallbackQueryHandler(unban_user_action, pattern="^unban_user_"))
    application.add_handler(CallbackQueryHandler(show_user_detail, pattern="^user_detail_"))
    application.add_handler(CallbackQueryHandler(confirm_reset_database, pattern="^admin_reset_db"))
    application.add_handler(CallbackQueryHandler(reset_database, pattern="^confirm_reset"))
    application.add_handler(CallbackQueryHandler(cancel_reset_database, pattern="^cancel_reset"))
    
    # Обробник текстового вводу для пошуку
    application.add_handler(CallbackQueryHandler(start_search, pattern="^admin_search$"))
    
    # Додаємо обробник повідомлень для пошуку
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))