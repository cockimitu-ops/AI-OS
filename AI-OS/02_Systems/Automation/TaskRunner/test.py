import os, glob
def find_codex_session():
    sessions = glob.glob(os.path.expanduser("~/.codex/sessions/**/*.jsonl"), recursive=True)
    if not sessions: return None
    newest = max(sessions, key=os.path.getmtime)
    print("Newest:", newest)
    import json
    with open(newest) as f:
        for line in f:
            try:
                ev = json.loads(line)
                if ev.get("type") == "session_meta" and ev.get("payload", {}).get("session_id"):
                    print("Found:", ev["payload"]["session_id"])
                    return ev["payload"]["session_id"]
            except Exception:
                pass
find_codex_session()
