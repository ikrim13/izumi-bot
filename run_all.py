import subprocess
import sys
import os
import threading
import time

bot_files = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    "bot_nexus.py"
]

def run_bot(filename):
    print(f"-> Memulai thread untuk {filename}")
    # Menggunakan subprocess dengan unbuffered output agar log-nya keluar
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    subprocess.run([sys.executable, filename], env=env)

if __name__ == "__main__":
    threads = []
    
    for bot in bot_files:
        if os.path.exists(bot):
            t = threading.Thread(target=run_bot, args=(bot,))
            t.daemon = True
            t.start()
            threads.append(t)
            time.sleep(1) # Jeda sedikit tiap bot
        else:
            print(f"File {bot} tidak ditemukan.")

    print("Semua bot thread telah diinisialisasi secara paralel!")
    
    # Menjaga proses utama tetap hidup
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Mematikan semua bot...")
