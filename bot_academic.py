import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("IZUMI_ACADEMIC_TOKEN")

async def academic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Menteri Academic aktif.\n"
        "Siap mengelola jadwal kuliah, tugas, dan materi akademik."
    )

if __name__ == "__main__":
    if not TOKEN:
        print("Error: IZUMI_ACADEMIC_TOKEN belum diatur!")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", academic_start))

    print("Izumi Academic Bot aktif dan berjalan...")
    app.run_polling()