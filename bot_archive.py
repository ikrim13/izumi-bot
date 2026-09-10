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
        "📌 **Perintah Arsip:**\n"
        "• `/archive <Matkul> | <Catatan>` : Simpan teks\n"
        "• Kirim file + caption `/archive <Matkul> | <Catat>` : Simpan berkas\n"
        "• `/archive` : Lihat semua daftar arsip\n"
        "• `/search <Kata Kunci>` : Cari arsip berdasarkan matkul/catatan\n\n"
        "🗑️ **Perintah Hapus:**\n"
        "• `/delitem <Matkul> | <Nomor>` : Hapus arsip satuan\n"
        "• `/delmatkul <Matkul>` : Hapus 1 matkul penuh\n"
        "• `/cleararchive` : Hapus seluruh arsip"
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
        f"✅ **Arsip Disimpan!**\n\n"
        f"📖 Matkul: **{matkul}**\n"
        f"📝 Keterangan: {catatan}"
    )

async def search_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip().lower()
    if not query:
        await update.message.reply_text(
            "⚠️ Masukkan kata kunci pencarian!\n"
            "Contoh: `/search Pemrograman` atau `/search database`"
        )
        return

    data = load_data()
    archives = data.get("archive", {})
    if not archives:
        await update.message.reply_text("📭 Belum ada arsip yang tersimpan.")
        return

    found_results = []
    for matkul, catatan_list in archives.items():
        # Cek apakah query cocok dengan nama matkul atau ada di dalam catatan
        matched_items = []
        for idx, item in enumerate(catatan_list, 1):
            if query in matkul.lower() or query in item.lower():
                matched_items.append((idx, item))
        
        if matched_items or query in matkul.lower():
            found_results.append((matkul, matched_items if matched_items else list(enumerate(catatan_list, 1))))

    if not found_results:
        await update.message.reply_text(f"🔍 Tidak ditemukan arsip dengan kata kunci: **{query}**")
        return

    msg = f"🔎 **Hasil Pencarian untuk:** `{query}`\n"
    for matkul, items in found_results:
        msg += f"\n📖 **{matkul}**:\n"
        for idx, item in items:
            msg += f"  {idx}. {item}\n"

    await update.message.reply_text(msg)

async def archive_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption or ""
    
    if not caption.startswith("/archive"):
        return

    raw_content = caption.replace("/archive", "", 1).strip()
    if not raw_content:
        await update.message.reply_text("⚠️ Format salah! Contoh: `/archive Pemrograman | Modul praktikum 1`")
        return

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

    if custom_note:
        final_entry = f"{file_label} - {custom_note}"
    else:
        final_entry = file_label

    data["archive"][matkul].append(final_entry)
    save_data(data)

    await message.reply_text(
        f"✅ **Berkas Masuk Arsip!**\n\n"
        f"📖 Matkul: **{matkul}**\n"
        f"📌 Keterangan: {final_entry}"
    )

async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    if "|" not in text_args:
        await update.message.reply_text(
            "⚠️ Format salah!\n\n"
            "Gunakan format:\n`/delitem <Matkul> | <Nomor>`\n"
            "*(Contoh: `/delitem Pemrograman | 1`)*"
        )
        return

    parts = text_args.split("|", 1)
    matkul = parts[0].strip()
    idx_str = parts[1].strip()

    if not idx_str.isdigit():
        await update.message.reply_text("⚠️ Nomor arsip harus berupa angka! Contoh: `/delitem Pemrograman | 1`")
        return

    idx = int(idx_str) - 1

    data = load_data()
    if "archive" not in data or matkul not in data["archive"]:
        await update.message.reply_text(f"❌ Mata kuliah **{matkul}** tidak ditemukan di arsip.")
        return

    items = data["archive"][matkul]
    if idx < 0 or idx >= len(items):
        await update.message.reply_text(f"❌ Nomor arsip tidak valid! Mata kuliah **{matkul}** hanya memiliki {len(items)} item.")
        return

    removed_item = items.pop(idx)
    
    if not items:
        del data["archive"][matkul]

    save_data(data)
    await update.message.reply_text(f"🗑️ Berhasil menghapus arsip nomor {idx_str} dari **{matkul}**:\n`{removed_item}`")

async def delete_matkul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matkul = " ".join(context.args).strip()
    if not matkul:
        await update.message.reply_text("⚠️ Masukkan nama mata kuliah yang mau dihapus!\nContoh: `/delmatkul Pemrograman`")
        return

    data = load_data()
    if "archive" not in data or matkul not in data["archive"]:
        await update.message.reply_text(f"❌ Mata kuliah **{matkul}** tidak ditemukan di arsip.")
        return

    del data["archive"][matkul]
    save_data(data)
    await update.message.reply_text(f"🗑️ Seluruh arsip untuk mata kuliah **{matkul}** berhasil dihapus!")

async def clear_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["archive"] = {}
    save_data(data)
    await update.message.reply_text("🗑️ Seluruh arsip dan berkas berhasil dikosongkan!")

def main():
    if not ARCHIVE_TOKEN:
        logging.error("IZUMI_ARCHIVE_TOKEN tidak ditemukan!")
        return

    app = Application.builder().token(ARCHIVE_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("archive", archive_command))
    app.add_handler(CommandHandler("search", search_archive))
    app.add_handler(CommandHandler("delitem", delete_item))
    app.add_handler(CommandHandler("delmatkul", delete_matkul))
    app.add_handler(CommandHandler("cleararchive", clear_archive))
    app.add_handler(MessageHandler(filters.ATTACHMENT | filters.PHOTO | filters.VIDEO | filters.AUDIO, archive_media_handler))

    print("Archive Bot All-In-One (with Search & Delete) sedang berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
