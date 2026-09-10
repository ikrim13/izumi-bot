import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ACADEMIC_TOKEN = os.getenv("IZUMI_ACADEMIC_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

STORAGE_FILE = "storage_data.json"

def load_data():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "schedules": {
            "Senin": ["Pemrograman Web"],
            "Selasa": ["Basis Data"],
            "Rabu": ["Jaringan Komputer"],
            "Kamis": ["Sistem Operasi"]
        },
        "archive": {}
    }

def save_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Gagal save data: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 [Academic Bot] Modul akademik aktif.\n"
        "Perintah:\n"
        "- `/jadwal` : Lihat jadwal\n"
        "- `/tambah_jadwal Hari | Matkul` : Tambah jadwal\n"
        "- `/hapus_jadwal Hari | Matkul` : Hapus jadwal\n"
        "- `/tugas` : Lihat tugas"
    )

async def jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    schedules = data.get("schedules", {})
    text = "📅 **Jadwal Kuliah:**\n"
    for hari, matkuls in schedules.items():
        text += f"\n• **{hari}**: {', '.join(matkuls)}"
    await update.message.reply_text(text)

async def tambah_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    if "|" not in text_args:
        await update.message.reply_text("⚠️ Format salah! Gunakan: `/tambah_jadwal Senin | Basis Data`")
        return
    parts = text_args.split("|", 1)
    hari = parts[0].strip().capitalize()
    matkul = parts[1].strip()
    
    data = load_data()
    if hari not in data["schedules"]:
        data["schedules"][hari] = []
    if matkul in data["schedules"][hari]:
        await update.message.reply_text(f"⚠️ **{matkul}** di hari **{hari}** sudah ada.")
    else:
        data["schedules"][hari].append(matkul)
        save_data(data)
        await update.message.reply_text(f"✅ Berhasil menambah **{matkul}** ke hari **{hari}**.")

async def hapus_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    if "|" not in text_args:
        await update.message.reply_text("⚠️ Format salah! Gunakan: `/hapus_jadwal Senin | Basis Data`")
        return
    parts = text_args.split("|", 1)
    hari = parts[0].strip().capitalize()
    matkul = parts[1].strip()
    
    data = load_data()
    if hari in data["schedules"] and matkul in data["schedules"][hari]:
        data["schedules"][hari].remove(matkul)
        if not data["schedules"][hari]:
            del data["schedules"][hari]
        save_data(data)
        await update.message.reply_text(f"🗑️ Berhasil menghapus **{matkul}** dari hari **{hari}**.")
    else:
        await update.message.reply_text("⚠️ Jadwal tidak ditemukan.")

async def tugas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 **Daftar Tugas Aktif:**\n1. Project Bot Telegram\n2. Laporan Praktikum")

def main():
    if not ACADEMIC_TOKEN:
        logging.error("IZUMI_ACADEMIC_TOKEN tidak ditemukan!")
        return
    app = Application.builder().token(ACADEMIC_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jadwal", jadwal))
    app.add_handler(CommandHandler("tambah_jadwal", tambah_jadwal))
    app.add_handler(CommandHandler("hapus_jadwal", hapus_jadwal))
    app.add_handler(CommandHandler("tugas", tugas))
    
    print("Academic Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
