import os

# Токен бота - береться з змінних середовища Render
TOKEN = os.environ.get('BOT_TOKEN', '7823150178:AAElnZEQB9nSwJxAZ_J75Mg-1UVaVWQcr-s')
ADMIN_ID = 1385645772

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

# Шлях до бази даних на Render
DATABASE_PATH = 'dating_bot.db'