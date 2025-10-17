import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def search_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук анкет"""
    try:
        from database.models import db
        from utils.states import user_states, States
        
        user = update.effective_user
        user_states[user.id] = States.SEARCH
        
        # Отримуємо анкети для пошуку
        users = db.get_users_for_search(user.id)
        
        if not users:
            await update.message.reply_text("😔 Наразі немає анкет для перегляду.")
            return
        
        context.user_data['search_users'] = users
        context.user_data['current_index'] = 0
        
        # Показуємо першу анкету
        await show_user_profile(update, context, users[0], "💕 Режим пошуку")
        
    except Exception as e:
        logger.error(f"❌ Помилка пошуку анкет: {e}")
        await update.message.reply_text("❌ Помилка пошуку анкет.")

async def search_by_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук анкет по місту"""
    try:
        from utils.states import user_states, States
        
        user = update.effective_user
        user_states[user.id] = States.SEARCH_BY_CITY
        
        await update.message.reply_text(
            "🏙️ Введіть назву міста для пошуку:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Скасувати", callback_data="cancel_search")]])
        )
        
        context.user_data['waiting_for_city'] = True
        
    except Exception as e:
        logger.error(f"❌ Помилка пошуку по місту: {e}")
        await update.message.reply_text("❌ Помилка пошуку по місту.")

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати наступну анкету"""
    try:
        current_index = context.user_data.get('current_index', 0)
        search_users = context.user_data.get('search_users', [])
        
        if current_index + 1 >= len(search_users):
            await update.message.reply_text("🎉 Ви переглянули всі анкети!")
            return
        
        context.user_data['current_index'] = current_index + 1
        next_user = search_users[current_index + 1]
        
        await show_user_profile(update, context, next_user, "💕 Режим пошуку")
        
    except Exception as e:
        logger.error(f"❌ Помилка показу наступної анкети: {e}")
        await update.message.reply_text("❌ Помилка завантаження анкети.")

async def show_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, caption=""):
    """Показати анкету користувача"""
    try:
        user_id = update.effective_user.id
        
        profile_text = f"""
👤 *Анкета*

🆔 ID: `{user_data['user_id']}`
👤 Ім'я: {user_data['name']}
📅 Вік: {user_data['age']}
🚻 Стать: {user_data['gender']}
🎯 Шукає: {user_data['seeking_gender']}
🏙️ Місто: {user_data['city']}
💬 Про себе: {user_data['bio']}

{caption}
"""
        
        keyboard = [
            [InlineKeyboardButton("❤️ Вподобати", callback_data=f"like_{user_data['user_id']}")],
            [InlineKeyboardButton("➡️ Далі", callback_data="next_profile")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if 'message' in update and update.message:
            await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
        elif 'callback_query' in update and update.callback_query:
            await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"❌ Помилка показу профілю: {e}")
        if 'message' in update and update.message:
            await update.message.reply_text("❌ Помилка завантаження анкети.")

async def show_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати топ користувачів"""
    try:
        keyboard = [
            [InlineKeyboardButton("👨 Топ чоловіків", callback_data="top_male")],
            [InlineKeyboardButton("👩 Топ жінок", callback_data="top_female")],
            [InlineKeyboardButton("🏆 Загальний топ", callback_data="top_all")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏆 *Топ користувачів*\n\nОберіть категорію:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка показу топу: {e}")
        await update.message.reply_text("❌ Помилка завантаження топу.")

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати матчі"""
    try:
        from database.models import db
        
        user_id = update.effective_user.id
        matches = db.get_matches(user_id)
        
        if not matches:
            await update.message.reply_text("💔 У вас ще немає матчів.")
            return
        
        matches_text = "💌 *Ваші матчі:*\n\n"
        
        for match in matches:
            matches_text += f"👤 {match['name']} (ID: `{match['user_id']}`)\n"
        
        await update.message.reply_text(matches_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Помилка показу матчів: {e}")
        await update.message.reply_text("❌ Помилка завантаження матчів.")

async def show_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати хто вас лайкнув"""
    try:
        from database.models import db
        
        user_id = update.effective_user.id
        likes = db.get_likes(user_id)
        
        if not likes:
            await update.message.reply_text("💔 Вас ще ніхто не вподобав.")
            return
        
        likes_text = "❤️ *Вас вподобали:*\n\n"
        
        for like in likes:
            likes_text += f"👤 {like['name']} (ID: `{like['user_id']}`)\n"
            keyboard = [[InlineKeyboardButton("❤️ Вподобати взаємно", callback_data=f"like_back_{like['user_id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"👤 {like['name']} вподобав(ла) вашу анкету!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка показу лайків: {e}")
        await update.message.reply_text("❌ Помилка завантаження лайків.")

async def handle_top_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору топу"""
    try:
        from database.models import db
        
        text = update.message.text
        user_id = update.effective_user.id
        
        if text == "👨 Топ чоловіків":
            top_users = db.get_top_users(gender="Чоловік")
            title = "👨 Топ чоловіків"
        elif text == "👩 Топ жінок":
            top_users = db.get_top_users(gender="Жінка")
            title = "👩 Топ жінок"
        else:
            top_users = db.get_top_users()
            title = "🏆 Загальний топ"
        
        if not top_users:
            await update.message.reply_text("😔 Наразі немає даних для топу.")
            return
        
        top_text = f"{title}:\n\n"
        
        for i, user in enumerate(top_users[:10], 1):
            top_text += f"{i}. {user['name']} - {user['likes_count']} ❤️\n"
        
        await update.message.reply_text(top_text)
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки топу: {e}")
        await update.message.reply_text("❌ Помилка завантаження топу.")

# CALLBACK HANDLERS - ДОДАНІ ВІДСУТНІ ФУНКЦІЇ
async def handle_like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка лайку з callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        liked_user_id = int(callback_data.split('_')[1])
        
        from database.models import db
        user_id = query.from_user.id
        
        # Додаємо лайк
        db.add_like(user_id, liked_user_id)
        
        # Перевіряємо чи це взаємний лайк
        if db.has_like(liked_user_id, user_id):
            # Це матч!
            await query.edit_message_text(
                "🎉 У вас взаємний лайк! Це матч!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💌 Написати повідомлення", callback_data=f"message_{liked_user_id}")],
                    [InlineKeyboardButton("➡️ Продовжити пошук", callback_data="next_profile")]
                ])
            )
        else:
            # Звичайний лайк
            await query.edit_message_text(
                "❤️ Ви вподобали цю анкету!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➡️ Далі", callback_data="next_profile")]
                ])
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Помилка при обробці лайку")
        except:
            pass

async def handle_next_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопки 'Далі' з callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Отримуємо наступний профіль
        current_index = context.user_data.get('current_index', 0)
        search_users = context.user_data.get('search_users', [])
        
        if current_index + 1 < len(search_users):
            context.user_data['current_index'] = current_index + 1
            next_user = search_users[current_index + 1]
            await show_user_profile(update, context, next_user, "💕 Режим пошуку")
        else:
            await query.edit_message_text("🎉 Ви переглянули всі анкети!")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки наступного профілю: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Помилка завантаження наступної анкети")
        except:
            pass

async def handle_like_back(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Обробка взаємного лайку"""
    try:
        query = update.callback_query
        await query.answer()
        
        if user_id is None:
            callback_data = query.data
            user_id = int(callback_data.split('_')[2])
        
        from database.models import db
        current_user_id = query.from_user.id
        
        # Додаємо взаємний лайк
        db.add_like(current_user_id, user_id)
        
        # Перевіряємо на матч
        if db.has_like(user_id, current_user_id):
            await query.edit_message_text(
                "🎉 Тепер у вас матч!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💌 Написати повідомлення", callback_data=f"message_{user_id}")],
                    [InlineKeyboardButton("🔙 До меню", callback_data="back_to_menu")]
                ])
            )
        else:
            await query.edit_message_text("❤️ Ви вподобали цю анкету!")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки взаємного лайку: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Помилка при обробці лайку")
        except:
            pass

# Додаткові функції для адміністрації
async def handle_admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук користувачів для адміністратора"""
    try:
        from database.models import db
        
        user_id = update.effective_user.id
        from config import ADMIN_ID
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ заборонено.")
            return
        
        search_query = update.message.text
        users = db.search_users(search_query)
        
        if not users:
            await update.message.reply_text("😔 Користувачів не знайдено.")
            return
        
        users_text = "👥 *Знайдені користувачі:*\n\n"
        
        for user in users[:10]:  # Обмежуємо до 10 користувачів
            users_text += f"🆔 {user['user_id']} | 👤 {user['name']} | 📅 {user['age']}\n"
        
        await update.message.reply_text(users_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Помилка адмін пошуку: {e}")
        await update.message.reply_text("❌ Помилка пошуку.")

async def handle_user_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка скарг на користувачів"""
    try:
        from database.models import db
        
        user_id = update.effective_user.id
        reported_user_id = context.user_data.get('reported_user_id')
        
        if not reported_user_id:
            await update.message.reply_text("❌ Не вдалося ідентифікувати користувача для скарги.")
            return
        
        report_text = update.message.text
        db.add_report(user_id, reported_user_id, report_text)
        
        await update.message.reply_text(
            "✅ Скаргу відправлено адміністрації. Дякуємо за звернення!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 До пошуку", callback_data="back_to_search")]])
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки скарги: {e}")
        await update.message.reply_text("❌ Помилка відправки скарги.")