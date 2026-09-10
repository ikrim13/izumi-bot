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
        "archive": {},
        "notified_logs": [],
        "notified_classes": []
    }

def save_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Gagal save data: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 [Academic Bot] Modul akademik & kalender aktif.\n\n"
        "Perintah manual:\n"
        "- `/jadwal` : Lihat jadwal/kegiatan kalender terdekat\n"
        "- `/besok` : Cek jadwal & kegiatan untuk besok\n"
        "- `/minggu` : Cek jadwal & kegiatan 7 hari ke depan\n"
        "- `/tugas` : Cek daftar tugas/deadline terbaru"
    )

async def jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Sedang mengambil jadwal dan kegiatan dari Kalender...")
    events = fetch_calendar_events()
    
    if not events:
        await update.message.reply_text("🎉 Tidak ada jadwal atau kegiatan ditemukan di kalender.")
        return

    text = "📅 **Jadwal & Kegiatan Kalender Terkini:**\n"
    for i, (title, dt) in enumerate(events[:15], 1):
        formatted_date = dt.strftime("%d %b %Y, %H:%M")
        text += f"\n{i}. **{title}**\n   ⏰ {formatted_date}"
        
    await update.message.reply_text(text)

async def besok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Sedang mengecek jadwal untuk besok...")
    events = fetch_calendar_events()
    
    if not events:
        await update.message.reply_text("🎉 Tidak ada jadwal atau kegiatan di kalender.")
        return

    tomorrow = datetime.now().date() + timedelta(days=1)
    
    tomorrow_events = []
    for title, dt in events:
        if dt.date() == tomorrow:
            tomorrow_events.append((title, dt))

    if not tomorrow_events:
        await update.message.reply_text(f"🎉 Santai! Tidak ada jadwal kuliah atau tugas untuk besok ({tomorrow.strftime('%d %b %Y')}).")
        return

    text = f"📅 **Jadwal & Kegiatan Besok ({tomorrow.strftime('%d %b %Y')}):**\n"
    for i, (title, dt) in enumerate(tomorrow_events, 1):
        formatted_time = dt.strftime("%H:%M")
        text += f"\n{i}. **{title}**\n   ⏰ Pukul {formatted_time}"
        
    await update.message.reply_text(text)

async def minggu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Sedang mengambil jadwal dan kegiatan untuk 7 hari ke depan...")
    events = fetch_calendar_events()
    
    if not events:
        await update.message.reply_text("🎉 Tidak ada jadwal atau kegiatan ditemukan di kalender.")
        return

    now = datetime.now()
    one_week_later = now + timedelta(days=7)
    
    week_events = []
    for title, dt in events:
        if now <= dt <= one_week_later:
            week_events.append((title, dt))

    if not week_events:
        await update.message.reply_text("🎉 Santai! Tidak ada jadwal kuliah atau tugas untuk 7 hari ke depan.")
        return

    text = "📅 **Jadwal & Kegiatan 7 Hari ke Depan:**\n"
    for i, (title, dt) in enumerate(week_events, 1):
        formatted_date = dt.strftime("%d %b %Y, %H:%M")
        text += f"\n{i}. **{title}**\n   ⏰ {formatted_date}"
        
    await update.message.reply_text(text)

async def tugas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Sedang mengambil data deadline dari Kalender...")
    events = fetch_calendar_events()
    
    if not events:
        await update.message.reply_text("🎉 Tidak ada deadline tugas aktif saat ini di kalender.")
        return

    text = "📝 **Daftar Tugas & Deadline Terdekat:**\n"
    for i, (title, dt) in enumerate(events[:10], 1):
        formatted_date = dt.strftime("%d %b %Y, %H:%M")
        text += f"\n{i}. **{title}**\n   ⏰ Deadline: {formatted_date}"
        
    await update.message.reply_text(text)

def fetch_calendar_events():
    try:
        response = requests.get(ICAL_URL, timeout=10)
        if response.status_code != 200:
            logging.error(f"Gagal mengambil iCal, status code: {response.status_code}")
            return []

        cal = Calendar.from_ical(response.content)
        events = []
        
        for component in cal.walk('vevent'):
            summary = component.get('summary')
            dt = component.get('dtstart') or component.get('dtend')
            
            if summary and dt:
                date_time = dt.dt
                if isinstance(date_time, datetime):
                    if date_time.tzinfo is not None:
                        date_time = date_time.astimezone().replace(tzinfo=None)
                    events.append((str(summary), date_time))
                elif isinstance(date_time, type(datetime.now().date())):
                    date_time = datetime.combine(date_time, time(0, 0))
                    events.append((str(summary), date_time))
                    
        events.sort(key=lambda x: x[1])
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

    events = fetch_calendar_events()
    today_date = datetime.now().date()
    
    todays_classes = [title for title, dt in events if dt.date() == today_date]

    text = f"☀️ **Selamat Pagi!**\n📅 Jadwal & Kegiatan Hari Ini (**{today_id}**):\n"
    if todays_classes:
        for c in todays_classes:
            text += f"• **{c}**\n"
    else:
        text += "• Tidak ada jadwal kuliah atau kegiatan hari ini.\n"

    await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=text)

async def job_check_class_reminder(context: ContextTypes.DEFAULT_TYPE):
    if not TARGET_GROUP_ID:
        return

    events = fetch_calendar_events()
    if not events:
        return

    now = datetime.now()
    data = load_data()
    if "notified_classes" not in data:
        data["notified_classes"] = []

    for title, dt in events:
        diff = dt - now
        total_seconds = diff.total_seconds()

        if 0 <= total_seconds <= 1800:
            unique_key = f"{title}_{dt.strftime('%Y%m%d%H%M')}"
            
            if unique_key not in data["notified_classes"]:
                msg = (
                    f"🔔 **PENGINGAT KEGIATAN (30 MENIT LAGI)**\n\n"
                    f"📖 Kegiatan: **{title}**\n"
                    f"⏰ Waktu: {dt.strftime('%H:%M')}\n\n"
                    f"Ayo bersiap-siap!"
                )
                await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=msg)
                
                data["notified_classes"].append(unique_key)
                if len(data["notified_classes"]) > 50:
                    data["notified_classes"] = data["notified_classes"][-30:]
                save_data(data)

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
    app.add_handler(CommandHandler("besok", besok))
    app.add_handler(CommandHandler("minggu", minggu))
    app.add_handler(CommandHandler("tugas", tugas))
    
    job_queue = app.job_queue
    job_queue.run_daily(job_daily_schedule, time=time(hour=7, minute=0))
    job_queue.run_repeating(job_check_class_reminder, interval=300, first=15)
    job_queue.run_repeating(job_check_deadlines, interval=300, first=10)

    print("Academic Bot sedang berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
