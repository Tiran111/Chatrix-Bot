from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu, get_search_navigation
from utils.states import user_states, States
from handlers.notifications import notification_system

# Допоміжна функція для форматування профілю - ОНОВЛЕНА ВЕРСІЯ З РЕЙТИНГОМ
def format_profile_text(user_data, title=""):
    """Форматування тексту профілю з рейтингом"""
    if isinstance(user_data, dict):
        # Якщо user_data - словник
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
        # Якщо user_data - tuple (з бази даних)
        # Отримуємо повну інформацію про користувача для правильного імені
        from database.models import db
        full_user_data = db.get_user_by_id(user_data[1])
        
        if full_user_data:
            first_name = full_user_data.get('first_name', 'Користувач')
            rating = full_user_data.get('rating', 5.0)
        else:
            # Якщо не вдалося отримати повні дані, використовуємо те, що є
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

async def search_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук анкет"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    user_data, is_complete = db.get_user_profile(user.id)
    
    if not is_complete:
        await update.message.reply_text("❌ Спочатку заповніть профіль!", reply_markup=get_main_menu(user.id))
        return
    
    # Перевіряємо чи є фото
    if not db.get_main_photo(user.id):
        await update.message.reply_text(
            "❌ Додайте головне фото до профілю, щоб шукати анкети!",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    await update.message.reply_text("🔍 Шукаю анкети...")
    
    # Знаходимо випадкову анкету
    random_user = db.get_random_user(user.id)
    
    if random_user:
        # Додаємо запис про перегляд профілю
        db.add_profile_view(user.id, random_user[1])
        
        await show_user_profile(update, context, random_user, "💕 Знайдені анкети")
        context.user_data['search_users'] = [random_user]
        context.user_data['current_index'] = 0
        context.user_data['search_type'] = 'random'
    else:
        await update.message.reply_text(
            "😔 Наразі немає анкет для перегляду",
            reply_markup=get_main_menu(user.id)
        )

async def search_by_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук за містом"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
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

async def show_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, title=""):
    """Показати профіль користувача"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
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
    
    if main_photo:
        await update.message.reply_photo(
            photo=main_photo, 
            caption=profile_text,
            reply_markup=get_search_navigation(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            profile_text,
            reply_markup=get_search_navigation(),
            parse_mode='Markdown'
        )

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка лайку"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    current_profile_id = context.user_data.get('current_profile_id')
    
    if current_profile_id:
        success, message = db.add_like(user.id, current_profile_id)
        if success:
            # Відправляємо сповіщення про лайк
            await notification_system.notify_new_like(context, user.id, current_profile_id)
            
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(current_profile_id, user.id)
            
            if is_mutual:
                # Відправляємо сповіщення про матч
                await notification_system.notify_new_match(context, user.id, current_profile_id)
                await update.message.reply_text("💕 У вас матч! Ви вподобали один одного!")
            else:
                await update.message.reply_text("❤️ Ви поставили лайк!")
        else:
            await update.message.reply_text(f"❌ {message}")
    else:
        await update.message.reply_text("❌ Не знайдено профіль для лайку")

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Наступний профіль"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
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
        else:
            await update.message.reply_text("😔 Більше немає анкет для перегляду", reply_markup=get_main_menu(user.id))

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка навігації"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    text = update.message.text
    
    if text == "🔙 Меню":
        await update.message.reply_text("👋 Повертаємось до головного меню", reply_markup=get_main_menu(user.id))
    elif text == "🔙 Пошук":
        await search_profiles(update, context)
    elif text == "🔙 Скасувати":
        await update.message.reply_text("❌ Дію скасовано", reply_markup=get_main_menu(user.id))

async def show_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати вибір топу"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
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

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Мої матчі"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    matches = db.get_user_matches(user.id)
    
    if matches:
        await update.message.reply_text("💌 *Ваші матчі:*", parse_mode='Markdown')
        for match in matches:
            profile_text = format_profile_text(match, "💕 МАТЧ!")
            main_photo = db.get_main_photo(match[1])
            
            if main_photo:
                await update.message.reply_photo(
                    photo=main_photo,
                    caption=profile_text,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(profile_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("😔 У вас ще немає матчів", reply_markup=get_main_menu(user.id))

async def show_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати хто мене лайкнув"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    # Отримуємо список користувачів, які лайкнули поточного користувача
    likers = db.get_user_likers(user.id)
    
    if likers:
        await update.message.reply_text(f"❤️ *Вас лайкнули ({len(likers)}):*", parse_mode='Markdown')
        
        for liker in likers:
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(user.id, liker[1])
            status = "💕 МАТЧ" if is_mutual else "❤️ Лайкнув(ла) вас"
            
            profile_text = format_profile_text(liker, status)
            main_photo = db.get_main_photo(liker[1])
            
            if main_photo:
                await update.message.reply_photo(
                    photo=main_photo,
                    caption=profile_text,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(profile_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "😔 Вас ще ніхто не лайкнув\n\n"
            "💡 *Порада:* Активніше шукайте анкети та ставте лайки - це збільшить вашу видимість!",
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )

async def handle_top_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору топу"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
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
    else:  # "🏆 Загальний топ"
        top_users = db.get_top_users_by_rating(limit=10)
        title = "🏆 Загальний топ"
    
    if top_users:
        await update.message.reply_text(f"**{title}** 🏆", parse_mode='Markdown')
        for i, user_data in enumerate(top_users, 1):
            print(f"🔍 [TOP] Дані користувача {i}: {user_data}")
            print(f"🔍 [TOP] Індекс 3 (first_name): '{user_data[3]}'")
            print(f"🔍 [TOP] Індекс 2 (username): '{user_data[2]}'")
            print(f"🔍 [TOP] Усі індекси: 0={user_data[0]}, 1={user_data[1]}, 2={user_data[2]}, 3={user_data[3]}")
        
            likes_count = user_data[12] if len(user_data) > 12 else 0
            rating = user_data[14] if len(user_data) > 14 else 5.0
            profile_text = format_profile_text(user_data, f"🏅 #{i} | ⭐ {rating:.1f} | ❤️ {likes_count} лайків")
            main_photo = db.get_main_photo(user_data[1])
            
            if main_photo:
                await update.message.reply_photo(
                    photo=main_photo,
                    caption=profile_text,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(profile_text, parse_mode='Markdown')
        
        # Показуємо кнопку для повернення до вибору топу
        keyboard = [
            ['👨 Топ чоловіків', '👩 Топ жінок'],
            ['🏆 Загальний топ', '🔙 Меню']
        ]
        await update.message.reply_text(
            "🏆 Оберіть іншу категорію або поверніться в меню:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(f"😔 Ще немає користувачів у {title}", reply_markup=get_main_menu(user.id))