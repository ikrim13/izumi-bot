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

def get_target_date_from_text(text_lower):
    now = datetime.now()
    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text_lower)
    if match_date:
        return match_date.group(0)
        
    if "besok" in text_lower:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "kemarin" in text_lower:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "hari ini" in text_lower or "sekarang" in text_lower or "nih" in text_lower:
        return now.strftime("%Y-%m-%d")
        
    target_weekday = None
    for day_name, d_idx in day_map_full.items():
        if day_name in text_lower:
            target_weekday = d_idx
            break
            
    if target_weekday is not None:
        days_ahead = target_weekday - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
    return now.strftime("%Y-%m-%d")

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Smart Natural Mode) is running!"

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

    # --- 1. DETEKSI NIAT: HAPUS JADWAL ---
    if any(w in msg_lower for w in ["hapus", "batalkan", "buang", "nggak jadi"]):
        keyword = msg_lower
        for w in ["hapus", "jadwal", "tolong", "batalkan", "buang", "yang", "nggak jadi"]:
            keyword = keyword.replace(w, "")
        keyword = keyword.strip(" ,.-")
        
        if keyword:
            initial_len = len(db["jadwal"])
            db["jadwal"] = [j for j in db["jadwal"] if keyword not in j["nama"].lower()]
            if len(db["jadwal"]) < initial_len:
                save_data(db)
                await update.message.reply_text(f"Aman, jadwal yang ada unsur '{keyword}' udah gua hapus.")
                return
        await update.message.reply_text("Mau hapus jadwal yang mana bro? Coba sebutin lebih spesifik.")
        return

    # --- 2. DETEKSI NIAT: TAMBAH JADWAL ---
    # Jika kalimat mengandung indikasi menambah (tambah, bikin, catet, ada, atau langsung sebut kegiatan + jam)
    is_adding = any(w in msg_lower for w in ["tambah", "tambahin", "bikin", "catet", "catat", "masukin", "buat"])
    has_time_or_place = bool(re.search(r'\d{1,2}[:\.]\d{2}', msg_lower) or "jam" in msg_lower)
    
    if is_adding or (has_time_or_place and not any(w in msg_lower for w in ["apa", "sih", "mana", "kapan"])):
        is_recurring = "setiap" in msg_lower
        target_weekday = None
        for day_name, d_idx in day_map_full.items():
            if day_name in msg_lower:
                target_weekday = d_idx
                break
                
        match_time = re.search(r'(\d{1,2})[:\.](\d{2})', user_message)
        if match_time:
            waktu = f"{int(match_time.group(1)):02d}:{match_time.group(2)}"
        else:
            match_jam = re.search(r'jam\s+(\d{1,2})', msg_lower)
            waktu = f"{int(match_jam.group(1)):02d}:00" if match_jam else "08:00"
                
        tanggal = get_target_date_from_text(msg_lower)

        clean_text = user_message
        for w in ["setiap", "tambahin", "tambah", "jadwal", "tolong", "buatkan", "agenda", "buat", "catet", "catat", "masukin", "hari"]:
            clean_text = re.sub(w, '', clean_text, flags=re.IGNORECASE)
        for day_name in day_map_full.keys():
            clean_text = re.sub(day_name, '', clean_text, flags=re.IGNORECASE)
            
        clean_text = re.sub(r'\d{4}-\d{2}-\d{2}', '', clean_text)
        clean_text = re.sub(r'jam\s+\d{1,2}[:\.]?\d*', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'\d{1,2}[:\.]\d{2}', '', clean_text)
        clean_text = clean_text.replace("tanggal", "").strip(" ,|-")
        
        nama_kegiatan = clean_text.capitalize() if clean_text else "Agenda Baru"

        if is_recurring and target_weekday is not None:
            now = datetime.now()
            days_ahead = target_weekday - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            start_date = now + timedelta(days=days_ahead)
            for i in range(52):
                current_date = start_date + timedelta(weeks=i)
                db["jadwal"].append({"nama": nama_kegiatan, "tanggal": current_date.strftime("%Y-%m-%d"), "waktu": waktu, "sumber": "Chat Rutin"})
            save_data(db)
            await update.message.reply_text(f"Sip! Jadwal rutin **{nama_kegiatan}** udah dipatok tiap hari tersebut untuk setahun ke depan.")
            return
        else:
            db["jadwal"].append({"nama": nama_kegiatan, "tanggal": tanggal, "waktu": waktu, "sumber": "Chat Manual"})
            save_data(db)
            await update.message.reply_text(f"Berhasil dicatet bro:\n📌 **{nama_kegiatan}**\n📅 {tanggal} | ⏰ {waktu}")
            return

    # --- 3. DETEKSI NIAT: CEK TUGAS E-LEARNING ---
    if any(k in msg_lower for k in ["tugas", "deadline", "pr", "ujian", "quiz", "kuis"]):
        live_tugas = fetch_elearning_tasks()
        if live_tugas:
            db["tugas"] = live_tugas
            save_data(db)
            
        tugas_list = db.get("tugas", [])
        now = datetime.now()
        upcoming_tugas = [t for t in tugas_list if datetime.strptime(t.get("tanggal"), "%Y-%m-%d").date() >= now.date()]
        upcoming_tugas = sorted(upcoming_tugas, key=lambda x: x.get("tanggal", ""))
        
        resp = f"📌 **Daftar Tugas & Deadline E-Learning:**\n"
        if upcoming_tugas:
            for t in upcoming_tugas[:10]:
                resp += f"- **{t.get('tanggal')}** ({t.get('waktu', '-')}) | {t['name'] if 'name' in t else t['nama']}\n"
        else:
            resp += "Aman banget, gak ada deadline tugas aktif saat ini."
        await update.message.reply_text(resp)
        return

    # --- 4. DETEKSI NIAT: CEK RENTANG WAKTU (Seminggu / 7 Hari) ---
    if any(k in msg_lower for k in ["seminggu", "7 hari", "minggu ini", "beberapa hari"]):
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

    # --- 5. DEFAULT / FALLBACK: CEK JADWAL HARIAN (Hari ini, besok, atau hari tertentu) ---
    # Kalimat santai seperti "jadwal hari ini?", "besok ada apa?", "senin ada apa aja" akan masuk sini
    target_date = get_target_date_from_text(msg_lower)
    filtered = [j for j in db.get("jadwal", []) if j.get("tanggal") == target_date]
    filtered = sorted(filtered, key=lambda x: x.get("waktu", ""))
    
    resp = f"📅 **Jadwal untuk tanggal {target_date}:**\n"
    if filtered:
        for j in filtered:
            resp += f"- {j['nama']} ({j.get('waktu', '-')})\n"
    else:
        resp += "Nggak ada jadwal tercatat di tanggal ini, kosong bro!"
    await update.message.reply_text(resp)

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

    logging.info("Izumi Academic Bot (Smart Natural Mode) berjalan mulus...")
    application.run_polling()

if __name__ == '__main__':
    main()
