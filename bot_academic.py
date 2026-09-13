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
                data = json.load(f)
                if not data.get("jadwal"):
                    data["jadwal"] = get_initial_semester3_schedule()
                    save_data(data)
                return data
        except Exception:
            pass
            
    initial_data = {"jadwal": get_initial_semester3_schedule(), "tugas": []}
    save_data(initial_data)
    return initial_data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

day_map_full = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, 
    "jumat": 4, "sabtu": 5, "minggu": 6
}

def get_initial_semester3_schedule():
    raw_courses = [
        # SENIN
        {"nama": "Manajemen Keuangan", "weekday": 0, "waktu": "13.00-14.20", "ruang": "R. 3.7"},
        # SELASA (Sesuai request: sesi 2 jam 10.15 di ruang 3.4)
        {"nama": "Kuliah Sesi 2", "weekday": 1, "waktu": "10.15", "ruang": "R. 3.4"},
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
    
    nama_kegiatan = clean_text.capitalize() if clean_text else "Kegiatan"

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
            item = {"nama": nama_kegiatan, "tanggal": date_str, "waktu": waktu, "sumber": "Chat"}
            db["jadwal"].append(item)
            added_count += 1
        save_data(db)
        return f"Sip! Jadwal rutin **{nama_kegiatan}** berhasil ditambahkan untuk 1 tahun ke depan."
    else:
        tgl_final = tanggal if tanggal else datetime.now().strftime("%Y-%m-%d")
        item = {"nama": nama_kegiatan, "tanggal": tgl_final, "waktu": waktu, "sumber": "Chat"}
        db["jadwal"].append(item)
        save_data(db)
        return f"Sip, udah dicatat:\n📌 **{nama_kegiatan}**\n📅 {tgl_final} | ⏰ {waktu}"

def hapus_jadwal_lokal(text: str) -> str:
    text_lower = text.lower()
    
    target_weekday = None
    for day_name, d_idx in day_map_full.items():
        if f"hari {day_name}" in text_lower or day_name in text_lower:
            if any(k in text_lower for k in [f"hari {day_name}", f"di {day_name}", f"pada {day_name}"]):
                target_weekday = d_idx
                break

    if target_weekday is not None:
        initial_len = len(db["jadwal"])
        day_name_str = list(day_map_full.keys())[list(day_map_full.values()).index(target_weekday)].capitalize()
        
        filtered_list = []
        for j in db["jadwal"]:
            try:
                j_date = datetime.strptime(j.get("tanggal"), "%Y-%m-%d")
                if j_date.weekday() != target_weekday:
                    filtered_list.append(j)
            except Exception:
                filtered_list.append(j)
                
        db["jadwal"] = filtered_list
        save_data(db)
        removed_count = initial_len - len(db["jadwal"])
        return f"🗑️ Berhasil menghapus {removed_count} sesi jadwal di hari **{day_name_str}**!"

    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text)
    target_date = match_date.group(0) if match_date else None
    
    keyword = text_lower
    for w in ["hapus", "jadwal", "tolong", "batalkan", "buang", "tanggal", "semua"]:
        keyword = keyword.replace(w, "")
    if target_date:
        keyword = keyword.replace(target_date, "")
    keyword = keyword.strip(" ,.-")
    
    if not keyword:
        return "Mau hapus jadwal apa nih?"

    initial_len = len(db["jadwal"])
    if target_date:
        db["jadwal"] = [j for j in db["jadwal"] if not (keyword in j["nama"].lower() and j["tanggal"] == target_date)]
        msg = f"Oke, jadwal '{keyword}' pada tanggal {target_date} dihapus."
    else:
        db["jadwal"] = [j for j in db["jadwal"] if keyword not in j["nama"].lower()]
        msg = f"Oke, semua jadwal dengan kata kunci '{keyword}' dihapus."
        
    if len(db["jadwal"]) < initial_len:
        save_data(db)
        return msg
    return f"Gak nemu jadwal dengan kata kunci '{keyword}'."

# Flask Keep-Alive Server (Port 8080)
app = Flask(__name__)

@app.route('/')
def home():
    return "Izumi Academic Bot (Smart Delete Mode) is running!"

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

    if any(k in msg_lower for k in ["tambahin", "tambah", "setiap", "buatkan jadwal"]):
        res = parse_natural_add(user_message)
        await update.message.reply_text(res)
        return

    if any(k in msg_lower for k in ["hapus", "batalkan", "buang jadwal"]):
        res = hapus_jadwal_lokal(user_message)
        await update.message.reply_text(res)
        return

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
            resp += "Nggak ada jadwal di tanggal ini."
        await update.message.reply_text(resp)
        return

    await update.message.reply_text(
        "🤖 Halo Ikrimah! Jadwal Semester 3 PNJ Akuntansi sudah diperbarui:\n"
        "- Ketik nama hari (misal: `senin`, `selasa`, `rabu`, dll) buat cek jadwal.\n"
        "- Bot juga bisa hapus jadwal per hari (contoh: *'hapus semua jadwal di hari minggu'*)."
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

    logging.info("Izumi Academic Bot (Smart Delete Mode) berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
