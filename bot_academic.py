import os
import logging
from flask import Flask
from threading import Thread
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Konfigurasi Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Menggunakan model gemini-1.5-flash yang cepat dan stabil
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None
    logging.error("GEMINI_API_KEY belum disetel di environment variables!")

# Flask Keep-Alive Server untuk Railway (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot is running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Handler Pesan Telegram
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logging.info(f"Pesan diterima: {user_message}")

    if not model:
        await update.message.reply_text("Duh, API Key Gemini belum dipasang di Railway nih bos.")
        return

    try:
        # Panggilan standar Gemini AI
        response = model.generate_content(user_message)
        reply_text = response.text
        await update.message.reply_text(reply_text)
    except Exception as e:
        logging.error(f"Error Gemini API: {e}")
        await update.message.reply_text(f"Duh, otak AI-ku error: {str(e)}")

def main():
    token = os.getenv("IZUMI_ACADEMIC_TOKEN")
    if not token:
        logging.error("IZUMI_ACADEMIC_TOKEN tidak ditemukan di environment variables!")
        return

    # Jalankan server Flask di background thread agar tidak memblokir bot Telegram
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Jalankan Bot Telegram
    application = ApplicationBuilder().token(token).build()
    
    # Menerima semua pesan teks
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logging.info("Izumi Academic Bot mulai melakukan polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
