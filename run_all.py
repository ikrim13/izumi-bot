import subprocess
import sys
import time

# Daftar file bot yang mau dijalankan secara bersamaan
bot_scripts = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    "bot_nexus.py"
]

def run_bot(script_name):
    """Menjalankan satu script bot dan otomatis me-restart jika crash."""
    while True:
        print(f"[RUNNER] Menjalankan {script_name}...")
        process = subprocess.Popen([sys.executable, script_name])
        process.wait()
        print(f"[RUNNER] {script_name} berhenti. Me-restart dalam 5 detik...")
        time.sleep(5)

if __name__ == "__main__":
    processes = []
    
    # Jalankan setiap bot di proses terpisah
    for script in bot_scripts:
        p = subprocess.Popen([sys.executable, script])
        processes.append(p)
        print(f"[RUNNER] Berhasil mentrigger {script} (PID: {p.pid})")
        time.sleep(2) # Jeda dikit biar gak nabrak pas inisialisasi awal

    try:
        # Biar proses utamanya tetep hidup mantau
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[RUNNER] Menghentikan semua bot...")
        for p in processes:
            p.terminate()
        sys.exit(0)
