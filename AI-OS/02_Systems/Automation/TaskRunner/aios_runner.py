import os
import glob
import time
import sys
from dotenv import load_dotenv

# Disable telemetry and interactive terminal hooks before importing interpreter
os.environ["INTERPRETER_ANONYMOUS_TELEMETRY"] = "false"
os.environ["ANONYMOUS_TELEMETRY"] = "false"

from interpreter import interpreter

# Upstream bug workaround: interpreter/core/respond.py calls
# display_markdown_message(...) in its RateLimitError handling branch without
# ever importing it, so a rate-limited primary-model call raises a NameError
# instead of the RateLimitError it should. Inject the missing name into that
# module's namespace so the call resolves and the real error surfaces.
import interpreter.core.respond as _respond_module
from interpreter.terminal_interface.utils.display_markdown_message import (
    display_markdown_message as _display_markdown_message,
)

_respond_module.display_markdown_message = _display_markdown_message

# 1. Load Environment Variables
load_dotenv("/home/nost/AI-OS/.env")

AIOS_DIR = os.environ.get("AIOS_WORKSPACE", "/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner")
INBOX = os.path.join(AIOS_DIR, "tasks", "inbox")
COMPLETED = os.path.join(AIOS_DIR, "tasks", "completed")
LOGS = os.path.join(AIOS_DIR, "tasks", "logs")

for folder in [INBOX, COMPLETED, LOGS]:
    os.makedirs(folder, exist_ok=True)

# 2. Model Configuration
# NOTE: this version of open-interpreter (0.4.3) has no built-in model_list/
# fallbacks/router support on interpreter.llm - those fields are dead attributes
# that the library never reads. Fallback is implemented explicitly in the
# polling loop below instead.
# llama-3.3-70b-versatile and gemini-2.5-flash have both been retired by
# their providers; these are the current equivalents as of 2026-08-26.
PRIMARY_MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "gemini/gemini-3.6-flash"

# 3. Open Interpreter Headless Setup
interpreter.auto_run = True
interpreter.safe_mode = "off"
interpreter.offline = False
interpreter.verbose = False
# anonymous_telemetry is a read-only computed property in this version
# (derived from disable_telemetry/offline); assigning to it directly raises
# AttributeError and crash-loops the service.
interpreter.disable_telemetry = True
interpreter.llm.model = PRIMARY_MODEL

interpreter.system_message = """
You are the headless execution worker of AI-OS on Ubuntu Server.
Run all necessary shell and file commands non-interactively without user prompts.
Return concise, structured Markdown summaries of the results.
Commands that can produce a lot of output (recursive find/grep, listing many
files, printing whole directory trees) are truncated after a few thousand
characters - bound the output yourself instead (head, wc -l, a narrower path
or -maxdepth, grep -c, etc.) rather than dumping everything and re-reading
a truncation notice.
"""

def format_interpreter_output(messages):
    if isinstance(messages, str):
        return messages
    if not isinstance(messages, list):
        return str(messages)

    formatted = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        msg_type = msg.get("type", "")
        msg_format = msg.get("format", "")

        if role == "assistant" and msg_type == "message" and content:
            formatted.append(content)
        elif role == "assistant" and msg_type == "code" and content:
            lang = msg_format if msg_format and msg_format != "execution" else ""
            formatted.append(f"```{lang}\n{content}\n```")
        elif role == "computer" and content:
            formatted.append(f"Output:\n```\n{content.strip()}\n```")
            
    return "\n\n".join(formatted) if formatted else "Task completed."

def _attempt(model, instruction):
    """Run one chat turn on `model`. Raises on failure (including the
    swallowed-RateLimitError case where open-interpreter returns an empty
    message list instead of raising - see respond.py's display_markdown_message
    branch)."""
    interpreter.messages = []
    interpreter.llm.model = model
    raw_output = interpreter.chat(instruction, display=False, stream=False)
    if not raw_output:
        raise RuntimeError(f"{model} produced no output (likely rate-limited)")
    return format_interpreter_output(raw_output)

def run_worker():
    print("[AI-OS Worker] Active. Polling tasks/inbox/ ...")
    while True:
        task_files = sorted(glob.glob(os.path.join(INBOX, "*.md")))
        for task_path in task_files:
            filename = os.path.basename(task_path)
            with open(task_path, "r", encoding="utf-8") as f:
                instruction = f.read().strip()

            if not instruction:
                os.remove(task_path)
                continue

            print(f"[*] Processing task: {filename}")
            try:
                output = _attempt(PRIMARY_MODEL, instruction)
            except Exception as primary_error:
                # Groq's per-minute token bucket is small enough that
                # open-interpreter's system prompt alone can trip it; that
                # clears in well under a minute, so retry once locally before
                # burning the fallback model's much scarcer daily quota.
                print(f"[!] {PRIMARY_MODEL} failed ({primary_error}); retrying once in 20s")
                time.sleep(20)
                try:
                    output = _attempt(PRIMARY_MODEL, instruction)
                except Exception as retry_error:
                    print(f"[!] {PRIMARY_MODEL} retry failed ({retry_error}); falling back to {FALLBACK_MODEL}")
                    try:
                        output = _attempt(FALLBACK_MODEL, instruction)
                    except Exception as fallback_error:
                        output = (
                            f"ERROR during execution.\n"
                            f"Primary ({PRIMARY_MODEL}): {type(retry_error).__name__}: {retry_error}\n"
                            f"Fallback ({FALLBACK_MODEL}): {type(fallback_error).__name__}: {fallback_error}"
                        )

            log_path = os.path.join(LOGS, f"{filename}.log")
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write(output)

            os.rename(task_path, os.path.join(COMPLETED, filename))
            print(f"[✓] Done: {filename}")

        time.sleep(2)

if __name__ == "__main__":
    run_worker()
