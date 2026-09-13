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
        # SENIN (Dikosongkan sesuai request)
        
        # SELASA (Sesi 2 diganti jadi Manajemen Keuangan, ruang 3.4)
        {"nama": "Manajemen Keuangan", "weekday": 1, "waktu": "10.15", "ruang": "R. 3.4"},
        {"nama": "Aplikasi Komputer", "weekday": 1, "waktu": "13.00-15.00", "ruang": "Lab E.2.1"},
        # RABU
        {"nama": "Bahasa Indonesia & TPI", "weekday": 2, "waktu": "07.30-08.50", "ruang": "R. 3.2"},
        {"nama": "Lalu Lintas Pembayaran", "weekday": 2, "waktu": "10.00-11.20", "ruang": "R. 3.13"},
        {"nama": "Prak. Manajemen Keuangan", "weekday": 2, "waktu": "13.00-15.00", "ruang": "R. 3.11"},
        {"nama": "Metodologi Penelitian", "weekday": 2, "waktu": "15.15-16.35", "ruang": "R. 1.3"},
        # KAMIS
        {"nama": "Prak. Lalu Lintas Pembayaran", "weekday": 3, "waktu": "07.30-09.30", "ruang": "R. 3.1"},
        {"nama": "Kewirausahaan", "weekday": 3, "waktu": "10.00-11.20", "ruang": "R. 2.6"},
        {"nama": "Prak. Kewirausahaan", "weekday": 3, "waktu": "13.00-15.00", "ruang": "R. 2.6"},
        {"nama": "Ilmu Ekonomi", "weekday": 3, "waktu": "15.15-17.15", "ruang": "R. 1.1"},
        # JUMAT
        {"nama": "Tugas Besar II", "weekday": 4, "waktu": "13.00-15.00", "ruang": "Lab E.2.1"},
        {"nama": "Tugas Besar II (Sesi 2)", "weekday": 4, "waktu": "15.15-17.15", "ruang": "Lab E.2.1"}
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
                "nama": f"{course['nama']} ({course['ruang']})",
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
            logging.info(f"Berhasil memuat {len(tugas_list)} tugas dari E-Learning.")
        else:
            logging.error(f"Gagal tarik iCal E-Learning, status: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching E-Learning iCal: {e}")
        
    return tugas_list

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                # Paksa update ulang jadwal supaya hari senin kosong dan selasa ter-update
                data["jadwal"] = get_initial_semester3_schedule()
                if not data.get("tugas"):
                    data["tugas"] = fetch_elearning_tasks()
                save_data(data)
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
    logging.info("Memulai sinkronisasi tugas E-Learning berkala...")
    live_tugas = fetch_elearning_tasks()
    if live_tugas:
        db["tugas"] = live_tugas
        save_data(db)
        logging.info("Sinkronisasi tugas E-Learning selesai.")

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Updated Schedule) is running!"

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

    # 1. CEK TUGAS E-LEARNING
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

    # 2. CEK JADWAL BERDASARKAN HARI
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

    # 3. CEK 7 HARI KEDEPAN
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

    # 4. FALLBACK UMUM
    await update.message.reply_text(
        "🤖 Halo Ikrimah! Jadwal sudah diperbarui (Senin kosong, Selasa sesi 2 Manajemen Keuangan):\n"
        "- Ketik **'tugas'** buat cek deadline E-Learning.\n"
        "- Ketik nama hari (misal: `senin`, `selasa`, `rabu`) buat cek jadwal kuliah."
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

    logging.info("Izumi Academic Bot (Updated) berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
