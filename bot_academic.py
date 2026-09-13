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
    """Mengambil data iCal dengan aman untuk mencegah spam request."""
    jadwal_list = []
    urls = [("Google Calendar", ICAL_GOOGLE), ("E-Learning Poltek APP", ICAL_ELEARNING)]
    
    for source_name, url in urls:
        try:
            response = requests.get(url, timeout=10)
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
                        
                        # Hindari duplikat data
                        item_baru = {"nama": summary, "tanggal": tanggal, "waktu": waktu, "sumber": source_name}
                        if item_baru not in jadwal_list:
                            jadwal_list.append(item_baru)
                logging.info(f"Berhasil memuat jadwal dari {source_name}")
            else:
                logging.error(f"Gagal ambil iCal {source_name}, status: {response.status_code}")
        except Exception as e:
            logging.error(f"Error parsing iCal {source_name}: {e}")
            
    return jadwal_list

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Default jika file belum ada
    initial_jadwal = fetch_and_parse_ical()
    data = {"jadwal": initial_jadwal, "tugas": []}
    save_data(data)
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

# Fungsi Background untuk Sync iCal otomatis tiap 1 jam sekali (Caches data)
def background_sync_ical():
    global db
    logging.info("Memulai sinkronisasi berkala iCal...")
    live_jadwal = fetch_and_parse_ical()
    if live_jadwal:
        # Pertahankan tugas dan jadwal manual, update dari iCal
        manual_items = [j for j in db.get("jadwal", []) if j.get("sumber") == "Manual"]
        db["jadwal"] = live_jadwal + manual_items
        save_data(db)
        logging.info("Sinkronisasi iCal selesai.")

# --- FUNGSI TOOLS CRUD ---
def tambah_jadwal(nama: str, tanggal: str, waktu: str, ruang: str = "Kampus") -> str:
    """Menambahkan jadwal kuliah manual."""
    item = {"nama": nama, "tanggal": tanggal, "waktu": waktu, "ruang": ruang, "sumber": "Manual"}
    db["jadwal"].append(item)
    save_data(db)
    return f"Berhasil nambah jadwal: {nama} tanggal {tanggal} pukul {waktu} di {ruang}."

def hapus_jadwal(nama: str) -> str:
    """Menghapus jadwal berdasarkan nama."""
    initial_len = len(db["jadwal"])
    db["jadwal"] = [j for j in db["jadwal"] if nama.lower() not in j["nama"].lower()]
    if len(db["jadwal"]) < initial_len:
        save_data(db)
        return f"Jadwal '{nama}' berhasil dihapus."
    return f"Jadwal dengan nama '{nama}' tidak ditemukan."

def tambah_tugas(nama: str, deadline: str) -> str:
    """Menambahkan tugas baru dengan format deadline (YYYY-MM-DD HH:MM)."""
    try:
        dl_obj = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        item = {"nama": nama, "deadline": deadline, "deadline_obj": dl_obj.isoformat()}
        db["tugas"].append(item)
        save_data(db)
        return f"Berhasil nambah tugas: {nama} dengan deadline {deadline}."
    except Exception as e:
        return f"Format deadline salah. Gunakan format YYYY-MM-DD HH:MM. Error: {e}"

def hapus_tugas(nama: str) -> str:
    """Menghapus tugas berdasarkan nama."""
    initial_len = len(db["tugas"])
    db["tugas"] = [t for t in db["tugas"] if nama.lower() not in t["nama"].lower()]
    if len(db["tugas"]) < initial_len:
        save_data(db)
        return f"Tugas '{nama}' berhasil dihapus."
    return f"Tugas dengan nama '{nama}' tidak ditemukan."

available_tools = {
    "tambah_jadwal": tambah_jadwal,
    "hapus_jadwal": hapus_jadwal,
    "tambah_tugas": tambah_tugas,
    "hapus_tugas": hapus_tugas,
}

# Konfigurasi Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    today_str = datetime.now().strftime("%Y-%m-%d (%A)")
    
    system_instruction = (
        f"Kamu adalah Izumi Academic Bot, asisten akademik khusus untuk Ikrimah (Politeknik APP Jakarta). "
        f"Hari ini: {today_str}. Bantu kelola jadwal & tugas berdasarkan database yang ada. "
        f"Jangan pernah bahas hal non-akademik."
    )
    
    model = genai.GenerativeModel(
        model_name='gemini-3.6-flash',
        system_instruction=system_instruction,
        tools=[tambah_jadwal, hapus_jadwal, tambah_tugas, hapus_tugas]
    )
else:
    model = None

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Optimized Anti-Limit) is running!"

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

    # Cek Tugas (H-2, H-1, 2 jam sebelum deadline)
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

    # Cek Jadwal Kuliah (30 menit sebelum mulai)
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

    # Shortcut manual instan untuk cek jadwal/tugas (TANPA MEMAKAI KUOTA GEMINI AI!)
    if "jadwal" in msg_lower and ("besok" in msg_lower or "hari ini" in msg_lower or "minggu" in msg_lower):
        target_date = datetime.now().strftime("%Y-%m-%d")
        if "besok" in msg_lower:
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        filtered = [j for j in db["jadwal"] if j.get("tanggal") == target_date]
        resp = f"📅 **Jadwal untuk tanggal {target_date}:**\n"
        if filtered:
            for j in filtered:
                resp += f"- {j['nama']} ({j['waktu']})\n"
        else:
            resp += "Tidak ada jadwal tercatat di tanggal ini."
        await update.message.reply_text(resp)
        return

    if not model:
        await update.message.reply_text("Duh, API Key Gemini belum dipasang.")
        return

    try:
        # Kirim data ringkas ke Gemini agar hemat kuota token
        chat_context = f"Jadwal ringkas: {len(db['jadwal'])} item. Tugas: {len(db['tugas'])} item.\nUser: {user_message}"
        response = model.generate_content(chat_context)
        
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if fn := getattr(part, 'function_call', None):
                fn_name = fn.name
                fn_args = dict(fn.args)
                if fn_name in available_tools:
                    result_msg = available_tools[fn_name](**fn_args)
                    await update.message.reply_text(result_msg)
                    return

        await update.message.reply_text(response.text)
        
    except Exception as e:
        logging.error(f"Error Gemini API (Kemungkinan Rate Limit): {e}")
        # Fallback pengaman: Jika Gemini kena limit, bot tetap responsif pakai teks biasa
        await update.message.reply_text(
            "⚠️ Duh, otak AI-ku lagi agak sibuk (kena limit sesaat). "
            "Tapi tenang, database jadwal & tugas kamu aman! Coba ketik ulang beberapa saat lagi ya."
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

    # Background Scheduler (Reminder tiap 1 menit, Sync iCal otomatis tiap 1 jam)
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.add_job(background_sync_ical, 'interval', hours=1)
    scheduler.start()

    application = ApplicationBuilder().token(token).build()
    telegram_app = application
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logging.info("Izumi Academic Bot (Optimized & Anti-Limit) berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
