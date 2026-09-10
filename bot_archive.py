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
    return {"schedules": {}, "archive": {}}

def save_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Gagal save data: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗂️ [Archive Bot] Modul arsip aktif.\n"
        "Perintah:\n"
        "- `/archive` : Lihat seluruh daftar arsip\n"
        "- `/archive <Matkul> | <Catatan>` : Simpan catatan teks"
    )

async def list_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    data = load_data()
    archive = data.get("archive", {})

    if not archive:
        await update.message.reply_text("🗂️ Belum ada arsip yang tersimpan.")
        return

    if text_args:
        matkul_key = text_args.strip().title()
        if matkul_key in archive:
            items = archive[matkul_key]
            resp = f"📂 **Arsip untuk {matkul_key}:**\n"
            for i, item in enumerate(items, 1):
                resp += f"{i}. {item}\n"
            await update.message.reply_text(resp)
        else:
            await update.message.reply_text(f"⚠️ Tidak ada arsip ditemukan untuk mata kuliah **{matkul_key}**.")
        return

    text = "🗂️ **Daftar Seluruh Arsip Mata Kuliah:**\n"
    for matkul, items in archive.items():
        text += f"\n• **{matkul}**: {len(items)} item tersimpan"
    await update.message.reply_text(text)

async def save_text_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = update.message.text
    if text_args and text_args.startswith("/archive"):
        parts_cmd = text_args.replace("/archive", "", 1).strip()
        if "|" in parts_cmd:
            parts = parts_cmd.split("|", 1)
            matkul = parts[0].strip().title()
            catatan = parts[1].strip()

            data = load_data()
            if matkul not in data["archive"]:
                data["archive"][matkul] = []
            
            data["archive"][matkul].append(f"📝 {catatan}")
            save_data(data)
            await update.message.reply_text(f"✅ Catatan berhasil disimpan ke arsip **{matkul}**.")

def main():
    if not ARCHIVE_TOKEN:
        logging.error("IZUMI_ARCHIVE_TOKEN tidak ditemukan!")
        return
    app = Application.builder().token(ARCHIVE_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("archive", list_archive))
    
    print("Archive Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
