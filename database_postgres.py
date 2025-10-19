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
            logger.info("✅ Підключено до PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Помилка підключення до PostgreSQL: {e}")
            raise

    def init_db(self):
        """Ініціалізація бази даних"""
        logger.info("🔄 Ініціалізація бази даних PostgreSQL...")

        # Таблиця користувачів
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                city TEXT,
                seeking_gender TEXT,
                goal TEXT,
                bio TEXT,
                has_photo BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                likes_count INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                rating REAL DEFAULT 5.0,
                daily_likes_count INTEGER DEFAULT 0,
                last_like_date DATE,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця фото
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця лайків
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER NOT NULL REFERENCES users(id),
                to_user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        
        # Таблиця матчів
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                user1_id INTEGER NOT NULL REFERENCES users(id),
                user2_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user1_id, user2_id)
            )
        ''')
        
        # Таблиця для відстеження переглядів профілю
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_views (
                id SERIAL PRIMARY KEY,
                viewer_id INTEGER NOT NULL REFERENCES users(id),
                viewed_user_id INTEGER NOT NULL REFERENCES users(id),
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ База даних PostgreSQL ініціалізована")

    def add_user(self, telegram_id, username, first_name):
        """Додавання нового користувача"""
        try:
            self.cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
            ''', (telegram_id, username, first_name))
            self.conn.commit()
            logger.info(f"✅ Користувач доданий/оновлений: {telegram_id} - {first_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка додавання користувача: {e}")
            return False

    def get_user(self, telegram_id):
        """Отримання користувача за telegram_id"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувача: {e}")
            return None

    def update_user_profile(self, telegram_id, age, gender, city, seeking_gender, goal, bio):
        """Оновлення профілю користувача"""
        try:
            logger.info(f"🔄 Оновлення профілю для {telegram_id}")
            
            self.cursor.execute('''
                UPDATE users 
                SET age = %s, gender = %s, city = %s, seeking_gender = %s, goal = %s, bio = %s, last_active = CURRENT_TIMESTAMP
                WHERE telegram_id = %s
            ''', (age, gender, city, seeking_gender, goal, bio, telegram_id))
            
            self.conn.commit()
            logger.info(f"✅ Профіль оновлено для {telegram_id}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Помилка оновлення профілю: {e}")
            return False

    def add_profile_photo(self, telegram_id, file_id):
        """Додавання фото до профілю"""
        try:
            logger.info(f"🔄 Додаємо фото для {telegram_id}")
            
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено")
                return False
            
            user_id = user['id']
            
            # Перевіряємо кількість фото
            self.cursor.execute('SELECT COUNT(*) FROM photos WHERE user_id = %s', (user_id,))
            photo_count = self.cursor.fetchone()['count']
            
            if photo_count >= 3:
                logger.error("❌ Досягнуто ліміт фото (максимум 3)")
                return False
            
            self.cursor.execute('INSERT INTO photos (user_id, file_id) VALUES (%s, %s)', (user_id, file_id))
            self.cursor.execute('UPDATE users SET has_photo = TRUE WHERE telegram_id = %s', (telegram_id,))
            
            self.conn.commit()
            logger.info("✅ Фото успішно додано до бази даних!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання фото: {e}")
            return False

    def get_profile_photos(self, telegram_id):
        """Отримання всіх фото профілю"""
        try:
            self.cursor.execute('''
                SELECT p.file_id FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = %s
            ''', (telegram_id,))
            photos = self.cursor.fetchall()
            return [photo['file_id'] for photo in photos]
        except Exception as e:
            logger.error(f"❌ Помилка отримання фото: {e}")
            return []

    def get_user_profile(self, telegram_id):
        """Отримання профілю користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            if user and user['age']:
                return user, True
            return user, False
        except Exception as e:
            logger.error(f"❌ Помилка отримання профілю: {e}")
            return None, False

    # Додайте інші методи з models.py по мірі необхідності
    # Просто адаптуйте SQL синтаксис (? → %s)

# Глобальний об'єкт бази даних
db = Database()