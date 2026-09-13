import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# Konfigurasi Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Ambil Variabel Lingkungan (Kita sediakan token khusus nexus atau pakai command token kalau disamakan)
TOKEN = os.getenv("IZUMI_NEXUS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8791729948"))

# Konfigurasi Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App Sederhana untuk UptimeRobot (Anti-Tidur Railway - Port 8084)
app = Flask('')

@app.route('/')
def home():
    return "Izumi Nexus Companion Bot is alive and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8084)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Handler Ngobrol Santai & Asisten Serbaguna
async def handle_nexus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Keamanan Mutlak: Tolak jika bukan kamu!
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Maaf, akses Nexus dibatasi khusus untuk pemilik.")
        return

    user_text = update.message.text
    logging.info(f"Pesan Nexus dari Admin: {user_text}")

    prompt = f"""
    Kamu adalah Izumi Nexus, sahabat ngobrol dan asisten serbaguna yang santai, asyik, dan fleksibel untuk Ikrimah. 
    Ikrimah mengajakmu berdiskusi atau mengobrol tentang: "{user_text}".
    Berikan respons yang interaktif, natural, menyenangkan, dan solutif.
    """
    
    try:
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        logging.error(f"Error AI Nexus: {e}")
        reply_text = "Wah, sinyal pikiranku agak terganggu nih bos. Coba ngobrol lagi ya."

    await update.message.reply_text(reply_text)

def main():
    if not TOKEN:
        logging.error("IZUMI_NEXUS_TOKEN belum diset!")
        return

    # Jalankan server keep-alive (Port 8084)
    keep_alive()

    # Inisialisasi Bot Telegram Nexus
    application = ApplicationBuilder().token(TOKEN).build()

    # Tangkap pesan teks bebas
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_nexus))

    logging.info("Izumi Nexus Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
