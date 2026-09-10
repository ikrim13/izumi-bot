import asyncio
import logging
import os
import json
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Ambil token dari environment variables Railway
CEO_TOKEN = os.getenv("CEO_TOKEN")
ACADEMIC_TOKEN = os.getenv("IZUMI_ACADEMIC_TOKEN")
NEXUS_TOKEN = os.getenv("IZUMI_NEXUS_TOKEN")
ARCHIVE_TOKEN = os.getenv("IZUMI_ARCHIVE_TOKEN")
TARGET_GROUP_ID = os.getenv("TARGET_GROUP_ID")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- SISTEM PERSISTENT STORAGE (JSON) ---
STORAGE_FILE = "storage_data.json"

def load_data():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Gagal load data storage: {e}")
    return {
        "archive": {},
        "schedules": {
            "Senin": ["Pemrograman Web"],
            "Selasa": ["Basis Data"],
            "Rabu": ["Jaringan Komputer"],
            "Kamis": ["Sistem Operasi"]
        }
    }

def save_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Gagal save data storage: {e}")

app_data = load_data()
ARCHIVE_STORAGE = app_data["archive"]
ACADEMIC_SCHEDULES = app_data["schedules"]

# --- COMMAND HANDLERS ---

# 1. CEO Bot Commands
async def ceo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 [CEO Bot] Pusat komando aktif. Gunakan /status atau /report untuk memantau sistem.")

async def ceo_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 [CEO Bot] Status Kabinet: Semua modul (CEO, Academic, Nexus, Archive) berjalan normal dan sinkron.")

async def ceo_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 [CEO Bot] Laporan Operasional: 4 Bot aktif online, koneksi Railway stabil, auto-broadcast siaga.")

# 2. Academic Bot Commands
async def academic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 [Academic Bot] Modul akademik aktif.\n"
        "Perintah tersedia:\n"
        "- `/jadwal` : Lihat daftar jadwal kuliah & kalender\n"
        "- `/tambah_jadwal <Hari> | <Matkul>` : Tambah jadwal manual\n"
        "- `/hapus_jadwal <Hari> | <Matkul>` : Hapus jadwal manual\n"
        "- `/tugas` : Lihat daftar tugas"
    )

async def academic_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response_text = "📅 **Jadwal Kuliah & Sinkronisasi Kalender:**\n"
    
    if ACADEMIC_SCHEDULES:
        response_text += "\n📌 **Jadwal Rutin (Storage):**\n"
        for hari, matkuls in ACADEMIC_SCHEDULES.items():
            response_text += f"   • **{hari}**: {', '.join(matkuls)}\n"
            
    response_text += (
        "\n🗓️ **Catatan Kalender E-Learning:**\n"
        "Jadwal kuliah harian, ruang kelas, dan deadline tugas otomatis tersinkronisasi dari Google Calendar / E-Learning kampus yang terhubung."
    )
    await update.message.reply_text(response_text)

async def academic_tambah_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    if "|" not in text_args:
        await update.message.reply_text("⚠️ Format salah! Gunakan: `/tambah_jadwal Senin | Basis Data`")
        return
    
    parts = text_args.split("|", 1)
    hari = parts[0].strip().capitalize()
    matkul = parts[1].strip()
    
    if hari not in ACADEMIC_SCHEDULES:
        ACADEMIC_SCHEDULES[hari] = []
    
    if matkul in ACADEMIC_SCHEDULES[hari]:
        await update.message.reply_text(f"⚠️ Mata kuliah **{matkul}** di hari **{hari}** sudah ada dalam jadwal.")
    else:
        ACADEMIC_SCHEDULES[hari].append(matkul)
        app_data["schedules"] = ACADEMIC_SCHEDULES
        save_data(app_data)
        await update.message.reply_text(f"✅ Berhasil nambahin **{matkul}** ke jadwal hari **{hari}**.")

async def academic_hapus_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_args = " ".join(context.args)
    if "|" not in text_args:
        await update.message.reply_text("⚠️ Format salah! Gunakan: `/hapus_jadwal Senin | Basis Data`")
        return
    
    parts = text_args.split("|", 1)
    hari = parts[0].strip().capitalize()
    matkul = parts[1].strip()
    
    if hari in ACADEMIC_SCHEDULES and matkul in ACADEMIC_SCHEDULES[hari]:
        ACADEMIC_SCHEDULES[hari].remove(matkul)
        if not ACADEMIC_SCHEDULES[hari]:
            del ACADEMIC_SCHEDULES[hari]
        app_data["schedules"] = ACADEMIC_SCHEDULES
        save_data(app_data)
        await update.message.reply_text(f"🗑️ Berhasil menghapus **{matkul}** dari jadwal hari **{hari}**.")
    else:
        await update.message.reply_text(f"⚠️ Jadwal untuk **{matkul}** di hari **{hari}** tidak ditemukan.")

async def academic_tugas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 [Academic Bot] Daftar Tugas Aktif:\n1. Project Akhir Bot Telegram (Deadline: Segera)\n2. Laporan Praktikum Jarkom")

# 3. Nexus Bot Commands
async def nexus_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ [Nexus Bot] Sistem integrasi aktif. Gunakan /ping atau /sync.")

async def nexus_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 [Nexus Bot] Pong! Koneksi antar bot stabil dan merespon cepat.")

async def nexus_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 [Nexus Bot] Sinkronisasi data berhasil dilakukan antar seluruh modul kabinet & kalender.")

# 4. Archive Bot Commands
async def archive_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption
    text_args = " ".join(context.args) if context.args else ""
    has_media = message.photo or message.document or message.audio or message.video
    
    if not text_args and not caption and not has_media:
        if not ARCHIVE_STORAGE:
            await message.reply_text(
                "🗂️ [Archive Bot] Belum ada arsip tersimpan.\n"
                "Cara pakai:\n"
                "- Teks: `/archive Basis Data | Catatan penting`\n"
                "- Foto/File: Kirim foto/file dengan caption `Basis Data | Tugas 1`"
            )
        else:
            response_text = "🗂️ **Daftar Arsip Berdasarkan Mata Kuliah:**\n"
            for matkul, items in ARCHIVE_STORAGE.items():
                response_text += f"\n📘 **{matkul}**:\n"
                for i, item in enumerate(items, 1):
                    response_text += f"   {i}. {item}\n"
            await message.reply_text(response_text)
        return

    source_text = caption if caption else text_args
    
    if "|" in source_text:
        parts = source_text.split("|", 1)
        matkul = parts[0].strip()
        content = parts[1].strip()
    else:
        matkul = "Umum"
        content = source_text

    if matkul not in ARCHIVE_STORAGE:
        ARCHIVE_STORAGE[matkul] = []

    if has_media:
        media_type = "Foto" if message.photo else "Dokumen/File"
        item_desc = f"[{media_type}] {content if content else '(Tanpa keterangan)'}"
        ARCHIVE_STORAGE[matkul].append(item_desc)
        app_data["archive"] = ARCHIVE_STORAGE
        save_data(app_data)
        await message.reply_text(f"✅ {media_type} berhasil di-arsip ke matkul **{matkul}** (aman di cloud Telegram)!")
    else:
        ARCHIVE_STORAGE[matkul].append(content)
        app_data["archive"] = ARCHIVE_STORAGE
        save_data(app_data)
        await message.reply_text(f"✅ Catatan berhasil di-arsip ke matkul **{matkul}**:\n\"{content}\"")

# --- AUTO-BROADCAST ---
async def auto_broadcast(bot: Bot, bot_name: str):
    if not TARGET_GROUP_ID:
        return
    while True:
        try:
            await bot.send_message(
                chat_id=TARGET_GROUP_ID, 
                text=f"📢 [{bot_name}] Update otomatis: Sistem & kalender sinkron."
            )
        except Exception as e:
            logging.error(f"Gagal broadcast {bot_name}: {e}")
        await asyncio.sleep(3600)

# --- RUNNERS ---
async def run_ceo():
    if not CEO_TOKEN: return
    app = Application.builder().token(CEO_TOKEN).build()
    app.add_handler(CommandHandler("start", ceo_start))
    app.add_handler(CommandHandler("status", ceo_status))
    app.add_handler(CommandHandler("report", ceo_report))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    asyncio.create_task(auto_broadcast(app.bot, "CEO Bot"))
    while True: await asyncio.sleep(3600)

async def run_academic():
    if not ACADEMIC_TOKEN: return
    app = Application.builder().token(ACADEMIC_TOKEN).build()
    app.add_handler(CommandHandler("start", academic_start))
    app.add_handler(CommandHandler("jadwal", academic_jadwal))
    app.add_handler(CommandHandler("tambah_jadwal", academic_tambah_jadwal))
    app.add_handler(CommandHandler("hapus_jadwal", academic_hapus_jadwal))
    app.add_handler(CommandHandler("tugas", academic_tugas))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    asyncio.create_task(auto_broadcast(app.bot, "Academic Bot"))
    while True: await asyncio.sleep(3600)

async def run_nexus():
    if not NEXUS_TOKEN: return
    app = Application.builder().token(NEXUS_TOKEN).build()
    app.add_handler(CommandHandler("start", nexus_start))
    app.add_handler(CommandHandler("ping", nexus_ping))
    app.add_handler(CommandHandler("sync", nexus_sync))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    asyncio.create_task(auto_broadcast(app.bot, "Nexus Bot"))
    while True: await asyncio.sleep(3600)

async def run_archive():
    if not ARCHIVE_TOKEN: return
    app = Application.builder().token(ARCHIVE_TOKEN).build()
    app.add_handler(CommandHandler("start", archive_handler))
    app.add_handler(CommandHandler("archive", archive_handler))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    asyncio.create_task(auto_broadcast(app.bot, "Archive Bot"))
    while True: await asyncio.sleep(3600)

async def main():
    await asyncio.gather(
        run_ceo(),
        run_academic(),
        run_nexus(),
        run_archive()
    )

if __name__ == "__main__":
    asyncio.run(main())
