import subprocess
import sys
import time

# Daftar script bot yang akan dijalankan bersamaan
BOT_SCRIPTS = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    "bot_nexus.py"
]

def run_bots():
    processes = []
    
    print("🚀 Memulai ekosistem Izumi Bots...")
    
    # Jalankan setiap script bot di proses terpisah
    for script in BOT_SCRIPTS:
        try:
            print(f"▶️ Menjalankan {script}...")
            p = subprocess.Popen([sys.executable, script])
            processes.append(p)
        except Exception as e:
            print(f"❌ Gagal menjalankan {script}: {e}")

    print("✅ Semua bot telah diproses dan berjalan di background!")

    # Jaga agar script utama tidak mati
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n⏹️ Mematikan semua bot...")
        for p in processes:
            p.terminate()

if __name__ == '__main__':
    run_bots()
