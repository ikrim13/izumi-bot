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
TOKEN = os.getenv("IZUMI_NEXUS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8791729948"))

# Konfigurasi Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App Sederhana untuk UptimeRobot (Anti-Tidur Railway - Port 8083)
app = Flask('')

@app.route('/')
def home():
    return "Izumi Nexus Companion Bot is alive and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8083)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Handler Utama Nexus: Teman Ngobrol, Curhat, & Bantu Tugas Bebas
async def handle_nexus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Keamanan Mutlak: Tolak jika bukan kamu!
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Akses ditolak. Nexus terkunci.")
        return

    user_text = update.message.text
    logging.info(f"Pesan Nexus dari Admin: {user_text}")

    # Prompt instruksi untuk Nexus sebagai Companion & Partner Pengerjaan Tugas
    prompt = f"""
    Kamu adalah Izumi Nexus, sahabat ngobrol, teman diskusi, sekaligus partner andalan Ikrimah untuk ngerjain berbagai tugas (nulis esai, coding, analisis, dll).
    Gunakan gaya bahasa yang santai, asik, cerdas, solutif, dan mendukung selayaknya partner dekat.
    
    Pesan/Permintaan dari Ikrimah: "{user_text}"
    """

    try:
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        logging.error(f"Error AI Nexus: {e}")
        reply_text = "Wah, koneksi otakku ke-lag sebentar nih bos. Coba ulangi pertanyaannya ya."

    await update.message.reply_text(reply_text)

def main():
    if not TOKEN:
        logging.error("IZUMI_NEXUS_TOKEN belum diset!")
        return

    # Jalankan server keep-alive (Port 8083)
    keep_alive()

    # Inisialisasi Bot Nexus Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Tangkap semua pesan teks chat biasa
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_nexus))

    logging.info("Izumi Nexus Companion Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
