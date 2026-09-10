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
                content = f.read()
                if content.strip():
                    return json.loads(content)
        except Exception as e:
            logging.error(f"Gagal load data: {e}")
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
        "• Kirim file/foto + caption `/archive <Matkul> | <Catatan>` : Simpan berkas + kirim balik\n"
        "• `/archive` : Lihat semua daftar arsip\n"
        "• `/search <Kata Kunci>` : Cari arsip\n\n"
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
            for idx, entry in enumerate(catatan_list, 1):
                # Tangani format lama (string) vs format baru (dictionary)
                if isinstance(entry, dict):
                    msg += f"  {idx}. [1 File/Media] {entry.get('note', '')}\n"
                else:
                    msg += f"  {idx}. {entry}\n"
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

    # Simpan sebagai dictionary untuk teks murni
    entry_data = {
        "type": "text",
        "note": catatan
    }

    data["archive"][matkul].append(entry_data)
    save_data(data)

    await update.message.reply_text(
        f"✅ **Arsip Teks Disimpan!**\n\n"
        f"📖 Matkul: **{matkul}**\n"
        f"📝 Keterangan: {catatan}"
    )

async def search_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip().lower()
    if not query:
        await update.message.reply_text("⚠️ Masukkan kata kunci pencarian!\nContoh: `/search iseng`")
        return

    data = load_data()
    archives = data.get("archive", {})
    if not archives:
        await update.message.reply_text("📭 Belum ada arsip yang tersimpan.")
        return

    found_results = []
    for matkul, catatan_list in archives.items():
        matched_items = []
        for idx, entry in enumerate(catatan_list, 1):
            note_text = entry.get("note", "") if isinstance(entry, dict) else str(entry)
            if query in matkul.lower() or query in note_text.lower():
                matched_items.append((idx, entry))
        
        if matched_items or query in matkul.lower():
            found_results.append((matkul, matched_items if matched_items else list(enumerate(catatan_list, 1))))

    if not found_results:
        await update.message.reply_text(f"🔍 Tidak ditemukan arsip dengan kata kunci: **{query}**")
        return

    for matkul, items in found_results:
        msg = f"🔎 **Hasil untuk Matkul: {matkul}**\n"
        await update.message.reply_text(msg)
        
        for idx, entry in items:
            if isinstance(entry, dict) and entry.get("type") != "text":
                file_type = entry.get("type")
                file_id = entry.get("file_id")
                caption_text = f"[{matkul} - #{idx}] {entry.get('note', '')}"
                
                try:
                    if file_type == "photo":
                        await update.message.reply_photo(photo=file_id, caption=caption_text)
                    elif file_type == "document":
                        await update.message.reply_document(document=file_id, caption=caption_text)
                    elif file_type == "video":
                        await update.message.reply_video(video=file_id, caption=caption_text)
                    elif file_type == "audio":
                        await update.message.reply_audio(audio=file_id, caption=caption_text)
                    else:
                        await update.message.reply_text(f"{idx}. {entry.get('note', '')}")
                except Exception as e:
                    logging.error(f"Gagal kirim ulang file: {e}")
                    await update.message.reply_text(f"{idx}. [File gagal dimuat] - {entry.get('note', '')}")
            else:
                note_content = entry.get("note", "") if isinstance(entry, dict) else str(entry)
                await update.message.reply_text(f"📝 {idx}. (Teks) {note_content}")

async def archive_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption or ""
    
    if not caption.startswith("/archive"):
        return

    raw_content = caption.replace("/archive", "", 1).strip()
    if not raw_content:
        await update.message.reply_text("⚠️ Format salah! Contoh: `/archive iseng | Foto kucing`")
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

    file_type = ""
    file_id = ""
    file_label = ""

    if message.document:
        file_type = "document"
        file_id = message.document.file_id
        file_label = f"📁 Dokumen ({message.document.file_name})"
    elif message.photo:
        file_type = "photo"
        # Ambil resolusi foto tertinggi
        file_id = message.photo[-1].file_id
        file_label = "🖼️ [Foto/Gambar]"
    elif message.video:
        file_type = "video"
        file_id = message.video.file_id
        file_label = "🎥 [Video]"
    elif message.audio:
        file_type = "audio"
        file_id = message.audio.file_id
        file_label = "🎵 [Audio]"
    else:
        file_type = "text"
        file_label = "📎 [Berkas Media]"

    full_note = f"{file_label} - {custom_note}" if custom_note else file_label

    entry_data = {
        "type": file_type,
        "file_id": file_id,
        "note": full_note
    }

    data["archive"][matkul].append(entry_data)
    save_data(data)

    # Kirim konfirmasi sekaligus kirim balik file/foto aslinya ke chat
    confirmation_text = f"✅ **Berkas Masuk Arsip & Dikirim Balik!**\n\n📖 Matkul: **{matkul}**\n📌 Keterangan: {full_note}"
    
    if file_type == "photo":
        await message.reply_photo(photo=file_id, caption=confirmation_text)
    elif file_type == "document":
        await message.reply_document(document=file_id, caption=confirmation_text)
    elif file_type == "video":
        await message.reply_video(video=file_id, caption=confirmation_text)
    elif file_type == "audio":
        await message.reply_audio(audio=file_id, caption=confirmation_text)
    else:
        await message.reply_text(confirmation_text)

async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    if "|" not in text_args:
        await update.message.reply_text("⚠️ Format salah! Gunakan: `/delitem <Matkul> | <Nomor>`")
        return

    parts = text_args.split("|", 1)
    matkul = parts[0].strip()
    idx_str = parts[1].strip()

    if not idx_str.isdigit():
        await update.message.reply_text("⚠️ Nomor arsip harus berupa angka!")
        return

    idx = int(idx_str) - 1
    data = load_data()
    if "archive" not in data or matkul not in data["archive"]:
        await update.message.reply_text(f"❌ Mata kuliah **{matkul}** tidak ditemukan.")
        return

    items = data["archive"][matkul]
    if idx < 0 or idx >= len(items):
        await update.message.reply_text(f"❌ Nomor arsip tidak valid!")
        return

    removed_item = items.pop(idx)
    note_val = removed_item.get("note", "") if isinstance(removed_item, dict) else str(removed_item)

    if not items:
        del data["archive"][matkul]

    save_data(data)
    await update.message.reply_text(f"🗑️ Berhasil menghapus arsip nomor {idx_str} dari **{matkul}**:\n`{note_val}`")

async def delete_matkul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matkul = " ".join(context.args).strip()
    if not matkul:
        await update.message.reply_text("⚠️ Masukkan nama mata kuliah!\nContoh: `/delmatkul iseng`")
        return

    data = load_data()
    if "archive" not in data or matkul not in data["archive"]:
        await update.message.reply_text(f"❌ Mata kuliah **{matkul}** tidak ditemukan.")
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

    print("Archive Bot All-In-One (Media Sendback) sedang berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
