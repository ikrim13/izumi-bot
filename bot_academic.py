import os
import json
import logging
import re
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import requests
from icalendar import Calendar
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DATA_FILE = "academic_data.json"
ICAL_ELEARNING = "https://e-learn.poltekapp.ac.id/calendar/export_execute.php?userid=5325&authtoken=16e794057ce3844f51ea241e4fe35032993933db&preset_what=all&preset_time=custom"

day_map_full = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, 
    "jumat": 4, "sabtu": 5, "minggu": 6
}

def get_initial_semester3_schedule():
    raw_courses = [
        # SELASA
        {"nama": "Manajemen Keuangan (R. 3.4)", "weekday": 1, "waktu": "10.15"},
        {"nama": "Aplikasi Komputer (Lab E.2.1)", "weekday": 1, "waktu": "13.00-15.00"},
        # RABU
        {"nama": "Bahasa Indonesia & TPI (R. 3.2)", "weekday": 2, "waktu": "07.30-08.50"},
        {"nama": "Lalu Lintas Pembayaran (R. 3.13)", "weekday": 2, "waktu": "10.00-11.20"},
        {"nama": "Prak. Manajemen Keuangan (R. 3.11)", "weekday": 2, "waktu": "13.00-15.00"},
        {"nama": "Metodologi Penelitian (R. 1.3)", "weekday": 2, "waktu": "15.15-16.35"},
        # KAMIS
        {"nama": "Prak. Lalu Lintas Pembayaran (R. 3.1)", "weekday": 3, "waktu": "07.30-09.30"},
        {"nama": "Kewirausahaan (R. 2.6)", "weekday": 3, "waktu": "10.00-11.20"},
        {"nama": "Prak. Kewirausahaan (R. 2.6)", "weekday": 3, "waktu": "13.00-15.00"},
        {"nama": "Ilmu Ekonomi (R. 1.1)", "weekday": 3, "waktu": "15.15-17.15"},
        # JUMAT
        {"nama": "Tugas Besar II (Lab E.2.1)", "weekday": 4, "waktu": "13.00-15.00"},
        {"nama": "Tugas Besar II Sesi 2 (Lab E.2.1)", "weekday": 4, "waktu": "15.15-17.15"}
    ]

    generated_list = []
    now = datetime.now()

    for course in raw_courses:
        target_weekday = course["weekday"]
        days_ahead = target_weekday - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        start_date = now + timedelta(days=days_ahead)

        for i in range(52):
            current_date = start_date + timedelta(weeks=i)
            date_str = current_date.strftime("%Y-%m-%d")
            item = {
                "nama": course['nama'],
                "tanggal": date_str,
                "waktu": course["waktu"],
                "sumber": "Semester 3"
            }
            generated_list.append(item)

    return generated_list

def fetch_elearning_tasks():
    tugas_list = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(ICAL_ELEARNING, headers=headers, timeout=10)
        if response.status_code == 200:
            cal = Calendar.from_ical(response.content)
            for component in cal.walk('vevent'):
                summary = str(component.get('summary', 'Tugas Tanpa Nama'))
                dtstart = component.get('dtstart')
                
                if dtstart:
                    dt = dtstart.dt
                    if isinstance(dt, datetime):
                        tanggal = dt.strftime("%Y-%m-%d")
                        waktu = dt.strftime("%H:%M")
                    else:
                        tanggal = dt.strftime("%Y-%m-%d")
                        waktu = "Sepanjang Hari"
                    
                    item_tugas = {"nama": summary, "tanggal": tanggal, "waktu": waktu, "sumber": "E-Learning"}
                    if item_tugas not in tugas_list:
                        tugas_list.append(item_tugas)
    except Exception as e:
        logging.error(f"Error fetching E-Learning iCal: {e}")
    return tugas_list

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if not data.get("jadwal"):
                    data["jadwal"] = get_initial_semester3_schedule()
                if not data.get("tugas"):
                    data["tugas"] = fetch_elearning_tasks()
                return data
        except Exception:
            pass
            
    initial_data = {
        "jadwal": get_initial_semester3_schedule(), 
        "tugas": fetch_elearning_tasks()
    }
    save_data(initial_data)
    return initial_data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

def background_sync_elearning():
    global db
    live_tugas = fetch_elearning_tasks()
    if live_tugas:
        db["tugas"] = live_tugas
        save_data(db)

# --- PARSER TAMBAH JADWAL MANUAL ---
def parse_natural_add(text):
    text_lower = text.lower()
    is_recurring = "setiap" in text_lower
    
    target_weekday = None
    for day_name, d_idx in day_map_full.items():
        if day_name in text_lower:
            target_weekday = d_idx
            break
            
    match_time = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if match_time:
        waktu = f"{int(match_time.group(1)):02d}:{match_time.group(2)}"
    else:
        match_jam = re.search(r'jam\s+(\d{1,2})', text_lower)
        if match_jam:
            waktu = f"{int(match_jam.group(1)):02d}:00"
        else:
            waktu = "08:00"
            
    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text)
    tanggal = match_date.group(0) if match_date else None

    clean_text = text
    for w in ["setiap", "tambahin", "tambah", "jadwal", "tolong", "buatkan", "agenda", "buat", "hari"]:
        clean_text = re.sub(w, '', clean_text, flags=re.IGNORECASE)
    
    for day_name in day_map_full.keys():
        clean_text = re.sub(day_name, '', clean_text, flags=re.IGNORECASE)
        
    clean_text = re.sub(r'\d{4}-\d{2}-\d{2}', '', clean_text)
    clean_text = re.sub(r'jam\s+\d{1,2}[:\.]?\d*', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\d{1,2}[:\.]\d{2}', '', clean_text)
    clean_text = clean_text.replace("tanggal", "").strip(" ,|-")
    
    nama_kegiatan = clean_text.capitalize() if clean_text else "Kegiatan Baru"

    if is_recurring and target_weekday is not None:
        now = datetime.now()
        days_ahead = target_weekday - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        start_date = now + timedelta(days=days_ahead)
        
        added_count = 0
        for i in range(52):
            current_date = start_date + timedelta(weeks=i)
            date_str = current_date.strftime("%Y-%m-%d")
            item = {"nama": nama_kegiatan, "tanggal": date_str, "waktu": waktu, "sumber": "Chat Rutin"}
            db["jadwal"].append(item)
            added_count += 1
        save_data(db)
        return f"Sip! Jadwal rutin **{nama_kegiatan}** berhasil ditambahkan untuk 1 tahun ke depan."
    else:
        tgl_final = tanggal if tanggal else datetime.now().strftime("%Y-%m-%d")
        item = {"nama": nama_kegiatan, "tanggal": tgl_final, "waktu": waktu, "sumber": "Chat Manual"}
        db["jadwal"].append(item)
        save_data(db)
        return f"Sip, udah dicatat:\n📌 **{nama_kegiatan}**\n📅 {tgl_final} | ⏰ {waktu}"

def hapus_jadwal_lokal(text: str) -> str:
    text_lower = text.lower()
    keyword = text_lower
    for w in ["hapus", "jadwal", "tolong", "batalkan", "buang"]:
        keyword = keyword.replace(w, "")
    keyword = keyword.strip(" ,.-")
    
    if not keyword:
        return "Mau hapus jadwal apa nih?"

    initial_len = len(db["jadwal"])
    db["jadwal"] = [j for j in db["jadwal"] if keyword not in j["nama"].lower()]
    
    if len(db["jadwal"]) < initial_len:
        save_data(db)
        return f"Oke, semua jadwal dengan kata kunci '{keyword}' berhasil dihapus."
    return f"Gak nemu jadwal dengan kata kunci '{keyword}'."

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot is running!"

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
            waktu_str = jadwal.get("waktu", "")
            time_part = waktu_str.split("-")[0].replace(".", ":").strip()
            if len(time_part) == 5 and ":" in time_part:
                try:
                    kuliah_time = datetime.strptime(f"{jadwal['tanggal']} {time_part}", "%Y-%m-%d %H:%M")
                    diff = kuliah_time - now
                    
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

    # 1. TAMBAH JADWAL MANUAL / RUTIN
    if any(k in msg_lower for k in ["tambahin", "tambah", "setiap", "buatkan jadwal"]):
        res = parse_natural_add(user_message)
        await update.message.reply_text(res)
        return

    # 2. HAPUS JADWAL
    if any(k in msg_lower for k in ["hapus", "batalkan", "buang"]):
        res = hapus_jadwal_lokal(user_message)
        await update.message.reply_text(res)
        return

    # 3. CEK TUGAS E-LEARNING
    if any(k in msg_lower for k in ["tugas", "deadline", "pr"]):
        live_tugas = fetch_elearning_tasks()
        if live_tugas:
            db["tugas"] = live_tugas
            save_data(db)
            
        tugas_list = db.get("tugas", [])
        now = datetime.now()
        upcoming_tugas = []
        for t in tugas_list:
            try:
                t_date = datetime.strptime(t.get("tanggal"), "%Y-%m-%d")
                if t_date.date() >= now.date():
                    upcoming_tugas.append(t)
            except Exception:
                pass
                
        upcoming_tugas = sorted(upcoming_tugas, key=lambda x: x.get("tanggal", ""))
        
        resp = f"📌 **Daftar Tugas & Deadline E-Learning:**\n"
        if upcoming_tugas:
            for t in upcoming_tugas[:10]:
                resp += f"- **{t.get('tanggal')}** ({t.get('waktu', '-')}) | {t['nama']}\n"
        else:
            resp += "Belum ada tugas atau deadline tercatat dari E-Learning saat ini. Aman!"
        await update.message.reply_text(resp)
        return

    # 4. CEK JADWAL BERDASARKAN HARI
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
        
        if filtered:
            target_date_str = filtered[0].get('tanggal')
            todays_sessions = [j for j in filtered if j.get('tanggal') == target_date_str]
            
            resp = f"📅 **Jadwal Hari {day_str_target} ({target_date_str}):**\n"
            for j in todays_sessions:
                resp += f"- {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp = f"Nggak ada jadwal tercatat buat hari {day_str_target} ke depan."
        await update.message.reply_text(resp)
        return

    # 5. CEK 7 HARI KEDEPAN
    if any(k in msg_lower for k in ["seminggu", "7 hari", "minggu ini"]):
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
            for j in filtered[:12]:
                resp += f"- **{j.get('tanggal')}** | {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp += "Aman, gak ada jadwal dalam 7 hari ke depan."
        await update.message.reply_text(resp)
        return

    await update.message.reply_text(
        "🤖 Halo Ikrimah! Bot siap jalan:\n"
        "- Cek jadwal: Ketik nama hari (`selasa`, `rabu`, dll).\n"
        "- Cek tugas E-Learning: Ketik `tugas` atau `deadline`.\n"
        "- Tambah jadwal manual: *'tambahin rapat bimbingan tanggal 2026-09-15 jam 14:00'*.\n"
        "- Hapus jadwal: *'hapus rapat bimbingan'*."
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
    scheduler.add_job(background_sync_elearning, 'interval', hours=2)
    scheduler.start()

    application = ApplicationBuilder().token(token).build()
    telegram_app = application
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logging.info("Izumi Academic Bot berjalan mulus...")
    application.run_polling()

if __name__ == '__main__':
    main()
