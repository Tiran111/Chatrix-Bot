import logging
import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TOKEN = os.environ.get('BOT_TOKEN')

@app.route('/')
def home():
    return "🤖 Bot is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"✅ НОВИЙ токен! Привіт, {user.first_name}!")

def main():
    logger.info(f"🚀 Запуск бота з токеном: {TOKEN[:10]}...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        # Простий Flask
        def run_flask():
            port = int(os.environ.get('PORT', 10000))
            logger.info(f"🌐 Flask на порті {port}")
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
        import threading
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        logger.info("✅ Бот запускається...")
        application.run_polling(
            drop_pending_updates=True,
            timeout=10,
            pool_timeout=10
        )
        
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")

if __name__ == "__main__":
    main()