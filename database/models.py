import sqlite3
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "dating_bot.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Ініціалізація бази даних"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблиця користувачів
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        name TEXT NOT NULL,
                        age INTEGER,
                        gender TEXT CHECK(gender IN ('male', 'female')),
                        city TEXT,
                        seeking_gender TEXT CHECK(seeking_gender IN ('male', 'female', 'all')),
                        goal TEXT,
                        bio TEXT,
                        likes_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_banned BOOLEAN DEFAULT FALSE,
                        ban_reason TEXT
                    )
                ''')
                
                # Таблиця фото
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS profile_photos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        file_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
                    )
                ''')
                
                # Таблиця лайків
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS likes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_user_id INTEGER NOT NULL,
                        to_user_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (from_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                        FOREIGN KEY (to_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                        UNIQUE(from_user_id, to_user_id)
                    )
                ''')
                
                # Таблиця матчів
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user1_id INTEGER NOT NULL,
                        user2_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user1_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                        FOREIGN KEY (user2_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                        UNIQUE(user1_id, user2_id)
                    )
                ''')
                
                conn.commit()
                logger.info("✅ База даних ініціалізована")
                
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка ініціалізації БД: {e}")

    def add_user(self, telegram_id: int, username: str, name: str) -> bool:
        """Додати користувача"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO users (telegram_id, username, name)
                    VALUES (?, ?, ?)
                ''', (telegram_id, username, name))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка додавання користувача: {e}")
            return False

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Отримати дані користувача"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання користувача: {e}")
            return None

    def update_user_profile(self, telegram_id: int, age: int, gender: str, city: str, 
                          seeking_gender: str, goal: str, bio: str) -> bool:
        """Оновити профіль користувача"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET age = ?, gender = ?, city = ?, seeking_gender = ?, goal = ?, bio = ?, last_active = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                ''', (age, gender, city, seeking_gender, goal, bio, telegram_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка оновлення профілю: {e}")
            return False

    def get_user_profile(self, telegram_id: int) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Отримати профіль користувача та чи він заповнений"""
        user = self.get_user(telegram_id)
        if not user:
            return None, False
        
        is_complete = all([
            user.get('age'),
            user.get('gender'), 
            user.get('city'),
            user.get('bio')
        ])
        
        return user, is_complete

    def add_profile_photo(self, telegram_id: int, file_id: str) -> bool:
        """Додати фото профілю"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Перевіряємо кількість фото
                cursor.execute('SELECT COUNT(*) FROM profile_photos WHERE user_id = ?', (telegram_id,))
                count = cursor.fetchone()[0]
                
                if count >= 3:
                    return False  # Максимум 3 фото
                
                cursor.execute('''
                    INSERT INTO profile_photos (user_id, file_id)
                    VALUES (?, ?)
                ''', (telegram_id, file_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка додавання фото: {e}")
            return False

    def get_profile_photos(self, telegram_id: int) -> List[str]:
        """Отримати фото профілю"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT file_id FROM profile_photos WHERE user_id = ? ORDER BY created_at', (telegram_id,))
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання фото: {e}")
            return []

    def get_users_for_search(self, current_user_id: int, seeking_gender: str = None) -> List[Tuple]:
        """Отримати користувачів для пошуку"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT u.telegram_id, u.name, u.age, u.gender, u.city, u.bio, u.goal, u.likes_count
                    FROM users u
                    WHERE u.telegram_id != ? 
                    AND u.age IS NOT NULL 
                    AND u.gender IS NOT NULL
                    AND u.city IS NOT NULL
                    AND u.bio IS NOT NULL
                    AND u.is_banned = FALSE
                '''
                params = [current_user_id]
                
                if seeking_gender and seeking_gender != 'all':
                    query += ' AND u.gender = ?'
                    params.append(seeking_gender)
                
                query += ' ORDER BY u.last_active DESC LIMIT 100'
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка пошуку користувачів: {e}")
            return []

    def get_users_by_city(self, city: str, current_user_id: int) -> List[Tuple]:
        """Отримати користувачів по місту"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.telegram_id, u.name, u.age, u.gender, u.city, u.bio, u.goal, u.likes_count
                    FROM users u
                    WHERE u.city LIKE ? 
                    AND u.telegram_id != ? 
                    AND u.age IS NOT NULL 
                    AND u.is_banned = FALSE
                    ORDER BY u.last_active DESC
                    LIMIT 50
                ''', (f'%{city}%', current_user_id))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка пошуку по місту: {e}")
            return []

    def add_like(self, from_user_id: int, to_user_id: int) -> bool:
        """Додати лайк"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Перевіряємо чи вже лайкали
                cursor.execute('SELECT 1 FROM likes WHERE from_user_id = ? AND to_user_id = ?', (from_user_id, to_user_id))
                if cursor.fetchone():
                    return False
                
                # Додаємо лайк
                cursor.execute('''
                    INSERT INTO likes (from_user_id, to_user_id)
                    VALUES (?, ?)
                ''', (from_user_id, to_user_id))
                
                # Оновлюємо лічильник лайків
                cursor.execute('UPDATE users SET likes_count = likes_count + 1 WHERE telegram_id = ?', (to_user_id,))
                
                # Перевіряємо чи це взаємний лайк (матч)
                cursor.execute('SELECT 1 FROM likes WHERE from_user_id = ? AND to_user_id = ?', (to_user_id, from_user_id))
                if cursor.fetchone():
                    # Створюємо матч
                    cursor.execute('''
                        INSERT OR IGNORE INTO matches (user1_id, user2_id)
                        VALUES (?, ?)
                    ''', (min(from_user_id, to_user_id), max(from_user_id, to_user_id)))
                
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка додавання лайку: {e}")
            return False

    def get_likes_received(self, user_id: int) -> List[Tuple]:
        """Отримати лайки, отримані користувачем"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.telegram_id, u.name, u.age, u.city
                    FROM likes l
                    JOIN users u ON l.from_user_id = u.telegram_id
                    WHERE l.to_user_id = ? AND u.is_banned = FALSE
                    ORDER BY l.created_at DESC
                ''', (user_id,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання лайків: {e}")
            return []

    def get_matches(self, user_id: int) -> List[Tuple]:
        """Отримати матчі користувача"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.telegram_id, u.name, u.age, u.city, u.bio
                    FROM matches m
                    JOIN users u ON (m.user1_id = u.telegram_id OR m.user2_id = u.telegram_id)
                    WHERE (m.user1_id = ? OR m.user2_id = ?) AND u.telegram_id != ? AND u.is_banned = FALSE
                    ORDER BY m.created_at DESC
                ''', (user_id, user_id, user_id))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання матчів: {e}")
            return []

    def get_top_users(self, limit: int = 10, gender: str = None) -> List[Tuple]:
        """Отримати топ користувачів"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT telegram_id, name, age, city, likes_count
                    FROM users 
                    WHERE age IS NOT NULL AND is_banned = FALSE
                '''
                params = []
                
                if gender:
                    query += ' AND gender = ?'
                    params.append(gender)
                
                query += ' ORDER BY likes_count DESC, last_active DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання топу: {e}")
            return []

    def get_statistics(self) -> Tuple[int, int, int, List[Tuple]]:
        """Отримати статистику"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Чоловіки
                cursor.execute('SELECT COUNT(*) FROM users WHERE gender = "male" AND age IS NOT NULL AND is_banned = FALSE')
                male = cursor.fetchone()[0]
                
                # Жінки
                cursor.execute('SELECT COUNT(*) FROM users WHERE gender = "female" AND age IS NOT NULL AND is_banned = FALSE')
                female = cursor.fetchone()[0]
                
                # Активні користувачі
                cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND is_banned = FALSE')
                total_active = cursor.fetchone()[0]
                
                # Статистика цілей
                cursor.execute('''
                    SELECT goal, COUNT(*) 
                    FROM users 
                    WHERE goal IS NOT NULL AND is_banned = FALSE
                    GROUP BY goal 
                    ORDER BY COUNT(*) DESC
                ''')
                goals_stats = cursor.fetchall()
                
                return male, female, total_active, goals_stats
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    def get_detailed_statistics(self):
        """Детальна статистика"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Загальна кількість користувачів
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                # Активні користувачі
                cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND is_banned = FALSE')
                active_users = cursor.fetchone()[0]
                
                # Чоловіки/жінки
                cursor.execute('SELECT COUNT(*) FROM users WHERE gender = "male" AND is_banned = FALSE')
                male_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM users WHERE gender = "female" AND is_banned = FALSE')
                female_count = cursor.fetchone()[0]
                
                # Середній вік
                cursor.execute('SELECT AVG(age) FROM users WHERE age IS NOT NULL AND is_banned = FALSE')
                avg_age = cursor.fetchone()[0] or 0
                
                # Статистика цілей
                cursor.execute('''
                    SELECT goal, COUNT(*) 
                    FROM users 
                    WHERE goal IS NOT NULL AND is_banned = FALSE
                    GROUP BY goal 
                    ORDER BY COUNT(*) DESC
                ''')
                goals_stats = cursor.fetchall()
                
                # Статистика міст
                cursor.execute('''
                    SELECT city, COUNT(*) 
                    FROM users 
                    WHERE city IS NOT NULL AND is_banned = FALSE
                    GROUP BY city 
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                ''')
                cities_stats = cursor.fetchall()
                
                return total_users, active_users, male_count, female_count, avg_age, goals_stats, cities_stats
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка детальної статистики: {e}")
            return 0, 0, 0, 0, 0, [], []

    def get_users_count(self) -> int:
        """Отримати кількість користувачів"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка підрахунку користувачів: {e}")
            return 0

    def get_all_users(self) -> List[Tuple]:
        """Отримати всіх користувачів"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users')
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання користувачів: {e}")
            return []

    def get_all_active_users(self, exclude_user_id: int = None) -> List[Tuple]:
        """Отримати всіх активних користувачів"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if exclude_user_id:
                    cursor.execute('''
                        SELECT * FROM users 
                        WHERE age IS NOT NULL AND is_banned = FALSE AND telegram_id != ?
                        ORDER BY last_active DESC
                    ''', (exclude_user_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM users 
                        WHERE age IS NOT NULL AND is_banned = FALSE
                        ORDER BY last_active DESC
                    ''')
                
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання активних користувачів: {e}")
            return []

    def get_banned_users(self) -> List[Tuple]:
        """Отримати заблокованих користувачів"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE is_banned = TRUE')
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка отримання заблокованих: {e}")
            return []

    def ban_user(self, user_id: int, reason: str = "Порушення правил") -> bool:
        """Заблокувати користувача"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET is_banned = TRUE, ban_reason = ?
                    WHERE telegram_id = ?
                ''', (reason, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка блокування: {e}")
            return False

    def unban_user(self, user_id: int) -> bool:
        """Розблокувати користувача"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET is_banned = FALSE, ban_reason = NULL
                    WHERE telegram_id = ?
                ''', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка розблокування: {e}")
            return False

    def search_users_by_name(self, name: str) -> List[Tuple]:
        """Пошук користувачів по імені"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE name LIKE ? AND is_banned = FALSE
                    ORDER BY last_active DESC
                    LIMIT 20
                ''', (f'%{name}%',))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"❌ Помилка пошуку по імені: {e}")
            return []

# Глобальний екземпляр бази даних
db = Database()