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
else:
    logging.error("GEMINI_API_KEY belum disetel di environment variables!")

# Flask Keep-Alive Server untuk Railway (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot is running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def get_ai_response(prompt):
    """Fungsi helper untuk mencoba beberapa variasi nama model Gemini secara otomatis"""
    model_names = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-pro', 'models/gemini-1.5-pro', 'gemini-pro']
    
    last_error = ""
    for m_name in model_names:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            continue
            
    return f"Maaf krim, semua model Gemini gagal diakses. Error terakhir: {last_error}"

# Handler Pesan Telegram
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logging.info(f"Pesan diterima: {user_message}")

    if not GEMINI_API_KEY:
        await update.message.reply_text("Duh, API Key Gemini belum dipasang di Railway nih bos.")
        return

    try:
        # Panggil helper yang otomatis nge-test berbagai nama model
        reply_text = get_ai_response(user_message)
        await update.message.reply_text(reply_text)
    except Exception as e:
        logging.error(f"Error Handler: {e}")
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
