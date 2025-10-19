from telegram import Update
from telegram.ext import ContextTypes
from models import db
import logging

logger = logging.getLogger(__name__)

class NotificationSystem:
    """Система сповіщень для бота"""
    
    async def notify_new_like(self, context: ContextTypes.DEFAULT_TYPE, from_user_id, to_user_id):
        """Сповістити про новий лайк"""
        try:
            from_user = db.get_user(from_user_id)
            if not from_user:
                return False
            
            message = f"❤️ Вас лайкнув(ла) {from_user['first_name']}!"
            
            # Додаємо інформацію про профіль
            if from_user.get('age') and from_user.get('city'):
                message += f"\n\n👤 {from_user['first_name']}, {from_user['age']} років, {from_user['city']}"
            
            await context.bot.send_message(
                chat_id=to_user_id,
                text=message
            )
            return True
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про лайк: {e}")
            return False
    
    async def notify_new_match(self, context: ContextTypes.DEFAULT_TYPE, user1_id, user2_id):
        """Сповістити про новий матч"""
        try:
            user1 = db.get_user(user1_id)
            user2 = db.get_user(user2_id)
            
            if not user1 or not user2:
                return False
            
            # Сповіщаємо першого користувача
            message1 = f"💕 У вас матч з {user2['first_name']}!"
            if user2.get('username'):
                message1 += f"\n💬 Напишіть: @{user2['username']}"
            
            await context.bot.send_message(chat_id=user1_id, text=message1)
            
            # Сповіщаємо другого користувача
            message2 = f"💕 У вас матч з {user1['first_name']}!"
            if user1.get('username'):
                message2 += f"\n💬 Напишіть: @{user1['username']}"
            
            await context.bot.send_message(chat_id=user2_id, text=message2)
            
            return True
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про матч: {e}")
            return False
    
    async def notify_contact_admin(self, context: ContextTypes.DEFAULT_TYPE, user_id, message_text):
        """Сповістити адміна про контакт"""
        try:
            from config import ADMIN_ID
            user = db.get_user(user_id)
            
            if not user:
                return False
            
            admin_message = (
                f"📨 *Нове повідомлення від користувача:*\n\n"
                f"👤 *Користувач:* {user['first_name']}\n"
                f"🆔 *ID:* `{user_id}`\n"
                f"📝 *Повідомлення:* {message_text}"
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            # Зберігаємо повідомлення в базі
            db.add_admin_message(user_id, message_text)
            
            return True
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення адміна: {e}")
            return False
    
    async def notify_broadcast_message(self, context: ContextTypes.DEFAULT_TYPE, user_id, message_text):
        """Відправити розсилку користувачу"""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Розсилка від адміністратора:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"❌ Помилка відправки розсилки для {user_id}: {e}")
            return False
    
    async def notify_broadcast_complete(self, context: ContextTypes.DEFAULT_TYPE, admin_id, success_count, total_count):
        """Сповістити адміна про завершення розсилки"""
        try:
            message = (
                f"📊 *Розсилка завершена*\n\n"
                f"✅ Успішно: {success_count}\n"
                f"❌ Не вдалося: {total_count - success_count}\n"
                f"📨 Всього: {total_count}"
            )
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про завершення розсилки: {e}")
            return False

# Глобальний екземпляр системи сповіщень
notification_system = NotificationSystem()