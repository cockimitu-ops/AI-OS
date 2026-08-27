#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents

load_dotenv("/home/nost/AI-OS/.env")

AIOS_DIR = os.environ.get("AIOS_WORKSPACE", "/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner")
INBOX = os.path.join(AIOS_DIR, "tasks", "inbox")
COMPLETED = os.path.join(AIOS_DIR, "tasks", "completed")
LOGS = os.path.join(AIOS_DIR, "tasks", "logs")

def main():
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("Verwendung: python3 dispatch_task.py \"<Deine Anweisung>\" [--no-wait] [--agent NAME]")
        print("\nVerfuegbare Agents (--agent, Alias oder voller Name):\n")
        print(agents.describe())
        sys.exit(0 if ("--help" in sys.argv or "-h" in sys.argv) else 1)

    argv = sys.argv[1:]
    no_wait = "--no-wait" in argv

    agent = None
    if "--agent" in argv:
        i = argv.index("--agent")
        if i + 1 >= len(argv):
            print("Fehler: --agent braucht einen Namen. Verfuegbar:\n")
            print(agents.describe())
            sys.exit(1)
        requested = argv[i + 1]
        agent = agents.resolve(requested)
        if not agent:
            # Hard error here, unlike the worker's silent fallback: an explicit
            # --agent is a stated intent, and running the task on the wrong
            # prompt is worse than making the user retype the name.
            print(f"Fehler: unbekannter Agent '{requested}'. Verfuegbar:\n")
            print(agents.describe())
            sys.exit(1)
        argv = argv[:i] + argv[i + 2:]

    args = [a for a in argv if a != "--no-wait"]
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

    # Atomar einreihen: der Worker globt tasks/inbox/*.md im Sekundentakt und
    # koennte sonst eine halb geschriebene Datei aufschnappen und eine
    # abgeschnittene Anweisung ausfuehren. .part wird vom Glob nicht erfasst.
    body = (agents.directive(agent) if agent else "") + prompt
    tmp_path = f"{task_path}.part"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp_path, task_path)

    suffix = f" (Agent: {agent})" if agent else ""
    print(f"[*] Task eingereiht: {task_filename}{suffix}")

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
