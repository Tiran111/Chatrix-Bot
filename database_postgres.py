import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # Отримуємо URL бази даних з змінних середовища
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.error("❌ DATABASE_URL не встановлено")
            # Для локального тестування
            database_url = "postgresql://user:pass@localhost/dating_bot"
        
        logger.info("🔄 Підключення до PostgreSQL...")
        try:
            self.conn = psycopg2.connect(database_url, sslmode='require')
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            self.init_db()
            self.update_database_structure()
            logger.info("✅ Підключено до PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Помилка підключення до PostgreSQL: {e}")
            raise

    def init_db(self):
        """Ініціалізація бази даних"""
        logger.info("🔄 Ініціалізація бази даних...")
        try:
            # Створення таблиці users
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255) NOT NULL,
                    age INTEGER,
                    gender VARCHAR(10),
                    city VARCHAR(255),
                    seeking_gender VARCHAR(10) DEFAULT 'all',
                    goal VARCHAR(255),
                    bio TEXT,
                    has_photo BOOLEAN DEFAULT FALSE,
                    rating FLOAT DEFAULT 5.0,
                    likes_count INTEGER DEFAULT 0,
                    is_banned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Створення таблиці photos
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS photos (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    file_id VARCHAR(255) NOT NULL,
                    is_main BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Створення таблиці likes
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS likes (
                    id SERIAL PRIMARY KEY,
                    from_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    to_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(from_user_id, to_user_id)
                )
            ''')
            
            # Створення таблиці matches
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id SERIAL PRIMARY KEY,
                    user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user1_id, user2_id)
                )
            ''')
            
            # Створення таблиці profile_views
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS profile_views (
                    id SERIAL PRIMARY KEY,
                    viewer_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    viewed_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            logger.info("✅ База даних ініціалізована")
            
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації бази даних: {e}")
            self.conn.rollback()

    def update_database_structure(self):
        """Оновлення структури бази даних"""
        try:
            # Додавання відсутніх стовпців
            columns_to_add = [
                "ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0",
                "ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE"
            ]
            
            for column_sql in columns_to_add:
                try:
                    self.cursor.execute(f'ALTER TABLE users {column_sql}')
                except Exception as e:
                    logger.warning(f"⚠️ Не вдалося додати стовпець до users: {e}")
            
            # Додаємо колонку is_main до таблиці photos, якщо її немає
            try:
                self.cursor.execute('''
                    ALTER TABLE photos 
                    ADD COLUMN IF NOT EXISTS is_main BOOLEAN DEFAULT FALSE
                ''')
                logger.info("✅ Колонка is_main додана до таблиці photos")
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося додати is_main до photos: {e}")
            
            self.conn.commit()
            logger.info("✅ Структура бази даних оновлена")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення структури: {e}")
            self.conn.rollback()

    def add_user(self, telegram_id, username, first_name):
        """Додавання нового користувача"""
        try:
            # Перевіряємо чи існує користувач
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            existing_user = self.cursor.fetchone()
            
            if existing_user:
                logger.info(f"ℹ️ Користувач {telegram_id} вже існує")
                return True
            
            # Додаємо нового користувача
            self.cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, created_at, last_active, rating)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (telegram_id, username, first_name, datetime.now(), datetime.now(), 5.0))
            
            self.conn.commit()
            logger.info(f"✅ Користувач {telegram_id} успішно доданий")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання користувача {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def get_user(self, telegram_id):
        """Отримання користувача за ID"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            return user
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувача {telegram_id}: {e}")
            return None

    def update_user_profile(self, telegram_id, age=None, gender=None, city=None, 
                          seeking_gender=None, goal=None, bio=None):
        """Оновлення профілю користувача"""
        try:
            # Спочатку перевіряємо чи існує користувач
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для оновлення")
                return False
            
            # Оновлюємо профіль
            update_fields = []
            values = []
            
            if age is not None:
                update_fields.append("age = %s")
                values.append(age)
            if gender is not None:
                update_fields.append("gender = %s")
                values.append(gender)
            if city is not None:
                update_fields.append("city = %s")
                values.append(city)
            if seeking_gender is not None:
                update_fields.append("seeking_gender = %s")
                values.append(seeking_gender)
            if goal is not None:
                update_fields.append("goal = %s")
                values.append(goal)
            if bio is not None:
                update_fields.append("bio = %s")
                values.append(bio)
            
            # Додаємо оновлення часу останньої активності
            update_fields.append("last_active = %s")
            values.append(datetime.now())
            
            # Додаємо telegram_id в кінець для WHERE умови
            values.append(telegram_id)
            
            if update_fields:
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE telegram_id = %s"
                self.cursor.execute(query, values)
                self.conn.commit()
                
                logger.info(f"✅ Профіль користувача {telegram_id} оновлено")
                return True
            else:
                logger.warning(f"⚠️ Немає полів для оновлення для користувача {telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка оновлення профілю {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def update_or_create_user_profile(self, telegram_id, age, gender, city, seeking_gender, goal, bio):
        """Оновлення або створення профілю користувача"""
        try:
            # Спочатку перевіряємо чи існує користувач
            user = self.get_user(telegram_id)
            
            if not user:
                # Якщо користувача немає, створюємо його
                logger.info(f"🔄 Користувача {telegram_id} не знайдено, створюємо...")
                success = self.add_user(telegram_id, "unknown", "User")
                if not success:
                    logger.error(f"❌ Не вдалося створити користувача {telegram_id}")
                    return False
            
            # Тепер оновлюємо профіль
            return self.update_user_profile(
                telegram_id=telegram_id,
                age=age,
                gender=gender,
                city=city,
                seeking_gender=seeking_gender,
                goal=goal,
                bio=bio
            )
            
        except Exception as e:
            logger.error(f"❌ Помилка в update_or_create_user_profile: {e}")
            return False

    def get_user_profile(self, telegram_id):
        """Отримання профілю користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if user:
                # Перевіряємо чи профіль заповнений
                is_complete = all([
                    user.get('age'),
                    user.get('gender'), 
                    user.get('city'),
                    user.get('goal'),
                    user.get('bio')
                ])
                return user, is_complete
            return None, False
            
        except Exception as e:
            logger.error(f"❌ Помилка отримання профілю {telegram_id}: {e}")
            return None, False

    def add_user_photo(self, telegram_id, file_id, is_main=False):
        """Додавання фото користувача до бази даних"""
        try:
            # Отримуємо ID користувача
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для додавання фото")
                return False
            
            # Перевіряємо кількість фото користувача
            self.cursor.execute('SELECT COUNT(*) FROM photos WHERE user_id = %s', (user['id'],))
            result = self.cursor.fetchone()
            photo_count = result['count'] if result else 0
            
            # Якщо це перше фото, автоматично робимо його основним
            if photo_count == 0:
                is_main = True
            
            # Додаємо фото
            self.cursor.execute('''
                INSERT INTO photos (user_id, file_id, is_main)
                VALUES (%s, %s, %s)
            ''', (user['id'], file_id, is_main))
            
            # Оновлюємо прапорець has_photo у користувача
            self.cursor.execute('''
                UPDATE users SET has_photo = TRUE 
                WHERE telegram_id = %s
            ''', (telegram_id,))
            
            self.conn.commit()
            logger.info(f"✅ Фото додано для користувача {telegram_id}, is_main: {is_main}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання фото для {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def get_profile_photos(self, telegram_id):
        """Отримання фото профілю"""
        try:
            # Спочатку перевіряємо чи існує колонка is_main
            self.cursor.execute('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'photos' AND column_name = 'is_main'
            ''')
            has_is_main = self.cursor.fetchone() is not None
            
            if has_is_main:
                self.cursor.execute('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
                    ORDER BY p.is_main DESC, p.created_at ASC
                ''', (telegram_id,))
            else:
                # Якщо колонки is_main немає, використовуємо старий запит
                self.cursor.execute('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
                    ORDER BY p.created_at ASC
                ''', (telegram_id,))
                
            photos = self.cursor.fetchall()
            return [photo['file_id'] for photo in photos]
        except Exception as e:
            logger.error(f"❌ Помилка отримання фото для {telegram_id}: {e}")
            return []

    def get_main_photo(self, telegram_id):
        """Отримання головного фото"""
        try:
            # Спочатку перевіряємо чи існує колонка is_main
            self.cursor.execute('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'photos' AND column_name = 'is_main'
            ''')
            has_is_main = self.cursor.fetchone() is not None
            
            if has_is_main:
                self.cursor.execute('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s AND p.is_main = TRUE
                    ORDER BY p.created_at ASC
                    LIMIT 1
                ''', (telegram_id,))
            else:
                # Якщо колонки is_main немає, беремо перше фото
                self.cursor.execute('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
                    ORDER BY p.created_at ASC
                    LIMIT 1
                ''', (telegram_id,))
                
            result = self.cursor.fetchone()
            return result['file_id'] if result else None
        except Exception as e:
            logger.error(f"❌ Помилка отримання головного фото для {telegram_id}: {e}")
            return None

    def set_main_photo(self, telegram_id, file_id):
        """Встановлення головного фото"""
        try:
            # Отримуємо ID користувача
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                return False
            
            # Спочатку скидаємо всі is_main на False
            self.cursor.execute('''
                UPDATE photos SET is_main = FALSE 
                WHERE user_id = %s
            ''', (user['id'],))
            
            # Потім встановлюємо обране фото як головне
            self.cursor.execute('''
                UPDATE photos SET is_main = TRUE 
                WHERE user_id = %s AND file_id = %s
            ''', (user['id'], file_id))
            
            self.conn.commit()
            logger.info(f"✅ Головне фото оновлено для {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка встановлення головного фото для {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def delete_photo(self, telegram_id, file_id):
        """Видалення фото"""
        try:
            # Отримуємо ID користувача
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                return False
            
            # Видаляємо фото
            self.cursor.execute('''
                DELETE FROM photos 
                WHERE user_id = %s AND file_id = %s
            ''', (user['id'], file_id))
            
            # Перевіряємо чи залишилися фото
            self.cursor.execute('SELECT COUNT(*) FROM photos WHERE user_id = %s', (user['id'],))
            result = self.cursor.fetchone()
            remaining_photos = result['count'] if result else 0
            
            # Якщо фото не залишилося, оновлюємо has_photo
            if remaining_photos == 0:
                self.cursor.execute('''
                    UPDATE users SET has_photo = FALSE 
                    WHERE telegram_id = %s
                ''', (telegram_id,))
            # Якщо видалили головне фото, встановлюємо нове головне
            else:
                self.cursor.execute('''
                    SELECT file_id FROM photos 
                    WHERE user_id = %s 
                    ORDER BY created_at ASC 
                    LIMIT 1
                ''', (user['id'],))
                new_main = self.cursor.fetchone()
                if new_main:
                    self.set_main_photo(telegram_id, new_main['file_id'])
            
            self.conn.commit()
            logger.info(f"✅ Фото видалено для {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка видалення фото для {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def get_users_count(self):
        """Отримання загальної кількості користувачів"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання кількості користувачів: {e}")
            return 0

    def get_statistics(self):
        """Отримання статистики"""
        try:
            # Кількість чоловіків
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = %s AND is_banned = FALSE', ('male',))
            male_count = self.cursor.fetchone()['count']
            
            # Кількість жінок
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = %s AND is_banned = FALSE', ('female',))
            female_count = self.cursor.fetchone()['count']
            
            # Загальна кількість активних користувачів
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND is_banned = FALSE')
            total_active = self.cursor.fetchone()['count']
            
            # Статистика цілей
            self.cursor.execute('SELECT goal, COUNT(*) FROM users WHERE goal IS NOT NULL AND is_banned = FALSE GROUP BY goal')
            goals_stats = self.cursor.fetchall()
            
            return male_count, female_count, total_active, goals_stats
            
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    # ... решта методів залишається без змін ...

# Глобальний об'єкт бази даних
db = Database()