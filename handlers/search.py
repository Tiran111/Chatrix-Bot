from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
from config import ADMIN_ID
from handlers.notifications import notification_system
import logging

logger = logging.getLogger(__name__)

def format_profile_text(user_data, title=""):
    """Форматування тексту профілю з рейтингом"""
    try:
        if isinstance(user_data, dict):
            gender_display = "👨 Чоловік" if user_data.get('gender') == 'male' else "👩 Жінка"
            rating = user_data.get('rating', 5.0)
            profile_text = f"""👤 {title}

*Ім'я:* {user_data.get('first_name', 'Не вказано')}
*Вік:* {user_data.get('age', 'Не вказано')} років
*Стать:* {gender_display}
*Місто:* {user_data.get('city', 'Не вказано')}
*Ціль:* {user_data.get('goal', 'Не вказано')}
*⭐ Рейтинг:* {rating:.1f}/10.0

*Про себе:*
{user_data.get('bio', 'Не вказано')}"""
        else:
            gender_display = "👨 Чоловік" if user_data[5] == 'male' else "👩 Жінка"
            profile_text = f"""👤 {title}

*Ім'я:* {user_data[3] if len(user_data) > 3 and user_data[3] else 'Користувач'}
*Вік:* {user_data[4]} років
*Стать:* {gender_display}
*Місто:* {user_data[6]}
*Ціль:* {user_data[8]}
*⭐ Рейтинг:* 5.0/10.0

*Про себе:*
{user_data[9] if user_data[9] else "Не вказано"}"""
        
        return profile_text
    except Exception as e:
        logger.error(f"❌ Помилка форматування профілю: {e}")
        return f"❌ Помилка завантаження профілю"

async def search_profiles(update: Update, context: CallbackContext):
    """Пошук анкет"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        user_profile, is_complete = db.get_user_profile(user.id)
        
        if not is_complete:
            await update.message.reply_text("❌ Спочатку заповніть профіль!", reply_markup=get_main_menu(user.id))
            return
        
        main_photo = db.get_main_photo(user.id)
        if not main_photo:
            await update.message.reply_text(
                "❌ Додайте головне фото до профілю, щоб шукати анкети!",
                reply_markup=get_main_menu(user.id)
            )
            return
        
        await update.message.reply_text("🔍 Шукаю анкети...")
        
        random_user = db.get_random_user(user.id)
        
        if random_user:
            logger.info(f"🔍 [SEARCH] Знайдено користувача: {random_user.get('telegram_id') if isinstance(random_user, dict) else random_user[1]}")
            
            # Додаємо запис про перегляд
            target_id = random_user.get('telegram_id') if isinstance(random_user, dict) else random_user[1]
            db.add_profile_view(user.id, target_id)
            
            await show_user_profile(update, context, random_user, "💕 Знайдені анкети")
            context.user_data['search_users'] = [random_user]
            context.user_data['current_index'] = 0
            context.user_data['search_type'] = 'random'
        else:
            await update.message.reply_text(
                "😔 Наразі немає анкет для перегляду\n\n"
                "💡 *Можливі причини:*\n"
                "• Не залишилося анкет за вашими критеріями\n"
                "• Всі анкети вже переглянуті\n"
                "• Спробуйте змінити критерії пошуку",
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка пошуку: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def search_by_city(update: Update, context: CallbackContext):
    """Пошук за містом"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        user_data, is_complete = db.get_user_profile(user.id)
        
        if not is_complete:
            await update.message.reply_text("❌ Спочатку заповніть профіль!", reply_markup=get_main_menu(user.id))
            return
        
        context.user_data['waiting_for_city'] = True
        await update.message.reply_text("🏙️ Введіть назву міста для пошуку:")
        
    except Exception as e:
        logger.error(f"❌ Помилка пошуку за містом: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def show_user_profile(update: Update, context: CallbackContext, user_data, title=""):
    """Показати профіль користувача"""
    user = update.effective_user
    
    try:
        current_user_data = db.get_user(user.id)
        if current_user_data and current_user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        profile_text = format_profile_text(user_data, title)
        
        if isinstance(user_data, dict):
            telegram_id = user_data.get('telegram_id')
        else:
            telegram_id = user_data[1]
        
        context.user_data['current_profile_id'] = telegram_id
        
        # ДОДАЄМО ПЕРЕГЛЯД ПРОФІЛЮ (тільки якщо це не той самий користувач)
        if telegram_id and telegram_id != user.id:
            success = db.add_profile_view(user.id, telegram_id)
            if success:
                logger.info(f"👀 Додано перегляд профілю: {user.id} -> {telegram_id}")
            else:
                logger.error(f"❌ Не вдалося додати перегляд: {user.id} -> {telegram_id}")
        
        main_photo = db.get_main_photo(telegram_id)
        
        # Зберігаємо поточний профіль для лайку
        context.user_data['current_profile_for_like'] = telegram_id
        
        if main_photo:
            await update.message.reply_photo(
                photo=main_photo, 
                caption=profile_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                profile_text,
                parse_mode='Markdown'
            )
        
        # Показуємо меню з кнопками лайку та далі
        keyboard = [
            ['❤️ Лайк', '➡️ Далі'],
            ['🔙 Меню']
        ]
        await update.message.reply_text(
            "Оберіть дію:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
            
    except Exception as e:
        logger.error(f"❌ Помилка відправки профілю: {e}")
        await update.message.reply_text(
            "❌ Помилка завантаження профілю. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def handle_like(update: Update, context: CallbackContext):
    """Обробка лайку з будь-якого місця (пошук, топ, перегляди)"""
    try:
        user = update.effective_user
        
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        # Отримуємо ID користувача з контексту
        target_user_id = context.user_data.get('current_profile_for_like')
        
        if not target_user_id:
            await update.message.reply_text("❌ Не знайдено профіль для лайку")
            return
        
        logger.info(f"🔍 [LIKE] Користувач {user.id} лайкає {target_user_id}")
        
        # Додаємо лайк з перевіркою обмежень
        success, message = db.add_like(user.id, target_user_id)
        
        logger.info(f"🔍 [LIKE RESULT] Успіх: {success}, Повідомлення: {message}")
        
        if success:
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(target_user_id, user.id)
            logger.info(f"🔍 [LIKE MUTUAL] Взаємний: {is_mutual}")
            
            if is_mutual:
                # Відправляємо сповіщення про матч
                await notification_system.notify_new_match(context, user.id, target_user_id)
                
                # Отримуємо дані користувача для кнопки переходу в Telegram
                matched_user = db.get_user(target_user_id)
                if matched_user:
                    username = matched_user.get('username')
                    if username:
                        await update.message.reply_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            f"💬 *Тепер ви можете почати спілкування з {matched_user['first_name']}!*\n"
                            f"Username: @{username}",
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            f"ℹ️ *У {matched_user['first_name']} немає username*",
                            parse_mode='Markdown'
                        )
                else:
                    await update.message.reply_text("💕 У вас матч! Ви вподобали один одного!")
            else:
                # Відправляємо сповіщення про лайк
                await notification_system.notify_new_like(context, user.id, target_user_id)
                await update.message.reply_text(f"❤️ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка при обробці лайку.")

async def show_next_profile(update: Update, context: CallbackContext):
    """Наступний профіль"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        search_users = context.user_data.get('search_users', [])
        current_index = context.user_data.get('current_index', 0)
        search_type = context.user_data.get('search_type', 'random')
        
        if not search_users:
            await search_profiles(update, context)
            return
        
        # Якщо це пошук за містом, шукаємо наступного користувача
        if search_type == 'city':
            if current_index < len(search_users) - 1:
                current_index += 1
                context.user_data['current_index'] = current_index
                user_data = search_users[current_index]
                
                # Безпечне отримання ID користувача
                if isinstance(user_data, dict):
                    user_id = user_data.get('telegram_id')
                else:
                    user_id = user_data[1] if len(user_data) > 1 else None
                
                if user_id:
                    db.add_profile_view(user.id, user_id)
                
                await show_user_profile(update, context, user_data, "🏙️ Знайдені анкети")
            else:
                await update.message.reply_text("✅ Це остання анкета в цьому місті", reply_markup=get_main_menu(user.id))
        else:
            # Для випадкового пошуку - шукаємо нову анкету
            random_user = db.get_random_user(user.id)
            if random_user:
                # Безпечне отримання ID користувача
                if isinstance(random_user, dict):
                    user_id = random_user.get('telegram_id')
                else:
                    user_id = random_user[1] if len(random_user) > 1 else None
                
                if user_id:
                    db.add_profile_view(user.id, user_id)
                
                await show_user_profile(update, context, random_user, "💕 Знайдені анкети")
                context.user_data['search_users'] = [random_user]
                context.user_data['current_index'] = 0
            else:
                await update.message.reply_text(
                    "😔 Більше немає анкет для перегляду\n\n"
                    "💡 Спробуйте:\n"
                    "• Змінити критерії пошуку\n"
                    "• Пошукати за іншим містом\n"
                    "• Зачекати поки з'являться нові користувачі",
                    reply_markup=get_main_menu(user.id)
                )
                
    except Exception as e:
        logger.error(f"❌ Помилка наступного профілю: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def show_top_users(update: Update, context: CallbackContext):
    """Показати вибір топу"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        keyboard = [
            ['👨 Топ чоловіків', '👩 Топ жінок'],
            ['🏆 Загальний топ', '🔙 Меню']
        ]
        
        await update.message.reply_text(
            "🏆 Оберіть категорію для перегляду топу:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка показу топу: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def show_matches(update: Update, context: CallbackContext):
    """Мої матчі"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        matches = db.get_user_matches(user.id)
        
        if matches:
            await update.message.reply_text(f"💌 *Ваші матчі ({len(matches)}):*", parse_mode='Markdown')
            
            for match in matches:
                try:
                    # Визначаємо ID матчу
                    if isinstance(match, dict):
                        match_id = match.get('telegram_id')
                    else:
                        match_id = match[1] if len(match) > 1 else None
                    
                    if not match_id:
                        continue
                    
                    profile_text = format_profile_text(match, "💕 МАТЧ!")
                    main_photo = db.get_main_photo(match_id)
                    
                    # Отримуємо username
                    matched_user = db.get_user(match_id)
                    username = matched_user.get('username') if matched_user else None
                    
                    if main_photo:
                        caption = profile_text
                        if username:
                            caption += f"\n\n💬 Написати: @{username}"
                        else:
                            caption += "\n\nℹ️ *У цього користувача немає username*"
                        
                        await update.message.reply_photo(
                            photo=main_photo,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                    else:
                        text = profile_text
                        if username:
                            text += f"\n\n💬 Написати: @{username}"
                        else:
                            text += "\n\nℹ️ *У цього користувача немає username*"
                        
                        await update.message.reply_text(
                            text,
                            parse_mode='Markdown'
                        )
                        
                except Exception as e:
                    logger.error(f"❌ Помилка обробки матчу: {e}")
                    continue
                    
        else:
            await update.message.reply_text(
                "😔 У вас ще немає матчів\n\n"
                "💡 *Порада:* Ставте лайки іншим користувачам, щоб отримувати взаємність!",
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка показу матчів: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка завантаження матчів. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def show_likes(update: Update, context: CallbackContext):
    """Показати хто мене лайкнув"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        likers = db.get_user_likers(user.id)
        
        if likers:
            await update.message.reply_text(f"❤️ *Вас лайкнули ({len(likers)}):*", parse_mode='Markdown')
            
            for liker in likers:
                try:
                    # Визначаємо ID лайкера
                    if isinstance(liker, dict):
                        liker_id = liker.get('telegram_id')
                        is_mutual = db.has_liked(user.id, liker_id)
                    else:
                        liker_id = liker[1] if len(liker) > 1 else None
                        is_mutual = db.has_liked(user.id, liker_id) if liker_id else False
                    
                    status = "💕 МАТЧ" if is_mutual else "❤️ Лайкнув(ла) вас"
                    
                    # Форматуємо профіль
                    profile_text = format_profile_text(liker, status)
                    main_photo = db.get_main_photo(liker_id)
                    
                    # Отримуємо username
                    liked_user = db.get_user(liker_id)
                    username = liked_user.get('username') if liked_user else None
                    
                    if main_photo:
                        caption = profile_text
                        if username:
                            caption += f"\n\n💬 Username: @{username}"
                        
                        await update.message.reply_photo(
                            photo=main_photo,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                    else:
                        text = profile_text
                        if username:
                            text += f"\n\n💬 Username: @{username}"
                        
                        await update.message.reply_text(
                            text,
                            parse_mode='Markdown'
                        )
                    
                    # Додаємо кнопку для взаємного лайку, якщо ще не матч
                    if not is_mutual and liker_id:
                        context.user_data['current_profile_for_like'] = liker_id
                        keyboard = [
                            ['❤️ Взаємний лайк'],
                            ['➡️ Наступний лайк']
                        ]
                        await update.message.reply_text(
                            "Бажаєте поставити взаємний лайк?",
                            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        )
                        break  # Показуємо по одному з можливістю взаємності
                        
                except Exception as e:
                    logger.error(f"❌ Помилка обробки лайкера: {e}")
                    continue
                    
        else:
            await update.message.reply_text(
                "😔 Вас ще ніхто не лайкнув\n\n"
                "💡 *Порада:* Активніше шукайте анкети та ставте лайки - це збільшить вашу видимість!",
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка показу лайків: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка завантаження лайків. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def handle_like_back(update: Update, context: CallbackContext):
    """Обробка взаємного лайку зі списку лайків"""
    try:
        user = update.effective_user
        
        # Отримуємо ID користувача з контексту
        target_user_id = context.user_data.get('current_profile_for_like')
        
        if not target_user_id:
            await update.message.reply_text("❌ Не знайдено профіль для лайку")
            return
        
        logger.info(f"🔍 [LIKE BACK] Користувач {user.id} лайкає назад {target_user_id}")
        
        success, message = db.add_like(user.id, target_user_id)
        
        logger.info(f"🔍 [LIKE BACK RESULT] Успіх: {success}, Повідомлення: {message}")
        
        if success:
            current_user = db.get_user(user.id)
            target_user = db.get_user(target_user_id)
            
            if current_user and target_user:
                if db.has_liked(target_user_id, user.id):
                    match_text = "🎉 У вас новий матч!"
                    
                    await update.message.reply_text(
                        f"{match_text}\n\n💞 Тепер ви можете спілкуватися з {target_user['first_name']}!"
                    )
                    
                    try:
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text=f"🎉 У вас новий матч з {current_user['first_name']}!"
                        )
                    except Exception as e:
                        logger.error(f"❌ Не вдалося сповістити користувача {target_user_id} про матч: {e}")
                else:
                    await update.message.reply_text(
                        "❤️ Ви відправили лайк! Очікуйте на взаємність."
                    )
                    
                    try:
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text=f"❤️ Вас лайкнув(ла) {current_user['first_name']}! Перевірте хто вас лайкнув у меню."
                        )
                    except Exception as e:
                        logger.error(f"❌ Не вдалося сповістити користувача {target_user_id} про лайк: {e}")
            else:
                await update.message.reply_text("❌ Помилка: користувача не знайдено")
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка в handle_like_back: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка при обробці лайку.")

async def handle_top_selection(update: Update, context: CallbackContext):
    """Обробка вибору топу"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        text = update.message.text
        
        if text == "👨 Топ чоловіків":
            top_users = db.get_top_users_by_rating(limit=10, gender='male')
            title = "👨 Топ чоловіків"
        elif text == "👩 Топ жінок":
            top_users = db.get_top_users_by_rating(limit=10, gender='female')
            title = "👩 Топ жінок"
        else:
            top_users = db.get_top_users_by_rating(limit=10)
            title = "🏆 Топ користувачів"
        
        if top_users:
            await update.message.reply_text(f"**{title}** 🏆\n\n*Знайдено анкет: {len(top_users)}*", parse_mode='Markdown')
            
            for i, user_data in enumerate(top_users[:5], 1):  # Показуємо перших 5
                try:
                    # Визначаємо дані користувача
                    if isinstance(user_data, dict):
                        user_id = user_data.get('telegram_id')
                        first_name = user_data.get('first_name', 'Користувач')
                        age = user_data.get('age', 'Не вказано')
                        gender = user_data.get('gender', 'unknown')
                        city = user_data.get('city', 'Не вказано')
                        goal = user_data.get('goal', 'Не вказано')
                        bio = user_data.get('bio', 'Не вказано')
                        rating = user_data.get('rating', 5.0)
                        likes_count = user_data.get('likes_count', 0)
                    else:
                        user_id = user_data[1] if len(user_data) > 1 else None
                        first_name = user_data[3] if len(user_data) > 3 and user_data[3] else 'Користувач'
                        age = user_data[4] if len(user_data) > 4 else 'Не вказано'
                        gender = user_data[5] if len(user_data) > 5 else 'unknown'
                        city = user_data[6] if len(user_data) > 6 else 'Не вказано'
                        goal = user_data[8] if len(user_data) > 8 else 'Не вказано'
                        bio = user_data[9] if len(user_data) > 9 else 'Не вказано'
                        rating = user_data[14] if len(user_data) > 14 else 5.0
                        likes_count = user_data[12] if len(user_data) > 12 else 0
                    
                    if not user_id:
                        continue
                    
                    profile_text = f"""🏅 #{i} | ⭐ {rating:.1f} | ❤️ {likes_count} лайків

*Ім'я:* {first_name}
*Вік:* {age} років
*Стать:* {'👨 Чоловік' if gender == 'male' else '👩 Жінка'}
*Місто:* {city}
*Ціль:* {goal}
*⭐ Рейтинг:* {rating:.1f}/10.0

*Про себе:*
{bio if bio else "Не вказано"}"""
                    
                    main_photo = db.get_main_photo(user_id)
                    
                    # Зберігаємо поточний профіль для лайку
                    context.user_data['current_profile_for_like'] = user_id
                    context.user_data['current_top_user'] = user_data
                    
                    if main_photo:
                        await update.message.reply_photo(
                            photo=main_photo,
                            caption=profile_text,
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(profile_text, parse_mode='Markdown')
                    
                    # Показуємо меню з кнопкою лайку для топу
                    keyboard = [
                        ['❤️ Лайк'],
                        ['➡️ Наступний у топі']
                    ]
                    await update.message.reply_text(
                        "Оберіть дію:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                    
                    # Зупиняємося на цьому профілі
                    context.user_data['current_top_index'] = i
                    context.user_data['top_users'] = top_users
                    break  # Показуємо по одному
                    
                except Exception as e:
                    logger.error(f"❌ Помилка обробки топу #{i}: {e}")
                    continue
            
            # Клавіатура для навігації
            keyboard = [
                ['👨 Топ чоловіків', '👩 Топ жінок'],
                ['🏆 Загальний топ', '🔙 Меню']
            ]
            await update.message.reply_text(
                "🏆 Оберіть іншу категорію або поверніться в меню:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                f"😔 Ще немає користувачів у {title}\n\n"
                f"💡 *Порада:* Заповніть профіль повністю та додайте фото, щоб потрапити в топ!",
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка топу: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка завантаження топу. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def handle_top_navigation(update: Update, context: CallbackContext):
    """Навігація по топу"""
    user = update.effective_user
    text = update.message.text
    
    if text == "➡️ Наступний у топі":
        top_users = context.user_data.get('top_users', [])
        current_index = context.user_data.get('current_top_index', 0)
        
        if current_index < len(top_users):
            # Показуємо наступного користувача
            user_data = top_users[current_index]
            
            # Оновлюємо індекс
            context.user_data['current_top_index'] = current_index + 1
            
            # Показуємо профіль (використовуємо ту саму логіку що й у handle_top_selection)
            # ... код для показу профілю ...
            
        else:
            await update.message.reply_text("✅ Це останній користувач у топі")

async def handle_top_like(update: Update, context: CallbackContext):
    """Обробка лайку з топу"""
    try:
        user = update.effective_user
        
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        # Отримуємо ID користувача з контексту
        target_user_id = context.user_data.get('current_profile_for_like')
        
        if not target_user_id:
            await update.message.reply_text("❌ Не знайдено профіль для лайку")
            return
        
        logger.info(f"🔍 [TOP LIKE] Користувач {user.id} лайкає з топу {target_user_id}")
        
        # Додаємо лайк з перевіркою обмежень
        success, message = db.add_like(user.id, target_user_id)
        
        if success:
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(target_user_id, user.id)
            
            if is_mutual:
                # Отримуємо дані користувача для кнопки переходу в Telegram
                matched_user = db.get_user(target_user_id)
                if matched_user:
                    username = matched_user.get('username')
                    if username:
                        await update.message.reply_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            f"💬 *Тепер ви можете почати спілкування з {matched_user['first_name']}!*\n"
                            f"Username: @{username}",
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            f"ℹ️ *У {matched_user['first_name']} немає username*",
                            parse_mode='Markdown'
                        )
                else:
                    await update.message.reply_text("💕 У вас матч! Ви вподобали один одного!")
                
                # Відправляємо сповіщення про матч
                await notification_system.notify_new_match(context, user.id, target_user_id)
            else:
                # Відправляємо сповіщення про лайк
                await notification_system.notify_new_like(context, user.id, target_user_id)
                await update.message.reply_text(f"❤️ {message}")
                
            # Показуємо наступного користувача після лайку
            await show_next_after_like(update, context)
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку з топу: {e}", exc_info=True)
        await update.message.reply_text("❌ Сталася помилка при обробці лайку.")    

async def show_profile_views(update: Update, context: CallbackContext):
    """Показати хто переглядав профіль"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        viewers = db.get_profile_views(user.id)
        
        logger.info(f"🔍 [PROFILE VIEWS] Для користувача {user.id} знайдено {len(viewers)} переглядів")
        
        if viewers:
            # Зберігаємо переглядачів у контексті
            context.user_data['profile_viewers'] = viewers
            context.user_data['current_viewer_index'] = 0
            
            await update.message.reply_text(
                f"👀 *Вас переглядали ({len(viewers)} користувачів):*", 
                parse_mode='Markdown'
            )
            
            # Показуємо першого переглядача
            await show_next_profile_view(update, context)
                    
        else:
            await update.message.reply_text(
                "😔 Вас ще ніхто не переглядав\n\n"
                "💡 *Порада:*\n"
                "• Активніше шукайте анкети\n"
                "• Ставте лайки\n" 
                "• Заповніть профіль повністю\n"
                "• Додайте якісні фото",
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка показу переглядів: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка завантаження переглядів. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )                     