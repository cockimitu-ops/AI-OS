#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/home/nost/AI-OS/.env")

AIOS_DIR = os.environ.get("AIOS_WORKSPACE", "/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner")
INBOX = os.path.join(AIOS_DIR, "tasks", "inbox")
COMPLETED = os.path.join(AIOS_DIR, "tasks", "completed")
LOGS = os.path.join(AIOS_DIR, "tasks", "logs")

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python3 dispatch_task.py \"<Deine Anweisung>\" [--no-wait]")
        sys.exit(1)

    no_wait = "--no-wait" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--no-wait"]
    prompt = " ".join(args).strip()

    if not prompt:
        print("Fehler: Kein Task-Text angegeben.")
        sys.exit(1)

    for d in [INBOX, COMPLETED, LOGS]:
        os.makedirs(d, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_filename = f"task_{timestamp}.md"
    task_path = os.path.join(INBOX, task_filename)
    log_path = os.path.join(LOGS, f"{task_filename}.log")

    with open(task_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"[*] Task eingereiht: {task_filename}")

    if no_wait:
        print("[+] Task läuft asynchron im Hintergrund.")
        sys.exit(0)

    print("[*] Warte auf Worker-Ausführung...", end="", flush=True)
    timeout = 180
    start_time = time.time()

    while time.time() - start_time < timeout:
        if os.path.exists(log_path):
            print("\n\n" + "=" * 20 + " ERGEBNIS " + "=" * 20)
            with open(log_path, "r", encoding="utf-8") as lf:
                print(lf.read().strip())
            print("=" * 50)
            sys.exit(0)
        time.sleep(1)
        print(".", end="", flush=True)

    print("\n[!] Timeout: Task wurde nicht rechtzeitig fertiggestellt.")
    sys.exit(1)

if __name__ == "__main__":
    main()
