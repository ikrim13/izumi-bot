import os
import logging
from flask import Flask
from threading import Thread
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Konfigurasi Gemini AI dengan System Instruction yang ketat & konteks waktu 2026
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Instruksi khusus agar AI sadar waktu (2026) dan fokus murni ke akademik / jadwal kuliah
    system_instruction = (
        "Kamu adalah Izumi Academic Bot, asisten pribadi akademik khusus untuk Ikrimah "
        "(mahasiswa Politeknik APP Jakarta). "
        "Waktu saat ini adalah TAHUN 2026. "
        "Tugas utamamu adalah membantu mengecek jadwal kuliah, tugas, ujian, dan kegiatan akademik dari data kalender/e-learning. "
        "ATURAN MUTLAK: "
        "1. JANGAN PERNAH membahas jadwal sepak bola, balapan, atau hari libur nasional/peringatan umum yang tidak ada hubungannya dengan kuliah. "
        "2. Jika ditanya jadwal, jawablah berdasarkan data akademik, jadwal kampus, atau iCal e-learning yang relevan. "
        "3. Jangan mengarang data. Jika tidak tahu, katakan dengan jujur sesuai data kalender akademik."
    )
    
    model = genai.GenerativeModel(
        model_name='gemini-3.6-flash',
        system_instruction=system_instruction
    )
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
        # Kirim pesan ke Gemini dengan konteks tahun 2026 & aturan ketat akademik
        prompt = f"[Konteks Waktu: September 2026] Pertanyaan/Perintah dari Ikrimah: {user_message}"
        response = model.generate_content(prompt)
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
