from flask import Flask, request
import logging
from keep_alive import start_keep_alive

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Запускаємо keep-alive при старті
start_keep_alive()

@app.route('/')
def home():
    return "🤖 Dating Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        logger.info("📨 Отримано вебхук від Telegram")
        
        # Тут ваш код обробки вебхука
        # ...
        
        return 'OK', 200
    except Exception as e:
        logger.error(f"❌ Помилка обробки вебхука: {e}")
        return 'Error', 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)