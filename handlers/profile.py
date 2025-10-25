import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from utils.states import user_states, States, user_profiles
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок створення профілю"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    # Ініціалізуємо профіль
    user_states[user.id] = States.PROFILE_AGE
    user_profiles[user.id] = {}
    
    logger.info(f"🔧 [PROFILE START] Користувач {user.id} почав створення профілю")
    
    await update.message.reply_text(
        "📝 *Створення профілю*\n\nВведіть ваш вік (18-100):",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_profile_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлень під час створення/редагування профілю"""
    user = update.effective_user
    text = update.message.text
    state = user_states.get(user.id)

    logger.info(f"🔧 [PROFILE] {user.first_name}: '{text}', стан: {state}")

    if text == "🔙 Скасувати":
        user_states[user.id] = States.START
        user_profiles.pop(user.id, None)
        await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
        return

    # Перевіряємо чи існує профіль для користувача
    if user.id not in user_profiles:
        user_profiles[user.id] = {}
        logger.info(f"🔧 [PROFILE] Створено новий тимчасовий профіль для {user.id}")

    # Визначаємо чи це створення нового профілю чи редагування існуючого
    is_editing = False
    existing_user_data = db.get_user(user.id)
    if existing_user_data and existing_user_data.get('age'):
        is_editing = True
        logger.info(f"🔧 [PROFILE] Режим: РЕДАГУВАННЯ для {user.id}")

    if state == States.PROFILE_AGE:
        try:
            age = int(text)
            if age < 18 or age > 100:
                await update.message.reply_text("❌ Вік має бути від 18 до 100 років")
                return
            
            user_profiles[user.id]['age'] = age
            user_states[user.id] = States.PROFILE_GENDER
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} встановив вік: {age}")
            
            keyboard = [[KeyboardButton("👨"), KeyboardButton("👩")], [KeyboardButton("🔙 Скасувати")]]
            await update.message.reply_text(
                f"✅ Вік: {age} років\n\nОберіть стать:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        except ValueError:
            await update.message.reply_text("❌ Введіть коректний вік (число)")

    elif state == States.PROFILE_GENDER:
        if text == "👨":
            user_profiles[user.id]['gender'] = 'male'
            user_states[user.id] = States.PROFILE_CITY
            logger.info(f"🔧 [PROFILE] Користувач {user.id} обрав стать: male")
            await update.message.reply_text(
                "✅ Стать: 👨 Чоловік\n\nВведіть ваше місто:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        elif text == "👩":
            user_profiles[user.id]['gender'] = 'female'
            user_states[user.id] = States.PROFILE_CITY
            logger.info(f"🔧 [PROFILE] Користувач {user.id} обрав стать: female")
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
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} встановив місто: {text}")
            
            keyboard = [
                [KeyboardButton("👩 Дівчину"), KeyboardButton("👨 Хлопця")],
                [KeyboardButton("👫 Всіх")],
                [KeyboardButton("🔙 Скасувати")]
            ]
            await update.message.reply_text(
                f"✅ Місто: {text}\n\nКого шукаєте?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Назва міста закоротка. Спробуйте ще раз:")

    elif state == States.PROFILE_SEEKING_GENDER:
        if text == "👩 Дівчину":
            user_profiles[user.id]['seeking_gender'] = 'female'
            user_states[user.id] = States.PROFILE_GOAL
            logger.info(f"🔧 [PROFILE] Користувач {user.id} шукає: female")
        elif text == "👨 Хлопця":
            user_profiles[user.id]['seeking_gender'] = 'male'
            user_states[user.id] = States.PROFILE_GOAL
            logger.info(f"🔧 [PROFILE] Користувач {user.id} шукає: male")
        elif text == "👫 Всіх":
            user_profiles[user.id]['seeking_gender'] = 'all'
            user_states[user.id] = States.PROFILE_GOAL
            logger.info(f"🔧 [PROFILE] Користувач {user.id} шукає: all")
        else:
            await update.message.reply_text("❌ Оберіть варіант з кнопок")
            return
        
        # Показуємо вибір цілі
        keyboard = [
            [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
            [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
            [KeyboardButton("🔙 Скасувати")]
        ]
        seeking_text = {
            'female': '👩 Дівчину',
            'male': '👨 Хлопця', 
            'all': '👫 Всіх'
        }.get(user_profiles[user.id]['seeking_gender'])
        
        await update.message.reply_text(
            f"✅ Шукаю: {seeking_text}\n\nОберіть ціль знайомства:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    elif state == States.PROFILE_GOAL:
        goal_map = {
            '💞 Серйозні стосунки': 'Серйозні стосунки',
            '👥 Дружба': 'Дружба',
            '🎉 Разові зустрічі': 'Разові зустрічі',
            '🏃 Активний відпочинок': 'Активний відпочинок'
        }
        
        if text in goal_map:
            user_profiles[user.id]['goal'] = goal_map[text]
            user_states[user.id] = States.PROFILE_BIO
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} обрав ціль: {goal_map[text]}")
            
            await update.message.reply_text(
                f"✅ Ціль: {text}\n\nНапишіть про себе (мінімум 10 символів):",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Оберіть ціль з кнопок")

    # В функції handle_profile_message, коли заповнюється біо:
elif state == States.PROFILE_BIO:
    if len(text) >= 10:
        user_profiles[user.id]['bio'] = text
        
        logger.info(f"🔧 [PROFILE] Користувач {user.id} заповнив біо")
        
        # Зберігаємо профіль
        success = db.update_or_create_user_profile(
            telegram_id=user.id,
            age=user_profiles[user.id]['age'],
            gender=user_profiles[user.id]['gender'],
            city=user_profiles[user.id]['city'],
            seeking_gender=user_profiles[user.id].get('seeking_gender', 'all'),
            goal=user_profiles[user.id]['goal'],
            bio=user_profiles[user.id]['bio']
        )
        
        if success:
            # ОБОВ'ЯЗКОВО переходимо до додавання фото
            user_states[user.id] = States.ADD_MAIN_PHOTO
            
            await update.message.reply_text(
                "🎉 *Профіль створено!*\n\n"
                "📸 *Тепер обов'язково додайте фото для вашого профілю:*\n\n"
                "• Надішліть фото як звичайне повідомлення\n"  
                "• Можна додати до 3 фото\n"
                "• Перше фото буде основним\n\n"
                "📷 *Без фото ви не зможете шукати інші анкети!*",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Завершити")]], resize_keyboard=True),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Помилка збереження профілю")
    else:
        await update.message.reply_text("❌ Опис закороткий. Мінімум 10 символів.")

async def handle_main_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка додавання фото"""
    user = update.effective_user
    
    # Перевіряємо чи користувач є в базі
    user_data = db.get_user(user.id)
    if not user_data:
        # Створюємо користувача, якщо його немає
        logger.info(f"👤 Користувача {user.id} не знайдено, створюємо...")
        success = db.add_user(user.id, user.username, user.first_name)
        if success:
            logger.info(f"✅ Користувача {user.id} успішно створено")
        else:
            logger.error(f"❌ Не вдалося створити користувача {user.id}")
            await update.message.reply_text("❌ Помилка створення профілю")
            return
    
    # Обробка кнопки "Пропустити"
    if update.message.text == "🔙 Пропустити":
        user_states[user.id] = States.START
        user_profiles.pop(user.id, None)
        await update.message.reply_text(
            "✅ Можете додати фото пізніше через '👤 Мій профіль' → '📝 Редагувати'",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    # Обробка фото
    if user_states.get(user.id) == States.ADD_MAIN_PHOTO and update.message.photo:
        photo = update.message.photo[-1]
        
        logger.info(f"🔧 [PHOTO] Користувач {user.id} додає фото")
        
        # Додаємо фото
        success = db.add_user_photo(user.id, photo.file_id, is_main=True)
        
        if success:
            photos = db.get_profile_photos(user.id)
            if len(photos) < 3:
                await update.message.reply_text(
                    f"✅ Фото додано! У вас {len(photos)}/3 фото\n\n"
                    f"Можете додати ще фото або натиснути '🔙 Завершити'",
                    reply_markup=ReplyKeyboardMarkup([['🔙 Завершити']], resize_keyboard=True)
                )
            else:
                # Оновлюємо стан та показуємо головне меню
                user_states[user.id] = States.START
                user_profiles.pop(user.id, None)
                
                await update.message.reply_text(
                    "✅ Ви додали максимальну кількість фото (3 фото)\n🎉 Профіль готовий!",
                    reply_markup=get_main_menu(user.id)
                )
        else:
            await update.message.reply_text(
                "❌ Помилка додавання фото. Спробуйте ще раз або натисніть '🔙 Завершити'",
                reply_markup=ReplyKeyboardMarkup([['🔙 Завершити']], resize_keyboard=True)
            )
    
    elif user_states.get(user.id) == States.ADD_MAIN_PHOTO and update.message.text == "🔙 Завершити":
        # Оновлюємо стан та показуємо головне меню
        user_states[user.id] = States.START
        user_profiles.pop(user.id, None)
        photos_count = len(db.get_profile_photos(user.id))
        
        if photos_count > 0:
            await update.message.reply_text(
                f"🎉 Профіль створено! Додано {photos_count} фото",
                reply_markup=get_main_menu(user.id)
            )
        else:
            await update.message.reply_text(
                "✅ Профіль створено! Можете додати фото пізніше через '👤 Мій профіль'",
                reply_markup=get_main_menu(user.id)
            )
    
    elif user_states.get(user.id) == States.ADD_MAIN_PHOTO:
        await update.message.reply_text(
            "📷 Будь ласка, надішліть фото або натисніть '🔙 Завершити':",
            reply_markup=ReplyKeyboardMarkup([['🔙 Завершити']], resize_keyboard=True)
        )

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати профіль користувача"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ У вас ще немає профілю", reply_markup=get_main_menu(user.id))
            return
        
        # Перевіряємо чи профіль заповнений
        if not user_data.get('age') or not user_data.get('gender') or not user_data.get('city'):
            await update.message.reply_text(
                "❌ Ваш профіль не заповнений повністю!\n\n"
                "📝 Натисніть '📝 Заповнити профіль' щоб завершити реєстрацію",
                reply_markup=get_main_menu(user.id)
            )
            return
        
        photos = db.get_profile_photos(user.id)
        
        # Форматування профілю
        gender_display = "👨 Чоловік" if user_data['gender'] == 'male' else "👩 Жінка"
        
        seeking_display = {
            'female': '👩 Дівчину',
            'male': '👨 Хлопця',
            'all': '👫 Всіх'
        }.get(user_data.get('seeking_gender', 'all'), '👫 Всіх')
        
        goal_display = {
            'Серйозні стосунки': '💞 Серйозні стосунки',
            'Дружба': '👥 Дружба',
            'Разові зустрічі': '🎉 Разові зустрічі',
            'Активний відпочинок': '🏃 Активний відпочинок'
        }.get(user_data.get('goal', 'Не вказано'), user_data.get('goal', 'Не вказано'))
        
        profile_text = f"""👤 *Ваш профіль*

*Ім'я:* {user.first_name}
*Вік:* {user_data.get('age', 'Не вказано')} років
*Стать:* {gender_display}
*Місто:* {user_data.get('city', 'Не вказано')}
*Шукаю:* {seeking_display}  
*Ціль:* {goal_display}

*Про себе:*
{user_data.get('bio', 'Не вказано')}

*Фото:* {len(photos)}/3
❤️ *Лайків:* {user_data.get('likes_count', 0)}"""
        
        # Відправляємо фото з описом
        if photos:
            await update.message.reply_photo(
                photo=photos[0], 
                caption=profile_text,
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                profile_text,
                reply_markup=get_main_menu(user.id),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка показу профілю: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка завантаження профілю. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок редагування профілю"""
    user = update.effective_user
    
    user_data = db.get_user(user.id)
    if not user_data or not user_data.get('age'):
        await update.message.reply_text(
            "❌ У вас ще немає профілю. Спочатку заповніть його!",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    # Ініціалізуємо редагування - завантажуємо поточні дані
    user_states[user.id] = States.PROFILE_AGE
    user_profiles[user.id] = {
        'age': user_data.get('age'),
        'gender': user_data.get('gender'),
        'city': user_data.get('city'),
        'seeking_gender': user_data.get('seeking_gender', 'all'),
        'goal': user_data.get('goal'),
        'bio': user_data.get('bio')
    }
    
    logger.info(f"🔧 [EDIT PROFILE] Початок редагування для {user.id}")
    logger.info(f"🔧 [EDIT PROFILE] Поточні дані: {user_profiles[user.id]}")
    
    await update.message.reply_text(
        "✏️ *Редагування профілю*\n\nВведіть ваш вік (18-100):",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True),
        parse_mode='Markdown'
    )