import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# Konfigurasi Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Ambil Variabel Lingkungan
TOKEN = os.getenv("IZUMI_COMMAND_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8791729948"))

# Konfigurasi Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App Sederhana untuk UptimeRobot (Anti-Tidur Railway - Port 8083)
app = Flask('')

@app.route('/')
def home():
    return "Izumi Command & Control Bot is alive and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8083)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Handler Kontrol Sistem & Instruksi Manajemen
async def handle_command_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Keamanan Mutlak: Tolak jika bukan kamu!
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Akses ditolak. Ini pusat kontrol sistem Izumi.")
        return

    user_text = update.message.text
    logging.info(f"Perintah sistem dari Admin: {user_text}")

    prompt = f"""
    Kamu adalah Izumi Command, pusat kendali sistem dan manajemen operasional untuk Ikrimah. 
    Ikrimah memberikan instruksi kontrol sistem atau pengelolaan: "{user_text}".
    Berikan respons tanggap, laporan status, atau konfirmasi eksekusi perintah dengan gaya profesional, ringkas, dan tegas ala sistem pusat.
    """
    
    try:
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        logging.error(f"Error AI Command Center: {e}")
        reply_text = "Perintah diterima, sistem sedang memproses pembaruan bos!"

    await update.message.reply_text(reply_text)

def main():
    if not TOKEN:
        logging.error("IZUMI_COMMAND_TOKEN belum diset!")
        return

    # Jalankan server keep-alive (Port 8083)
    keep_alive()

    # Inisialisasi Bot Telegram Command & Control
    application = ApplicationBuilder().token(TOKEN).build()

    # Tangkap pesan teks instruksi sistem
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_command_center))

    logging.info("Izumi Command Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
