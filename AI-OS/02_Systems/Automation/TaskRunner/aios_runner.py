import os
import contextlib
import glob
import re
import signal
import subprocess
import threading
import time
import sys
from dotenv import load_dotenv

# This file is launched by absolute path from systemd with WorkingDirectory set
# to the repo root, so its own folder is not on sys.path by default.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents
import memory
import proposals
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import spend_guard
import voice_style

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

# Bound how long a single model call may block.
#
# litellm ships with request_timeout = 6000.0 - one hundred minutes. That is
# not a theoretical concern: on 2026-08-30 a single task sat in the worker
# from 14:32:31 to 16:14:01 (101 minutes) on one groq attempt, and because
# the queue is strictly serial, every task behind it waited too. `systemctl
# is-active` still reported the worker healthy the entire time, so nothing
# anywhere said a thing.
#
# Two independent ceilings, because they fail differently:
#   - LLM_REQUEST_TIMEOUT_S bounds each HTTP request (litellm's own knob).
#   - ATTEMPT_TIMEOUT_S bounds one model's *entire* tool-calling loop, which
#     is many HTTP requests, via SIGALRM - so a model that keeps making fast
#     calls forever is still capped and the chain moves on to the next entry.
import litellm

LLM_REQUEST_TIMEOUT_S = 120
ATTEMPT_TIMEOUT_S = 300
# Interactive chat gets a much shorter per-model budget than a scheduled job.
# Five minutes per attempt is right for a nightly task that has all night; on
# a chat message it means one exhausted provider stalls the answer for five
# minutes, and a chain of six can grind for half an hour. Observed live
# 2026-09-01: "how much battery does my phone have" sat unanswered for 12+
# minutes after Groq returned its quota error.
#
# The failure mode matters more than the number. A model that is rate-limited
# usually says so in seconds; one that is going to be slow is rarely worth
# waiting five minutes for when five other providers are queued behind it.
# Falling through fast to a working model beats waiting for a dead one.
CHAT_ATTEMPT_TIMEOUT_S = 75
litellm.request_timeout = LLM_REQUEST_TIMEOUT_S


class AttemptTimeout(Exception):
    """Raised when one MODEL_CHAIN entry exceeds ATTEMPT_TIMEOUT_S. Caught by
    the same handler as any other attempt failure, so a hung model is just a
    failed model and the chain continues."""


@contextlib.contextmanager
def _time_limit(seconds):
    """Hard wall-clock ceiling around a blocking call.

    SIGALRM only works on the main thread; the worker loop is the main thread,
    but the test suite and any future caller might not be. Degrading to "no
    extra ceiling" there is correct - LLM_REQUEST_TIMEOUT_S still applies, and
    silently doing nothing beats raising an unrelated ValueError."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _fire(signum, frame):
        raise AttemptTimeout(f"exceeded {seconds}s wall clock")

    previous = signal.signal(signal.SIGALRM, _fire)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)

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

def _chain_entry(model, delay=0, api_base=None, api_key=None,
                  context_window=None, max_tokens=None, paid=False):
    """One MODEL_CHAIN entry. A factory instead of 7+ hand-written dict
    literals - context_window/max_tokens were added after api_base/api_key
    without touching every existing entry, which is the point of building
    entries this way rather than inline. None on any field means "let litellm/
    Open Interpreter use its own default or auto-detection for this model,"
    a real intentional value, not an unset one - it must be explicitly
    re-asserted on every entry so nothing leaks from the attempt before it."""
    return {
        "model": model, "delay": delay,
        "api_base": api_base, "api_key": api_key,
        "context_window": context_window, "max_tokens": max_tokens,
        "paid": paid,
    }


# Ordered chain of free models to try per task.
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
    _chain_entry(PRIMARY_MODEL),
    # Groq's per-minute token bucket is small enough that open-interpreter's
    # system prompt alone can trip it; that clears in well under a minute.
    _chain_entry(PRIMARY_MODEL, delay=20),
    # Smaller sibling of PRIMARY_MODEL on the same Groq key - separate quota.
    _chain_entry("groq/openai/gpt-oss-20b"),
    _chain_entry(FALLBACK_MODEL),
    # Lite sibling of FALLBACK_MODEL on the same Gemini key - separate quota.
    # NOT "gemini-flash-lite-latest": that alias currently resolves to a newer
    # model that 400s inside Open Interpreter's tool-calling flow (missing
    # thought_signature on function-call parts - a real API constraint on
    # newer "thinking" Gemini models, not a config mistake). Verified
    # 2026-08-26 that gemini-3.5-flash-lite works cleanly through the same
    # tool-calling path the worker actually uses.
    _chain_entry("gemini/gemini-3.5-flash-lite"),
]

# Two more free providers, added 2026-08-30 as backup tiers - direct API
# integrations, not another service to run. Each is appended only if its key
# is actually present, so shipping this causes zero behaviour change until
# Felix adds the corresponding key to .env; litellm reads these env vars
# itself (CEREBRAS_API_KEY, OPENROUTER_API_KEY), no api_base override needed
# since both are litellm-native providers, same as Groq and Gemini above.
if os.environ.get("CEREBRAS_API_KEY"):
    # gpt-oss-120b - same model family already used via Groq (PRIMARY_MODEL),
    # just a separate vendor's quota. Genuinely generous free tier per
    # Cerebras' own docs (1M tokens/day, 14,400 requests/day per model, no
    # expiration, 65k context on the free tier) - blocked live as of
    # 2026-08-30 by a "Payment required" error on Felix's specific account,
    # unresolved, see README. Placed early in the chain to match the
    # documented headroom once that's sorted out.
    MODEL_CHAIN.insert(2, _chain_entry("cerebras/gpt-oss-120b"))

if os.environ.get("OPENROUTER_API_KEY"):
    # OpenRouter's free (":free" suffix) models are known to rotate without
    # warning - confirmed live via https://openrouter.ai/api/v1/models on
    # 2026-08-30, not assumed from a blog post (an initial pick,
    # meta-llama/llama-3.3-70b-instruct:free, was already gone from that list
    # by the time this was checked - exactly the failure mode being guarded
    # against). If this model 404s later, re-check that endpoint for a
    # current replacement rather than guessing a new name.
    #
    # context_window/max_tokens set explicitly: verified live 2026-08-30 that
    # without them, Open Interpreter can't auto-detect this model's window and
    # silently defaults to 8000 - a real cap against the model's actual 1M
    # (OpenRouter's own model page), not just a cosmetic warning. Numbers
    # taken from that page, not guessed.
    #
    # Last in the chain deliberately: the free tier caps at 50 requests/day
    # on an unfunded account, the tightest quota of anything here - genuinely
    # last-resort, not a peer to Groq/Gemini/Cerebras.
    MODEL_CHAIN.append(_chain_entry(
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        context_window=1_000_000, max_tokens=16_384,
    ))

# Optional paid tier via OpenRouter, appended after every free tier - "only
# fires when they're exhausted," per Felix's own framing when this was first
# proposed. Off by default: OPENROUTER_PAID_ENABLED must be explicitly "true"
# in .env, a separate decision from just having OPENROUTER_API_KEY present
# (that key already powers the free nemotron entry above and existed before
# any paid spend was on the table).
#
# The 2026-08-30 101-minute-stuck-call incident is why this has a budget cap
# at all: every model above this line is free, so a stuck loop cost time, not
# money. spend_guard.py enforces OPENROUTER_MONTHLY_BUDGET_USD and fails
# closed - once the month's spend hits the cap, this entry is skipped before
# the call, never billed past it.
OPENROUTER_PAID_MODEL = os.environ.get("OPENROUTER_PAID_MODEL", "openrouter/z-ai/glm-5.2")
OPENROUTER_MONTHLY_BUDGET_USD = float(os.environ.get(
    "OPENROUTER_MONTHLY_BUDGET_USD", spend_guard.DEFAULT_MONTHLY_BUDGET_USD))
# OpenRouter's own listed rate for OPENROUTER_PAID_MODEL, used only as a
# fallback if litellm's pricing database doesn't yet know this model (it is
# new) - see _cost_for_paid_call(). Verify current pricing at
# openrouter.ai/z-ai/glm-5.2 before trusting this figure for long; the free
# OpenRouter entry above already documented that OpenRouter's listings move
# without warning, and a priced model is no different.
OPENROUTER_PAID_INPUT_PER_M = float(os.environ.get("OPENROUTER_PAID_INPUT_PER_M", "0.4875"))
OPENROUTER_PAID_OUTPUT_PER_M = float(os.environ.get("OPENROUTER_PAID_OUTPUT_PER_M", "1.56"))

if os.environ.get("OPENROUTER_PAID_ENABLED", "").lower() == "true" and os.environ.get("OPENROUTER_API_KEY"):
    # context_window/max_tokens set explicitly, same reason as the free
    # nemotron entry above: verified live 2026-08-31 that without them, Open
    # Interpreter can't auto-detect this model's window and silently
    # defaults to 8000 against the real 1,048,576 (confirmed directly against
    # https://openrouter.ai/api/v1/models, not assumed from a listing page -
    # the free entry's own comment already warns OpenRouter's numbers move).
    # max_tokens is deliberately far below the model's real 262,144 ceiling:
    # this is a budget-capped paid model, and one runaway response must not
    # be able to burn a large fraction of a month's cap in a single call.
    MODEL_CHAIN.append(_chain_entry(
        OPENROUTER_PAID_MODEL, paid=True,
        context_window=1_048_576, max_tokens=32_768,
    ))

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
# Felix raised the budget to EUR20/month and asked for GLM to be prioritised
# generally rather than per agent. Measured cost is ~$0.006 per task at ~25
# tasks/day, so full coverage is roughly $6/month - three times inside the new
# budget. At that point per-agent tiering is complexity without a payoff, so
# the default inverts: paid model first for everything, free chain still
# behind it as the fallback.
#
# This is also the most direct answer to tonight's failure. Tech_Scout invented
# a GitHub repository out of a digest that contained one unrelated project, and
# the approval gate could not catch it because a plausible technical claim is
# not something a human can check from a Telegram message. A stronger model
# does not make that impossible - it makes it much less likely, which is worth
# more than any single deterministic check.
#
# Off means off: with OPENROUTER_PAID_ENABLED unset there is no paid entry in
# the chain at all and this flag changes nothing.
PAID_FIRST_DEFAULT = os.environ.get(
    "OPENROUTER_PAID_DEFAULT", "true").lower() == "true"


def chain_for(preference):
    """MODEL_CHAIN, ordered for this task. -> list of entries.

    Default order is every free tier first and the paid model only as a last
    resort, which is right for the ~25 tasks a day that are routine. It is
    wrong for the handful where the answer's quality decides the outcome: a
    study note carries a definition Felix will memorise from a flashcard, and
    the daily system plan has twice now asserted drift in files it had not
    actually read. For those, "paid" puts the paid model first.

    Reordering rather than replacing matters: if the paid attempt fails or
    the month's budget is spent, the free chain is still behind it and the
    task still gets done. The budget check in the loop below is what makes
    this safe to turn on - an exhausted budget silently degrades to free
    rather than failing the task.

    Cost, measured rather than guessed (2026-08-31): the system prompt is
    3,150-4,800 tokens and goes out on every call, Open Interpreter makes
    2-4 calls per task, so a paid task is roughly $0.005-0.01. Every task
    paid would be ~$6/month, exactly the cap with no headroom; a handful of
    quality tasks a day is ~$1.50."""
    # "free" is now the explicit opt-OUT rather than the default. Anything
    # that has not asked for free gets the paid model first.
    if preference == "free" or (preference is None and not PAID_FIRST_DEFAULT):
        return MODEL_CHAIN
    paid = [e for e in MODEL_CHAIN if e["paid"]]
    return paid + [e for e in MODEL_CHAIN if not e["paid"]] if paid else MODEL_CHAIN


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

# 3b. Paid-tier plumbing: cache injection + usage capture for
# OPENROUTER_PAID_MODEL specifically, never for any other entry in the chain.
#
# Open Interpreter's own Llm.run() builds a fixed params dict from its own
# attributes (api_key, api_base, max_tokens, temperature - see
# interpreter/core/llm/llm.py) with no passthrough for extra litellm kwargs,
# so cache_control_injection_points and stream_options can't reach
# litellm.completion() any other way without patching. Wrapping
# interpreter.llm.completions (== fixed_litellm_completions) is the smallest
# change that gets both without touching OI's own source.
#
# Scoped by an exact model-string check inside the wrapper, not a global
# patch - Groq/Gemini/Cerebras/the free OpenRouter entry are already getting
# their own automatic caching for free (see README) and must never see an
# unfamiliar kwarg from a change made for a model they aren't.
#
# hasattr-guarded: a stubbed or future-Open-Interpreter interpreter.llm
# without a `completions` attribute degrades to "no caching, no captured
# usage" rather than crashing worker startup - _attempt() falls back to
# litellm.token_counter() for the budget ledger either way, so this patch
# failing to apply costs accuracy, not correctness.
_last_paid_usage = {"values": []}

if hasattr(interpreter.llm, "completions"):
    _original_completions = interpreter.llm.completions

    def _completions_with_paid_tier_support(**params):
        is_paid = params.get("model") == OPENROUTER_PAID_MODEL
        if is_paid:
            params.setdefault("cache_control_injection_points",
                              [{"location": "message", "role": "system"}])
            params.setdefault("stream_options", {"include_usage": True})
        for chunk in _original_completions(**params):
            if is_paid:
                usage = getattr(chunk, "usage", None)
                if usage is None and isinstance(chunk, dict):
                    usage = chunk.get("usage")
                if usage:
                    # Appended, not overwritten: _attempt() may call
                    # interpreter.chat() twice on the same model (the
                    # original turn, then a synthesis nudge if the first
                    # produced no prose - see _attempt()). Overwriting would
                    # silently drop the first call's tokens from the budget
                    # ledger, undercounting real spend.
                    _last_paid_usage["values"].append(usage)
            yield chunk

    interpreter.llm.completions = _completions_with_paid_tier_support


def _usage_field(usage, name):
    value = getattr(usage, name, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(name)
    return value or 0


def _cost_for_paid_call(model, prompt_tokens, completion_tokens, reported_cost=None):
    """USD for one call, in order of trust:

    1. OpenRouter reports the actual billed cost directly on usage.cost -
       verified live 2026-08-31 on a plain, non-streamed litellm.completion()
       call (usage.cost=4.9476e-05 alongside the token counts). This is what
       was actually charged, not an estimate of it, so nothing beats it when
       present. Caveat, also verified live the same day: it did NOT appear
       on the usage captured off Open Interpreter's real streaming path (the
       one _attempt() actually uses) on an otherwise-identical call - so in
       practice tier 3 below is what prices most real calls today, not this
       one. Kept as the first check anyway since it costs nothing to try and
       will simply start winning if that gap closes upstream. `reported_cost`
       is pre-summed by the caller across every chat() call this attempt
       made (original turn + a possible synthesis nudge), not a single raw
       usage object - see _record_paid_spend().
    2. litellm.completion_cost() - its own maintained, provider-aware
       pricing database. Confirmed live the same day that it does NOT yet
       know this model ("This model isn't mapped yet") - kept as the middle
       tier anyway since it will start working the moment litellm adds it,
       with no code change here.
    3. The hand-set env rate, only as a last resort. Confirmed live
       2026-08-31 against https://openrouter.ai/api/v1/models that this
       model actually bills $1.19/$3.74 per million - notably different
       from the $0.4875/$1.56 an initial web search had suggested a day
       earlier. Numbers below were corrected to the verified figures, but
       this whole tier is proof that OpenRouter's real-time pricing must
       never be trusted from a search result once options 1 or 2 exist.
    """
    if reported_cost:
        return reported_cost
    try:
        cost = litellm.completion_cost(
            model=model, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens)
        if cost:
            return cost
    except Exception:
        pass
    return ((prompt_tokens / 1e6) * OPENROUTER_PAID_INPUT_PER_M
            + (completion_tokens / 1e6) * OPENROUTER_PAID_OUTPUT_PER_M)


def _record_paid_spend(model, instruction, system_prompt, history, output):
    """Called once, right after a successful paid-tier attempt. Sums usage
    across every chat() call this attempt made - the original turn, plus a
    synthesis nudge if one happened (see _attempt()) - since both are real
    billed calls on the same model. Falls back to counting the text that was
    actually sent/received if no usage was captured at all - a budget cap
    that silently records $0 on a bug is worse than one that slightly
    over-counts, since the entire point is to fail closed."""
    usages = _last_paid_usage["values"]
    _last_paid_usage["values"] = []
    if usages:
        prompt_tok = sum(_usage_field(u, "prompt_tokens") for u in usages)
        completion_tok = sum(_usage_field(u, "completion_tokens") for u in usages)
        reported_cost = sum(c for c in (_usage_field(u, "cost") for u in usages) if c) or None
    else:
        reported_cost = None
        sent = (system_prompt or "") + "\n" + (instruction or "") + "\n" + \
            "\n".join(str(turn.get("content", "")) for turn in (history or []))
        prompt_tok = litellm.token_counter(model=model, text=sent)
        completion_tok = litellm.token_counter(model=model, text=output or "")
    usd = _cost_for_paid_call(model, prompt_tok, completion_tok, reported_cost=reported_cost)
    # model/task go into the per-call log so the cost view can answer
    # "on what", not just "how much".
    total = spend_guard.record_spend(usd, model=model,
                                     task=(instruction or "").strip()[:120])
    print(f"[$] {model}: ~${usd:.4f} this call (~{prompt_tok}+{completion_tok} tok), "
          f"${total:.2f} of ${OPENROUTER_MONTHLY_BUDGET_USD:.2f} this month")


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


KNOWLEDGE_CORE_PATH = os.path.join(agents.VAULT, "07_Context", "Knowledge_Core.md")


def _load_knowledge_core():
    """Read fresh on every task, deliberately NOT cached like
    BASE_SYSTEM_PROMPT. Knowledge_Core.md's own header declares it
    `Stability: Dynamic` and gets edited by AI sessions "whenever a
    conversation surfaces something genuinely durable" - baking it into the
    one-time startup prompt would let a Restart=always service with
    multi-day uptime run for days on facts already corrected. An audit of
    this vault already flagged exactly that staleness as its single
    highest-impact bug, in this exact file.

    This exists because relying on the model to *decide* to go read this
    file did not work: dispatched live 2026-08-31, given a question whose
    answer lives only in Knowledge_Core.md and no hint of the filename, the
    worker searched the vault broadly, found adjacent-but-wrong sources, and
    never found or opened this file at all. The fix is to stop asking the
    model to discover it and just always hand it over - the file exists
    specifically to be small (hard-capped ~10,000 chars) and cheap to load
    unconditionally, per its own Purpose line ("always cheap to load").

    Never raises: a missing/renamed file must not become a new way for
    every single task in the system to fail. Logs and continues with no
    standing context instead."""
    try:
        with open(KNOWLEDGE_CORE_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except OSError as e:
        print(f"[!] Could not read Knowledge_Core.md: {e}", file=sys.stderr)
        return ""


VOICE_PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "voice", "Voice_Profile.md")

# Only a live conversation with Felix gets his own register. Telegram threads
# are "tg_<chat_id>" and the web client's are "web_<id>"; every scheduled
# agent task runs with no thread at all, which is what makes this a structural
# gate rather than a prompt asking the model to remember when to be casual.
# Nothing client-facing can reach it: the DMARC letters, Gumroad and Fiverr
# copy are all produced by threadless scheduled or dispatched tasks.
VOICE_THREAD_PREFIXES = ("tg_", "web_")


def _load_voice_profile(thread_id):
    """The generated voice profile, but only for Felix's own chat threads.

    Read fresh rather than cached for the same reason Knowledge_Core is:
    voice_import.py regenerates the file whenever he imports more chats, and
    a Restart=always service with multi-day uptime would otherwise keep
    running on the first version of it forever.

    Never raises. No profile (he has not imported anything yet) just means
    the normal assistant register, which is a perfectly good default - it
    must never be a new way for every task to fail."""
    if not thread_id or not thread_id.startswith(VOICE_THREAD_PREFIXES):
        return ""
    try:
        with open(VOICE_PROFILE_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _system_prompt_for(agent_name, thread_id=None):
    """Base prompt, plus fresh Knowledge_Core content, plus the selected
    agent's block - all appended, never substituted, in that order. Plus
    Felix's voice profile, last, and only in his own chat threads.

    Appending rather than substituting matters for the base prompt (it
    carries what is true regardless of role - the vault map, the
    destructive-action guardrail) and for Knowledge_Core (standing context
    for every task, not something an agent selection should be able to
    silently drop).

    The voice block goes last on purpose: it is the weakest instruction in
    the prompt and has to read as a modifier on everything above it, not as
    a replacement for any of it."""
    prompt = BASE_SYSTEM_PROMPT
    knowledge = _load_knowledge_core()
    if knowledge:
        prompt = (
            f"{prompt}\n\n"
            f"## Standing context: who Felix is, what's active right now\n"
            f"{knowledge}"
        )
    voice = _load_voice_profile(thread_id)
    if not agent_name:
        return _with_voice(prompt, voice)
    block = agents.load_prompt(agent_name)
    if not block:
        return _with_voice(prompt, voice)
    return _with_voice(
        f"{prompt}\n\n"
        f"## Your role for this task: {agent_name.replace('_', ' ')}\n"
        f"{block}",
        voice,
    )


def _with_voice(prompt, voice):
    if not voice:
        return prompt
    return (
        f"{prompt}\n\n"
        f"## How to talk in this conversation\n"
        f"You are talking to Felix directly, in his own chat. Use the voice "
        f"described below. It governs tone and shape only - it never makes "
        f"something more certain than it is, and it never replaces anything "
        f"above.\n\n{voice}"
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

# One retry, not a loop: if the model still won't synthesize after being
# told plainly to stop exploring and answer, a second nudge is very unlikely
# to succeed where the first didn't, and every retry is a real extra call
# against a model's rate limit (or real money, on the paid tier).
SYNTHESIS_NUDGE = ("Based only on what you already found above, answer the "
                   "original question directly now, in plain prose. Do not "
                   "run any more commands.")


def _has_prose(messages):
    """True if any assistant message in this turn is prose, not just a tool
    call. Mirrors format_interpreter_output()'s own "prefer prose" check -
    kept as a separate, smaller function because _attempt() needs the yes/no
    answer before it has a final string to inspect, not the formatted text
    itself."""
    for msg in (messages or []):
        if (isinstance(msg, dict) and msg.get("role") == "assistant"
                and msg.get("type") == "message" and msg.get("content")):
            return True
    return False


def _attempt(model, instruction, system_prompt=None, history=None,
             api_base=None, api_key=None, context_window=None, max_tokens=None):
    """Run one chat turn on `model`. Raises on failure (including the
    swallowed-RateLimitError case where open-interpreter returns an empty
    message list instead of raising - see respond.py's display_markdown_message
    branch).

    Every one of api_base/api_key/context_window/max_tokens is always set
    explicitly, never left as "whatever the previous attempt left behind" - a
    custom endpoint or a context-window override from one entry must not leak
    into the next entry's attempt in either direction. None means "use
    litellm/Open Interpreter's own default or auto-detection for this field,"
    a real, intentional value here, not an unset one."""
    # Seed with prior conversation turns, or [] for a cold task. Assigning a
    # fresh list every attempt matters: a failed model leaves its partial
    # messages behind, and the next model in MODEL_CHAIN must not inherit them.
    interpreter.messages = list(history) if history else []
    interpreter.llm.model = model
    interpreter.llm.api_base = api_base
    interpreter.llm.api_key = api_key
    interpreter.llm.context_window = context_window
    interpreter.llm.max_tokens = max_tokens
    if system_prompt is not None:
        interpreter.system_message = system_prompt
    # Reset here, not just after a successful _record_paid_spend(): a paid
    # attempt that raises leaves this un-cleared otherwise, and a LATER
    # successful paid call could silently inherit an earlier failed call's
    # leftover token counts.
    _last_paid_usage["values"] = []
    raw_output = interpreter.chat(instruction, display=False, stream=False)
    if not raw_output:
        raise RuntimeError(f"{model} produced no output (likely rate-limited)")

    if not _has_prose(raw_output):
        # The model ran commands and explored, correctly in some cases, but
        # never actually answered - verified live 2026-08-31 on two of three
        # real dispatches in one afternoon on free-tier models, not a rare
        # edge case. One nudge, same interpreter session so it keeps
        # everything already explored, asking it to stop and answer.
        try:
            nudge_output = interpreter.chat(SYNTHESIS_NUDGE, display=False, stream=False)
        except Exception as e:  # noqa: BLE001 - a nudge that errors is the
            # same "still no answer" outcome as one that runs and stays
            # silent - both fall through to the raise below, which is what
            # lets MODEL_CHAIN try a different model instead of accepting
            # this one's failure as if it were a real answer.
            print(f"[!] {model}: synthesis nudge itself failed ({e})")
            nudge_output = []

        if _has_prose(nudge_output):
            raw_output = raw_output + nudge_output
        else:
            # Verified live 2026-08-31: this is exactly the case that first
            # exposed the gap - the nudge ran, produced no exception and no
            # prose either, and the old code accepted the raw transcript as
            # a successful result. That meant a model already struggling
            # (quota-exhausted, in the live case) got to "answer" with a
            # dump of its own shell commands instead of MODEL_CHAIN moving
            # on to a model actually capable of synthesizing one. Raising
            # here makes this participate in the exact same retry-the-next-
            # model logic a quota error already does - an honest "all
            # models failed" beats a confident-looking transcript dump.
            raise RuntimeError(
                f"{model} explored but produced no final answer, even after "
                f"a synthesis nudge")
    return format_interpreter_output(raw_output)

# Orchestration: pick the right agent when Felix didn't name one.
#
# Deliberately a direct litellm call rather than _attempt() - routing is a
# classification, and putting it through Open Interpreter would spin up the
# whole tool-calling loop (shell access included) to answer a question that
# needs one word. Direct is cheaper, faster, and structurally can't run a
# command.
#
# Only the first few MODEL_CHAIN entries are tried: routing must not become
# more expensive than the task it routes, and if the chain is that degraded
# the right answer is to run on the base prompt rather than keep spending.
ROUTING_ENABLED = True
ROUTING_TIMEOUT_S = 45
ROUTING_MAX_MODELS = 3
# Generous for a one-word answer, and it has to be. gpt-oss - the whole top
# of MODEL_CHAIN - is a reasoning model: it spends tokens thinking before it
# emits any content. Verified live 2026-08-30 that max_tokens=16 returns an
# empty string every time (the entire budget goes to reasoning), while 512
# returns "Business_Development" for the same prompt. The failure is silent -
# an empty reply just looks like "no specialist fits" - so this is exactly
# the kind of thing that would have quietly disabled routing forever.
ROUTING_MAX_TOKENS = 512


def _route(instruction):
    """-> canonical agent name, or None to run on the base prompt.

    Never raises and never blocks the task: every failure path returns None,
    which is exactly the behaviour that existed before routing did."""
    catalog = agents.summaries()
    if not catalog:
        return None

    options = "\n".join(f"- {name}: {scope}" for name, scope in catalog)
    system = (
        "You route a task to exactly one specialist, or to none.\n\n"
        f"Specialists:\n{options}\n\n"
        "Reply with one agent name from that list, or NONE if no specialist "
        "clearly fits. Reply with the name only - no explanation, no "
        "punctuation. Prefer NONE over a weak guess: a general-purpose run "
        "handles anything, a wrong specialist actively misleads."
    )

    # Routing deliberately stays on the free chain even when everything else
    # is paid-first. It is a one-word classification - picking a specialist
    # from a list - and paying a premium model to answer "Business_Development"
    # would be a meaningful share of the monthly spend for a decision the
    # cheap models already get right.
    for entry in [e for e in MODEL_CHAIN if not e["paid"]][:ROUTING_MAX_MODELS]:
        try:
            with _time_limit(ROUTING_TIMEOUT_S):
                response = litellm.completion(
                    model=entry["model"],
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": instruction[:2000]}],
                    api_base=entry["api_base"], api_key=entry["api_key"],
                    max_tokens=ROUTING_MAX_TOKENS, temperature=0,
                )
            reply = (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"[!] routing via {entry['model']} failed ({type(e).__name__}: {e})")
            continue

        if not reply or reply.strip().upper().startswith("NONE"):
            return None
        # Take the first bare token: small models like to add a period, a
        # bullet, or a "The answer is" preamble no instruction prevents.
        for token in re.findall(r"[A-Za-z0-9_\-]+", reply):
            resolved = agents.resolve(token)
            if resolved:
                return resolved
        return None

    return None


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

# A task carrying this directive gets its result pushed to Telegram when it
# finishes. Interactive tasks don't need it - dispatch_task.py and
# telegram_bridge.py both poll for the log and show it themselves. A
# scheduled task has nobody waiting on it, so without this its answer would
# land in tasks/logs/ and be read by no one, which is not automation so much
# as a very slow way of writing files.
NOTIFY_RE = re.compile(r"^\s*<!--\s*notify\s*-->\s*\n?", re.I)

# A task carrying this writes its output into the proposals store instead of
# notifying, and is the only thing a self-directed agent run is allowed to
# produce. The gate is that there is no code path from here into
# tasks/inbox/ - see proposals.py.
PROPOSE_RE = re.compile(r"^\s*<!--\s*propose\s*-->\s*\n?", re.I)
NOTIFIER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "scripts",
    "send_telegram_notification.py")


def _parse_notify(raw):
    """-> (should_notify, remaining_text)."""
    m = NOTIFY_RE.match(raw or "")
    if not m:
        return False, raw or ""
    return True, raw[m.end():]


def _parse_propose(raw):
    """-> (is_proposal_run, remaining_text)."""
    m = PROPOSE_RE.match(raw or "")
    if not m:
        return False, raw or ""
    return True, raw[m.end():]


def _push_to_telegram(text):
    """Best-effort. A failed notification must never fail the task - the work
    is already done and logged by the time this runs. Uses /usr/bin/python3
    rather than sys.executable: the notifier is deliberately stdlib-only and
    the venv is not needed to run it."""
    try:
        subprocess.run(["/usr/bin/python3", NOTIFIER, text],
                       timeout=30, check=False)
    except Exception as e:
        print(f"[!] Could not push result to Telegram: {e}")


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


def _enqueue_handoff_task(target_agent, depth, reason, prior_output, source_agent):
    """Writes a new task file into INBOX the same atomic way dispatch_task.py
    and telegram_bridge.py do (.part, then os.replace) - this runs from
    inside the worker's own loop, which globs INBOX again on its very next
    pass, so a half-written file here would be exactly as real a bug as the
    ones those two already guard against."""
    filename = f"task_handoff_{time.strftime('%Y%m%d_%H%M%S')}.md"
    task_path = os.path.join(INBOX, filename)
    tmp_path = f"{task_path}.part"
    body = (
        f"{agents.directive(target_agent)}"
        f"{agents.handoff_depth_marker(depth)}"
        f"Handoff from {(source_agent or 'the worker').replace('_', ' ')}: {reason}\n\n"
        f"---\n{prior_output}\n"
    )
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp_path, task_path)
    return filename


# How many chain entries a voice rewrite may try before giving up. Same
# reasoning as ROUTING_MAX_MODELS: a formatting fix must never cost more than
# the answer it is reformatting.
VOICE_REWRITE_MAX_MODELS = 2
VOICE_REWRITE_TIMEOUT_S = 60


def _rewrite_in_his_voice(output, thread_id, entry):
    """Second pass over a chat reply that came back in assistant format.

    The voice profile was already in the system prompt and the worker still
    answered him in bold headers and numbered lists. Tonight's real Telegram
    replies show why a stronger prompt would not have fixed it: the register
    held on short throwaway lines and collapsed the moment the answer had
    substance. That is a habit, not a misunderstanding - so this measures the
    output and hands back a specific, named correction instead of repeating
    an instruction that was already ignored.

    A direct litellm call, not _attempt(): reformatting is a text
    transformation, and putting it through Open Interpreter would spin up the
    whole tool-calling loop - shell access included - to rewrite a sentence.

    Never raises and never loses an answer: any failure, and the original
    reply is returned untouched. A slightly formal answer is a small problem;
    an empty one is a real one."""
    if not output or not thread_id or not thread_id.startswith(VOICE_THREAD_PREFIXES):
        return output
    profile = _load_voice_profile(thread_id)
    if not profile:
        return output
    found = voice_style.violations(output)
    if not found:
        return output

    system = (
        "You rewrite one chat message so it reads exactly like the person "
        "below writes. You change only the wording and shape - never the "
        "facts, never the language, never drop or add information.\n\n"
        + profile
    )
    user = voice_style.nudge(found) + "\n\n--- the message to rewrite ---\n" + output
    for candidate_entry in ([entry] + MODEL_CHAIN)[:VOICE_REWRITE_MAX_MODELS + 1]:
        if candidate_entry["paid"] and not spend_guard.can_spend(
                spend_guard.load_ledger(), OPENROUTER_MONTHLY_BUDGET_USD):
            continue
        try:
            with _time_limit(VOICE_REWRITE_TIMEOUT_S):
                response = litellm.completion(
                    model=candidate_entry["model"],
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    api_base=candidate_entry["api_base"],
                    api_key=candidate_entry["api_key"],
                    max_tokens=1024,
                )
            rewritten = (response.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001 - see docstring: never lose the answer
            print(f"[!] voice rewrite via {candidate_entry['model']} failed ({e})")
            continue
        if voice_style.is_better(rewritten, output):
            print(f"[~] voice: rewrote reply ({', '.join(found)})")
            return rewritten
    return output


def _run_task(task_path, filename):
    with open(task_path, "r", encoding="utf-8") as f:
        raw = f.read()

    thread_id, raw = memory.parse_directive(raw)
    agent_name, raw = agents.parse_directive(raw)
    model_pref, raw = agents.parse_model_directive(raw)
    handoff_depth, raw = agents.parse_handoff_depth(raw)
    notify, raw = _parse_notify(raw)
    propose, instruction = _parse_propose(raw)

    # A bare follow-up stays in whatever role the conversation was already in.
    if not agent_name and thread_id:
        agent_name = agents.resolve(memory.last_agent(thread_id) or "")

    # Nothing named an agent and no thread implied one, so orchestrate: pick
    # the specialist this task actually belongs to. Runs last, so it can
    # never override an explicit choice or a thread's established role.
    routed = False
    if not agent_name and instruction and ROUTING_ENABLED:
        agent_name = _route(instruction)
        routed = bool(agent_name)

    # Explicit directive wins over the agent's own default, the same
    # precedence the agent directive itself has over routing: something a
    # caller wrote down deliberately is never overridden by a default.
    #
    # A ROUTED agent deliberately does not inherit its paid preference. The
    # router is a guess - its own prompt says to prefer NONE over a weak one -
    # and a guess must not spend money. Caught live: "welche obsidian plugins
    # fuers studium?" routed to Study_Teacher on the word "Studium" and would
    # have billed a casual chat question to the paid tier. Naming the agent
    # explicitly, or writing the directive, still pays.
    if model_pref is None and not routed:
        model_pref = agents.model_preference(agent_name)

    system_prompt = _system_prompt_for(agent_name, thread_id)
    history = memory.as_messages(thread_id) if thread_id else None
    # Same signal the voice profile uses: a thread id means a human is waiting
    # on the other end, and nothing else does.
    interactive = bool(thread_id and thread_id.startswith(VOICE_THREAD_PREFIXES))
    attempt_budget = CHAT_ATTEMPT_TIMEOUT_S if interactive else ATTEMPT_TIMEOUT_S

    if not instruction:
        # Still write a log: a caller waiting on this file would otherwise
        # block for its full 180s timeout on what is an instant, known failure.
        _write_log(filename, "ERROR: task file was empty - nothing to execute.")
        os.rename(task_path, os.path.join(COMPLETED, filename))
        return

    bits = []
    if agent_name:
        bits.append(f"agent: {agent_name}{' (routed)' if routed else ''}")
    if handoff_depth:
        bits.append(f"handoff depth: {handoff_depth}")
    if history:
        bits.append(f"memory: {len(history) // 2} turn(s)")
    if model_pref == "paid":
        bits.append("model: paid-first")
    label = f" ({', '.join(bits)})" if bits else ""
    print(f"[*] Processing task: {filename}{label}", flush=True)
    output = None
    errors = []
    for entry in chain_for(model_pref):
        model = entry["model"]
        if entry["delay"]:
            time.sleep(entry["delay"])
        # Live check, not a build-time decision: MODEL_CHAIN is built once at
        # process start in a Restart=always service that runs for days, so
        # "has this month's budget run out" has to be asked fresh on every
        # task, not baked in when the chain was constructed.
        if entry["paid"]:
            if not spend_guard.can_spend(spend_guard.load_ledger(), OPENROUTER_MONTHLY_BUDGET_USD):
                print(f"[!] {model} skipped - monthly budget "
                      f"(${OPENROUTER_MONTHLY_BUDGET_USD:.2f}) reached")
                errors.append(f"{model}: skipped, monthly budget reached")
                continue
        try:
            with _time_limit(attempt_budget):
                output = _attempt(model, instruction, system_prompt, history,
                                  api_base=entry["api_base"], api_key=entry["api_key"],
                                  context_window=entry["context_window"],
                                  max_tokens=entry["max_tokens"])
            if entry["paid"]:
                _record_paid_spend(model, instruction, system_prompt, history, output)
            output = _rewrite_in_his_voice(output, thread_id, entry)
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

    # A successful agent can hand its own output to another agent by ending
    # with `<!-- handoff: Agent: reason -->` - see agents.py. Checked before
    # memory/log so neither ever shows the raw directive, and so the enqueued
    # follow-up task gets the same cleaned text a human would read.
    if not output.startswith("ERROR"):
        handoff_agent, handoff_reason, output = agents.parse_handoff(output)
        if handoff_agent == agent_name:
            # Handing off to yourself isn't a pipeline, it's a no-op that
            # would otherwise still burn a queue slot.
            handoff_agent = None
        if handoff_agent and handoff_depth >= agents.MAX_HANDOFF_DEPTH:
            print(f"[!] Handoff to {handoff_agent} suppressed - depth {handoff_depth} at the cap ({agents.MAX_HANDOFF_DEPTH})")
            output += f"\n\n(Handoff to {handoff_agent.replace('_', ' ')} suppressed - this chain hit its depth limit.)"
        elif handoff_agent:
            next_file = _enqueue_handoff_task(handoff_agent, handoff_depth + 1, handoff_reason, output, agent_name)
            print(f"[>] Handed off to {handoff_agent} ({next_file})")
            output += f"\n\n(Handed off to {handoff_agent.replace('_', ' ')}: {handoff_reason})"

    # Only successful turns enter memory. Replaying "all models failed" as
    # context teaches the model nothing and spends budget a real turn needs.
    if thread_id and not output.startswith("ERROR"):
        memory.save_turn(thread_id, instruction, output, agent_name)

    # A proposal run's output goes into the store and nowhere else - not to
    # Telegram (Felix sees it at 20:00, in one place, not as it trickles in)
    # and never into tasks/inbox/. Failures are deliberately not stored: a
    # list of "all models failed" is not a proposal, and padding the evening
    # review with them would train him to skim it.
    if propose and not output.startswith("ERROR"):
        stored = proposals.add(agent_name, proposals.parse(output))
        print(f"[~] Stored {stored} proposal(s) from {agent_name or 'worker'}")

    # An approved task that answers with another proposal did nothing. It used
    # to be logged as completed, which is how two approved items on
    # 2026-09-01 silently accomplished nothing while reporting success. Say so
    # instead - a task that produced no work is not done.
    if (not propose and filename.startswith("task_approved_")
            and proposals.PROPOSAL_RE.search(output or "")):
        output = ("NICHTS GETAN: Der Agent hat auf einen genehmigten Auftrag "
                  "erneut mit einem Vorschlag geantwortet, statt ihn "
                  "auszuführen.\n\n" + output)

    _write_log(filename, output)
    os.rename(task_path, os.path.join(COMPLETED, filename))
    if notify and not propose:
        label = f" [{agent_name.replace('_', ' ')}]" if agent_name else ""
        _push_to_telegram(f"Scheduled task{label}:\n\n{output}")
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
