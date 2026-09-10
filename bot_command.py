import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

CEO_TOKEN = os.getenv("CEO_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 [CEO Bot] Pusat komando aktif. Gunakan /status atau /report untuk memantau sistem.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 Status Kabinet:\n"
        "• Command/CEO: Online\n"
        "• Academic: Standby\n"
        "• Archive: Standby\n"
        "• Nexus: Standby"
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 [CEO Bot] Laporan Operasional: Modul kabinet terpantau stabil.")

def main():
    if not CEO_TOKEN:
        logging.error("CEO_TOKEN tidak ditemukan di environment variables!")
        return
    app = Application.builder().token(CEO_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("report", report))
    
    print("CEO Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
