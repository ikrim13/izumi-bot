import os
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("IZUMI_NEXUS_TOKEN")

async def nexus_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menteri Nexus aktif. Siap mengelola integrasi dan sistem.")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: IZUMI_NEXUS_TOKEN belum diatur!")
        exit(1)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", nexus_start))
    app.run_polling()