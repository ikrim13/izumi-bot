import os
import json
import logging
import requests
from icalendar import Calendar
from datetime import datetime, timedelta, time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ACADEMIC_TOKEN = os.getenv("IZUMI_ACADEMIC_TOKEN")
TARGET_GROUP_ID = os.getenv("TARGET_GROUP_ID")
ICAL_URL = os.getenv("ICAL_URL")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

STORAGE_FILE = "storage_data.json"

def load_data():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "schedules": {
            "Senin": [{"matkul": "Pemrograman Web", "jam": "08:00", "ruang": "Lab Komputer 1"}],
            "Selasa": [{"matkul": "Basis Data", "jam": "10:00", "ruang": "Kelas 3.2"}],
            "Rabu": [{"matkul": "Jaringan Komputer", "jam": "13:00", "ruang": "Lab Jaringan"}],
            "Kamis": [{"matkul": "Sistem Operasi", "jam": "08:00", "ruang": "Kelas 2.1"}]
        },
        "archive": {},
        "notified_logs": [],
        "notified_classes": []  # Riwayat notifikasi kelas agar tidak spam
    }

def save_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Gagal save data: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 [Academic Bot] Modul akademik & e-learning aktif.\n"
        "Fitur otomatis:\n"
        "- Pengingat jadwal harian (07:00)\n"
        "- Pengingat 30 menit sebelum kuliah mulai (lengkap dengan ruangan)\n"
        "- Pengingat deadline tugas (H-1, 3 jam, 30 menit)\n\n"
        "Perintah manual:\n"
        "- `/jadwal` : Lihat jadwal kuliah\n"
        "- `/tugas` : Cek daftar tugas/deadline terbaru"
    )

async def jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    schedules = data.get("schedules", {})
    text = "📅 **Jadwal Kuliah & Ruangan:**\n"
    for hari, items in schedules.items():
        text += f"\n• **{hari}**:\n"
        for item in items:
            text += f"  - {item['matkul']} | ⏰ {item['jam']} | 🚪 {item['ruang']}\n"
    await update.message.reply_text(text)

async def tugas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Sedang mengambil data deadline dari E-Learning Poltekapp...")
    events = fetch_calendar_events()
    
    if not events:
        await update.message.reply_text("🎉 Tidak ada deadline tugas aktif saat ini di kalender E-Learning.")
        return

    text = "📝 **Daftar Tugas & Deadline E-Learning Poltekapp:**\n"
    for i, (title, dt) in enumerate(events[:10], 1):
        formatted_date = dt.strftime("%d %b %Y, %H:%M")
        text += f"\n{i}. **{title}**\n   ⏰ Deadline: {formatted_date}"
        
    await update.message.reply_text(text)

def fetch_calendar_events():
    try:
        response = requests.get(ICAL_URL, timeout=10)
        if response.status_code != 200:
            return []

        cal = Calendar.from_ical(response.content)
        events = []
        
        for component in cal.walk('vevent'):
            summary = component.get('summary')
            dtend = component.get('dtend')
            
            if summary and dtend:
                date_time = dtend.dt
                if isinstance(date_time, datetime):
                    if date_time.tzinfo is not None:
                        date_time = date_time.astimezone().replace(tzinfo=None)
                    events.append((str(summary), date_time))
        return events
    except Exception as e:
        logging.error(f"Error fetching ical: {e}")
        return []

# --- JOB QUEUE OTOMATIS ---
async def job_daily_schedule(context: ContextTypes.DEFAULT_TYPE):
    if not TARGET_GROUP_ID:
        return
    
    days_map = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu", "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}
    today_en = datetime.now().strftime("%A")
    today_id = days_map.get(today_en, "Senin")

    data = load_data()
    schedules = data.get("schedules", {})
    todays_classes = schedules.get(today_id, [])

    text = f"☀️ **Selamat Pagi, Kabinet!**\n📅 Jadwal Kuliah Hari Ini (**{today_id}**):\n"
    if todays_classes:
        for c in todays_classes:
            text += f"• **{c['matkul']}** — ⏰ {c['jam']} | 🚪 {c['ruang']}\n"
    else:
        text += "• Tidak ada jadwal kuliah hari ini. Santai dulu bro!\n"

    await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=text)

async def job_check_class_reminder(context: ContextTypes.DEFAULT_TYPE):
    if not TARGET_GROUP_ID:
        return

    days_map = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu", "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}
    now = datetime.now()
    today_en = now.strftime("%A")
    today_id = days_map.get(today_en, "Senin")

    data = load_data()
    schedules = data.get("schedules", {})
    todays_classes = schedules.get(today_id, [])
    
    if "notified_classes" not in data:
        data["notified_classes"] = []

    for c in todays_classes:
        # Format jam kelas "HH:MM"
        try:
            class_time_obj = datetime.strptime(c['jam'], "%H:%M").time()
            class_datetime = datetime.combine(now.date(), class_time_obj)
            
            # Hitung selisih waktu (30 menit = 1800 detik)
            diff = class_datetime - now
            total_seconds = diff.total_seconds()

            # Jika mendekati 30 menit sebelum mulai (rentang toleransi 5 menit / 300 detik)
            if 0 <= total_seconds <= 1800:
                unique_key = f"{today_id}_{c['matkul']}_{c['jam']}_{now.strftime('%Y%m%d')}"
                
                if unique_key not in data["notified_classes"]:
                    msg = (
                        f"🔔 **PENGINGAT KULIAH (30 MENIT LAGI)**\n\n"
                        f"📖 Mata Kuliah: **{c['matkul']}**\n"
                        f"⏰ Jam: {c['jam']}\n"
                        f"🚪 Ruangan: **{c['ruang']}**\n\n"
                        f"Ayo bersiap-siap menuju kelas!"
                    )
                    await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=msg)
                    
                    data["notified_classes"].append(unique_key)
                    if len(data["notified_classes"]) > 50:
                        data["notified_classes"] = data["notified_classes"][-30:]
                    save_data(data)
        except Exception as e:
            logging.error(f"Error parsing class time: {e}")

async def job_check_deadlines(context: ContextTypes.DEFAULT_TYPE):
    if not TARGET_GROUP_ID:
        return

    events = fetch_calendar_events()
    if not events:
        return

    now = datetime.now()
    data = load_data()
    if "notified_logs" not in data:
        data["notified_logs"] = []

    for title, dt in events:
        diff = dt - now
        total_seconds = diff.total_seconds()

        if total_seconds < 0:
            continue

        intervals = [
            (86400, "⚠️ **PENGINGAT DEADLINE (H-1)**"),
            (10800, "⚠️ **PENGINGAT DEADLINE (3 JAM LAGI!)**"),
            (1800, "🚨 **PERINGATAN KRITIS (30 MENIT LAGI!)**")
        ]

        for limit_sec, label in intervals:
            if abs(total_seconds - limit_sec) <= 300:
                unique_key = f"{title}_{limit_sec}_{dt.strftime('%Y%m%d%H%M')}"
                
                if unique_key not in data["notified_logs"]:
                    msg = (
                        f"{label}\n\n"
                        f"📝 Tugas: **{title}**\n"
                        f"⏰ Waktu Deadline: {dt.strftime('%d %b %Y, %H:%M')}"
                    )
                    await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=msg)
                    
                    data["notified_logs"].append(unique_key)
                    if len(data["notified_logs"]) > 100:
                        data["notified_logs"] = data["notified_logs"][-50:]
                    save_data(data)

def main():
    if not ACADEMIC_TOKEN:
        logging.error("IZUMI_ACADEMIC_TOKEN tidak ditemukan!")
        return
    
    app = Application.builder().token(ACADEMIC_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jadwal", jadwal))
    app.add_handler(CommandHandler("tugas", tugas))
    
    job_queue = app.job_queue
    # Kirim jadwal harian jam 07:00 pagi
    job_queue.run_daily(job_daily_schedule, time=datetime.strptime("07:00", "%H:%M").time())
    # Cek pengingat kelas setiap 5 menit (300 detik)
    job_queue.run_repeating(job_check_class_reminder, interval=300, first=15)
    # Cek deadline e-learning setiap 5 menit (300 detik)
    job_queue.run_repeating(job_check_deadlines, interval=300, first=10)

    print("Academic Bot sedang berjalan dengan integrasi E-Learning & Job Automation lengkap...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
