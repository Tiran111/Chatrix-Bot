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
            # Додавання відсутніх стовпців, якщо потрібно
            columns_to_add = [
                "ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0",
                "ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE"
            ]
            
            for column_sql in columns_to_add:
                try:
                    self.cursor.execute(f'ALTER TABLE users {column_sql}')
                except Exception as e:
                    logger.warning(f"⚠️ Не вдалося додати стовпець: {e}")
            
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

    def safe_update_profile(self, telegram_id, age, gender, city, seeking_gender, goal, bio):
        """Безпечне оновлення профілю з автоматичним створенням користувача"""
        try:
            # Перевіряємо чи існує користувач, якщо ні - створюємо
            user_data = self.get_user(telegram_id)
            if not user_data:
                logger.info(f"🔄 Користувача {telegram_id} не знайдено, створюємо...")
                # Створюємо з мінімальними даними
                success = self.add_user(telegram_id, "unknown", "User")
                if not success:
                    logger.error(f"❌ Не вдалося створити користувача {telegram_id}")
                    return False
            
            # Тепер оновлюємо профіль
            return self.update_user_profile(telegram_id, age, gender, city, seeking_gender, goal, bio)
            
        except Exception as e:
            logger.error(f"❌ Помилка в safe_update_profile: {e}")
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

    def add_profile_photo(self, telegram_id, file_id, is_main=False):
        """Додавання фото до профілю"""
        try:
            # Отримуємо ID користувача
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для додавання фото")
                return False
            
            # Перевіряємо кількість фото
            self.cursor.execute('SELECT COUNT(*) FROM photos WHERE user_id = %s', (user['id'],))
            photo_count = self.cursor.fetchone()['count']
            
            if photo_count >= 3:
                logger.warning(f"⚠️ Користувач {telegram_id} вже має максимальну кількість фото")
                return False
            
            # Додаємо фото
            self.cursor.execute('''
                INSERT INTO photos (user_id, file_id, is_main)
                VALUES (%s, %s, %s)
            ''', (user['id'], file_id, is_main))
            
            self.conn.commit()
            logger.info(f"✅ Фото додано для користувача {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання фото для {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def get_profile_photos(self, telegram_id):
        """Отримання фото профілю"""
        try:
            self.cursor.execute('''
                SELECT p.file_id FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = %s
                ORDER BY p.is_main DESC, p.created_at ASC
            ''', (telegram_id,))
            photos = self.cursor.fetchall()
            return [photo['file_id'] for photo in photos]
        except Exception as e:
            logger.error(f"❌ Помилка отримання фото для {telegram_id}: {e}")
            return []

    def get_main_photo(self, telegram_id):
        """Отримання головного фото"""
        try:
            photos = self.get_profile_photos(telegram_id)
            return photos[0] if photos else None
        except Exception as e:
            logger.error(f"❌ Помилка отримання головного фото для {telegram_id}: {e}")
            return None

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

    def get_random_user(self, exclude_telegram_id):
        """Отримання випадкового користувача"""
        try:
            self.cursor.execute('''
                SELECT u.* FROM users u
                WHERE u.telegram_id != %s 
                AND u.age IS NOT NULL 
                AND u.gender IS NOT NULL
                AND u.is_banned = FALSE
                ORDER BY RANDOM()
                LIMIT 1
            ''', (exclude_telegram_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ Помилка отримання випадкового користувача: {e}")
            return None

    def get_all_active_users(self, exclude_telegram_id=None):
        """Отримання всіх активних користувачів"""
        try:
            if exclude_telegram_id:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE telegram_id != %s 
                    AND age IS NOT NULL 
                    AND is_banned = FALSE
                    ORDER BY created_at DESC
                ''', (exclude_telegram_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL 
                    AND is_banned = FALSE
                    ORDER BY created_at DESC
                ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання активних користувачів: {e}")
            return []

    def get_all_users(self):
        """Отримання всіх користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання всіх користувачів: {e}")
            return []

    def get_banned_users(self):
        """Отримання заблокованих користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE is_banned = TRUE ORDER BY created_at DESC')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання заблокованих користувачів: {e}")
            return []

    def ban_user(self, telegram_id):
        """Блокування користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = TRUE WHERE telegram_id = %s', (telegram_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Помилка блокування користувача {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def unban_user(self, telegram_id):
        """Розблокування користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE telegram_id = %s', (telegram_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Помилка розблокування користувача {telegram_id}: {e}")
            self.conn.rollback()
            return False

    def search_user(self, query):
        """Пошук користувача"""
        try:
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE telegram_id::TEXT LIKE %s 
                   OR username ILIKE %s 
                   OR first_name ILIKE %s
                ORDER BY created_at DESC
            ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка пошуку користувача: {e}")
            return []

    def add_like(self, from_user_id, to_user_id):
        """Додавання лайку"""
        try:
            # Перевіряємо чи існують користувачі
            from_user = self.get_user(from_user_id)
            to_user = self.get_user(to_user_id)
            
            if not from_user or not to_user:
                return False, "Користувача не знайдено"
            
            # Додаємо лайк
            self.cursor.execute('''
                INSERT INTO likes (from_user_id, to_user_id)
                VALUES ((SELECT id FROM users WHERE telegram_id = %s), 
                       (SELECT id FROM users WHERE telegram_id = %s))
                ON CONFLICT (from_user_id, to_user_id) DO NOTHING
            ''', (from_user_id, to_user_id))
            
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                # Оновлюємо кількість лайків
                self.cursor.execute('''
                    UPDATE users SET likes_count = likes_count + 1 
                    WHERE telegram_id = %s
                ''', (to_user_id,))
                self.conn.commit()
                
                return True, "Лайк додано"
            else:
                return False, "Лайк вже поставлено"
                
        except Exception as e:
            logger.error(f"❌ Помилка додавання лайку: {e}")
            self.conn.rollback()
            return False, "Помилка додавання лайку"

    def has_liked(self, from_user_id, to_user_id):
        """Перевірка чи користувач вже лайкнув"""
        try:
            self.cursor.execute('''
                SELECT 1 FROM likes 
                WHERE from_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                AND to_user_id = (SELECT id FROM users WHERE telegram_id = %s)
            ''', (from_user_id, to_user_id))
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайку: {e}")
            return False

    def get_user_matches(self, telegram_id):
        """Отримання матчів користувача"""
        try:
            self.cursor.execute('''
                SELECT u.* FROM users u
                WHERE u.id IN (
                    SELECT l1.from_user_id FROM likes l1
                    JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
                    WHERE l1.to_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                )
                OR u.id IN (
                    SELECT l2.to_user_id FROM likes l1
                    JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
                    WHERE l1.from_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                )
            ''', (telegram_id, telegram_id))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання матчів: {e}")
            return []

    def get_user_likers(self, telegram_id):
        """Отримання тих, хто лайкнув користувача"""
        try:
            self.cursor.execute('''
                SELECT u.* FROM users u
                JOIN likes l ON u.id = l.from_user_id
                WHERE l.to_user_id = (SELECT id FROM users WHERE telegram_id = %s)
            ''', (telegram_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання лайкерів: {e}")
            return []

    def add_profile_view(self, viewer_id, viewed_id):
        """Додавання перегляду профілю"""
        try:
            self.cursor.execute('''
                INSERT INTO profile_views (viewer_user_id, viewed_user_id)
                VALUES ((SELECT id FROM users WHERE telegram_id = %s), 
                       (SELECT id FROM users WHERE telegram_id = %s))
            ''', (viewer_id, viewed_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка додавання перегляду: {e}")
            self.conn.rollback()
            return False

    def get_profile_views(self, telegram_id):
        """Отримання переглядів профілю"""
        try:
            self.cursor.execute('''
                SELECT u.* FROM users u
                JOIN profile_views pv ON u.id = pv.viewer_user_id
                WHERE pv.viewed_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                ORDER BY pv.viewed_at DESC
            ''', (telegram_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання переглядів: {e}")
            return []

    def get_top_users_by_rating(self, limit=10, gender=None):
        """Отримання топу користувачів за рейтингом"""
        try:
            if gender:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE gender = %s AND age IS NOT NULL AND is_banned = FALSE
                    ORDER BY rating DESC, likes_count DESC
                    LIMIT %s
                ''', (gender, limit))
            else:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL AND is_banned = FALSE
                    ORDER BY rating DESC, likes_count DESC
                    LIMIT %s
                ''', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання топу: {e}")
            return []

    def calculate_user_rating(self, telegram_id):
        """Розрахунок рейтингу користувача"""
        try:
            # Простий розрахунок рейтингу
            user = self.get_user(telegram_id)
            if not user:
                return 5.0
            
            base_rating = 5.0
            # Бонуси за заповненість профілю
            if user.get('age'):
                base_rating += 0.5
            if user.get('bio') and len(user.get('bio', '')) > 20:
                base_rating += 0.5
            if user.get('has_photo'):
                base_rating += 1.0
            
            # Бонус за лайки
            likes_bonus = min(user.get('likes_count', 0) * 0.1, 2.0)
            base_rating += likes_bonus
            
            # Обмежуємо рейтинг
            final_rating = min(max(base_rating, 1.0), 10.0)
            
            # Оновлюємо рейтинг в базі
            self.cursor.execute('UPDATE users SET rating = %s WHERE telegram_id = %s', (final_rating, telegram_id))
            self.conn.commit()
            
            return final_rating
            
        except Exception as e:
            logger.error(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

    def update_all_ratings(self):
        """Оновлення всіх рейтингів"""
        try:
            users = self.get_all_active_users()
            for user in users:
                self.calculate_user_rating(user['telegram_id'])
            logger.info("✅ Всі рейтинги оновлено")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка оновлення рейтингів: {e}")
            return False

    def cleanup_old_data(self):
        """Очищення старих даних"""
        try:
            # Видаляємо дублікати лайків
            self.cursor.execute('''
                DELETE FROM likes 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM likes 
                    GROUP BY from_user_id, to_user_id
                )
            ''')
            
            # Видаляємо дублікати матчів
            self.cursor.execute('''
                DELETE FROM matches 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM matches 
                    GROUP BY user1_id, user2_id
                )
            ''')
            
            self.conn.commit()
            logger.info("✅ Старі дані очищено")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка очищення даних: {e}")
            self.conn.rollback()
            return False

    def reset_database(self):
        """Скидання бази даних"""
        try:
            # Видаляємо всі таблиці
            tables = ['profile_views', 'matches', 'likes', 'photos', 'users']
            for table in tables:
                self.cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
            
            self.conn.commit()
            
            # Повторно ініціалізуємо базу
            self.init_db()
            self.update_database_structure()
            
            logger.info("✅ База даних скинута та перестворена")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка скидання бази даних: {e}")
            self.conn.rollback()
            return False

# Глобальний об'єкт бази даних
db = Database()