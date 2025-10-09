from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import States, user_states, user_profiles

async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    user_states[user.id] = States.PROFILE_AGE
    user_profiles[user.id] = {}  # Ініціалізуємо словник для профілю
    await update.message.reply_text(
        "📝 Створення профілю\n\nВведіть ваш вік:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
    )

async def handle_profile_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    text = update.message.text
    state = user_states.get(user.id)

    print(f"🔧 [PROFILE] {user.first_name}: '{text}', стан: {state}")

    if text == "🔙 Скасувати":
        user_states[user.id] = States.START
        await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
        return

    if state == States.PROFILE_AGE:
        try:
            age = int(text)
            if age < 18 or age > 100:
                await update.message.reply_text("❌ Вік має бути від 18 до 100 років")
                return
            # Зберігаємо у user_profiles
            user_profiles[user.id]['age'] = age
            user_states[user.id] = States.PROFILE_GENDER
            keyboard = [[KeyboardButton("👨"), KeyboardButton("👩")], [KeyboardButton("🔙 Скасувати")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(f"✅ Вік: {age} років\n\nОберіть стать:", reply_markup=reply_markup)
        except ValueError:
            await update.message.reply_text("❌ Введіть коректний вік (число)")

    elif state == States.PROFILE_GENDER:
        if text == "👨":
            user_profiles[user.id]['gender'] = 'male'
            user_states[user.id] = States.PROFILE_CITY
            await update.message.reply_text(
                "✅ Стать: 👨 Чоловік\n\nВведіть ваше місто:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        elif text == "👩":
            user_profiles[user.id]['gender'] = 'female'
            user_states[user.id] = States.PROFILE_CITY
            await update.message.reply_text(
                "✅ Стать: 👩 Жінка\n\nВведіть ваше місто:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Оберіть стать з кнопок")

    elif state == States.PROFILE_CITY:
        if len(text) >= 2:
            user_profiles[user.id]['city'] = text
            user_states[user.id] = States.PROFILE_SEEKING_GENDER
            # Клавіатура для вибору статі (з'являється тільки після введення міста)
            keyboard = [[KeyboardButton("👩 Дівчину"), KeyboardButton("👨 Хлопця")], [KeyboardButton("👫 Всіх")], [KeyboardButton("🔙 Скасувати")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(f"✅ Місто: {text}\n\nКого шукаєте?", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Назва міста закоротка. Спробуйте ще раз:")

    elif state == States.PROFILE_SEEKING_GENDER:
        if text == "👩 Дівчину":
            user_profiles[user.id]['seeking_gender'] = 'female'
            user_states[user.id] = States.PROFILE_GOAL
            keyboard = [
                [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
                [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
                [KeyboardButton("🔙 Скасувати")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("✅ Шукаю: 👩 Дівчину\n\nОберіть ціль знайомства:", reply_markup=reply_markup)
        elif text == "👨 Хлопця":
            user_profiles[user.id]['seeking_gender'] = 'male'
            user_states[user.id] = States.PROFILE_GOAL
            keyboard = [
                [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
                [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
                [KeyboardButton("🔙 Скасувати")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("✅ Шукаю: 👨 Хлопця\n\nОберіть ціль знайомства:", reply_markup=reply_markup)
        elif text == "👫 Всіх":
            user_profiles[user.id]['seeking_gender'] = 'all'
            user_states[user.id] = States.PROFILE_GOAL
            keyboard = [
                [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
                [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
                [KeyboardButton("🔙 Скасувати")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("✅ Шукаю: 👫 Всіх\n\nОберіть ціль знайомства:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Оберіть варіант з кнопок")

    elif state == States.PROFILE_GOAL:
        if text == "💞 Серйозні стосунки":
            user_profiles[user.id]['goal'] = 'Серйозні стосунки'
            user_states[user.id] = States.PROFILE_BIO
            await update.message.reply_text(
                "✅ Ціль: 💞 Серйозні стосунки\n\nНапишіть про себе (мінімум 10 символів):",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        elif text == "👥 Дружба":
            user_profiles[user.id]['goal'] = 'Дружба'
            user_states[user.id] = States.PROFILE_BIO
            await update.message.reply_text(
                "✅ Ціль: 👥 Дружба\n\nНапишіть про себе (мінімум 10 символів):",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        elif text == "🎉 Разові зустрічі":
            user_profiles[user.id]['goal'] = 'Разові зустрічі'
            user_states[user.id] = States.PROFILE_BIO
            await update.message.reply_text(
                "✅ Ціль: 🎉 Разові зустрічі\n\nНапишіть про себе (мінімум 10 символів):",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        elif text == "🏃 Активний відпочинок":
            user_profiles[user.id]['goal'] = 'Активний відпочинок'
            user_states[user.id] = States.PROFILE_BIO
            await update.message.reply_text(
                "✅ Ціль: 🏃 Активний відпочинок\n\nНапишіть про себе (мінімум 10 символів):",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Оберіть ціль з кнопок")

    elif state == States.PROFILE_BIO:
        if len(text) >= 10:
            user_profiles[user.id]['bio'] = text
        
            print(f"💾 Зберігаємо профіль для {user.id}")
            print(f"💾 Дані профілю: {user_profiles[user.id]}")
        
            # Зберігаємо профіль в базу даних
            success = db.update_user_profile(
                telegram_id=user.id,
                age=user_profiles[user.id]['age'],
                gender=user_profiles[user.id]['gender'],
                city=user_profiles[user.id]['city'],
                seeking_gender=user_profiles[user.id].get('seeking_gender', 'all'),
                goal=user_profiles[user.id]['goal'],
                bio=user_profiles[user.id]['bio']
            )
        
            print(f"💾 Результат збереження: {success}")
        
            if success:
                user_states[user.id] = States.ADD_MAIN_PHOTO
                await update.message.reply_text(
                    "📷 Тепер додайте фото для профілю (максимум 3 фото):",
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Завершити")]], resize_keyboard=True)
                )
            else:
                await update.message.reply_text("❌ Помилка збереження профілю")
        else:
            await update.message.reply_text("❌ Опис закороткий. Мінімум 10 символів. Спробуйте ще раз:")

async def handle_main_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    if user_states.get(user.id) == States.ADD_MAIN_PHOTO and update.message.photo:
        photo = update.message.photo[-1]
        print(f"📷 Отримано фото для {user.id}")
        
        # Перевіряємо кількість фото
        current_photos = db.get_profile_photos(user.id)
        if len(current_photos) >= 3:
            user_states[user.id] = States.START
            await update.message.reply_text(
                "✅ Ви додали максимальну кількість фото (3 фото)\nПрофіль створено!",
                reply_markup=get_main_menu(user.id)
            )
            return
        
        success = db.add_profile_photo(user.id, photo.file_id)
        
        if success:
            photos = db.get_profile_photos(user.id)
            if len(photos) < 3:
                await update.message.reply_text(
                    f"✅ Фото додано! У вас {len(photos)}/3 фото\nНадішліть ще фото або натисніть '🔙 Завершити'",
                    reply_markup=ReplyKeyboardMarkup([['🔙 Завершити']], resize_keyboard=True)
                )
            else:
                user_states[user.id] = States.START
                await update.message.reply_text(
                    "✅ Ви додали максимальну кількість фото (3 фото)\nПрофіль створено!",
                    reply_markup=get_main_menu(user.id)
                )
        else:
            await update.message.reply_text("❌ Помилка додавання фото")
    
    elif user_states.get(user.id) == States.ADD_MAIN_PHOTO and update.message.text == "🔙 Завершити":
        user_states[user.id] = States.START
        photos_count = len(db.get_profile_photos(user.id))
        await update.message.reply_text(
            f"🎉 Профіль створено! Додано {photos_count} фото",
            reply_markup=get_main_menu(user.id)
        )
    
    elif user_states.get(user.id) == States.ADD_MAIN_PHOTO:
        await update.message.reply_text("📷 Будь ласка, надішліть фото:")

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    user_data = db.get_user(user.id)
    
    if not user_data or not user_data.get('age'):
        await update.message.reply_text("❌ У вас ще немає профілю", reply_markup=get_main_menu(user.id))
        return
    
    photos = db.get_profile_photos(user.id)
    
    # Відображення статі
    gender_display = "👨 Чоловік" if user_data['gender'] == 'male' else "👩 Жінка"
    
    # Відображення кого шукає
    seeking_display = {
        'female': '👩 Дівчину',
        'male': '👨 Хлопця',
        'all': '👫 Всіх'
    }.get(user_data.get('seeking_gender', 'all'), '👫 Всіх')
    
    # Відображення цілі
    goal_display = {
        'Серйозні стосунки': '💞 Серйозні стосунки',
        'Дружба': '👥 Дружба',
        'Разові зустрічі': '🎉 Разові зустрічі',
        'Активний відпочинок': '🏃 Активний відпочинок'
    }.get(user_data['goal'], user_data['goal'])
    
    profile_text = f"""👤 *Ваш профіль*

*Ім'я:* {user.first_name}
*Вік:* {user_data['age']} років
*Стать:* {gender_display}
*Місто:* {user_data['city']}
*Шукаю:* {seeking_display}  
*Ціль:* {goal_display}

*Про себе:*
{user_data['bio']}

*Фото:* {len(photos)}/3
❤️ *Лайків:* {user_data['likes_count']}"""
    
    # Відправляємо всі фото
    if photos:
        # Перше фото з описом профілю
        await update.message.reply_photo(
            photo=photos[0], 
            caption=profile_text,
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )
        
        # Решта фото без опису
        for i, photo_id in enumerate(photos[1:], 2):
            try:
                await update.message.reply_photo(
                    photo=photo_id, 
                    caption=f"Фото {i} з {len(photos)}"
                )
            except Exception as e:
                print(f"❌ Помилка завантаження фото: {e}")
                await update.message.reply_text(f"📸 Фото {i} (помилка завантаження)")
    else:
        await update.message.reply_text(
            profile_text,
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )