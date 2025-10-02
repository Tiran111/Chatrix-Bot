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
    """Початок розсилки - СПРОЩЕНА ВЕРСІЯ"""
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

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлення для розсилки - СПРОЩЕНА ВЕРСІЯ"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    print(f"🔧 [BROADCAST] Отримано повідомлення: '{text}'")
    
    if text == "🔙 Скасувати":
        await update.message.reply_text("❌ Розсилка скасована", reply_markup=get_admin_menu())
        return
    
    # Відразу показуємо підтвердження
    total_users = db.get_users_count()
    
    keyboard = [["✅ Так, відправити", "❌ Ні, скасувати"]]
    await update.message.reply_text(
        f"📢 *Попередній перегляд повідомлення:*\n\n{text}\n\n"
        f"Кількість одержувачів: {total_users}\n"
        f"*Підтверджуєте розсилку?*",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )
    
    # Зберігаємо повідомлення для розсилки
    context.user_data['broadcast_message'] = text

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Підтвердження розсилки - СПРОЩЕНА ВЕРСІЯ"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    broadcast_message = context.user_data.get('broadcast_message')
    
    print(f"🔧 [CONFIRM_BROADCAST] Текст: '{text}', повідомлення: '{broadcast_message}'")
    
    if text == "✅ Так, відправити" and broadcast_message:
        # Отримуємо всіх користувачів
        all_users = db.get_all_users()
        total_users = len(all_users)
        sent_count = 0
        failed_count = 0
        
        print(f"🔧 [BROADCAST] Початок розсилки для {total_users} користувачів")
        
        progress_msg = await update.message.reply_text("🔄 *Розпочато розсилку...*\n\n📊 Статус: 0%", parse_mode='Markdown')
        
        for i, user_id in enumerate(all_users):
            try:
                # Пропускаємо адміна
                if user_id == ADMIN_ID:
                    continue
                    
                print(f"🔧 [BROADCAST] Відправляємо користувачу {user_id}")
                # Відправляємо повідомлення
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 *Сповіщення від адміністратора:*\n\n{broadcast_message}",
                    parse_mode='Markdown'
                )
                sent_count += 1
                print(f"✅ Відправлено користувачу {user_id}")
                
                # Оновлюємо прогрес кожні 5 користувачів або на останньому
                if i % 5 == 0 or i == total_users - 1:
                    progress = int((i + 1) / total_users * 100)
                    try:
                        await progress_msg.edit_text(
                            f"🔄 *Розсилка в процесі...*\n\n"
                            f"📊 Статус: {progress}%\n"
                            f"✅ Відправлено: {sent_count}\n"
                            f"❌ Не вдалося: {failed_count}",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        print(f"❌ Помилка оновлення прогресу: {e}")
                
                # Невелика затримка щоб не перевантажувати сервер
                time.sleep(0.2)
                
            except Exception as e:
                failed_count += 1
                print(f"❌ Помилка відправки користувачу {user_id}: {e}")
        
        # Видаляємо повідомлення про прогрес
        try:
            await progress_msg.delete()
        except:
            pass
        
        success_rate = (sent_count / total_users * 100) if total_users > 0 else 0
        
        result_text = f"""🎉 *Розсилка завершена!*

📊 *Результати:*
✅ Відправлено: {sent_count}
❌ Не вдалося: {failed_count}
📈 Успішність: {success_rate:.1f}%"""
        
        await update.message.reply_text(
            result_text,
            reply_markup=get_admin_menu(),
            parse_mode='Markdown'
        )
        
        # Очищаємо дані
        context.user_data.pop('broadcast_message', None)
    
    else:
        await update.message.reply_text("❌ Розсилка скасована", reply_markup=get_admin_menu())
        context.user_data.pop('broadcast_message', None)

async def update_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оновлення бази даних"""
    user = update.effective_user
    
    progress_msg = await update.message.reply_text("🔄 Оновлення бази даних...")
    
    # Очищення старих даних
    cleaned = db.cleanup_old_data()
    
    # Отримуємо статистику після очищення
    stats = db.get_statistics()
    total_users = db.get_users_count()
    
    await progress_msg.delete()
    
    await update.message.reply_text(
        f"✅ *База даних оновлена успішно!*\n\n"
        f"📊 *Після оновлення:*\n"
        f"👥 Користувачів: {total_users}\n"
        f"✅ Активних: {stats[2]}\n"
        f"🧹 Очищено старих даних: {'Так' if cleaned else 'Ні'}",
        parse_mode='Markdown',
        reply_markup=get_admin_menu()
    )

async def show_ban_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Керування блокуванням"""
    banned_users = db.get_banned_users()
    
    ban_text = f"""🚫 *Керування блокуванням*

📊 Статистика:
• Заблоковано користувачів: {len(banned_users)}

⚙️ Доступні дії:"""
    
    keyboard = [
        ["🔍 Список заблокованих", "🆔 Заблокувати за ID"],
        ["📧 Заблокувати за повідомленням", "✅ Розблокувати всіх"],
        ["🔙 Назад до адмін-панелі"]
    ]
    
    await update.message.reply_text(ban_text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')

async def handle_ban_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка керування блокуванням"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text == "🔍 Список заблокованих":
        await show_banned_users(update, context)
    
    elif text == "🆔 Заблокувати за ID":
        await start_ban_by_id(update, context)
    
    elif text == "📧 Заблокувати за повідомленням":
        await start_ban_by_message(update, context)
    
    elif text == "✅ Розблокувати всіх":
        await unban_all_users(update, context)

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

async def start_ban_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок блокування за ID"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_BAN_BY_ID
    await update.message.reply_text(
        "🆔 Введіть ID користувача для блокування:",
        reply_markup=get_cancel_keyboard()
    )

async def start_ban_by_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок блокування за повідомленням"""
    user = update.effective_user
    user_states[user.id] = States.ADMIN_BAN_BY_MESSAGE
    await update.message.reply_text(
        "📧 Перешліть повідомлення від користувача, якого потрібно заблокувати:",
        reply_markup=get_cancel_keyboard()
    )

async def unban_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Розблокувати всіх користувачів"""
    user = update.effective_user
    db.unban_all_users()
    await update.message.reply_text(
        "✅ Всі користувачі розблоковані!",
        reply_markup=get_admin_menu()
    )

async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати детальну статистику"""
    user = update.effective_user
    
    stats = db.get_statistics()
    male, female, total_active, goals_stats = stats
    total_users = db.get_users_count()
    banned_users = len(db.get_banned_users())
    
    # Статистика за містами (спрощено)
    stats_text = f"""📈 *Детальна статистика*

👥 *Користувачі:*
• Загалом: {total_users}
• Активних: {total_active}
• Заблокованих: {banned_users}
• Чоловіків: {male}
• Жінок: {female}

📊 *Активність:*
• Заповнених профілів: {total_active}
• Відсоток активних: {(total_active/total_users*100) if total_users > 0 else 0:.1f}%"""

    if goals_stats:
        stats_text += "\n\n🎯 *Цілі знайомств:*"
        for goal, count in goals_stats:
            percentage = (count/total_active*100) if total_active > 0 else 0
            stats_text += f"\n• {goal}: {count} ({percentage:.1f}%)"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')
    await show_admin_panel(update, context)

async def handle_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка пошуку користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_SEARCH_USER:
        return
    
    query = update.message.text
    if query == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Пошук скасовано", reply_markup=get_admin_menu())
        return
    
    # Пошук користувача за ID або ім'ям
    found_users = db.search_user(query)
    
    if not found_users:
        await update.message.reply_text(
            f"❌ Користувача '{query}' не знайдено",
            reply_markup=get_admin_menu()
        )
        return
    
    user_data = found_users[0]
    user_id = user_data[1] if len(user_data) > 1 else "Невідомо"
    user_name = user_data[3] if len(user_data) > 3 else "Невідомо"
    is_banned = user_data[13] if len(user_data) > 13 else False
    
    status = "🚫 Заблокований" if is_banned else "✅ Активний"
    
    user_info = f"""🔍 *Результати пошуку:*

👤 Ім'я: {user_name}
🆔 ID: `{user_id}`
📊 Статус: {status}

📝 Дії:"""
    
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

async def handle_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка блокування користувача"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_BAN_USER:
        return
    
    user_id = update.message.text
    if user_id == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Блокування скасовано", reply_markup=get_admin_menu())
        return
    
    try:
        user_id = int(user_id)
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
    
    user_id = update.message.text
    if user_id == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Розблокування скасовано", reply_markup=get_admin_menu())
        return
    
    try:
        user_id = int(user_id)
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

async def handle_ban_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка блокування за ID"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_BAN_BY_ID:
        return
    
    user_id = update.message.text
    if user_id == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Блокування скасовано", reply_markup=get_admin_menu())
        return
    
    try:
        user_id = int(user_id)
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

async def handle_ban_by_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка блокування за повідомленням"""
    user = update.effective_user
    if user.id != ADMIN_ID or user_states.get(user.id) != States.ADMIN_BAN_BY_MESSAGE:
        return
    
    if update.message.forward_from:
        user_id = update.message.forward_from.id
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
    else:
        await update.message.reply_text(
            "❌ Не вдалося отримати інформацію про користувача. "
            "Переконайтеся, що користувач дозволив пересилання повідомлень.",
            reply_markup=get_admin_menu()
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
                reply_markup=get_cancel_keyboard(),
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