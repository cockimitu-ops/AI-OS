#!/usr/bin/env python3
"""Pico 4 headset as a device in the AI-OS, over adb.

PICO OS is Android, so everything the phone modules do works here: state,
input, app launching, screen capture, and the H.264 stream the device panel
uses. What differs is what is worth asking a headset, and what it costs to
reach one.

WHAT IS DIFFERENT ABOUT A HEADSET

  * It is not rooted, and does not need to be. The `input` restriction that
    forced phone_root.py through `su` is Xiaomi's, not Android's - on stock
    PICO OS the shell may inject events directly.
  * Its screen is a stereo pair. `screencap` returns the composited output,
    which is both eyes side by side - so the aspect ratio is wide, not tall,
    and every consumer of it has to take the size from the device rather
    than assume a phone.
  * It composites constantly. The problem that dogs the phones - a still
    screen produces no video at all - does not exist in a headset that is
    redrawing at 72 or 90 Hz. The live stream should be the best-behaved of
    the three devices.
  * It sleeps when taken off, and proximity is the trigger, not a timer.
    Nothing here can keep it awake; a headset on a desk is legitimately off.

SETUP, ONCE

Developer mode has to be enabled in the PICO app on Felix's phone, then over
USB:

    adb devices                 # accept the prompt in the headset
    adb tcpip 5555

After that it is reachable at its address on the network for as long as it
stays awake. To reach it from outside the flat it needs Tailscale, which the
headset can run as a sideloaded APK:

    scripts/pico_setup.sh --install-tailscale ~/Downloads/tailscale.apk

AIOS_PICO_HOST is where this module looks. Until that is set and reachable,
every function here raises PicoError with the reason, and the device panel
shows the headset as an offline device rather than pretending otherwise.

Stdlib only, plus adb.
"""
import os
import re
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(TASK_RUNNER_DIR, "phone")
SHOTS_DIR = os.path.join(STATE_DIR, "screenshots")
PREFIX = "pico"

# Not defaulted to a guess. An address that is wrong is worse than one that
# is absent: absent says "not set up", wrong says "your headset is broken".
DEVICE = os.environ.get("AIOS_PICO_HOST", "")
ADB_TIMEOUT = 25

KEYS = {"back": 4, "home": 3, "recents": 187, "power": 26, "enter": 66,
        "volume_up": 24, "volume_down": 25, "wake": 224, "sleep": 223,
        "menu": 82, "delete": 67}


class PicoError(RuntimeError):
    """Raised instead of returning a half-answer, same rule as the phones."""


def configured():
    return bool(DEVICE)


def _require():
    if not DEVICE:
        raise PicoError(
            "Pico 4 ist noch nicht eingerichtet. AIOS_PICO_HOST in .env "
            "setzen (z.B. 100.x.y.z:5555) - siehe scripts/pico_setup.sh")


def _attached():
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True,
                             timeout=10).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(line.startswith(DEVICE) and line.rstrip().endswith("device")
               for line in out.splitlines())


def connect():
    """-> True once the headset answers.

    `adb connect` reports success for a device that then sits in
    'unauthorized' - reachable, but the prompt inside the headset was never
    accepted. That is the single most likely state for a headset nobody has
    put on today, so it is named rather than reported as a generic failure."""
    _require()
    if _attached():
        return True
    try:
        out = subprocess.run(["adb", "connect", DEVICE], capture_output=True,
                             timeout=15).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as e:
        raise PicoError(f"adb connect fehlgeschlagen: {e}")
    if "unauthorized" in out.lower():
        raise PicoError("Pico meldet 'unauthorized' - die USB-Debugging-"
                        "Abfrage im Headset bestaetigen")
    if not _attached():
        raise PicoError(f"Pico nicht erreichbar unter {DEVICE} - "
                        "aufgesetzt und wach?")
    return True


def _adb(*args, timeout=ADB_TIMEOUT, binary=False):
    _require()
    if not _attached():
        connect()
    try:
        proc = subprocess.run(["adb", "-s", DEVICE, *args],
                              capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise PicoError("adb ist nicht installiert")
    except subprocess.TimeoutExpired:
        raise PicoError(f"Pico hat in {timeout}s nicht geantwortet")
    if proc.returncode != 0:
        raise PicoError(proc.stderr.decode("utf-8", "replace").strip()
                        or "adb-Befehl fehlgeschlagen")
    return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")


def sh(command, timeout=ADB_TIMEOUT):
    """A shell command on the headset. No root - PICO OS is stock enough that
    the shell user may inject input and read state without it."""
    return _adb("shell", command, timeout=timeout)


# --- reading state --------------------------------------------------------

# One round trip for everything, the same lesson the phones taught: each adb
# call over the network costs about a second, and five of them made a device
# panel miss its own deadline.
_STATUS_CMD = (
    "echo '<<<BATTERY>>>'; dumpsys battery; "
    "echo '<<<POWER>>>'; dumpsys power | grep -m1 mWakefulness; "
    "echo '<<<ACT>>>'; dumpsys activity activities | grep -m1 -E "
    "'mResumedActivity|topResumedActivity'; "
    "echo '<<<SIZE>>>'; wm size"
)


def _split_sections(raw):
    out, current = {}, None
    for line in (raw or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("<<<") and stripped.endswith(">>>"):
            current = stripped.strip("<>")
            out[current] = []
        elif current:
            out[current].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def status():
    """Everything readable, in a single round trip."""
    sections = _split_sections(sh(_STATUS_CMD))
    binfo = {}
    for line in sections.get("BATTERY", "").splitlines():
        if ":" in line:
            k, _, v = line.strip().partition(":")
            binfo[k.strip()] = v.strip()
    wake = re.search(r"mWakefulness=(\w+)", sections.get("POWER", ""))
    app = re.search(r"(?:mResumedActivity|topResumedActivity).*?\{[^}]*?\s([\w.]+)/",
                    sections.get("ACT", ""))
    size = re.search(r"Physical size:\s*(\d+)x(\d+)", sections.get("SIZE", ""))
    return {
        "reachable": True,
        "battery": {
            "level": int(binfo["level"]) if binfo.get("level", "").isdigit() else None,
            "charging": binfo.get("AC powered") == "true"
                        or binfo.get("USB powered") == "true",
            "temperature_c": (int(binfo["temperature"]) / 10
                              if binfo.get("temperature", "").isdigit() else None),
        },
        "screen_on": (wake.group(1).lower() == "awake") if wake else None,
        "current_app": app.group(1) if app else None,
        "size": (int(size.group(1)), int(size.group(2))) if size else None,
        "notifications": [],
    }


def screen_size():
    """-> (width, height) in device pixels, or None.

    Read, never assumed. A headset's composited output is a stereo pair and
    therefore wide; anything that guessed a phone shape would put every tap
    in the wrong eye."""
    m = re.search(r"Physical size:\s*(\d+)x(\d+)", sh("wm size"))
    return (int(m.group(1)), int(m.group(2))) if m else None


def battery():
    return status()["battery"]


def screen_on():
    return status()["screen_on"]


def current_app():
    return status()["current_app"]


def notifications():
    """Headsets do not have a useful notification shade. Empty, honestly,
    rather than a parser that always returns nothing for a subtler reason."""
    return []


def screenshot(name=None):
    """Grab the composited view. -> path on the server.

    Captured to a file on the device and pulled, not streamed through the
    shell, for the same reason as the phones: measured three times faster,
    and the bytes never pass through a shell that might translate them."""
    os.makedirs(SHOTS_DIR, exist_ok=True)
    remote = f"/sdcard/.aios_pico_{int(time.time() * 1000)}.png"
    path = os.path.join(SHOTS_DIR, name or f"{PREFIX}_{int(time.time())}.png")
    try:
        _adb("shell", "screencap", "-p", remote)
        _adb("pull", remote, path)
    finally:
        try:
            _adb("shell", "rm", "-f", remote)
        except PicoError:
            pass
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"\x89PNG":
                raise PicoError("screencap lieferte kein PNG")
    except OSError as e:
        raise PicoError(f"Screenshot nicht lesbar: {e}")
    return path


# --- acting ---------------------------------------------------------------

def tap(x, y):
    sh(f"input tap {int(x)} {int(y)}")
    return True


def swipe(x1, y1, x2, y2, ms=300):
    sh(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(ms)}")
    return True


def key(name):
    if name not in KEYS:
        raise PicoError(f"unbekannte Taste {name!r}; bekannt: {', '.join(sorted(KEYS))}")
    sh(f"input keyevent {KEYS[name]}")
    return True


def type_text(text):
    if not text:
        return False
    sh("input text " + "'" + text.replace("'", "'\\''").replace(" ", "%s") + "'")
    return True


def open_app(package):
    if not re.fullmatch(r"[\w.]+", package or ""):
        raise PicoError(f"ungueltiger Paketname: {package!r}")
    sh(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
    return True


def installed_apps():
    """Third-party packages, which on a headset means the games and tools
    rather than the forty system services nobody launches by hand."""
    out = sh("pm list packages -3")
    return sorted(line.split(":", 1)[1].strip()
                  for line in out.splitlines() if ":" in line)


def install(apk_path, timeout=300):
    """Sideload an APK. -> adb's own report.

    The thing a headset needs most and a phone rarely does: everything
    interesting on a Pico that is not in the store arrives this way."""
    if not os.path.isfile(apk_path):
        raise PicoError(f"APK nicht gefunden: {apk_path}")
    return _adb("install", "-r", apk_path, timeout=timeout)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", nargs="?", default="status",
                    choices=["status", "screenshot", "apps", "install", "connect"])
    ap.add_argument("value", nargs="?")
    args = ap.parse_args(argv)
    try:
        if args.command == "connect":
            connect()
            print(f"verbunden: {DEVICE}")
        elif args.command == "status":
            state = status()
            b = state["battery"]
            print(f"Pico 4: {b['level']}%{' laedt' if b['charging'] else ''}, "
                  f"{'wach' if state['screen_on'] else 'schlaeft'}, "
                  f"{state['current_app'] or 'keine App'}, "
                  f"{state['size'][0]}x{state['size'][1]}" if state["size"] else "")
        elif args.command == "screenshot":
            print(screenshot())
        elif args.command == "apps":
            for pkg in installed_apps():
                print(pkg)
        elif args.command == "install":
            print(install(args.value))
    except PicoError as e:
        print(f"[!] {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
