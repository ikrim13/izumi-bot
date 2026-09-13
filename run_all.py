import subprocess
import sys
import time

# Daftar script bot yang akan dijalankan secara paralel di Railway
bot_scripts = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    "bot_nexus.py"
]

processes = []

def start_bots():
    for script in bot_scripts:
        print(f"Menjalankan {script}...")
        # Jalankan setiap script menggunakan python interpreter
        p = subprocess.Popen([sys.executable, script])
        processes.append(p)
        # Beri jeda sedikit agar port flask / polling tidak bentrok bersamaan
        time.sleep(2)

if __name__ == "__main__":
    try:
        start_bots()
        # Terus pantau proses agar worker railway tetap hidup
        while True:
            time.sleep(10)
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"Perhatian: {bot_scripts[i]} mati, merestart...")
                    processes[i] = subprocess.Popen([sys.executable, bot_scripts[i]])
    except KeyboardInterrupt:
        print("Menghentikan semua bot...")
        for p in processes:
            p.terminate()
