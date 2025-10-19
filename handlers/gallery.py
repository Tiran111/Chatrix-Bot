from telegram import Update
from telegram.ext import ContextTypes
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from keyboards.main_menu import get_main_menu, get_gallery_menu, get_gallery_navigation, get_profile_navigation
from keyboards.main_menu import get_main_menu, get_gallery_menu, get_gallery_navigation, get_profile_navigation
from utils.states import States, user_states, gallery_view_data

async def show_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    gallery = db.get_user_gallery(user.id)
    profile, is_complete = db.get_user_profile(user.id)
    
    if profile and profile[9]:
        likes_count = db.get_likes_count(user.id)
        await update.message.reply_photo(
            photo=profile[9],
            caption=f"📷 Ваше головне фото в профілі\n❤️ Лайків: {likes_count}"
        )
    
    if gallery:
        await update.message.reply_text(f"📸 Ваша галерея ({len(gallery)} фото):")
        for i, photo_id in enumerate(gallery, 1):
            await update.message.reply_photo(photo=photo_id, caption=f"Фото {i}")
    else:
        await update.message.reply_text("📸 У вас ще немає фото в галереї")
    
    await update.message.reply_text("Що бажаєте зробити?", reply_markup=get_gallery_menu())

async def handle_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка додавання фото в галерею"""
    user = update.effective_user
    
    if user_states.get(user.id) == States.ADD_PHOTO and update.message.photo:
        photo = update.message.photo[-1]
        print(f"📷 Додаємо фото в галерею для {user.id}")
        
        # Додаємо фото
        success = db.add_profile_photo(user.id, photo.file_id)
        user_states[user.id] = States.START
        
        if success:
            photos = db.get_profile_photos(user.id)
            await update.message.reply_text(
                f"✅ Фото додано! У вас {len(photos)}/5 фото",
                reply_markup=get_main_menu(user.id)
            )
        else:
            await update.message.reply_text(
                "❌ Помилка додавання фото. Можливо досягнуто ліміт (5 фото).",
                reply_markup=get_main_menu(user.id)
            )
    elif user_states.get(user.id) == States.ADD_PHOTO:
        await update.message.reply_text("❌ Будь ласка, надішліть фото:")
async def view_user_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    current_profile_id = context.user_data.get('current_profile_id')
    
    if not current_profile_id:
        await update.message.reply_text("❌ Помилка: не знайдено профіль", reply_markup=get_main_menu(user.id))
        return
    
    user_profile = db.get_user_by_id(current_profile_id)
    if not user_profile:
        await update.message.reply_text("❌ Користувача не знайдено", reply_markup=get_main_menu(user.id))
        return
    
    gallery = db.get_other_user_gallery(current_profile_id)
    
    if not gallery:
        await update.message.reply_text(
            f"📸 У користувача {user_profile[2]} ще немає фото в галереї",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    gallery_view_data[user.id] = {
        'user_id': current_profile_id,
        'user_name': user_profile[2],
        'photos': gallery,
        'current_index': 0
    }
    
    user_states[user.id] = States.VIEW_USER_GALLERY
    
    photo_id = gallery[0]
    caption = f"📸 Галерея {user_profile[2]}\nФото 1 з {len(gallery)}"
    
    await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=get_gallery_navigation())

async def handle_gallery_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if user.id not in gallery_view_data:
        await update.message.reply_text("❌ Помилка навігації", reply_markup=get_main_menu(user.id))
        user_states[user.id] = States.START
        return
    
    gallery_data = gallery_view_data[user.id]
    photos = gallery_data['photos']
    current_index = gallery_data['current_index']
    user_name = gallery_data['user_name']
    
    if text == '➡️ Наступне':
        if current_index < len(photos) - 1:
            current_index += 1
        else:
            await update.message.reply_text("✅ Це останнє фото в галереї")
            return
    elif text == '⬅️ Попереднє':
        if current_index > 0:
            current_index -= 1
        else:
            await update.message.reply_text("✅ Це перше фото в галереї")
            return
    elif text == '📝 Профіль':
        user_profile = db.get_user_by_id(gallery_data['user_id'])
        from handlers.search import show_user_profile
        await show_user_profile(update, context, user_profile, "👤 Профіль")
        user_states[user.id] = States.START
        return
    elif text == '🔙 Галерея':
        await show_gallery(update, context)
        user_states[user.id] = States.START
        return
    
    gallery_data['current_index'] = current_index
    gallery_view_data[user.id] = gallery_data
    
    photo_id = photos[current_index]
    caption = f"📸 Галерея {user_name}\nФото {current_index + 1} з {len(photos)}"
    
    await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=get_gallery_navigation())

async def view_my_gallery_from_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    gallery = db.get_user_gallery(user.id)
    
    if not gallery:
        await update.message.reply_text("📸 У вас ще немає фото в галереї", reply_markup=get_profile_navigation())
        return
    
    gallery_view_data[user.id] = {
        'user_id': user.id,
        'user_name': "Ваша",
        'photos': gallery,
        'current_index': 0,
        'from_profile': True
    }
    
    user_states[user.id] = States.VIEW_USER_GALLERY
    
    photo_id = gallery[0]
    caption = f"📸 Ваша галерея\nФото 1 з {len(gallery)}"
    
    await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=get_gallery_navigation())