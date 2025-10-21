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

    def update_database_structure(self):
        """Оновлення структури бази даних"""
        try:
            logger.info("🔄 Перевірка структури бази даних...")
            
            # Перевіряємо наявність стовпців
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            columns = [row['column_name'] for row in self.cursor.fetchall()]
            
            logger.info(f"🔍 Наявні стовпці: {columns}")
            
            changes_made = False
            
            # Додаємо відсутні стовпці
            if 'first_name' not in columns:
                logger.info("➕ Додаємо стовпець first_name...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN first_name TEXT')
                changes_made = True
            
            if 'last_active' not in columns:
                logger.info("➕ Додаємо стовпець last_active...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN last_active TIMESTAMP')
                changes_made = True
            
            if 'rating' not in columns:
                logger.info("➕ Додаємо стовпець rating...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN rating REAL')
                changes_made = True
            
            if 'daily_likes_count' not in columns:
                logger.info("➕ Додаємо стовпець daily_likes_count...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN daily_likes_count INTEGER')
                changes_made = True
            
            if 'last_like_date' not in columns:
                logger.info("➕ Додаємо стовпець last_like_date...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN last_like_date DATE')
                changes_made = True
            
            if changes_made:
                self.conn.commit()
                logger.info("✅ Структура бази даних оновлена")
                self.initialize_new_columns()
            else:
                logger.info("✅ Структура бази даних вже актуальна")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення структури БД: {e}")

    def initialize_new_columns(self):
        """Ініціалізація значень для нових стовпців"""
        try:
            logger.info("🔄 Ініціалізація значень для нових стовпців...")
            
            self.cursor.execute("UPDATE users SET first_name = 'Користувач' WHERE first_name IS NULL")
            self.cursor.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE last_active IS NULL")
            self.cursor.execute("UPDATE users SET rating = 5.0 WHERE rating IS NULL")
            self.cursor.execute("UPDATE users SET daily_likes_count = 0 WHERE daily_likes_count IS NULL")
            
            self.conn.commit()
            logger.info("✅ Значення для нових стовпців ініціалізовані")
            
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації стовпців: {e}")

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
            logger.info(f"🔄 Дані для оновлення: вік={age}, стать={gender}, місто={city}, шукає={seeking_gender}, ціль={goal}")
        
            # Спочатку перевіряємо чи користувач існує
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
        
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено")
                return False
        
            # Оновлюємо профіль
            self.cursor.execute('''
                UPDATE users 
                SET age = %s, gender = %s, city = %s, seeking_gender = %s, goal = %s, bio = %s, 
                    last_active = CURRENT_TIMESTAMP, has_photo = TRUE
                WHERE telegram_id = %s
            ''', (age, gender, city, seeking_gender, goal, bio, telegram_id))
        
            # Оновлюємо рейтинг
            self.update_user_rating(telegram_id)
        
            self.conn.commit()
        
            logger.info(f"✅ Профіль оновлено для {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення профілю: {e}")
            self.conn.rollback()
            return False

    def update_user_rating(self, telegram_id):
        """Оновлення рейтингу користувача"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return
            
            base_rating = 5.0
            bonus = 0.0
            
            if user.get('has_photo'):
                bonus += 1.0
            
            if user.get('bio') and len(user.get('bio', '')) > 20:
                bonus += 1.0
            
            likes_count = user.get('likes_count', 0)
            bonus += min(likes_count * 0.1, 3.0)
            
            new_rating = min(base_rating + bonus, 10.0)
            
            self.cursor.execute('UPDATE users SET rating = %s WHERE telegram_id = %s', (new_rating, telegram_id))
            logger.info(f"✅ Рейтинг оновлено для {telegram_id}: {new_rating}")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення рейтингу: {e}")

    def get_random_user(self, current_user_id, city=None):
        """Отримання випадкового користувача для пошуку"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                logger.error(f"❌ Поточного користувача {current_user_id} не знайдено")
                return None
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            current_gender = current_user.get('gender')
            
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != %s AND u.age IS NOT NULL 
                AND u.has_photo = TRUE AND u.is_banned = FALSE
            '''
            params = [current_user_id]
            
            if seeking_gender != 'all':
                query += ' AND u.gender = %s'
                params.append(seeking_gender)
            
            if city:
                query += ' AND u.city LIKE %s'
                params.append(f'%{city}%')
            
            # ДЛЯ АДМІНА - не виключаємо вже лайкнутих користувачів
            admin_id_str = os.environ.get('ADMIN_ID', '0')
            if str(current_user_id) != admin_id_str:  # Тільки для звичайних користувачів
                query += ' AND u.telegram_id NOT IN (SELECT u2.telegram_id FROM users u2 JOIN likes l ON u2.id = l.to_user_id JOIN users u3 ON u3.id = l.from_user_id WHERE u3.telegram_id = %s)'
                params.append(current_user_id)
            
            query += ' ORDER BY RANDOM() LIMIT 1'
            
            self.cursor.execute(query, params)
            user = self.cursor.fetchone()
            
            return user
        except Exception as e:
            logger.error(f"❌ Помилка отримання випадкового користувача: {e}")
            return None

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
            
            current_photos = self.get_profile_photos(telegram_id)
            if len(current_photos) >= 3:
                logger.error("❌ Досягнуто ліміт фото (максимум 3)")
                return False
            
            self.cursor.execute('INSERT INTO photos (user_id, file_id) VALUES (%s, %s)', (user_id, file_id))
            self.cursor.execute('UPDATE users SET has_photo = TRUE WHERE telegram_id = %s', (telegram_id,))
            self.update_user_rating(telegram_id)
            
            self.conn.commit()
            logger.info("✅ Фото успішно додано до бази даних!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання фото: {e}")
            return False

    def get_main_photo(self, telegram_id):
        """Отримання першого фото користувача"""
        try:
            self.cursor.execute('''
                SELECT p.file_id FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = %s
                LIMIT 1
            ''', (telegram_id,))
            result = self.cursor.fetchone()
            return result['file_id'] if result else None
        except Exception as e:
            logger.error(f"❌ Помилка отримання фото: {e}")
            return None

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
            if user and user['age'] is not None:
                return user, True
            return user, False
        except Exception as e:
            logger.error(f"❌ Помилка отримання профілю: {e}")
            return None, False

    def get_users_by_city(self, city, current_user_id):
        """Отримання користувачів за містом"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                return []
        
            seeking_gender = current_user.get('seeking_gender', 'all')
        
            # Очищаємо назву міста від емодзі та зайвих пробілів
            clean_city = city.replace('🏙️', '').strip()
        
            logger.info(f"🔍 [CITY SEARCH] Шукаємо в місті: '{clean_city}', шукає стать: {seeking_gender}")
        
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != %s 
                AND LOWER(u.city) LIKE LOWER(%s)
                AND u.age IS NOT NULL 
                AND u.has_photo = TRUE 
                AND u.is_banned = FALSE
            '''
            params = [current_user_id, f'%{clean_city}%']
        
            if seeking_gender != 'all':
                query += ' AND u.gender = %s'
                params.append(seeking_gender)
        
            # Виключаємо вже лайкнутих користувачів
            admin_id_str = os.environ.get('ADMIN_ID', '0')
            if str(current_user_id) != admin_id_str:
                query += ' AND u.telegram_id NOT IN (SELECT u2.telegram_id FROM users u2 JOIN likes l ON u2.id = l.to_user_id JOIN users u3 ON u3.id = l.from_user_id WHERE u3.telegram_id = %s)'
                params.append(current_user_id)
        
            query += ' ORDER BY RANDOM() LIMIT 20'
        
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
        
            logger.info(f"🔍 [CITY SEARCH] Знайдено користувачів: {len(users)}")
        
            return users
        except Exception as e:
            logger.error(f"❌ Помилка пошуку за містом: {e}")
            return []

    def get_likes_count(self, user_id):
        """Отримання кількості лайків"""
        try:
            self.cursor.execute('SELECT likes_count FROM users WHERE telegram_id = %s', (user_id,))
            result = self.cursor.fetchone()
            return result['likes_count'] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання лайків: {e}")
            return 0

    def can_like_today(self, user_id):
        """Перевірка чи може користувач ставити лайки сьогодні"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False, "Користувача не знайдено"
            
            today = date.today()
            last_like_date = user.get('last_like_date')
            daily_likes = user.get('daily_likes_count', 0)
            
            if last_like_date != today:
                self.cursor.execute(
                    'UPDATE users SET daily_likes_count = 0, last_like_date = %s WHERE telegram_id = %s',
                    (today, user_id)
                )
                self.conn.commit()
                return True, "Можна ставити лайки"
            
            if daily_likes >= 50:
                return False, "Досягнуто денний ліміт лайків (50)"
            
            return True, f"Залишилось лайків: {50 - daily_likes}"
            
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайків: {e}")
            return False, "Помилка перевірки"

    def add_like(self, from_user_id, to_user_id):
        """Додавання лайку з перевіркою обмежень"""
        try:
            can_like, message = self.can_like_today(from_user_id)
            if not can_like:
                return False, message
            
            if self.has_liked(from_user_id, to_user_id):
                return False, "Ви вже лайкали цього користувача"
            
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (from_user_id,))
            from_user = self.cursor.fetchone()
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (to_user_id,))
            to_user = self.cursor.fetchone()
            
            if not from_user or not to_user:
                return False, "Користувача не знайдено"
            
            self.cursor.execute('INSERT INTO likes (from_user_id, to_user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (from_user['id'], to_user['id']))
            self.cursor.execute('UPDATE users SET likes_count = likes_count + 1 WHERE id = %s', (to_user['id'],))
            
            today = date.today()
            self.cursor.execute(
                'UPDATE users SET daily_likes_count = daily_likes_count + 1, last_like_date = %s WHERE telegram_id = %s',
                (today, from_user_id)
            )
            
            self.update_user_rating(to_user_id)
            
            self.conn.commit()
            
            is_mutual = self.has_liked(to_user_id, from_user_id)
            
            if is_mutual:
                self.cursor.execute('''
                    INSERT INTO matches (user1_id, user2_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING
                ''', (min(from_user['id'], to_user['id']), max(from_user['id'], to_user['id'])))
                self.conn.commit()
            
            return True, "Лайк додано" if not is_mutual else "Лайк додано! 💕 У вас матч!"
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання лайку: {e}")
            return False, "Помилка додавання лайку"

    def get_user_matches(self, telegram_id):
        """Отримання матчів користувача"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            if not user:
                return []
            
            self.cursor.execute('''
                SELECT DISTINCT u.* FROM users u
                JOIN matches m ON (u.id = m.user1_id OR u.id = m.user2_id)
                WHERE (m.user1_id = %s OR m.user2_id = %s) AND u.id != %s
            ''', (user['id'], user['id'], user['id']))
            
            matches = self.cursor.fetchall()
            return matches
        except Exception as e:
            logger.error(f"❌ Помилка отримання матчів: {e}")
            return []

    def get_top_users_by_rating(self, limit=10, gender=None):
        """Отримання топу користувачів за рейтингом"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE is_banned = FALSE AND age IS NOT NULL AND has_photo = TRUE
            '''
            params = []
            
            if gender:
                query += ' AND gender = %s'
                params.append(gender)
                
            query += ' ORDER BY rating DESC, likes_count DESC LIMIT %s'
            params.append(limit)
            
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
            
            return users
        except Exception as e:
            logger.error(f"❌ Помилка отримання топу за рейтингом: {e}")
            return []

    def get_user_likers(self, telegram_id):
        """Отримати список користувачів, які лайкнули поточного користувача"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            if not user:
                return []
            
            self.cursor.execute('''
                SELECT u.* FROM users u
                JOIN likes l ON u.id = l.from_user_id
                JOIN users target ON target.id = l.to_user_id
                WHERE target.telegram_id = %s AND u.telegram_id != %s
            ''', (telegram_id, telegram_id))
            
            likers = self.cursor.fetchall()
            return likers
        except Exception as e:
            logger.error(f"❌ Помилка отримання лайкерів: {e}")
            return []

    def has_liked(self, from_user_id, to_user_id):
        """Перевірити чи поставив користувач лайк іншому користувачу"""
        try:
            self.cursor.execute('''
                SELECT l.id FROM likes l
                JOIN users u1 ON u1.id = l.from_user_id
                JOIN users u2 ON u2.id = l.to_user_id
                WHERE u1.telegram_id = %s AND u2.telegram_id = %s
            ''', (from_user_id, to_user_id))
            
            result = self.cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайку: {e}")
            return False

    def get_statistics(self):
        """Отримання статистики"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = %s AND age IS NOT NULL', ('male',))
            male = self.cursor.fetchone()['count']
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = %s AND age IS NOT NULL', ('female',))
            female = self.cursor.fetchone()['count']
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND has_photo = TRUE')
            total_active = self.cursor.fetchone()['count']
            
            self.cursor.execute('SELECT goal, COUNT(*) FROM users WHERE goal IS NOT NULL GROUP BY goal')
            goals_stats = self.cursor.fetchall()
            
            return male, female, total_active, goals_stats
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    def get_users_count(self):
        """Отримання загальної кількості користувачів"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()['count']
        except Exception as e:
            logger.error(f"❌ Помилка отримання кількості користувачів: {e}")
            return 0

    def get_all_users(self):
        """Отримання всіх користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            users = self.cursor.fetchall()
            return users
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувачів: {e}")
            return []

    def get_banned_users(self):
        """Отримання заблокованих користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE is_banned = TRUE')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання заблокованих: {e}")
            return []

    def get_all_active_users(self, exclude_user_id=None):
        """Отримання всіх активних користувачів"""
        try:
            if exclude_user_id:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE AND telegram_id != %s
                    ORDER BY last_active DESC
                ''', (exclude_user_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE
                    ORDER BY last_active DESC
                ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання активних користувачів: {e}")
            return []

    def search_users_advanced(self, user_id, gender, city, goal):
        """Розширений пошук користувачів"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE telegram_id != %s AND age IS NOT NULL 
                AND has_photo = TRUE AND is_banned = FALSE
            '''
            params = [user_id]
            
            if gender != 'all':
                query += ' AND gender = %s'
                params.append(gender)
            
            if city:
                query += ' AND city LIKE %s'
                params.append(f'%{city}%')
            
            if goal:
                query += ' AND goal = %s'
                params.append(goal)
            
            query += ' ORDER BY RANDOM() LIMIT 20'
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка розширеного пошуку: {e}")
            return []

    def cleanup_old_data(self):
        """Очищення старих даних"""
        try:
            self.cursor.execute('''
                DELETE FROM users 
                WHERE age IS NULL AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
            ''')
            
            self.cursor.execute('''
                DELETE FROM likes 
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
            ''')
            
            self.conn.commit()
            logger.info("✅ Старі дані очищено")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка очищення даних: {e}")
            return False

    def ban_user(self, telegram_id):
        """Заблокувати користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для блокування")
                return False
            
            self.cursor.execute('UPDATE users SET is_banned = TRUE WHERE telegram_id = %s', (telegram_id,))
            self.conn.commit()
            logger.info(f"✅ Користувач {telegram_id} заблокований")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка блокування користувача {telegram_id}: {e}")
            return False

    def unban_user(self, telegram_id):
        """Розблокувати користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для розблокування")
                return False
            
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE telegram_id = %s', (telegram_id,))
            self.conn.commit()
            logger.info(f"✅ Користувач {telegram_id} розблокований")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка розблокування користувача {telegram_id}: {e}")
            return False

    def unban_all_users(self):
        """Розблокувати всіх користувачів"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE is_banned = TRUE')
            self.conn.commit()
            logger.info("✅ Всі користувачі розблоковані")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка розблокування всіх користувачів: {e}")
            return False

    def search_user(self, query):
        """Пошук користувача за ID або іменем"""
        try:
            try:
                user_id = int(query)
                self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (user_id,))
                result_by_id = self.cursor.fetchall()
                if result_by_id:
                    return result_by_id
            except ValueError:
                pass
            
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE first_name ILIKE %s OR username ILIKE %s
                ORDER BY created_at DESC
            ''', (f'%{query}%', f'%{query}%'))
            
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"❌ Помилка пошуку користувача: {e}")
            return []

    def get_user_by_id(self, telegram_id):
        """Отримати користувача за telegram_id"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувача: {e}")
            return None

    def update_user_name(self, telegram_id, first_name):
        """Оновити ім'я користувача"""
        try:
            self.cursor.execute('''
                UPDATE users SET first_name = %s WHERE telegram_id = %s
            ''', (first_name, telegram_id))
            self.conn.commit()
            logger.info(f"✅ Ім'я оновлено для {telegram_id}: {first_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка оновлення імені: {e}")
            return False

    def add_profile_view(self, viewer_id, viewed_user_id):
        """Додати запис про перегляд профілю"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (viewer_id,))
            viewer = self.cursor.fetchone()
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = %s', (viewed_user_id,))
            viewed = self.cursor.fetchone()
            
            if viewer and viewed:
                self.cursor.execute('''
                    INSERT INTO profile_views (viewer_id, viewed_user_id)
                    VALUES (%s, %s)
                ''', (viewer['id'], viewed['id']))
                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Помилка додавання перегляду: {e}")
        return False

    def debug_user_profile(self, telegram_id):
        """Відладка профілю користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
            user = self.cursor.fetchone()
            
            if user:
                logger.info(f"🔍 [DEBUG USER] ID: {user['telegram_id']}")
                logger.info(f"🔍 [DEBUG USER] Ім'я: {user['first_name']}")
                logger.info(f"🔍 [DEBUG USER] Вік: {user['age']}")
                logger.info(f"🔍 [DEBUG USER] Стать: {user['gender']}")
                logger.info(f"🔍 [DEBUG USER] Місто: {user['city']}")
                logger.info(f"🔍 [DEBUG USER] Фото: {user['has_photo']}")
                logger.info(f"🔍 [DEBUG USER] Лайків: {user['likes_count']}")
                logger.info(f"🔍 [DEBUG USER] Рейтинг: {user['rating']}")
                logger.info(f"🔍 [DEBUG USER] Заблокований: {user['is_banned']}")
                return True
            else:
                logger.info(f"🔍 [DEBUG USER] Користувача {telegram_id} не знайдено")
                return False
        except Exception as e:
            logger.error(f"❌ Помилка відладки: {e}")
            return False

    def calculate_user_rating(self, user_id):
        """Розрахунок рейтингу користувача"""
        try:
            user = self.get_user(user_id)
            if not user:
                return 5.0
            
            base_rating = 5.0
            bonus = 0.0
            
            if user.get('has_photo'):
                bonus += 1.0
            
            if user.get('bio') and len(user.get('bio', '')) > 20:
                bonus += 1.0
            
            likes_count = user.get('likes_count', 0)
            bonus += min(likes_count * 0.1, 3.0)
            
            if user.get('last_active'):
                try:
                    last_active = user['last_active']
                    if isinstance(last_active, str):
                        last_active = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                    
                    days_since_active = (datetime.now().replace(tzinfo=last_active.tzinfo) - last_active).days
                    if days_since_active <= 7:
                        bonus += 0.5
                except:
                    pass
            
            final_rating = min(base_rating + bonus, 10.0)
            return round(final_rating, 1)
        except Exception as e:
            logger.error(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

    def update_all_ratings(self):
        """Оновити рейтинги всіх користувачів"""
        try:
            self.cursor.execute('SELECT telegram_id FROM users WHERE age IS NOT NULL')
            users = self.cursor.fetchall()
            
            updated_count = 0
            for user in users:
                telegram_id = user['telegram_id']
                new_rating = self.calculate_user_rating(telegram_id)
                self.cursor.execute('UPDATE users SET rating = %s WHERE telegram_id = %s', (new_rating, telegram_id))
                updated_count += 1
            
            self.conn.commit()
            logger.info(f"✅ Оновлено рейтинги для {updated_count} користувачів")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка оновлення рейтингів: {e}")
            return False

    def reset_database(self):
        """Скидання бази даних (для адміна)"""
        try:
            logger.info("🔄 Скидання бази даних...")
            
            # Видаляємо всі таблиці
            self.cursor.execute('DROP TABLE IF EXISTS likes CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS matches CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS photos CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS profile_views CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS users CASCADE')
            
            self.conn.commit()
            
            # Перестворюємо таблиці
            self.init_db()
            
            logger.info("✅ База даних скинута та перестворена")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка скидання БД: {e}")
            self.conn.rollback()
            return False

    def get_profile_views(self, telegram_id):
        """Отримати список користувачів, які переглядали профіль"""
        try:
            self.cursor.execute('''
                SELECT u.* FROM users u
                JOIN profile_views pv ON u.id = pv.viewer_id
                JOIN users target ON target.id = pv.viewed_user_id
                WHERE target.telegram_id = %s AND u.telegram_id != %s
                ORDER BY pv.viewed_at DESC
            ''', (telegram_id, telegram_id))
        
            viewers = self.cursor.fetchall()
            return viewers
        except Exception as e:
            logger.error(f"❌ Помилка отримання переглядів: {e}")
            return []        

# Глобальний екземпляр бази даних
db = Database()