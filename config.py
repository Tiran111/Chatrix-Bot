import os

# Тепер токен буде з railway.toml
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')