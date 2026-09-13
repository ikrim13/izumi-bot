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

# --- HELPER MAPPING HARI ---
day_map_full = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, 
    "jumat": 4, "sabtu": 5, "minggu": 6
}

def generate_recurring_schedule(nama: str, target_weekday: int, waktu: str):
    """Otomatis generate jadwal rutin untuk 1 tahun ke depan berdasarkan hari dalam seminggu."""
    now = datetime.now()
    # Cari tanggal terdekat untuk hari tersebut
    days_ahead = target_weekday - now.weekday()
    if days_ahead < 0:
        days_ahead += 7
    
    start_date = now + timedelta(days=days_ahead)
    
    # Generate selama 52 minggu (1 tahun)
    added_count = 0
    for i in range(52):
        current_date = start_date + timedelta(weeks=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Cek apakah sudah ada di database supaya tidak duplikat
        exists = any(j['nama'].lower() == nama.lower() and j['tanggal'] == date_str for j in db["jadwal"])
        if not exists:
            item = {"nama": nama, "tanggal": date_str, "waktu": waktu, "sumber": "Rutin"}
            db["jadwal"].append(item)
            added_count += 1
            
    save_data(db)
    day_name = list(day_map_full.keys())[list(day_map_full.values()).index(target_weekday)].capitalize()
    return f"Sip! Jadwal rutin **{nama}** setiap hari **{day_name}** pukul **{waktu}** sudah otomatis dibuat untuk 1 tahun ke depan ({added_count} sesi dicatat)."

def parse_natural_add(text):
    text_lower = text.lower()
    
    # Deteksi apakah ini jadwal rutin mingguan (mengandung kata "setiap")
    is_recurring = "setiap" in text_lower
    
    target_weekday = None
    for day_name, d_idx in day_map_full.items():
        if day_name in text_lower:
            target_weekday = d_idx
            break
            
    # Cari waktu (HH:MM atau jam X)
    match_time = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if match_time:
        waktu = f"{int(match_time.group(1)):02d}:{match_time.group(2)}"
    else:
        match_jam = re.search(r'jam\s+(\d{1,2})', text_lower)
        if match_jam:
            waktu = f"{int(match_jam.group(1)):02d}:00"
        else:
            waktu = "08:00"
            
    # Cari tanggal spesifik jika ada (YYYY-MM-DD)
    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text)
    tanggal = match_date.group(0) if match_date else None

    # Bersihkan teks untuk nama kegiatan
    clean_text = text
    for w in ["setiap", "tambahin", "tambah", "jadwal", "tolong", "buatkan", "agenda", "buat", "hari"]:
        clean_text = re.sub(w, '', clean_text, flags=re.IGNORECASE)
    
    for day_name in day_map_full.keys():
        clean_text = re.sub(day_name, '', clean_text, flags=re.IGNORECASE)
        
    clean_text = re.sub(r'\d{4}-\d{2}-\d{2}', '', clean_text)
    clean_text = re.sub(r'jam\s+\d{1,2}[:\.]?\d*', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\d{1,2}[:\.]\d{2}', '', clean_text)
    clean_text = clean_text.replace("tanggal", "").strip(" ,|-")
    
    nama_kegiatan = clean_text.capitalize() if clean_text else "Kegiatan"

    if is_recurring and target_weekday is not None:
        return generate_recurring_schedule(nama_kegiatan, target_weekday, waktu)
    else:
        # Jadwal sekali jalan (single date)
        tgl_final = tanggal if tanggal else datetime.now().strftime("%Y-%m-%d")
        item = {"nama": nama_kegiatan, "tanggal": tgl_final, "waktu": waktu, "sumber": "Chat"}
        db["jadwal"].append(item)
        save_data(db)
        return f"Sip, udah aku catat ya:\n📌 **{nama_kegiatan}**\n📅 {tgl_final} | ⏰ Pukul {waktu}"

def hapus_jadwal_lokal(text: str) -> str:
    text_lower = text.lower()
    
    # Cari tanggal spesifik jika user mau hapus di tanggal tertentu doang
    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text)
    target_date = match_date.group(0) if match_date else None
    
    # Ambil keyword nama kegiatan
    keyword = text_lower
    for w in ["hapus", "jadwal", "tolong", "batalkan", "buang", "tanggal"]:
        keyword = keyword.replace(w, "")
    if target_date:
        keyword = keyword.replace(target_date, "")
    keyword = keyword.strip(" ,.-")
    
    if not keyword:
        return "Mau hapus jadwal apa nih? Coba sebutkan nama kegiatannya."

    initial_len = len(db["jadwal"])
    
    if target_date:
        # Hapus hanya pada tanggal tertentu saja
        db["jadwal"] = [j for j in db["jadwal"] if not (keyword in j["nama"].lower() and j["tanggal"] == target_date)]
        msg = f"Oke, jadwal '{keyword}' pada tanggal {target_date} berhasil dihapus."
    else:
        # Hapus semua dari seluruh tanggal
        db["jadwal"] = [j for j in db["jadwal"] if keyword not in j["nama"].lower()]
        msg = f"Oke, semua jadwal dengan kata kunci '{keyword}' berhasil dihapus dari daftar."
        
    if len(db["jadwal"]) < initial_len:
        save_data(db)
        return msg
    return f"Duh, gak nemu jadwal dengan kata kunci '{keyword}'{f' pada tanggal {target_date}' if target_date else ''}."

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Recurring Schedule Mode) is running!"

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

    # Cek reminder 30 menit sebelum jadwal
    for jadwal in db.get("jadwal", []):
        if jadwal.get("tanggal") == now.strftime("%Y-%m-%d"):
            waktu_str = jadwal.get("waktu", "")
            if ":" in waktu_str and len(waktu_str) == 5:
                try:
                    kuliah_time = datetime.strptime(f"{jadwal['tanggal']} {waktu_str}", "%Y-%m-%d %H:%M")
                    diff = kuliah_time - now
                    
                    # Jika sisa waktu antara 28 sampai 32 menit lagi dan belum pernah dinotifikasi
                    if timedelta(minutes=28) <= diff <= timedelta(minutes=32) and not jadwal.get("notif_30m"):
                        telegram_app.bot.send_message(
                            chat_id=admin_id, 
                            text=f"🔔 **REMINDER KULIAH (30 Menit Lagi)**\nKuliah **{jadwal['nama']}** akan mulai pukul {waktu_str}!"
                        )
                        jadwal["notif_30m"] = True
                        save_data(db)
                except Exception:
                    pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    msg_lower = user_message.lower()
    logging.info(f"Pesan diterima: {user_message}")

    # 1. TAMBAH JADWAL (Rutin atau Sekali)
    if any(k in msg_lower for k in ["tambahin", "tambah", "setiap", "buatkan jadwal", "ada jadwal baru"]):
        res = parse_natural_add(user_message)
        await update.message.reply_text(res)
        return

    # 2. HAPUS JADWAL (Semua atau Tanggal Tertentu)
    if any(k in msg_lower for k in ["hapus", "batalkan", "buang jadwal"]):
        res = hapus_jadwal_lokal(user_message)
        await update.message.reply_text(res)
        return

    # 3. CEK JADWAL BERDASARKAN HARI (Senin - Minggu)
    target_weekday = None
    day_str_target = ""
    for day_name, d_idx in day_map_full.items():
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

        filtered = sorted(filtered, key=lambda x: (x.get("tanggal", ""), x.get("waktu", "")))
        
        resp = f"📅 **Jadwal Hari {day_str_target} (Mendatang):**\n"
        if filtered:
            for j in filtered[:15]:
                resp += f"- **{j.get('tanggal')}** | {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp += f"Nggak ada jadwal tercatat buat hari {day_str_target} ke depan."
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
        filtered = sorted(filtered, key=lambda x: (x.get("tanggal", ""), x.get("waktu", "")))
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

    # 5. PANDUAN / FALLBACK
    await update.message.reply_text(
        "🤖 Halo Ikrimah! Bot siap jalan:\n"
        "- Cek jadwal: Ketik nama hari (misal: `rabu`, `kamis`).\n"
        "- Tambah rutin: *'Setiap hari Rabu jam 13:00 kuliah Algoritma'*.\n"
        "- Hapus permanen: *'Hapus jadwal Algoritma'*.\n"
        "- Hapus tanggal tertentu: *'Hapus jadwal Algoritma tanggal 2026-09-16'*."
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

    logging.info("Izumi Academic Bot (Recurring Schedule Mode) berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
