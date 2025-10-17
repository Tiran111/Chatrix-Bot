from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
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
            full_user_data = db.get_user_by_id(user_data[1])
            
            if full_user_data:
                first_name = full_user_data.get('first_name', 'Користувач')
                rating = full_user_data.get('rating', 5.0)
            else:
                first_name = user_data[3] if len(user_data) > 3 and user_data[3] else 'Користувач'
                rating = 5.0
            
            gender_display = "👨 Чоловік" if user_data[5] == 'male' else "👩 Жінка"
            profile_text = f"""👤 {title}

*Ім'я:* {first_name}
*Вік:* {user_data[4]} років
*Стать:* {gender_display}
*Місто:* {user_data[6]}
*Ціль:* {user_data[8]}
*⭐ Рейтинг:* {rating:.1f}/10.0

*Про себе:*
{user_data[9] if user_data[9] else "Не вказано"}"""
        
        return profile_text
    except Exception as e:
        logger.error(f"❌ Помилка форматування профілю: {e}")
        return f"❌ Помилка завантаження профілю"

async def search_profiles(update: Update, context: CallbackContext):
    """Пошук анкет"""
    user = update.effective_user
    
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    user_data, is_complete = db.get_user_profile(user.id)
    
    if not is_complete:
        await update.message.reply_text("❌ Спочатку заповніть профіль!", reply_markup=get_main_menu(user.id))
        return
    
    if not db.get_main_photo(user.id):
        await update.message.reply_text(
            "❌ Додайте головне фото до профілю, щоб шукати анкети!",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    await update.message.reply_text("🔍 Шукаю анкети...")
    
    random_user = db.get_random_user(user.id)
    
    if random_user:
        logger.info(f"🔍 [SEARCH] Знайдено користувача: {random_user[1]}")
        
        db.add_profile_view(user.id, random_user[1])
        
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
            reply_markup=get_main_menu(user.id)
        )

async def search_by_city(update: Update, context: CallbackContext):
    """Пошук за містом"""
    user = update.effective_user
    
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

async def show_user_profile(update: Update, context: CallbackContext, user_data, title=""):
    """Показати профіль користувача з звичайними кнопками меню"""
    user = update.effective_user
    
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
    
    main_photo = db.get_main_photo(telegram_id)
    
    # Створюємо звичайні кнопки меню замість inline кнопок
    keyboard = [
        ['❤️ Лайк', '➡️ Далі'],
        ['🔙 Меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    try:
        if main_photo:
            await update.message.reply_photo(
                photo=main_photo, 
                caption=profile_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                profile_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"❌ Помилка відправки профілю: {e}")
        await update.message.reply_text(
            "❌ Помилка завантаження профілю. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def show_next_profile(update: Update, context: CallbackContext):
    """Наступний профіль (для текстової кнопки)"""
    user = update.effective_user
    
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
            
            db.add_profile_view(user.id, user_data[1])
            
            await show_user_profile(update, context, user_data, "🏙️ Знайдені анкети")
        else:
            await update.message.reply_text("✅ Це остання анкета в цьому місті", reply_markup=get_main_menu(user.id))
    else:
        # Для випадкового пошуку - шукаємо нову анкету
        random_user = db.get_random_user(user.id)
        if random_user:
            db.add_profile_view(user.id, random_user[1])
            
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

async def show_top_users(update: Update, context: CallbackContext):
    """Показати вибір топу"""
    user = update.effective_user
    
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

async def show_matches(update: Update, context: CallbackContext):
    """Мої матчі"""
    user = update.effective_user
    
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    matches = db.get_user_matches(user.id)
    
    if matches:
        await update.message.reply_text(f"💌 *Ваші матчі ({len(matches)}):*", parse_mode='Markdown')
        for match in matches:
            profile_text = format_profile_text(match, "💕 МАТЧ!")
            main_photo = db.get_main_photo(match[1])
            
            matched_user = db.get_user(match[1])
            username = matched_user.get('username') if matched_user else None
            
            if main_photo:
                if username:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{username}")]
                    ])
                    await update.message.reply_photo(
                        photo=main_photo,
                        caption=profile_text,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_photo(
                        photo=main_photo,
                        caption=profile_text + "\n\nℹ️ *У цього користувача немає username*",
                        parse_mode='Markdown'
                    )
            else:
                if username:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{username}")]
                    ])
                    await update.message.reply_text(
                        profile_text,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        profile_text + "\n\nℹ️ *У цього користувача немає username*",
                        parse_mode='Markdown'
                    )
    else:
        await update.message.reply_text("😔 У вас ще немає матчів", reply_markup=get_main_menu(user.id))

async def show_likes(update: Update, context: CallbackContext):
    """Показати хто мене лайкнув"""
    user = update.effective_user
    
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    likers = db.get_user_likers(user.id)
    
    if likers:
        await update.message.reply_text(f"❤️ *Вас лайкнули ({len(likers)}):*", parse_mode='Markdown')
        
        for liker in likers:
            is_mutual = db.has_liked(user.id, liker[1])
            status = "💕 МАТЧ" if is_mutual else "❤️ Лайкнув(ла) вас"
            
            profile_text = format_profile_text(liker, status)
            main_photo = db.get_main_photo(liker[1])
            
            liked_user = db.get_user(liker[1])
            username = liked_user.get('username') if liked_user else None
            
            keyboard_buttons = []
            
            if is_mutual and username:
                keyboard_buttons.append([InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{username}")])
            
            if not is_mutual:
                keyboard_buttons.append([InlineKeyboardButton("❤️ Взаємний лайк", callback_data=f"like_back_{liker[1]}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
            
            if main_photo:
                await update.message.reply_photo(
                    photo=main_photo,
                    caption=profile_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    profile_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
    else:
        await update.message.reply_text(
            "😔 Вас ще ніхто не лайкнув\n\n"
            "💡 *Порада:* Активніше шукайте анкети та ставте лайки - це збільшить вашу видимість!",
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )

async def handle_like_back(update: Update, context: CallbackContext):
    """Обробка взаємного лайку зі списку лайків"""
    try:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        current_user_id = query.from_user.id
        
        # Отримуємо ID користувача з callback_data
        user_id = int(callback_data.split('_')[2])
        
        success, message = db.add_like(current_user_id, user_id)
        
        if success:
            current_user = db.get_user(current_user_id)
            target_user = db.get_user(user_id)
            
            if current_user and target_user:
                if db.has_liked(user_id, current_user_id):
                    match_text = "🎉 У вас новий матч!"
                    
                    await query.edit_message_text(
                        f"{match_text}\n\n💞 Тепер ви можете спілкуватися з {target_user['first_name']}!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{target_user['username']}")] if target_user.get('username') else []
                        ])
                    )
                    
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 У вас новий матч з {current_user['first_name']}!",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{current_user['username']}")] if current_user.get('username') else []
                            ])
                        )
                    except Exception as e:
                        logger.error(f"❌ Не вдалося сповістити користувача {user_id} про матч: {e}")
                else:
                    await query.edit_message_text(
                        "❤️ Ви відправили лайк! Очікуйте на взаємність.",
                        reply_markup=None
                    )
                    
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"❤️ Вас лайкнув(ла) {current_user['first_name']}! Перевірте хто вас лайкнув у меню."
                        )
                    except Exception as e:
                        logger.error(f"❌ Не вдалося сповістити користувача {user_id} про лайк: {e}")
            else:
                await query.edit_message_text("❌ Помилка: користувача не знайдено")
        else:
            await query.edit_message_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка в handle_like_back: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Сталася помилка при обробці лайку.")
        except:
            pass

async def handle_top_selection(update: Update, context: CallbackContext):
    """Обробка вибору топу"""
    user = update.effective_user
    
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
        
        for i, user_data in enumerate(top_users, 1):
            user_info = db.get_user_by_id(user_data[1])
            
            if user_info:
                first_name = user_info.get('first_name', 'Користувач')
                rating = user_info.get('rating', 5.0)
                likes_count = user_info.get('likes_count', 0)
            else:
                first_name = user_data[3] if len(user_data) > 3 and user_data[3] else 'Користувач'
                rating = user_data[14] if len(user_data) > 14 else 5.0
                likes_count = user_data[12] if len(user_data) > 12 else 0
            
            profile_text = f"""🏅 #{i} | ⭐ {rating:.1f} | ❤️ {likes_count} лайків

*Ім'я:* {first_name}
*Вік:* {user_data[4]} років
*Стать:* {'👨 Чоловік' if user_data[5] == 'male' else '👩 Жінка'}
*Місто:* {user_data[6]}
*Ціль:* {user_data[8]}
*⭐ Рейтинг:* {rating:.1f}/10.0

*Про себе:*
{user_data[9] if user_data[9] else "Не вказано"}"""
            
            main_photo = db.get_main_photo(user_data[1])
            
            # Додаємо кнопку лайку для топу
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{user_data[1]}")]
            ])
            
            if main_photo:
                await update.message.reply_photo(
                    photo=main_photo,
                    caption=profile_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(profile_text, reply_markup=keyboard, parse_mode='Markdown')
        
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
            reply_markup=get_main_menu(user.id)
        )

async def handle_like(update: Update, context: CallbackContext):
    """Обробка лайку з callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        callback_data = query.data
        
        logger.info(f"🔍 [LIKE CALLBACK] Отримано callback: {callback_data} від {user.id}")
        
        # Отримуємо ID користувача з callback_data
        target_user_id = int(callback_data.split('_')[1])
        
        logger.info(f"🔍 [LIKE] Користувач {user.id} лайкає {target_user_id}")
        
        # Додаємо лайк з перевіркою обмежень
        success, message = db.add_like(user.id, target_user_id)
        
        if success:
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(target_user_id, user.id)
            
            if is_mutual:
                # Відправляємо сповіщення про матч
                await notification_system.notify_new_match(context, user.id, target_user_id)
                
                # Отримуємо дані користувача для кнопки переходу в Telegram
                matched_user = db.get_user(target_user_id)
                if matched_user:
                    username = matched_user.get('username')
                    if username:
                        # Створюємо кнопку для переходу в Telegram
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{username}")]
                        ])
                        await query.edit_message_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            "💬 *Тепер ви можете почати спілкування!*",
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        await query.edit_message_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            "ℹ️ *У цього користувача немає username*",
                            parse_mode='Markdown'
                        )
                else:
                    await query.edit_message_text("💕 У вас матч! Ви вподобали один одного!")
            else:
                # Відправляємо сповіщення про лайк
                await notification_system.notify_new_like(context, user.id, target_user_id)
                await query.edit_message_text(f"❤️ {message}")
        else:
            await query.edit_message_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Сталася помилка при обробці лайку.")
        except:
            pass

async def handle_next(update: Update, context: CallbackContext):
    """Обробка кнопки 'Далі' з callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        logger.info(f"🔍 [NEXT CALLBACK] Обробка кнопки 'Далі' для {user.id}")
        
        search_users = context.user_data.get('search_users', [])
        current_index = context.user_data.get('current_index', 0)
        search_type = context.user_data.get('search_type', 'random')
        
        logger.info(f"🔍 [NEXT CALLBACK] Тип пошуку: {search_type}, індекс: {current_index}, знайдено: {len(search_users)}")
        
        if not search_users:
            await query.edit_message_text("🔄 Шукаємо нові анкети...")
            await search_profiles(update, context)
            return
        
        # Якщо це пошук за містом, шукаємо наступного користувача
        if search_type == 'city':
            if current_index < len(search_users) - 1:
                current_index += 1
                context.user_data['current_index'] = current_index
                user_data = search_users[current_index]
                
                # Додаємо запис про перегляд профілю
                db.add_profile_view(user.id, user_data[1])
                
                await show_user_profile(update, context, user_data, "🏙️ Знайдені анкети")
            else:
                await query.edit_message_text("✅ Це остання анкета в цьому місті", reply_markup=get_main_menu(user.id))
        else:
            # Для випадкового пошуку - шукаємо нову анкету
            random_user = db.get_random_user(user.id)
            if random_user:
                # Додаємо запис про перегляд профілю
                db.add_profile_view(user.id, random_user[1])
                
                await show_user_profile(update, context, random_user, "💕 Знайдені анкети")
                context.user_data['search_users'] = [random_user]
                context.user_data['current_index'] = 0
            else:
                await query.edit_message_text(
                    "😔 Більше немає анкет для перегляду\n\n"
                    "💡 Спробуйте:\n"
                    "• Змінити критерії пошуку\n"
                    "• Пошукати за іншим містом\n"
                    "• Зачекати поки з'являться нові користувачі",
                    reply_markup=get_main_menu(user.id)
                )
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки кнопки 'Далі': {e}")
        try:
            await update.callback_query.edit_message_text("❌ Сталася помилка.")
        except:
            pass

async def handle_like_button(update: Update, context: CallbackContext):
    """Обробка кнопки Лайк з меню"""
    try:
        user = update.effective_user
        target_user_id = context.user_data.get('current_profile_id')
        
        if not target_user_id:
            await update.message.reply_text("❌ Не знайдено профіль для лайку")
            return
        
        logger.info(f"🔍 [LIKE BUTTON] Користувач {user.id} лайкає {target_user_id}")
        
        # Додаємо лайк з перевіркою обмежень
        success, message = db.add_like(user.id, target_user_id)
        
        if success:
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(target_user_id, user.id)
            
            if is_mutual:
                # Відправляємо сповіщення про матч
                await notification_system.notify_new_match(context, user.id, target_user_id)
                
                # Отримуємо дані користувача
                matched_user = db.get_user(target_user_id)
                if matched_user:
                    username = matched_user.get('username')
                    match_text = f"💕 У вас матч з {matched_user['first_name']}!"
                    
                    if username:
                        match_text += f"\n💬 Напиши: @{username}"
                    
                    await update.message.reply_text(match_text)
                else:
                    await update.message.reply_text("💕 У вас матч! Ви вподобали один одного!")
            else:
                await update.message.reply_text(f"❤️ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку: {e}")
        await update.message.reply_text("❌ Сталася помилка при обробці лайку.")

async def handle_next_button(update: Update, context: CallbackContext):
    """Обробка кнопки Далі з меню"""
    try:
        user = update.effective_user
        
        logger.info(f"🔍 [NEXT BUTTON] Обробка кнопки 'Далі' для {user.id}")
        
        search_users = context.user_data.get('search_users', [])
        current_index = context.user_data.get('current_index', 0)
        search_type = context.user_data.get('search_type', 'random')
        
        if not search_users:
            await update.message.reply_text("🔄 Шукаємо нові анкети...")
            await search_profiles(update, context)
            return
        
        # Якщо це пошук за містом, шукаємо наступного користувача
        if search_type == 'city':
            if current_index < len(search_users) - 1:
                current_index += 1
                context.user_data['current_index'] = current_index
                user_data = search_users[current_index]
                
                # Додаємо запис про перегляд профілю
                db.add_profile_view(user.id, user_data[1])
                
                await show_user_profile(update, context, user_data, "🏙️ Знайдені анкети")
            else:
                await update.message.reply_text("✅ Це остання анкета в цьому місті", reply_markup=get_main_menu(user.id))
        else:
            # Для випадкового пошуку - шукаємо нову анкету
            random_user = db.get_random_user(user.id)
            if random_user:
                # Додаємо запис про перегляд профілю
                db.add_profile_view(user.id, random_user[1])
                
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
        logger.error(f"❌ Помилка обробки кнопки 'Далі': {e}")
        await update.message.reply_text("❌ Сталася помилка.")