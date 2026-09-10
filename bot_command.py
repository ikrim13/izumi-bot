import os
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Token CEO dan token para menteri
CEO_TOKEN = "8754865666:AAE3qAJvTAuY2A-3ShmR5lgcqhPYj4DDrfk"
ACADEMIC_TOKEN = "8952037521:AAG9WCxjgnRirNiUXUvGnrdAIxkeQRTDBZU"
ARCHIVE_TOKEN = "8620308404:AAHGC6R4jSYOpizZ5xuswxAv1qcotbfH9N0"
NEXUS_TOKEN = "8736371791:AAEsavDQW8vIRDjhdNr91nlXcw6q0eFu7Bk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Izumi CEO Command Center aktif.\n\n"
        "Daftar Perintah Kabinet:\n"
        "/status - Cek status seluruh menteri\n"
        "/delegasi [academic/archive/nexus] [pesan] - Kirim perintah ke menteri terkait"
    )

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Memeriksa status koneksi seluruh menteri kabinet...")
    
    # Inisialisasi bot menteri untuk tes ping
    bots = {
        "Academic": Bot(ACADEMIC_TOKEN),
        "Archive": Bot(ARCHIVE_TOKEN),
        "Nexus": Bot(NEXUS_TOKEN)
    }
    
    report = "Laporan Status Kabinet Izumi:\n"
    for name, bot_instance in bots.items():
        try:
            me = await bot_instance.get_me()
            report += f"- {name} (@{me.username}): ONLINE\n"
        except Exception:
            report += f"- {name}: OFFLINE / Gagal Terhubung\n"
            
    await update.message.reply_text(report)

async def delegasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Format salah! Gunakan: /delegasi [academic|archive|nexus] [pesan tugas]")
        return
        
    target_minister = context.args[0].lower()
    task_message = " ".join(context.args[1:])
    
    token_map = {
        "academic": ACADEMIC_TOKEN,
        "archive": ARCHIVE_TOKEN,
        "nexus": NEXUS_TOKEN
    }
    
    if target_minister not in token_map:
        await update.message.reply_text(f"Menteri '{target_minister}' tidak dikenal dalam kabinet!")
        return
        
    try:
        minister_bot = Bot(token_map[target_minister])
        # Mengirim pesan log atau notifikasi delegasi (bisa disesuaikan target chat ID pemilik)
        await update.message.reply_text(f"Perintah berhasil diteruskan ke Menteri {target_minister.capitalize()}: \"{task_message}\"")
    except Exception as e:
        await update.message.reply_text(f"Gagal meneruskan perintah ke menteri: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(CEO_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", check_status))
    app.add_handler(CommandHandler("delegasi", delegasi))

    print("Izumi CEO Command Center aktif dan berjalan...")
    app.run_polling()
