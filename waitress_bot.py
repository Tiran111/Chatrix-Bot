from waitress import serve
from flask import Flask, request
import os
import asyncio
from telegram.ext import Application, CommandHandler
from telegram import Update

app = Flask(__name__)
TOKEN = os.environ.get('BOT_TOKEN')
application = None

async def start(update: Update, context):
    await update.message.reply_text("🚀 Chatrix Bot працює з Waitress!")

async def init_bot():
    global application
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    await application.initialize()
    await application.bot.set_webhook("https://chatrix-bot-4m1p.onrender.com/webhook")
    await application.start()
    print("✅ Бот ініціалізовано")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), application.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
        return 'ok'
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return 'error', 500

@app.route('/')
def home():
    return "🤖 Bot is running with Waitress! ✅", 200

if __name__ == '__main__':
    # Ініціалізація бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_bot())
    
    # Запуск з waitress
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Запуск з Waitress на порті {port}")
    serve(app, host='0.0.0.0', port=port)