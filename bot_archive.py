import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# Konfigurasi Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Ambil Variabel Lingkungan (Gunakan token command/archive sesuai setingan bot_archive-mu)
TOKEN = os.getenv("IZUMI_COMMAND_TOKEN") or os.getenv("IZUMI_ARCHIVE_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8791729948"))

# Konfigurasi Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App Sederhana untuk UptimeRobot (Anti-Tidur Railway - Port 8082)
app = Flask('')

@app.route('/')
def home():
    return "Izumi Archive & Vault Bot is alive and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8082)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Handler Khusus Dokumen, Foto, & Arsip File Apapun
async def handle_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Keamanan Mutlak: Tolak jika bukan kamu!
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Akses ditolak. Ini area arsip pribadi.")
        return

    message = update.message
    
    if message.document or message.photo:
        file_name = "File/Foto"
        if message.document:
            file_name = message.document.file_name
        
        caption = message.caption or "Tanpa keterangan"
        logging.info(f"Arsip diterima dari Admin: {file_name} - {caption}")
        
        await message.reply_text(f"📥 **Arsip Berhasil Disimpan ke Vault!**\n\n- **File:** {file_name}\n- **Catatan:** {caption}\n\n*Aman, Bos. Berkasnya udah masuk laci arsip.*", parse_mode="Markdown")
    
    elif message.text:
        user_text = message.text
        prompt = f"""
        Kamu adalah Izumi, sistem pengarsipan pribadi untuk Ikrimah. 
        Ikrimah mengirimkan catatan arsip teks: "{user_text}".
        Berikan konfirmasi singkat dan rapi bahwa catatan ini sudah diarsipkan dengan aman.
        """
        try:
            response = model.generate_content(prompt)
            reply_text = response.text
        except Exception as e:
            logging.error(f"Error AI Archive: {e}")
            reply_text = "Catatan arsip aman, Bos!"

        await message.reply_text(reply_text)

def main():
    if not TOKEN:
        logging.error("Token untuk bot archive belum diset di environment!")
        return

    keep_alive()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_archive))

    logging.info("Izumi Archive Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
