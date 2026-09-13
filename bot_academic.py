import os
import json
import logging
import re
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DATA_FILE = "academic_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"jadwal": [], "tugas": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

# --- FUNGSI CRUD LOKAL NATURAL ---
def parse_natural_add(text):
    text_lower = text.lower()
    
    # Cari pola tanggal YYYY-MM-DD
    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text)
    tanggal = match_date.group(0) if match_date else datetime.now().strftime("%Y-%m-%d")
    
    # Cari pola waktu HH:MM atau jam X
    match_time = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if match_time:
        waktu = f"{int(match_time.group(1)):02d}:{match_time.group(2)}"
    else:
        match_jam = re.search(r'jam\s+(\d{1,2})', text_lower)
        if match_jam:
            waktu = f"{int(match_jam.group(1)):02d}:00"
        else:
            waktu = "08:00"
            
    # Bersihkan teks untuk ambil nama kegiatan
    clean_text = text
    for w in ["tambahin", "tambah", "jadwal", "tolong", "buatkan", "agenda", "buat"]:
        clean_text = re.sub(w, '', clean_text, flags=re.IGNORECASE)
    
    clean_text = re.sub(r'\d{4}-\d{2}-\d{2}', '', clean_text)
    clean_text = re.sub(r'jam\s+\d{1,2}[:\.]?\d*', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\d{1,2}[:\.]\d{2}', '', clean_text)
    clean_text = clean_text.replace("tanggal", "").replace("hari", "").strip(" ,|-")
    
    nama_kegiatan = clean_text.capitalize() if clean_text else "Kegiatan Baru"
    return nama_kegiatan, tanggal, waktu

def tambah_jadwal_lokal(nama: str, tanggal: str, waktu: str) -> str:
    item = {"nama": nama, "tanggal": tanggal, "waktu": waktu, "sumber": "Chat"}
    db["jadwal"].append(item)
    save_data(db)
    return f"Sip, udah aku catat ya:\n📌 **{nama}**\n📅 {tanggal} | ⏰ Pukul {waktu}"

def hapus_jadwal_lokal(text: str) -> str:
    keyword = text.lower()
    for w in ["hapus", "jadwal", "tolong", "batalkan", "buang", "nggak", "gak"]:
        keyword = keyword.replace(w, "")
    keyword = keyword.strip(" ,.-")
    
    if not keyword:
        return "Mau hapus jadwal apa nih? Coba sebutkan nama kegiatannya."

    initial_len = len(db["jadwal"])
    # Filter dan buang jadwal yang mengandung keyword tersebut
    db["jadwal"] = [j for j in db["jadwal"] if keyword not in j["nama"].lower()]
    
    if len(db["jadwal"]) < initial_len:
        save_data(db)
        return f"Oke, jadwal yang mengandung kata '{keyword}' udah aku hapus dari daftar."
    return f"Duh, gak nemu jadwal dengan nama atau kata kunci '{keyword}'."

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Local Storage Mode) is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

telegram_app = None

def check_reminders():
    global telegram_app
    if not telegram_app:
        return
    
    now = datetime.now()
    admin_id = os.getenv("ADMIN_USER_ID")
    if not admin_id:
        return

    for jadwal in db.get("jadwal", []):
        if jadwal.get("tanggal") == now.strftime("%Y-%m-%d"):
            try:
                waktu_str = jadwal["waktu"]
                if ":" in waktu_str and "-" in waktu_str:
                    jam_mulai = waktu_str.split("-")[0].strip()
                    kuliah_time = datetime.strptime(f"{jadwal['tanggal']} {jam_mulai}", "%Y-%m-%d %H:%M")
                    diff = kuliah_time - now
                    
                    if timedelta(minutes=28) <= diff <= timedelta(minutes=32) and not jadwal.get("notif_30m"):
                        telegram_app.bot.send_message(chat_id=admin_id, text=f"🔔 **REMINDER KULIAH (30 Menit Lagi)**\nKuliah **{jadwal['nama']}** mulai pukul {jadwal['waktu']}.")
                        jadwal["notif_30m"] = True
                        save_data(db)
            except Exception:
                pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    msg_lower = user_message.lower()
    logging.info(f"Pesan diterima: {user_message}")

    # 1. TAMBAH JADWAL NATURAL
    if any(k in msg_lower for k in ["tambahin", "tambah", "buatkan jadwal", "ada jadwal baru", "tambah jadwal"]):
        nama, tgl, wkt = parse_natural_add(user_message)
        res = tambah_jadwal_lokal(nama, tgl, wkt)
        await update.message.reply_text(res)
        return

    # 2. HAPUS JADWAL NATURAL
    if any(k in msg_lower for k in ["hapus", "batalkan", "buang jadwal"]):
        res = hapus_jadwal_lokal(user_message)
        await update.message.reply_text(res)
        return

    # 3. CEK JADWAL BERDASARKAN HARI (Senin - Minggu)
    day_map = {
        "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, 
        "jumat": 4, "sabtu": 5, "minggu": 6
    }
    
    target_weekday = None
    day_str_target = ""
    for day_name, d_idx in day_map.items():
        if day_name in msg_lower:
            target_weekday = d_idx
            day_str_target = day_name.capitalize()
            break

    if target_weekday is not None:
        now = datetime.now()
        filtered = []
        for j in db.get("jadwal", []):
            try:
                j_date = datetime.strptime(j.get("tanggal"), "%Y-%m-%d")
                if j_date.weekday() == target_weekday and j_date.date() >= now.date():
                    filtered.append(j)
            except Exception:
                pass

        filtered = sorted(filtered, key=lambda x: x.get("tanggal", ""))
        
        resp = f"📅 **Jadwal Hari {day_str_target} (Mendatang):**\n"
        if filtered:
            for j in filtered[:15]:
                resp += f"- **{j.get('tanggal')}** | {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp += f"Nggak ada jadwal tercatat buat hari {day_str_target} ke depan. Yuk tambahin dengan ngomong santai, contoh: *'tambahin kuliah algoritma tanggal 2026-09-16 jam 13:00'*."
        await update.message.reply_text(resp)
        return

    # 4. CEK JADWAL SEMINGGU / HARI INI / BESOK
    if any(k in msg_lower for k in ["seminggu", "7 hari", "minggu ini", "1 minggu"]):
        now = datetime.now()
        end_date = now + timedelta(days=7)
        filtered = []
        for j in db.get("jadwal", []):
            try:
                j_date = datetime.strptime(j.get("tanggal"), "%Y-%m-%d")
                if now.date() <= j_date.date() <= end_date.date():
                    filtered.append(j)
            except Exception:
                pass
        filtered = sorted(filtered, key=lambda x: x.get("tanggal", ""))
        resp = f"📅 **Jadwal 7 Hari ke Depan:**\n"
        if filtered:
            for j in filtered:
                resp += f"- **{j.get('tanggal')}** | {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp += "Aman, gak ada jadwal dalam 7 hari ke depan."
        await update.message.reply_text(resp)
        return

    if "jadwal" in msg_lower and ("besok" in msg_lower or "hari ini" in msg_lower):
        target_date = datetime.now().strftime("%Y-%m-%d")
        if "besok" in msg_lower:
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        filtered = [j for j in db.get("jadwal", []) if j.get("tanggal") == target_date]
        resp = f"📅 **Jadwal tanggal {target_date}:**\n"
        if filtered:
            for j in filtered:
                resp += f"- {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp += "Nggak ada jadwal di tanggal ini. Kosong!"
        await update.message.reply_text(resp)
        return

    # 5. FALLBACK / INFO PANDUAN
    await update.message.reply_text(
        "🤖 Halo Ikrimah! Bot siap dipakai tanpa error:\n"
        "- Ketik nama hari (misal: `rabu`, `kamis`) buat cek jadwal.\n"
        "- Tambah jadwal: *'tambahin Kuliah Algoritma tanggal 2026-09-16 jam 13:00'*.\n"
        "- Hapus jadwal: *'hapus jadwal Algoritma'*."
    )

def main():
    global telegram_app
    token = os.getenv("IZUMI_ACADEMIC_TOKEN")
    if not token:
        logging.error("IZUMI_ACADEMIC_TOKEN tidak ditemukan!")
        return

    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()

    application = ApplicationBuilder().token(token).build()
    telegram_app = application
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logging.info("Izumi Academic Bot (Local Storage Mode) berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
