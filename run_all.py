import subprocess
import sys
import os
import threading
import time

# Daftar bot dan token env yang harus dicek
bots_config = [
    ("bot_academic.py", "IZUMI_ACADEMIC_TOKEN"),
    ("bot_archive.py", "IZUMI_ARCHIVE_TOKEN"),
    ("bot_command.py", "CEO_TOKEN"), # Ganti env token command/nexus kalau namanya beda
    ("bot_nexus.py", "IZUMI_NEXUS_TOKEN")
]

def run_bot(filename, token_env):
    token = os.getenv(token_env)
    if not token:
        print(f"[WARNING] {filename} dilewati karena token ({token_env}) tidak ditemukan di Environment Variables Railway!")
        return

    print(f"[STARTING] Menjalankan {filename} menggunakan token {token_env}...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    process = subprocess.Popen([sys.executable, filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
    
    # Meneruskan log dari bot ke console Railway
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f"[{filename}] {output.strip()}")

if __name__ == "__main__":
    print("=== Multi-Bot Runner Dimulai ===")
    threads = []
    
    for filename, token_env in bots_config:
        if os.path.exists(filename):
            t = threading.Thread(target=run_bot, args=(filename, token_env))
            t.daemon = True
            t.start()
            threads.append(t)
            time.sleep(1)
        else:
            print(f"[ERROR] File {filename} tidak ditemukan di repository!")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Mematikan semua bot...")
