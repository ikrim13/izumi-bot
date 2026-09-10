import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

NEXUS_TOKEN = os.getenv("IZUMI_NEXUS_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ [Nexus Bot] Sistem integrasi aktif. Gunakan /ping atau /sync.")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 [Nexus Bot] Pong! Koneksi dan respons cepat.")

async def sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 [Nexus Bot] Sinkronisasi data antar modul berhasil.")

def main():
    if not NEXUS_TOKEN:
        logging.error("IZUMI_NEXUS_TOKEN tidak ditemukan!")
        return
    app = Application.builder().token(NEXUS_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("sync", sync))
    
    print("Nexus Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
