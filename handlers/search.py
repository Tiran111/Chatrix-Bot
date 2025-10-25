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

# ... інші функції залишаються без змін ...

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

async def show_next_profile_view(update: Update, context: CallbackContext):
    """Показати наступного переглядача"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        viewers = context.user_data.get('profile_viewers', [])
        
        if not viewers:
            await update.message.reply_text(
                "😔 Більше немає переглядів",
                reply_markup=get_main_menu(user.id)
            )
            return
        
        # Отримуємо поточний індекс з контексту
        current_index = context.user_data.get('current_viewer_index', 0)
        
        if current_index >= len(viewers):
            await update.message.reply_text(
                "✅ Це останній перегляд",
                reply_markup=get_main_menu(user.id)
            )
            return
        
        viewer = viewers[current_index]
        
        try:
            # Визначаємо ID переглядача
            if isinstance(viewer, dict):
                viewer_id = viewer.get('telegram_id')
            else:
                viewer_id = viewer[1] if len(viewer) > 1 else None
            
            if not viewer_id:
                # Пропускаємо пустий і йдемо далі
                context.user_data['current_viewer_index'] = current_index + 1
                await show_next_profile_view(update, context)
                return
            
            # Форматуємо профіль
            profile_text = format_profile_text(viewer, "👀 Переглядав(ла) ваш профіль")
            main_photo = db.get_main_photo(viewer_id)
            
            # Отримуємо username
            viewed_user = db.get_user(viewer_id)
            username = viewed_user.get('username') if viewed_user else None
            
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
            
            # Додаємо кнопку для лайку та повернення в меню
            context.user_data['current_profile_for_like'] = viewer_id
            keyboard = [
                ['❤️ Лайкнути'],
                ['➡️ Наступний перегляд', '🔙 Меню']
            ]
            await update.message.reply_text(
                "Бажаєте поставити лайк?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            
            # Оновлюємо індекс для наступного переглядача
            context.user_data['current_viewer_index'] = current_index + 1
                    
        except Exception as e:
            logger.error(f"❌ Помилка обробки переглядача #{current_index}: {e}")
            # Пробуємо наступного
            context.user_data['current_viewer_index'] = current_index + 1
            await show_next_profile_view(update, context)
            
    except Exception as e:
        logger.error(f"❌ Помилка показу наступного перегляду: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка завантаження перегляду. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def handle_top_navigation(update: Update, context: CallbackContext):
    """Навігація по топу"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
            return
        
        top_users = context.user_data.get('top_users', [])
        current_index = context.user_data.get('current_top_index', 0)
        
        if current_index < len(top_users) - 1:
            current_index += 1
            context.user_data['current_top_index'] = current_index
            
            user_data = top_users[current_index]
            
            # Показуємо наступного користувача
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
            
            profile_text = f"""🏅 #{current_index + 1} | ⭐ {rating:.1f} | ❤️ {likes_count} лайків

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
            
            if main_photo:
                await update.message.reply_photo(
                    photo=main_photo,
                    caption=profile_text,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(profile_text, parse_mode='Markdown')
            
            # Показуємо меню з кнопкою лайку
            keyboard = [
                ['❤️ Лайк'],
                ['➡️ Наступний у топі', '🔙 Меню']  # ← ДОДАЄМО КНОПКУ МЕНЮ
            ]
            await update.message.reply_text(
                "Оберіть дію:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                "✅ Це останній користувач у топі",
                reply_markup=get_main_menu(user.id)
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка навігації по топу: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка навігації. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )

async def show_next_after_like(update: Update, context: CallbackContext):
    """Показати наступного користувача після лайку"""
    try:
        user = update.effective_user
        
        # Перевіряємо звідки прийшов лайк (топ чи перегляди)
        if context.user_data.get('top_users'):
            # З топу - показуємо наступного в топі
            await handle_top_navigation(update, context)
        elif context.user_data.get('profile_viewers'):
            # З переглядів - показуємо наступного переглядача
            await show_next_profile_view(update, context)
        else:
            # Зі звичайного пошуку - показуємо наступний профіль
            await show_next_profile(update, context)
            
    except Exception as e:
        logger.error(f"❌ Помилка показу наступного після лайку: {e}")
        await update.message.reply_text(
            "🎉 Лайк поставлено!",
            reply_markup=get_main_menu(user.id)
        )                