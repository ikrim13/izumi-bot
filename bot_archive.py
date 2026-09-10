import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ARCHIVE_TOKEN = os.getenv("IZUMI_ARCHIVE_TOKEN")

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
        "archive": {},
        "notified_logs": [],
        "notified_classes": []
    }

def save_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Gagal save data: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗂️ **[Archive Bot] Modul Arsip & Catatan Aktif.**\n\n"
        "Perintah yang tersedia:\n"
        "- `/archive <Matkul> | <Catatan>` : Menyimpan catatan baru\n"
        "- `/archive` : Melihat semua daftar arsip tersimpan"
    )

async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    data = load_data()
    if "archive" not in data:
        data["archive"] = {}

    # Jika user mengirim perintah tanpa argumen (hanya /archive) -> Tampilkan daftar arsip
    if not text_args:
        archives = data["archive"]
        if not archives:
            await update.message.reply_text("📭 Belum ada arsip yang tersimpan.\n\nGunakan format:\n`/archive <Matkul> | <Catatan>`")
            return

        msg = "📚 **Daftar Arsip & Catatan Kuliah:**\n"
        for matkul, catatan_list in archives.items():
            msg += f"\n📖 **{matkul}**:\n"
            for idx, item in enumerate(catatan_list, 1):
                msg += f"  {idx}. {item}\n"
        await update.message.reply_text(msg)
        return

    # Jika user menggunakan format pemisah |
    if "|" not in text_args:
        await update.message.reply_text(
            "⚠️ Format salah!\n\nGunakan format:\n`/archive <Matkul> | <Catatan>`\n\n"
            "Contoh:\n`/archive Pemrograman | Jangan lupa pelajari database`"
        )
        return

    # Pecah matkul dan catatan
    parts = text_args.split("|", 1)
    matkul = parts[0].strip()
    catatan = parts[1].strip()

    if not matkul or not catatan:
        await update.message.reply_text("⚠️ Nama mata kuliah atau catatan tidak boleh kosong!")
        return

    if matkul not in data["archive"]:
        data["archive"][matkul] = []

    data["archive"][matkul].append(catatan)
    save_data(data)

    await update.message.reply_text(
        f"✅ **Arsip Berhasil Disimpan!**\n\n"
        f"📖 Matkul: **{matkul}**\n"
        f"📝 Catatan: {catatan}"
    )

def main():
    if not ARCHIVE_TOKEN:
        logging.error("IZUMI_ARCHIVE_TOKEN tidak ditemukan!")
        return

    app = Application.builder().token(ARCHIVE_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("archive", archive_command))

    print("Archive Bot sedang berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
