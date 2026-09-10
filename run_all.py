import os
import sys
import time
import threading

def start_bot(filename):
    print(f"Menjalankan {filename}...")
    # Menggunakan exec untuk menjalankan file bot di dalam thread terpisah
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Membuat namespace lokal/global sendiri untuk tiap bot agar variabelnya tidak bentrok
    namespace = {'__name__': '__main__', '__file__': filename}
    try:
        exec(code, namespace)
    except Exception as e:
        print(f"Error pada {filename}: {e}")

if __name__ == "__main__":
    bot_files = [
        "bot_academic.py",
        "bot_archive.py",
        "bot_command.py",
        "bot_nexus.py"
    ]

    threads = []
    for bot in bot_files:
        if os.path.exists(bot):
            t = threading.Thread(target=start_bot, args=(bot,))
            t.daemon = True
            t.start()
            threads.append(t)
            time.sleep(2) # Jeda 2 detik antar bot
        else:
            print(f"File {bot} tidak ditemukan.")

    # Menjaga proses utama tetap hidup
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Mematikan semua bot...")
