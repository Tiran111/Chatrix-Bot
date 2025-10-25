import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from datetime import datetime, date
import time

logger = logging.getLogger(__name__)

def cleanup_connections():
    """Очищення активних з'єднань з базою даних"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return
            
        conn = psycopg2.connect(database_url, sslmode='require')
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Завершення всіх активних транзакцій
        cursor.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = current_database()
            AND pid <> pg_backend_pid()
            AND state = 'idle in transaction'
        """)
        
        cursor.close()
        conn.close()
        logger.info("✅ Активні з'єднання очищено")
    except Exception as e:
        logger.warning(f"⚠️ Не вдалося очистити з'єднання: {e}")

class Database:
    def __init__(self):
        # Очищаємо активні з'єднання перед стартом
        cleanup_connections()
        
        # Отримуємо URL бази даних з змінних середовища
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.error("❌ DATABASE_URL не встановлено")
            raise ValueError("DATABASE_URL не встановлено")
        
        logger.info("🔄 Підключення до PostgreSQL...")
        self.conn = None
        self.cursor = None
        self.database_url = database_url
        self.connect_with_retry()
        self.init_db()
        logger.info("✅ Підключено до PostgreSQL")

    def connect_with_retry(self, max_retries=5):
        """Підключення з повторними спробами"""
        for attempt in range(max_retries):
            try:
                self.conn = psycopg2.connect(self.database_url, sslmode='require')
                self.conn.autocommit = True  # Важливо для уникнення проблем з транзакціями
                self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                logger.info(f"✅ Успішне підключення до PostgreSQL (спроба {attempt + 1})")
                return
            except Exception as e:
                logger.error(f"❌ Помилка підключення (спроба {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    # Спробуємо очистити з'єднання перед наступною спробою
                    cleanup_connections()
                else:
                    logger.error("❌ Не вдалося підключитися до PostgreSQL після всіх спроб")
                    raise

    def reconnect(self):
        """Перепідключення до бази даних"""
        try:
            if self.conn:
                self.conn.close()
        except:
            pass
        
        self.connect_with_retry()

    def execute_safe(self, query, params=None):
        """Безпечне виконання запиту з обробкою помилок"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return True
        except psycopg2.InterfaceError as e:
            logger.error(f"❌ Помилка з'єднання: {e}. Спробуємо перепідключитися...")
            self.reconnect()
            return False
        except Exception as e:
            logger.error(f"❌ Помилка запиту: {e}")
            # Спроба відкотити транзакцію
            try:
                self.conn.rollback()
            except:
                self.reconnect()
            return False

    def fetch_safe(self, query, params=None):
        """Безпечне виконання запиту з поверненням результату"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except psycopg2.InterfaceError as e:
            logger.error(f"❌ Помилка з'єднання: {e}. Спробуємо перепідключитися...")
            self.reconnect()
            return []
        except Exception as e:
            logger.error(f"❌ Помилка запиту: {e}")
            try:
                self.conn.rollback()
            except:
                self.reconnect()
            return []

    def fetch_one_safe(self, query, params=None):
        """Безпечне виконання запиту з поверненням одного результату"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchone()
        except psycopg2.InterfaceError as e:
            logger.error(f"❌ Помилка з'єднання: {e}. Спробуємо перепідключитися...")
            self.reconnect()
            return None
        except Exception as e:
            logger.error(f"❌ Помилка запиту: {e}")
            try:
                self.conn.rollback()
            except:
                self.reconnect()
            return None

    def init_db(self):
        """Ініціалізація бази даних"""
        logger.info("🔄 Ініціалізація бази даних...")
        
        # Створення таблиці users
        self.execute_safe('''
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
        self.execute_safe('''
            CREATE TABLE IF NOT EXISTS photos (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                file_id VARCHAR(255) NOT NULL,
                is_main BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Створення таблиці likes
        self.execute_safe('''
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                to_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        
        # Створення таблиці matches
        self.execute_safe('''
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user1_id, user2_id)
            )
        ''')
        
        # Створення таблиці profile_views з правильними назвами колонок
        self.execute_safe('''
            CREATE TABLE IF NOT EXISTS profile_views (
                id SERIAL PRIMARY KEY,
                viewer_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                viewed_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Додавання відсутніх колонок
        self.add_missing_columns()
        
        logger.info("✅ База даних ініціалізована")

    def add_missing_columns(self):
        """Додавання відсутніх колонок"""
        columns_to_add = [
            ("users", "likes_count", "INTEGER DEFAULT 0"),
            ("users", "is_banned", "BOOLEAN DEFAULT FALSE"),
            ("photos", "is_main", "BOOLEAN DEFAULT FALSE")
        ]
        
        for table, column, definition in columns_to_add:
            try:
                # Перевіряємо чи існує колонка
                self.execute_safe(f'''
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = '{column}'
                ''')
                exists = self.cursor.fetchone() is not None
                
                if not exists:
                    self.execute_safe(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
                    logger.info(f"✅ Колонка {column} додана до {table}")
                else:
                    logger.info(f"ℹ️ Колонка {column} вже існує в {table}")
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося додати {column} до {table}: {e}")

    def add_user(self, telegram_id, username, first_name):
        """Додавання нового користувача"""
        try:
            # Перевіряємо чи існує користувач
            existing_user = self.fetch_one_safe('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            
            if existing_user:
                logger.info(f"ℹ️ Користувач {telegram_id} вже існує")
                return True
            
            # Додаємо нового користувача
            if self.execute_safe('''
                INSERT INTO users (telegram_id, username, first_name, created_at, last_active, rating)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (telegram_id, username, first_name, datetime.now(), datetime.now(), 5.0)):
                logger.info(f"✅ Користувач {telegram_id} успішно доданий")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання користувача {telegram_id}: {e}")
            return False

    def get_user(self, telegram_id):
        """Отримання користувача за ID"""
        try:
            return self.fetch_one_safe('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувача {telegram_id}: {e}")
            return None

    def update_user_profile(self, telegram_id, age=None, gender=None, city=None, 
                          seeking_gender=None, goal=None, bio=None):
        """Оновлення профілю користувача"""
        try:
            # Спочатку перевіряємо чи існує користувач
            user = self.fetch_one_safe('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            
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
                if self.execute_safe(query, values):
                    logger.info(f"✅ Профіль користувача {telegram_id} оновлено")
                    return True
                return False
            else:
                logger.warning(f"⚠️ Немає полів для оновлення для користувача {telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка оновлення профілю {telegram_id}: {e}")
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
            user = self.fetch_one_safe('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            
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
            user = self.fetch_one_safe('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для додавання фото")
                return False
            
            # Перевіряємо кількість фото користувача
            result = self.fetch_one_safe('SELECT COUNT(*) FROM photos WHERE user_id = %s', (user['id'],))
            photo_count = result['count'] if result else 0
            
            # Якщо це перше фото, автоматично робимо його основним
            if photo_count == 0:
                is_main = True
            
            # Додаємо фото
            if self.execute_safe('''
                INSERT INTO photos (user_id, file_id, is_main)
                VALUES (%s, %s, %s)
            ''', (user['id'], file_id, is_main)):
                
                # Оновлюємо прапорець has_photo у користувача
                self.execute_safe('''
                    UPDATE users SET has_photo = TRUE 
                    WHERE telegram_id = %s
                ''', (telegram_id,))
                
                logger.info(f"✅ Фото додано для користувача {telegram_id}, is_main: {is_main}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання фото для {telegram_id}: {e}")
            return False

    def get_profile_photos(self, telegram_id):
        """Отримання фото профілю"""
        try:
            # Спочатку перевіряємо чи існує колонка is_main
            has_is_main = self.fetch_one_safe('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'photos' AND column_name = 'is_main'
            ''') is not None
            
            if has_is_main:
                photos = self.fetch_safe('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
                    ORDER BY p.is_main DESC, p.created_at ASC
                ''', (telegram_id,))
            else:
                # Якщо колонки is_main немає, використовуємо старий запит
                photos = self.fetch_safe('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
                    ORDER BY p.created_at ASC
                ''', (telegram_id,))
                
            return [photo['file_id'] for photo in photos]
        except Exception as e:
            logger.error(f"❌ Помилка отримання фото для {telegram_id}: {e}")
            return []

    def get_main_photo(self, telegram_id):
        """Отримання головного фото"""
        try:
            # Спочатку перевіряємо чи існує колонка is_main
            has_is_main = self.fetch_one_safe('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'photos' AND column_name = 'is_main'
            ''') is not None
            
            if has_is_main:
                result = self.fetch_one_safe('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s AND p.is_main = TRUE
                    ORDER BY p.created_at ASC
                    LIMIT 1
                ''', (telegram_id,))
            else:
                # Якщо колонки is_main немає, беремо перше фото
                result = self.fetch_one_safe('''
                    SELECT p.file_id FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
                    ORDER BY p.created_at ASC
                    LIMIT 1
                ''', (telegram_id,))
                
            return result['file_id'] if result else None
        except Exception as e:
            logger.error(f"❌ Помилка отримання головного фото для {telegram_id}: {e}")
            return None

    def set_main_photo(self, telegram_id, file_id):
        """Встановлення головного фото"""
        try:
            # Отримуємо ID користувача
            user = self.fetch_one_safe('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            
            if not user:
                return False
            
            # Спочатку скидаємо всі is_main на False
            self.execute_safe('''
                UPDATE photos SET is_main = FALSE 
                WHERE user_id = %s
            ''', (user['id'],))
            
            # Потім встановлюємо обране фото як головне
            if self.execute_safe('''
                UPDATE photos SET is_main = TRUE 
                WHERE user_id = %s AND file_id = %s
            ''', (user['id'], file_id)):
                logger.info(f"✅ Головне фото оновлено для {telegram_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Помилка встановлення головного фото для {telegram_id}: {e}")
            return False

    def delete_photo(self, telegram_id, file_id):
        """Видалення фото"""
        try:
            # Отримуємо ID користувача
            user = self.fetch_one_safe('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            
            if not user:
                return False
            
            # Видаляємо фото
            if self.execute_safe('''
                DELETE FROM photos 
                WHERE user_id = %s AND file_id = %s
            ''', (user['id'], file_id)):
                
                # Перевіряємо чи залишилися фото
                result = self.fetch_one_safe('SELECT COUNT(*) FROM photos WHERE user_id = %s', (user['id'],))
                remaining_photos = result['count'] if result else 0
                
                # Якщо фото не залишилося, оновлюємо has_photo
                if remaining_photos == 0:
                    self.execute_safe('''
                        UPDATE users SET has_photo = FALSE 
                        WHERE telegram_id = %s
                    ''', (telegram_id,))
                # Якщо видалили головне фото, встановлюємо нове головне
                else:
                    new_main = self.fetch_one_safe('''
                        SELECT file_id FROM photos 
                        WHERE user_id = %s 
                        ORDER BY created_at ASC 
                        LIMIT 1
                    ''', (user['id'],))
                    if new_main:
                        self.set_main_photo(telegram_id, new_main['file_id'])
                
                logger.info(f"✅ Фото видалено для {telegram_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Помилка видалення фото для {telegram_id}: {e}")
            return False

    def get_users_count(self):
        """Отримання загальної кількості користувачів"""
        try:
            result = self.fetch_one_safe('SELECT COUNT(*) FROM users')
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання кількості користувачів: {e}")
            return 0

    def get_statistics(self):
        """Отримання статистики"""
        try:
            # Кількість чоловіків
            male_result = self.fetch_one_safe('SELECT COUNT(*) FROM users WHERE gender = %s AND is_banned = FALSE', ('male',))
            male_count = male_result['count'] if male_result else 0
            
            # Кількість жінок
            female_result = self.fetch_one_safe('SELECT COUNT(*) FROM users WHERE gender = %s AND is_banned = FALSE', ('female',))
            female_count = female_result['count'] if female_result else 0
            
            # Загальна кількість активних користувачів
            active_result = self.fetch_one_safe('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND is_banned = FALSE')
            total_active = active_result['count'] if active_result else 0
            
            # Статистика цілей
            goals_stats = self.fetch_safe('SELECT goal, COUNT(*) FROM users WHERE goal IS NOT NULL AND is_banned = FALSE GROUP BY goal')
            
            return male_count, female_count, total_active, goals_stats
            
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    def get_random_user(self, exclude_telegram_id):
        """Отримання випадкового користувача"""
        try:
            return self.fetch_one_safe('''
                SELECT u.* FROM users u
                WHERE u.telegram_id != %s 
                AND u.age IS NOT NULL 
                AND u.gender IS NOT NULL
                AND u.is_banned = FALSE
                ORDER BY RANDOM()
                LIMIT 1
            ''', (exclude_telegram_id,))
        except Exception as e:
            logger.error(f"❌ Помилка отримання випадкового користувача: {e}")
            return None

    def get_all_active_users(self, exclude_telegram_id=None):
        """Отримання всіх активних користувачів"""
        try:
            if exclude_telegram_id:
                return self.fetch_safe('''
                    SELECT * FROM users 
                    WHERE telegram_id != %s 
                    AND age IS NOT NULL 
                    AND is_banned = FALSE
                    ORDER BY created_at DESC
                ''', (exclude_telegram_id,))
            else:
                return self.fetch_safe('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL 
                    AND is_banned = FALSE
                    ORDER BY created_at DESC
                ''')
        except Exception as e:
            logger.error(f"❌ Помилка отримання активних користувачів: {e}")
            return []

    def get_all_users(self):
        """Отримання всіх користувачів"""
        try:
            return self.fetch_safe('SELECT * FROM users ORDER BY created_at DESC')
        except Exception as e:
            logger.error(f"❌ Помилка отримання всіх користувачів: {e}")
            return []

    def get_banned_users(self):
        """Отримання заблокованих користувачів"""
        try:
            return self.fetch_safe('SELECT * FROM users WHERE is_banned = TRUE ORDER BY created_at DESC')
        except Exception as e:
            logger.error(f"❌ Помилка отримання заблокованих користувачів: {e}")
            return []

    def ban_user(self, telegram_id):
        """Блокування користувача"""
        try:
            if self.execute_safe('UPDATE users SET is_banned = TRUE WHERE telegram_id = %s', (telegram_id,)):
                return self.cursor.rowcount > 0
            return False
        except Exception as e:
            logger.error(f"❌ Помилка блокування користувача {telegram_id}: {e}")
            return False

    def unban_user(self, telegram_id):
        """Розблокування користувача"""
        try:
            if self.execute_safe('UPDATE users SET is_banned = FALSE WHERE telegram_id = %s', (telegram_id,)):
                return self.cursor.rowcount > 0
            return False
        except Exception as e:
            logger.error(f"❌ Помилка розблокування користувача {telegram_id}: {e}")
            return False

    def search_user(self, query):
        """Пошук користувача"""
        try:
            return self.fetch_safe('''
                SELECT * FROM users 
                WHERE telegram_id::TEXT LIKE %s 
                   OR username ILIKE %s 
                   OR first_name ILIKE %s
                ORDER BY created_at DESC
            ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
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
            if self.execute_safe('''
                INSERT INTO likes (from_user_id, to_user_id)
                VALUES ((SELECT id FROM users WHERE telegram_id = %s), 
                       (SELECT id FROM users WHERE telegram_id = %s))
                ON CONFLICT (from_user_id, to_user_id) DO NOTHING
            ''', (from_user_id, to_user_id)):
                
                if self.cursor.rowcount > 0:
                    # Оновлюємо кількість лайків
                    self.execute_safe('''
                        UPDATE users SET likes_count = likes_count + 1 
                        WHERE telegram_id = %s
                    ''', (to_user_id,))
                    
                    return True, "Лайк додано"
                else:
                    return False, "Лайк вже поставлено"
            return False, "Помилка додавання лайку"
                
        except Exception as e:
            logger.error(f"❌ Помилка додавання лайку: {e}")
            return False, "Помилка додавання лайку"

    def has_liked(self, from_user_id, to_user_id):
        """Перевірка чи користувач вже лайкнув"""
        try:
            result = self.fetch_one_safe('''
                SELECT 1 FROM likes 
                WHERE from_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                AND to_user_id = (SELECT id FROM users WHERE telegram_id = %s)
            ''', (from_user_id, to_user_id))
            return result is not None
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайку: {e}")
            return False

    def get_user_matches(self, telegram_id):
        """Отримання матчів користувача"""
        try:
            return self.fetch_safe('''
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
        except Exception as e:
            logger.error(f"❌ Помилка отримання матчів: {e}")
            return []

    def get_user_likers(self, telegram_id):
        """Отримання тих, хто лайкнув користувача"""
        try:
            return self.fetch_safe('''
                SELECT u.* FROM users u
                JOIN likes l ON u.id = l.from_user_id
                WHERE l.to_user_id = (SELECT id FROM users WHERE telegram_id = %s)
            ''', (telegram_id,))
        except Exception as e:
            logger.error(f"❌ Помилка отримання лайкерів: {e}")
            return []

    def add_profile_view(self, viewer_id, viewed_id):
        """Додавання перегляду профілю"""
        try:
            if self.execute_safe('''
                INSERT INTO profile_views (viewer_user_id, viewed_user_id)
                VALUES ((SELECT id FROM users WHERE telegram_id = %s), 
                       (SELECT id FROM users WHERE telegram_id = %s))
            ''', (viewer_id, viewed_id)):
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Помилка додавання перегляду: {e}")
            return False

    def get_profile_views(self, telegram_id):
        """Отримання переглядів профілю"""
        try:
            return self.fetch_safe('''
                SELECT u.* FROM users u
                JOIN profile_views pv ON u.id = pv.viewer_user_id
                WHERE pv.viewed_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                ORDER BY pv.viewed_at DESC
            ''', (telegram_id,))
        except Exception as e:
            logger.error(f"❌ Помилка отримання переглядів: {e}")
            return []

    def get_top_users_by_rating(self, limit=10, gender=None):
        """Отримання топу користувачів за рейтингом"""
        try:
            if gender:
                return self.fetch_safe('''
                    SELECT * FROM users 
                    WHERE gender = %s AND age IS NOT NULL AND is_banned = FALSE
                    ORDER BY rating DESC, likes_count DESC
                    LIMIT %s
                ''', (gender, limit))
            else:
                return self.fetch_safe('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL AND is_banned = FALSE
                    ORDER BY rating DESC, likes_count DESC
                    LIMIT %s
                ''', (limit,))
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
            self.execute_safe('UPDATE users SET rating = %s WHERE telegram_id = %s', (final_rating, telegram_id))
            
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
            self.execute_safe('''
                DELETE FROM likes 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM likes 
                    GROUP BY from_user_id, to_user_id
                )
            ''')
            
            # Видаляємо дублікати матчів
            self.execute_safe('''
                DELETE FROM matches 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM matches 
                    GROUP BY user1_id, user2_id
                )
            ''')
            
            logger.info("✅ Старі дані очищено")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка очищення даних: {e}")
            return False

    def reset_database(self):
        """Скидання бази даних"""
        try:
            # Видаляємо всі таблиці
            tables = ['profile_views', 'matches', 'likes', 'photos', 'users']
            for table in tables:
                self.execute_safe(f'DROP TABLE IF EXISTS {table} CASCADE')
            
            # Повторно ініціалізуємо базу
            self.init_db()
            
            logger.info("✅ База даних скинута та перестворена")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка скидання бази даних: {e}")
            return False

    def get_users_by_city(self, city, exclude_telegram_id):
        """Отримання користувачів за містом"""
        try:
            return self.fetch_safe('''
                SELECT * FROM users 
                WHERE city ILIKE %s 
                AND telegram_id != %s 
                AND age IS NOT NULL 
                AND is_banned = FALSE
                ORDER BY rating DESC
            ''', (f'%{city}%', exclude_telegram_id))
        except Exception as e:
            logger.error(f"❌ Помилка пошуку за містом {city}: {e}")
            return []

    def can_like_today(self, telegram_id):
        """Перевірка чи може користувач ставити лайки сьогодні"""
        try:
            # Проста перевірка - можна ставити до 50 лайків на день
            result = self.fetch_one_safe('''
                SELECT COUNT(*) FROM likes 
                WHERE from_user_id = (SELECT id FROM users WHERE telegram_id = %s)
                AND DATE(created_at) = CURRENT_DATE
            ''', (telegram_id,))
            likes_today = result['count'] if result else 0
            
            if likes_today >= 50:
                return False, f"Досягнуто ліміт лайків на сьогодні ({likes_today}/50)"
            return True, f"Лайків сьогодні: {likes_today}/50"
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайків: {e}")
            return True, "Ліміт не перевірено"

# Глобальний об'єкт бази даних
db = Database()