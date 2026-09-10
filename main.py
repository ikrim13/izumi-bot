import subprocess
import sys
import time

bots = [
    "bot_academic.py",
    "bot_archive.py",
    "bot_command.py",
    "bot_nexus.py"
]

if __name__ == "__main__":
    processes = []
    for bot in bots:
        print(f"Menjalankan {bot}...")
        p = subprocess.Popen([sys.executable, bot])
        processes.append(p)
        time.sleep(1)  # Jeda 1 detik antar bot biar gak bentrok

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("Mematikan semua bot...")
        for p in processes:
            p.terminate()
