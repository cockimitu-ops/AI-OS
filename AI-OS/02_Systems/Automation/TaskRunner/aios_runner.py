import os
import glob
import subprocess
import time
import sys
from dotenv import load_dotenv

# This file is launched by absolute path from systemd with WorkingDirectory set
# to the repo root, so its own folder is not on sys.path by default.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents
import memory

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

# Ordered chain of free models to try per task. Each entry is a dict rather
# than a tuple - api_base/api_key exist alongside model/delay so a future
# provider needing a custom endpoint (a self-hosted gateway, an OpenAI-
# compatible third party) can be added as data, not a code change. None means
# "use litellm's own native routing for this model," a real, intentional
# value here, not an unset one - a provider that DOES need a custom endpoint
# must not inherit None left behind by the entry before it, or vice versa.
#
# FreeLLMAPI (a self-hosted router in front of many free providers) sat as the
# primary tier here 2026-08-30, briefly. Removed the same day - reverted to
# direct providers only, no separate service to run or keep patched. Everything
# here is genuinely free - Groq and Gemini both meter quota per-model, not per
# account, so a second model on the same provider is a separate bucket, not
# just another name for the same limit. Added 2026-08-26 after both
# PRIMARY_MODEL and FALLBACK_MODEL failed live in the same test run - Felix has
# no budget for a paid API, so more free tiers beat a paid one.
MODEL_CHAIN = [
    {"model": PRIMARY_MODEL, "delay": 0, "api_base": None, "api_key": None},
    # Groq's per-minute token bucket is small enough that open-interpreter's
    # system prompt alone can trip it; that clears in well under a minute.
    {"model": PRIMARY_MODEL, "delay": 20, "api_base": None, "api_key": None},
    # Smaller sibling of PRIMARY_MODEL on the same Groq key - separate quota.
    {"model": "groq/openai/gpt-oss-20b", "delay": 0, "api_base": None, "api_key": None},
    {"model": FALLBACK_MODEL, "delay": 0, "api_base": None, "api_key": None},
    # Lite sibling of FALLBACK_MODEL on the same Gemini key - separate quota.
    # NOT "gemini-flash-lite-latest": that alias currently resolves to a newer
    # model that 400s inside Open Interpreter's tool-calling flow (missing
    # thought_signature on function-call parts - a real API constraint on
    # newer "thinking" Gemini models, not a config mistake). Verified
    # 2026-08-26 that gemini-3.5-flash-lite works cleanly through the same
    # tool-calling path the worker actually uses.
    {"model": "gemini/gemini-3.5-flash-lite", "delay": 0, "api_base": None, "api_key": None},
]

# Two more free providers, added 2026-08-30 as backup tiers - direct API
# integrations, not another service to run. Each is appended only if its key
# is actually present, so shipping this causes zero behaviour change until
# Felix adds the corresponding key to .env; litellm reads these env vars
# itself (CEREBRAS_API_KEY, OPENROUTER_API_KEY), no api_base override needed
# since both are litellm-native providers, same as Groq and Gemini above.
if os.environ.get("CEREBRAS_API_KEY"):
    # gpt-oss-120b - same model family already used via Groq (PRIMARY_MODEL),
    # just a separate vendor's quota. Genuinely generous free tier as of
    # 2026-08-30 (verified against Cerebras' own docs, not an aggregator site:
    # 1M tokens/day, 14,400 requests/day per model, no expiration, 65k context
    # on the free tier specifically - not the smaller cap some third-party
    # summaries claimed). Placed early in the chain to match that headroom.
    MODEL_CHAIN.insert(2, {
        "model": "cerebras/gpt-oss-120b", "delay": 0,
        "api_base": None, "api_key": None,
    })

if os.environ.get("OPENROUTER_API_KEY"):
    # OpenRouter's free (":free" suffix) models are known to rotate without
    # warning - confirmed live via https://openrouter.ai/api/v1/models on
    # 2026-08-30, not assumed from a blog post (an initial pick,
    # meta-llama/llama-3.3-70b-instruct:free, was already gone from that list
    # by the time this was checked - exactly the failure mode being guarded
    # against). If this model 404s later, re-check that endpoint for a
    # current replacement rather than guessing a new name.
    # Last in the chain deliberately: the free tier caps at 50 requests/day
    # on an unfunded account, the tightest quota of anything here - genuinely
    # last-resort, not a peer to Groq/Gemini/Cerebras.
    MODEL_CHAIN.append({
        "model": "openrouter/nvidia/nemotron-3-super-120b-a12b:free", "delay": 0,
        "api_base": None, "api_key": None,
    })

# Last-resort escalation via Claude Code headless (`claude -p`), billed against
# Felix's Pro subscription's 5h/weekly quota rather than a metered API. DISABLED
# as of 2026-08-26 pending a real answer on whether routing an unattended,
# Telegram-triggerable backend service through Pro-subscription auth is
# consistent with Claude Code's usage terms - a prior session's handoff
# (~/HANDOFF-1.md) flagged the same pattern in AI-Bridge's askClaude() as
# "likely a real ToS problem... parked until rebuilt with an actual API key."
# `-p` mode is Anthropic's own documented CI/scripting feature, so this isn't
# a clear-cut violation either way - genuinely unresolved, not dismissed.
# Do not flip this back to True without Felix explicitly deciding to accept
# that risk, or switching this to a real ANTHROPIC_API_KEY instead.
CLAUDE_ESCALATION_ENABLED = False
CLAUDE_MODEL = "sonnet"
CLAUDE_TIMEOUT_S = 170  # stay under dispatch_task.py/telegram_bridge.py's 180s wait

# 3. System prompt - loaded from the vault (System_Prompt.md), not hardcoded
# here, so it's visible/editable/versioned like the rest of AI-OS instead of
# buried in this file. See that file's own header for why it isn't a
# 04_Agents/ entry.
SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "System_Prompt.md")

def _load_system_prompt():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    start_marker = "<!-- WORKER_PROMPT_START -->"
    end_marker = "<!-- WORKER_PROMPT_END -->"
    try:
        start = content.index(start_marker) + len(start_marker)
        end = content.index(end_marker)
    except ValueError:
        raise RuntimeError(f"{SYSTEM_PROMPT_PATH} is missing {start_marker}/{end_marker} markers")
    return content[start:end].strip()

# 4. Open Interpreter Headless Setup
interpreter.auto_run = True
interpreter.safe_mode = "off"
interpreter.offline = False
interpreter.verbose = False
# anonymous_telemetry is a read-only computed property in this version
# (derived from disable_telemetry/offline); assigning to it directly raises
# AttributeError and crash-loops the service.
interpreter.disable_telemetry = True
interpreter.llm.model = PRIMARY_MODEL
BASE_SYSTEM_PROMPT = _load_system_prompt()
interpreter.system_message = BASE_SYSTEM_PROMPT


def _system_prompt_for(agent_name):
    """Base prompt, plus the selected agent's block appended.

    Appended rather than substituted: the base prompt carries what is true
    regardless of role - the vault map, the destructive-action guardrail, the
    code-language constraint - and selecting an agent should narrow the
    worker's focus, never strip its safety rules."""
    if not agent_name:
        return BASE_SYSTEM_PROMPT
    block = agents.load_prompt(agent_name)
    if not block:
        return BASE_SYSTEM_PROMPT
    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"## Your role for this task: {agent_name.replace('_', ' ')}\n"
        f"{block}"
    )

def format_interpreter_output(messages):
    """Return what the worker actually *said*, not a transcript of how it got
    there.

    This used to concatenate every assistant message, every code block, AND
    every raw command output into the log - so Telegram showed the model's
    scratch work (a `find` invocation, then a truncated wall of paths) instead
    of an answer. That is a formatter problem, not a prompting problem: the raw
    output got appended no matter how well the model wrote its summary.

    So: prefer the assistant's prose. Fall back to the full transcript only
    when there is no prose at all, because in that case the commands and their
    output are the only diagnostic information left and dropping them would
    turn a debuggable failure into a silent one."""
    if isinstance(messages, str):
        return messages
    if not isinstance(messages, list):
        return str(messages)

    prose = []
    transcript = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        msg_type = msg.get("type", "")
        msg_format = msg.get("format", "")

        if role == "assistant" and msg_type == "message" and content:
            prose.append(str(content).strip())
            transcript.append(str(content).strip())
        elif role == "assistant" and msg_type == "code" and content:
            lang = msg_format if msg_format and msg_format != "execution" else ""
            transcript.append(f"```{lang}\n{content}\n```")
        elif role == "computer" and content:
            transcript.append(f"Output:\n```\n{str(content).strip()}\n```")

    if prose:
        return "\n\n".join(prose)
    if transcript:
        # No prose: the model ran commands and never explained itself. Ship the
        # transcript so the failure is at least inspectable.
        return "\n\n".join(transcript)
    return "Task completed."

def _attempt(model, instruction, system_prompt=None, history=None,
             api_base=None, api_key=None):
    """Run one chat turn on `model`. Raises on failure (including the
    swallowed-RateLimitError case where open-interpreter returns an empty
    message list instead of raising - see respond.py's display_markdown_message
    branch).

    api_base/api_key are always set explicitly, never left as "whatever the
    previous attempt left behind" - a freellmapi entry's custom endpoint must
    not leak into the next entry's direct-provider call, and a direct-provider
    entry must not inherit a stale endpoint from a prior freellmapi attempt
    either. None means "use litellm's native routing for this model," which is
    a real, intentional value here, not an unset one."""
    # Seed with prior conversation turns, or [] for a cold task. Assigning a
    # fresh list every attempt matters: a failed model leaves its partial
    # messages behind, and the next model in MODEL_CHAIN must not inherit them.
    interpreter.messages = list(history) if history else []
    interpreter.llm.model = model
    interpreter.llm.api_base = api_base
    interpreter.llm.api_key = api_key
    if system_prompt is not None:
        interpreter.system_message = system_prompt
    raw_output = interpreter.chat(instruction, display=False, stream=False)
    if not raw_output:
        raise RuntimeError(f"{model} produced no output (likely rate-limited)")
    return format_interpreter_output(raw_output)

def _attempt_claude(instruction):
    """Last-resort escalation - see CLAUDE_MODEL comment above. Mirrors
    AI-Bridge's askClaude() directly instead of shelling out through
    bridge.mjs, so this runs with the worker's own cwd (AIOS repo root)
    rather than the AI-Bridge folder."""
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", CLAUDE_MODEL],
            input=instruction,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "claude CLI not found on PATH - install with: npm install -g @anthropic-ai/claude-code"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude -p timed out after {CLAUDE_TIMEOUT_S}s")

    if result.returncode != 0:
        # claude -p prints "Not logged in" to stdout, everything else to stderr
        detail = (result.stderr.strip() or result.stdout.strip())[:500]
        hint = " (run: claude setup-token)" if "logged in" in detail.lower() else ""
        raise RuntimeError(f"claude -p exited {result.returncode}: {detail}{hint}")

    output = result.stdout.strip()
    if not output:
        raise RuntimeError("claude -p produced no output")
    return output

def _write_log(filename, output):
    """Write the result log atomically. dispatch_task.py and telegram_bridge.py
    poll for this file's *existence*, so a plain open("w") would let them read a
    zero-byte or half-written log the instant it's created. Write to a temp name
    the pollers don't look at, then rename - rename is atomic on the same
    filesystem, so the log only ever appears complete."""
    log_path = os.path.join(LOGS, f"{filename}.log")
    tmp_path = f"{log_path}.partial"
    with open(tmp_path, "w", encoding="utf-8") as lf:
        lf.write(output)
    os.replace(tmp_path, log_path)


def _run_task(task_path, filename):
    with open(task_path, "r", encoding="utf-8") as f:
        raw = f.read()

    thread_id, raw = memory.parse_directive(raw)
    agent_name, instruction = agents.parse_directive(raw)

    # A bare follow-up stays in whatever role the conversation was already in.
    if not agent_name and thread_id:
        agent_name = agents.resolve(memory.last_agent(thread_id) or "")

    system_prompt = _system_prompt_for(agent_name)
    history = memory.as_messages(thread_id) if thread_id else None

    if not instruction:
        # Still write a log: a caller waiting on this file would otherwise
        # block for its full 180s timeout on what is an instant, known failure.
        _write_log(filename, "ERROR: task file was empty - nothing to execute.")
        os.rename(task_path, os.path.join(COMPLETED, filename))
        return

    bits = []
    if agent_name:
        bits.append(f"agent: {agent_name}")
    if history:
        bits.append(f"memory: {len(history) // 2} turn(s)")
    label = f" ({', '.join(bits)})" if bits else ""
    print(f"[*] Processing task: {filename}{label}", flush=True)
    output = None
    errors = []
    for entry in MODEL_CHAIN:
        model = entry["model"]
        if entry["delay"]:
            time.sleep(entry["delay"])
        try:
            output = _attempt(model, instruction, system_prompt, history,
                              api_base=entry["api_base"], api_key=entry["api_key"])
            break
        except Exception as e:
            print(f"[!] {model} failed ({e})")
            errors.append(f"{model}: {type(e).__name__}: {e}")

    if output is None and CLAUDE_ESCALATION_ENABLED:
        print("[!] All free models failed; escalating to Claude (Pro quota - last resort)")
        try:
            output = _attempt_claude(instruction)
        except Exception as e:
            errors.append(f"claude -p {CLAUDE_MODEL}: {type(e).__name__}: {e}")

    if output is None:
        error_lines = "\n".join(f"- {line}" for line in errors)
        note = (
            ""
            if CLAUDE_ESCALATION_ENABLED
            else "\n(Escalation: disabled pending ToS review - see CLAUDE_ESCALATION_ENABLED comment)"
        )
        output = f"ERROR during execution. All models failed:\n{error_lines}{note}"

    # Only successful turns enter memory. Replaying "all models failed" as
    # context teaches the model nothing and spends budget a real turn needs.
    if thread_id and not output.startswith("ERROR"):
        memory.save_turn(thread_id, instruction, output, agent_name)

    _write_log(filename, output)
    os.rename(task_path, os.path.join(COMPLETED, filename))
    print(f"[✓] Done: {filename}")


def run_worker():
    print("[AI-OS Worker] Active. Polling tasks/inbox/ ...")
    while True:
        task_files = sorted(glob.glob(os.path.join(INBOX, "*.md")))
        for task_path in task_files:
            filename = os.path.basename(task_path)
            try:
                _run_task(task_path, filename)
            except Exception as e:
                # Anything the per-model handling above didn't already catch
                # (unreadable task file, full disk, a rename failure, a library
                # blowing up outside _attempt). Without this the exception
                # escapes run_worker, systemd's Restart=always brings the worker
                # straight back, it re-globs the SAME still-in-inbox task, and
                # the service crash-loops on one poisoned file forever.
                print(f"[!] Task {filename} failed hard: {type(e).__name__}: {e}")
                try:
                    _write_log(filename, f"ERROR: worker failed on this task.\n{type(e).__name__}: {e}")
                    os.rename(task_path, os.path.join(COMPLETED, filename))
                except Exception as move_err:
                    # Can't even quarantine it - drop out of the loop for this
                    # pass rather than spinning on it at full speed.
                    print(f"[!] Could not quarantine {filename}: {move_err}")
                    time.sleep(10)
                    break

        time.sleep(2)

if __name__ == "__main__":
    run_worker()
