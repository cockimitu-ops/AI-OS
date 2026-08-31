#!/usr/bin/env python3
"""Turns a photograph of study material into text, as cheaply as it can.

Felix does not type notes on his phone - he photographs slides and boards. So
the study pipeline needs a way in that starts with an image, and he asked for
it to be token-efficient.

Two stages, cheapest first:

1. **Tesseract, locally.** Free, offline, no quota, no model. Verified on a
   German slide: umlauts intact ("prueft", "Zustaende", "ausdruecklich" all
   correct). This handles the case that is probably most common - printed
   slides and book pages photographed straight on.

2. **A vision model, only when stage 1 clearly failed.** The finding that
   makes this cheap: gemini-3.5-flash-lite is ALREADY in MODEL_CHAIN as a
   free fallback tier, and it reads images - tested 2026-08-31, it returned
   the test image's text word for word. GLM-5.2, the paid model, cannot do
   images at all ("No endpoints found" for image input), so paying more would
   buy nothing here.

Free is not unlimited, though, and that is what the daily cap is for: the
same Gemini key is a fallback tier for every ordinary task. A morning of
photographing an entire lecture must not silently eat the quota the worker
needs that evening.

Handwriting is the honest weak spot of stage 1 - classical OCR fails on it
almost always - which is exactly what stage 2 exists to catch.

Stdlib plus the tesseract binary; litellm is imported lazily and only for
stage 2, so OCR still works wherever litellm is not installed.
"""
import base64
import json
import os
import re
import subprocess
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(TASK_RUNNER_DIR, "study")
VISION_STATE_PATH = os.path.join(STATE_DIR, "vision_usage.json")

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".tif", ".tiff")
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".heic": "image/heic", ".bmp": "image/bmp",
        ".tif": "image/tiff", ".tiff": "image/tiff"}

OCR_LANGS = os.environ.get("STUDY_OCR_LANGS", "deu+eng")
OCR_TIMEOUT_S = 60
# Free, but shared: the same Gemini key backs a MODEL_CHAIN fallback tier, so
# an unbounded photo run could leave ordinary tasks without it. Raise it once
# real lecture volume is known - Felix does not know yet, and a number that
# can be edited beats a guess baked into the logic.
VISION_DAILY_MAX = int(os.environ.get("STUDY_VISION_DAILY_MAX", "40"))
VISION_MODELS = [m.strip() for m in os.environ.get(
    "STUDY_VISION_MODELS", "gemini/gemini-3.5-flash-lite").split(",") if m.strip()]
VISION_TIMEOUT_S = 90

VISION_PROMPT = (
    "Gib den gesamten Text auf diesem Bild wieder - Folie, Tafel, Buchseite "
    "oder Handschrift. Schreibe nur den Text selbst ab, in der Reihenfolge, "
    "in der er im Bild steht, mit Zeilenumbrüchen wie im Original. "
    "Keine Einleitung, keine Zusammenfassung, keine Erklärung, keine "
    "Beschreibung des Bildes. Wenn ein Wort unleserlich ist, schreibe [?] "
    "an dieser Stelle, statt zu raten. Wenn das Bild gar keinen Text "
    "enthält, antworte nur mit: KEIN TEXT"
)


# systemd passes .env in via EnvironmentFile, so the timer path has always
# had its keys. A hand-run `python3 scripts/photo_notes.py foto.jpg` did not,
# and failed with "API key not valid" - which reads like a broken key rather
# than an unloaded one. Parsed here rather than importing python-dotenv,
# because this has to keep working under /usr/bin/python3.
# TaskRunner is .../AI-OS/AI-OS/02_Systems/Automation/TaskRunner and the .env
# sits at the repo root, .../AI-OS/.env - five levels up. Counted rather than
# guessed: the first version was off by one and resolved to /home/nost/.env,
# which simply does not exist, so the fallback would have stayed silently
# unauthenticated.
# TaskRunner is .../AI-OS/AI-OS/02_Systems/Automation/TaskRunner; the .env
# sits at the repo root .../AI-OS/.env, four levels up (Automation,
# 02_Systems, the inner AI-OS, then the repo). Verified by resolving it, not
# counted in my head - the first attempt used five and landed on
# /home/nost/.env, which does not exist, leaving the fallback silently
# unauthenticated.
ENV_PATH = os.path.normpath(os.path.join(TASK_RUNNER_DIR, *([os.pardir] * 4), ".env"))


def load_env_file(path=ENV_PATH):
    """Fill in missing env vars from .env. Never overwrites what is already
    set - a value systemd or the shell provided is the more specific one."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def is_image(path):
    return path.lower().endswith(IMAGE_EXT)


# --- stage 1: local -------------------------------------------------------

def ocr(path, langs=OCR_LANGS):
    """Tesseract. -> text, or "" if it could not run at all.

    Never raises: a missing binary, an unreadable file or a format tesseract
    does not know all mean "stage 1 produced nothing", which is a case stage 2
    already handles - not a reason to fail the whole ingest."""
    try:
        proc = subprocess.run(
            ["tesseract", path, "-", "-l", langs],
            capture_output=True, text=True, timeout=OCR_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"[!] tesseract unavailable or timed out: {e}", file=sys.stderr)
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


# A "word" for the purposes of judging OCR output: letters only, long enough
# that random noise does not produce it by accident.
_WORDISH = re.compile(r"[A-Za-zÄÖÜäöüß]{4,}")


def looks_unusable(text):
    """Did stage 1 actually read anything? -> True when it plainly did not.

    Tesseract does not report failure on handwriting - it returns confident
    garbage, a scatter of one and two character fragments. So the test is not
    "did it error" but "does this look like language": enough characters, and
    enough of them forming real words rather than debris."""
    if not text or len(text.strip()) < 40:
        return True
    words = _WORDISH.findall(text)
    if len(words) < 5:
        return True
    # Share of the text made of plausible words. Real prose sits far above
    # this; OCR noise on handwriting sits far below.
    covered = sum(len(w) for w in words)
    return covered / max(len(re.sub(r"\s", "", text)), 1) < 0.45


# --- stage 2: vision, capped ---------------------------------------------

def _load_vision_state():
    try:
        with open(VISION_STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def vision_used_today(state=None):
    state = _load_vision_state() if state is None else state
    return int(state.get(date.today().isoformat(), 0))


def _record_vision_call():
    state = _load_vision_state()
    today = date.today().isoformat()
    state[today] = int(state.get(today, 0)) + 1
    # Keep only recent days; this file is a rate limiter, not a history.
    state = dict(sorted(state.items())[-14:])
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = VISION_STATE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, VISION_STATE_PATH)


def vision(path, models=None):
    """Read the image with a vision-capable model. -> text or "".

    Free today (gemini-3.5-flash-lite), but capped per day because that key is
    also a MODEL_CHAIN fallback tier. Never raises."""
    if vision_used_today() >= VISION_DAILY_MAX:
        print(f"[!] vision daily cap reached ({VISION_DAILY_MAX}) - "
              f"{os.path.basename(path)} left for tomorrow", file=sys.stderr)
        return ""
    load_env_file()
    try:
        import litellm
    except ImportError:
        print("[!] litellm not available - no vision fallback", file=sys.stderr)
        return ""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except OSError as e:
        print(f"[!] cannot read {path}: {e}", file=sys.stderr)
        return ""
    mime = MIME.get(os.path.splitext(path)[1].lower(), "image/jpeg")

    for model in (models or VISION_MODELS):
        try:
            response = litellm.completion(
                model=model, timeout=VISION_TIMEOUT_S, max_tokens=4096,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{b64}"}}]}])
            text = (response.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001 - every failure is "no text"
            print(f"[!] vision via {model} failed: {type(e).__name__}: "
                  f"{str(e)[:120]}", file=sys.stderr)
            continue
        _record_vision_call()
        if text.upper().startswith("KEIN TEXT"):
            return ""
        return text
    return ""


# --- the two stages together ---------------------------------------------

def text_from_image(path, allow_vision=True, verbose=False):
    """-> (text, how) where how is "ocr", "vision", or "failed"."""
    local = ocr(path)
    if not looks_unusable(local):
        if verbose:
            print(f"    OCR ok ({len(local)} Zeichen)")
        return local, "ocr"
    if not allow_vision:
        return local, "failed" if not local.strip() else "ocr"
    if verbose:
        print("    OCR unbrauchbar - Vision-Modell")
    seen = vision(path)
    if seen.strip():
        return seen, "vision"
    # Stage 1's output is returned even though it was judged unusable: a bad
    # transcription Felix can look at beats an empty file he cannot.
    return local, "failed"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("images", nargs="+")
    ap.add_argument("--no-vision", action="store_true")
    args = ap.parse_args(argv)
    for path in args.images:
        text, how = text_from_image(path, allow_vision=not args.no_vision,
                                    verbose=True)
        print(f"--- {os.path.basename(path)} [{how}] ---")
        print(text or "(kein Text)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
