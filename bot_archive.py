import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
        "🗂️ **[Archive Bot All-In-One] Aktif!**\n\n"
        "Cara pakai:\n"
        "1. **Teks**: `/archive <Matkul> | <Catatan>`\n"
        "2. **File + Catatan**: Kirim file dengan caption `/archive <Matkul> | <Catatan Tambahan>`\n"
        "3. **Lihat Arsip**: Ketik `/archive` saja."
    )

async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    data = load_data()
    if "archive" not in data:
        data["archive"] = {}

    if not text_args:
        archives = data["archive"]
        if not archives:
            await update.message.reply_text("📭 Belum ada arsip yang tersimpan.")
            return

        msg = "📚 **Daftar Arsip & Berkas Kuliah:**\n"
        for matkul, catatan_list in archives.items():
            msg += f"\n📖 **{matkul}**:\n"
            for idx, item in enumerate(catatan_list, 1):
                msg += f"  {idx}. {item}\n"
        await update.message.reply_text(msg)
        return

    if "|" not in text_args:
        await update.message.reply_text(
            "⚠️ Format salah!\n\n"
            "Gunakan format:\n`/archive <Matkul> | <Catatan>`"
        )
        return

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
        f"✅ **Arsip Teks Disimpan!**\n\n"
        f"📖 Matkul: **{matkul}**\n"
        f"📝 Catatan: {catatan}"
    )

async def archive_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption or ""
    
    if not caption.startswith("/archive"):
        return

    # Hilangkan prefix /archive
    raw_content = caption.replace("/archive", "", 1).strip()
    if not raw_content:
        await update.message.reply_text("⚠️ Format salah! Contoh: `/archive Pemrograman | Modul praktikum 1`")
        return

    # Pisahkan matkul dan catatan tambahan jika menggunakan tanda |
    if "|" in raw_content:
        parts = raw_content.split("|", 1)
        matkul = parts[0].strip()
        custom_note = parts[1].strip()
    else:
        matkul = raw_content
        custom_note = ""

    data = load_data()
    if "archive" not in data:
        data["archive"] = {}

    if matkul not in data["archive"]:
        data["archive"][matkul] = []

    # Identifikasi jenis file
    file_label = ""
    if message.document:
        file_label = f"📁 Dokumen ({message.document.file_name})"
    elif message.photo:
        file_label = "🖼️ [Foto/Gambar]"
    elif message.video:
        file_label = "🎥 [Video]"
    elif message.audio:
        file_label = "🎵 [Audio]"
    else:
        file_label = "📎 [Berkas Media]"

    # Gabungkan info file dan catatan teksnya
    if custom_note:
        final_entry = f"{file_label} - {custom_note}"
    else:
        final_entry = file_label

    data["archive"][matkul].append(final_entry)
    save_data(data)

    await message.reply_text(
        f"✅ **Berkas & Catatan Berhasil Masuk Arsip!**\n\n"
        f"📖 Matkul: **{matkul}**\n"
        f"📌 Keterangan: {final_entry}"
    )

def main():
    if not ARCHIVE_TOKEN:
        logging.error("IZUMI_ARCHIVE_TOKEN tidak ditemukan!")
        return

    app = Application.builder().token(ARCHIVE_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("archive", archive_command))
    app.add_handler(MessageHandler(filters.ATTACHMENT | filters.PHOTO | filters.VIDEO | filters.AUDIO, archive_media_handler))

    print("Archive Bot All-In-One (with Media & Notes) sedang berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
