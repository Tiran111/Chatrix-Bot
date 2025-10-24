import requests
import os

TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"

# Перевірка інформації про вебхук
response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
print("📡 Стан вебхука:")
print(response.json())

# Спробуємо оновити вебхук
set_response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    data={"url": WEBHOOK_URL}
)
print("🔄 Оновлення вебхука:")
print(set_response.json())