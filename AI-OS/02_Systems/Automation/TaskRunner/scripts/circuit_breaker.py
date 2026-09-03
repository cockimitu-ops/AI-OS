#!/usr/bin/env python3
"""Heuristic Loop-Detection und Auto-Recovery (Circuit Breaker).

Watches the shared events.jsonl journal and systemd logs for endless loops
(like repeated identical messages or crash loops) and automatically restarts
the affected worker/webapp services to break the lock.
"""
import os
import json
import time
import subprocess
from collections import deque

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
JOURNAL_PATH = os.path.join(TASK_RUNNER_DIR, "journal", "events.jsonl")

# Configuration
LOOP_THRESHOLD = 5         # How many identical messages trigger a restart
TIME_WINDOW_SEC = 300      # Window in seconds for the threshold
POLL_INTERVAL = 5          # How often to check events.jsonl

def _restart_services():
    print("[CircuitBreaker] Loop detected! Restarting worker and webapp...")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "aios-worker.service", "aios-webapp.service"], check=True)
        print("[CircuitBreaker] Services restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[CircuitBreaker] Failed to restart services: {e}")
        # Try without sudo if running as user
        try:
            subprocess.run(["systemctl", "--user", "restart", "aios-worker.service", "aios-webapp.service"], check=True)
            print("[CircuitBreaker] User services restarted successfully.")
        except subprocess.CalledProcessError:
            pass
            
    # Also clear out the inbox to prevent immediate re-trigger if poisoned tasks exist
    inbox_dir = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
    quarantine_dir = os.path.join(TASK_RUNNER_DIR, "tasks", "quarantine")
    os.makedirs(quarantine_dir, exist_ok=True)
    try:
        for f in os.listdir(inbox_dir):
            if f.endswith(".md"):
                src = os.path.join(inbox_dir, f)
                dst = os.path.join(quarantine_dir, f)
                os.rename(src, dst)
                print(f"[CircuitBreaker] Quarantined stuck task: {f}")
    except OSError as e:
        print(f"[CircuitBreaker] Error during quarantine: {e}")

def watch_events():
    """Polls events.jsonl for repeating identical messages."""
    print("[CircuitBreaker] Watching events.jsonl for loops...")
    last_size = 0
    recent_events = deque()
    
    while True:
        time.sleep(POLL_INTERVAL)
        
        if not os.path.exists(JOURNAL_PATH):
            continue
            
        try:
            current_size = os.path.getsize(JOURNAL_PATH)
            if current_size < last_size:
                # File was rotated/truncated
                last_size = 0
                
            if current_size == last_size:
                continue
                
            with open(JOURNAL_PATH, 'r', encoding='utf-8') as f:
                f.seek(last_size)
                new_lines = f.readlines()
                last_size = f.tell()
                
            now = time.time()
            for line in new_lines:
                try:
                    event = json.loads(line)
                    # Use current time instead of event timestamp for simplicity
                    recent_events.append((now, event))
                except json.JSONDecodeError:
                    continue
                    
            # Clean up old events outside the time window
            while recent_events and now - recent_events[0][0] > TIME_WINDOW_SEC:
                recent_events.popleft()
                
            # Check for loops (same engine + same text)
            counts = {}
            for _, ev in recent_events:
                text = ev.get("text", "").strip()
                engine = ev.get("engine", "")
                if not text:
                    continue
                key = (engine, text)
                counts[key] = counts.get(key, 0) + 1
                
                if counts[key] >= LOOP_THRESHOLD:
                    print(f"[CircuitBreaker] Threshold exceeded for '{text}' (engine: {engine})")
                    _restart_services()
                    
                    # Notify Felix about the intervention
                    try:
                        import safety_controls
                        safety_controls.escalate_error(
                            "Circuit Breaker", 
                            f"Endlosschleife detektiert ({counts[key]}x '{text[:30]}...'). Worker und Webapp wurden neu gestartet und Inbox geleert."
                        )
                    except Exception as e:
                        print(f"Failed to escalate: {e}")
                        
                    # Clear history to avoid multiple restarts for the same loop
                    recent_events.clear()
                    break
                    
        except Exception as e:
            print(f"[CircuitBreaker] Error reading journal: {e}")

if __name__ == "__main__":
    watch_events()
