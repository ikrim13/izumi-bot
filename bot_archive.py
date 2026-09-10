import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("IZUMI_ARCHIVE_TOKEN")

async def archive_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menteri Archive aktif. Siap mengelola penyimpanan arsip dan data.")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: IZUMI_ARCHIVE_TOKEN belum diatur!")
        exit(1)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", archive_start))
    app.run_polling()