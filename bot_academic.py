import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import requests
from icalendar import Calendar
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ICAL_GOOGLE = "https://calendar.google.com/calendar/ical/ikrimahikrim8%40gmail.com/private-364c46810d96e1681183ca6ad8be97c2/basic.ics"
ICAL_ELEARNING = "https://e-learn.poltekapp.ac.id/calendar/export_execute.php?userid=5325&authtoken=16e794057ce3844f51ea241e4fe35032993933db&preset_what=all&preset_time=custom"

DATA_FILE = "academic_data.json"

def fetch_and_parse_ical():
    """Mengambil data iCal secara aman."""
    jadwal_list = []
    urls = [("Google Calendar", ICAL_GOOGLE), ("E-Learning Poltek APP", ICAL_ELEARNING)]
    
    for source_name, url in urls:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                cal = Calendar.from_ical(response.content)
                for component in cal.walk('vevent'):
                    summary = str(component.get('summary', 'Tanpa Judul'))
                    dtstart = component.get('dtstart')
                    
                    if dtstart:
                        dt = dtstart.dt
                        if isinstance(dt, datetime):
                            tanggal = dt.strftime("%Y-%m-%d")
                            waktu = dt.strftime("%H:%M")
                        else:
                            tanggal = dt.strftime("%Y-%m-%d")
                            waktu = "Sepanjang Hari"
                        
                        item_baru = {"nama": summary, "tanggal": tanggal, "waktu": waktu, "sumber": source_name}
                        if item_baru not in jadwal_list:
                            jadwal_list.append(item_baru)
                logging.info(f"Berhasil memuat agenda dari {source_name}")
            else:
                logging.error(f"Gagal ambil iCal {source_name}, status: {response.status_code}")
        except Exception as e:
            logging.error(f"Error parsing iCal {source_name}: {e}")
            
    return jadwal_list

def load_data():
    initial_jadwal = fetch_and_parse_ical()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if initial_jadwal:
                    manual_items = [j for j in data.get("jadwal", []) if j.get("sumber") == "Manual"]
                    data["jadwal"] = initial_jadwal + manual_items
                    save_data(data)
                return data
        except Exception:
            pass
            
    data = {"jadwal": initial_jadwal, "tugas": []}
    save_data(data)
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

def background_sync_ical():
    global db
    logging.info("Memulai sinkronisasi berkala iCal...")
    live_jadwal = fetch_and_parse_ical()
    if live_jadwal:
        manual_items = [j for j in db.get("jadwal", []) if j.get("sumber") == "Manual"]
        db["jadwal"] = live_jadwal + manual_items
        save_data(db)
        logging.info("Sinkronisasi iCal berkala selesai.")

# --- FUNGSI LOCAL CRUD ---
def tambah_jadwal(nama: str, tanggal: str, waktu: str, ruang: str = "Kampus") -> str:
    item = {"nama": nama, "tanggal": tanggal, "waktu": waktu, "ruang": ruang, "sumber": "Manual"}
    db["jadwal"].append(item)
    save_data(db)
    return f"✅ Berhasil nambah jadwal: {nama} tanggal {tanggal} pukul {waktu} di {ruang}."

def hapus_jadwal(nama: str) -> str:
    initial_len = len(db["jadwal"])
    db["jadwal"] = [j for j in db["jadwal"] if nama.lower() not in j["nama"].lower()]
    if len(db["jadwal"]) < initial_len:
        save_data(db)
        return f"🗑️ Jadwal dengan kata kunci '{nama}' berhasil dihapus."
    return f"❌ Jadwal '{nama}' tidak ditemukan."

def tambah_tugas(nama: str, deadline: str) -> str:
    try:
        dl_obj = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        item = {"nama": nama, "deadline": deadline, "deadline_obj": dl_obj.isoformat()}
        db["tugas"].append(item)
        save_data(db)
        return f"📝 Berhasil nambah tugas: {nama} dengan deadline {deadline}."
    except Exception as e:
        return f"Format deadline salah. Gunakan format YYYY-MM-DD HH:MM."

def hapus_tugas(nama: str) -> str:
    initial_len = len(db["tugas"])
    db["tugas"] = [t for t in db["tugas"] if nama.lower() not in t["nama"].lower()]
    if len(db["tugas"]) < initial_len:
        save_data(db)
        return f"🎉 Tugas '{nama}' berhasil dihapus."
    return f"❌ Tugas '{nama}' tidak ditemukan."

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3.6-flash')
else:
    model = None

app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Anti-Limit Ultimate) is running!"

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

    for tugas in list(db.get("tugas", [])):
        if "deadline_obj" in tugas:
            dl_time = datetime.fromisoformat(tugas["deadline_obj"])
            diff = dl_time - now
            
            if timedelta(hours=47.5) <= diff <= timedelta(hours=48.5) and not tugas.get("notif_h2"):
                telegram_app.bot.send_message(chat_id=admin_id, text=f"⏰ **REMINDER TUGAS (H-2)**\nTugas **{tugas['nama']}** deadline dalam 2 hari ({tugas['deadline']}).")
                tugas["notif_h2"] = True
                save_data(db)
            
            if timedelta(hours=23.5) <= diff <= timedelta(hours=24.5) and not tugas.get("notif_h1"):
                telegram_app.bot.send_message(chat_id=admin_id, text=f"⏰ **REMINDER TUGAS (H-1)**\nTugas **{tugas['nama']}** deadline besok! ({tugas['deadline']}).")
                tugas["notif_h1"] = True
                save_data(db)
                
            if timedelta(hours=1.9) <= diff <= timedelta(hours=2.1) and not tugas.get("notif_2h"):
                telegram_app.bot.send_message(chat_id=admin_id, text=f"🚨 **URGENT: DEADLINE 2 JAM LAGI!**\nTugas **{tugas['nama']}** harus segera dikumpulkan!")
                tugas["notif_2h"] = True
                save_data(db)

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

    day_map = {
        "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, 
        "jumat": 4, "sabtu": 5, "minggu": 6
    }
    
    # Deteksi jika user menanyakan hari tertentu
    target_weekday = None
    for day_name, d_idx in day_map.items():
        if day_name in msg_lower:
            target_weekday = d_idx
            break

    if target_weekday is not None:
        now = datetime.now()
        days_ahead = target_weekday - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        # Filter pas tanggalnya
        filtered = [j for j in db.get("jadwal", []) if j.get("tanggal") == target_date]
        day_str = [k for k, v in day_map.items() if v == target_weekday][0].capitalize()
        
        resp = f"📅 **Jadwal Hari {day_str} ({target_date}):**\n"
        if filtered:
            for j in sorted(filtered, key=lambda x: x.get("waktu", "")):
                resp += f"- **{j['nama']}** ({j.get('waktu', '-')})\n"
        else:
            resp += f"Tidak ada jadwal kuliah atau agenda tercatat di hari {day_str} ({target_date})."
        await update.message.reply_text(resp)
        return

    # 1. CEK JADWAL SEMINGGU KEDEPAN / 7 HARI
    if any(k in msg_lower for k in ["seminggu", "7 hari", "minggu ini", "1 minggu", "apa aja", "agenda"]):
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
            resp += "Tidak ada jadwal kuliah atau agenda tercatat dalam 7 hari ke depan."
        await update.message.reply_text(resp)
        return

    # 2. CEK JADWAL HARI INI / BESOK
    if "jadwal" in msg_lower and ("besok" in msg_lower or "hari ini" in msg_lower):
        target_date = datetime.now().strftime("%Y-%m-%d")
        if "besok" in msg_lower:
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        filtered = [j for j in db.get("jadwal", []) if j.get("tanggal") == target_date]
        resp = f"📅 **Jadwal untuk tanggal {target_date}:**\n"
        if filtered:
            for j in filtered:
                resp += f"- {j['nama']} ({j.get('waktu', '-')})\n"
        else:
            resp += f"Tidak ada jadwal tercatat di tanggal ini."
        await update.message.reply_text(resp)
        return

    # 3. LIHAT DAFTAR TUGAS
    if "tugas" in msg_lower and ("lihat" in msg_lower or "apa" in msg_lower or "daftar" in msg_lower):
        tugas_list = db.get("tugas", [])
        resp = f"📝 **Daftar Tugas Aktif:**\n"
        if tugas_list:
            for t in tugas_list:
                resp += f"- {t['nama']} (Deadline: {t['deadline']})\n"
        else:
            resp += "Belum ada tugas akademik yang tercatat. Aman!"
        await update.message.reply_text(resp)
        return

    # 4. OBROLAN UMUM
    if not model:
        await update.message.reply_text("Duh, API Key Gemini belum dipasang.")
        return

    try:
        response = model.generate_content(f"Kamu adalah asisten akademik Politeknik APP Jakarta untuk Ikrimah. Jawab ringkas dan santai: {user_message}")
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Error Gemini API: {e}")
        await update.message.reply_text(
            "🤖 (Mode Hemat Aktif) Otak AI-ku lagi istirahat sebentar karena limit gratis harian tercapai, "
            "tapi **database jadwal, tugas, dan reminder otomatis kamu tetep jalan 100% normal!** "
            "Ketik 'jadwal' kapanpun kamu butuh."
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
    scheduler.add_job(background_sync_ical, 'interval', hours=1)
    scheduler.start()

    application = ApplicationBuilder().token(token).build()
    telegram_app = application
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logging.info("Izumi Academic Bot (Anti-Limit Ultimate) berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
