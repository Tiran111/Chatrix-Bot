import os

# Отримуємо змінні оточення
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # ТОКЕН БУДЕ БРАТИСЯ З RAILWAY
ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')