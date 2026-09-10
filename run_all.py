import subprocess
import sys
import time
import os

# Daftar file bot kamu yang mau dijalankan barengan
bot_files = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    "bot_nexus.py"
]

if __name__ == "__main__":
    processes = []
    
    for bot in bot_files:
        if os.path.exists(bot):
            print(f"Memulai {bot}...")
            # Menjalankan setiap file bot sebagai proses terpisah
            p = subprocess.Popen([sys.executable, bot])
            processes.append(p)
            time.sleep(1.5) # Jeda sedikit agar tidak bentrok saat inisialisasi
        else:
            print(f"File {bot} tidak ditemukan, dilewati.")

    try:
        # Menjaga proses utama tetap hidup agar semua bot terus berjalan
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("Mematikan semua bot...")
        for p in processes:
            p.terminate()
