import subprocess
import os
import sys

# Daftar file bot yang akan dijalankan secara bersamaan
bots = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    # Kalau bot_nexus.py mau dinyalakan juga, uncomment baris di bawah ini:
    # "bot_nexus.py"
]

processes = []

try:
    # Jalankan setiap bot sebagai proses terpisah
    for bot in bots:
        print(f"Menjalankan {bot}...")
        p = subprocess.Popen([sys.executable, bot])
        processes.append(p)

    # Biar proses utamanya tetap hidup memantau anak-anak buahnya
    for p in processes:
        p.wait()

except KeyboardInterrupt:
    print("\nMematikan seluruh ekosistem Izumi...")
    for p in processes:
        p.terminate()
    sys.exit(0)
