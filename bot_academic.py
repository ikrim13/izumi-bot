import os
import logging
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# Konfigurasi Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Ambil Variabel Lingkungan (Environment Variables)
TOKEN = os.getenv("IZUMI_ACADEMIC_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8791729948"))

# Konfigurasi Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App Sederhana untuk UptimeRobot (Anti-Tidur Railway)
app = Flask('')

@app.route('/')
def home():
    return "Izumi Academic Bot is alive and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Handler Utama: Chat Santai & Perintah Natural via AI
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Keamanan Mutlak: Tolak jika bukan kamu!
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Maaf, kamu tidak memiliki akses ke sistem Izumi.")
        return

    user_text = update.message.text
    logging.info(f"Pesan dari Admin: {user_text}")

    # Prompt instruksi dasar untuk Izumi sebagai Asisten Akademik & Pribadi
    prompt = f"""
    Kamu adalah Izumi, asisten pribadi AI otonom untuk Ikrimah. 
    Ikrimah mengajakmu ngobrol atau memberi instruksi terkait jadwal kuliah, tugas, catatan, atau kegiatan sehari-hari.
    Gunakan bahasa yang santai, akrab, ramah, dan solutif (seperti asisten pribadi profesional).
    
    Pesan dari Ikrimah: "{user_text}"
    """

    try:
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        logging.error(f"Error Gemini API: {e}")
        reply_text = "Duh, otak AI-ku lagi agak konslet nih boss. Coba ulangi sebentar ya."

    await update.message.reply_text(reply_text)

def main():
    if not TOKEN:
        logging.error("IZUMI_ACADEMIC_TOKEN belum diset!")
        return

    # Jalankan server keep-alive di background
    keep_alive()

    # Inisialisasi Bot Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Tangkap semua pesan teks chat biasa (Tanpa Command Kaku)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logging.info("Izumi Academic Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
