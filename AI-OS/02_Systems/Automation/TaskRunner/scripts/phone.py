#!/usr/bin/env python3
"""Control Felix's Android phone from AI-OS, over Tailscale, without root.

Why unrooted: rooting the Nothing Phone means unlocking the bootloader, which
wipes the device, and permanently failing Play Integrity - which breaks
banking apps, Google Wallet, and a growing list of others that simply refuse
to run on a rooted phone. Everything below works without any of that. Root
would add full filesystem access and little else that this actually needs, at
a cost Felix would feel every time he tried to pay for something.

The connection path is the part that is already solved: the phone is on the
tailnet (100.81.85.3), so once adbd is listening it is reachable from the
server anywhere in the world, with no port forwarding and no exposure to the
public internet. Tailscale is the perimeter, exactly as it is for the web
client.

SAFETY

adb is total control of the device. This module deliberately exposes a narrow,
named set of actions rather than a generic "run any adb command" tool:
read state, take a screenshot, tap/type, open an app. There is no uninstall,
no factory reset, no arbitrary shell passthrough - not because adb cannot do
them, but because an LLM with a shell on a phone should not be one malformed
instruction away from wiping it.

Stdlib only, plus the adb binary.
"""
import json
import os
import re
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(TASK_RUNNER_DIR, "phone")
SHOTS_DIR = os.path.join(STATE_DIR, "screenshots")

# The phone's tailnet address. Not the LAN one: the LAN address changes with
# every network he joins, while the tailnet address is stable and reachable
# from campus, a train, or anywhere else.
PHONE_HOST = os.environ.get("AIOS_PHONE_HOST", "100.81.85.3")
# 5555 is what `adb tcpip 5555` opens, and it binds all interfaces - including
# the tailnet one. Wireless Debugging's own port is randomised on every
# toggle, which makes it useless for an unattended service.
PHONE_PORT = int(os.environ.get("AIOS_PHONE_PORT", "5555"))
ADB_TIMEOUT = 25

SERIAL = f"{PHONE_HOST}:{PHONE_PORT}"


class PhoneError(RuntimeError):
    """Raised instead of returning a half-answer. A caller that cannot reach
    the phone must be able to tell that apart from a phone that answered and
    said 'nothing'."""


def _adb(*args, timeout=ADB_TIMEOUT, binary=False):
    cmd = ["adb", "-s", SERIAL, *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise PhoneError("adb is not installed on this machine")
    except subprocess.TimeoutExpired:
        raise PhoneError(f"adb timed out after {timeout}s: {' '.join(args[:2])}")
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise PhoneError(err or f"adb failed: {' '.join(args[:2])}")
    return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")


def connect():
    """-> True once the device is authorised and online.

    `adb connect` reports success even for a device that then sits in
    'unauthorized' - the state where the phone is reachable but Felix has not
    accepted the RSA prompt. Treating that as connected produces confusing
    failures later, so it is checked explicitly here."""
    try:
        subprocess.run(["adb", "connect", SERIAL],
                       capture_output=True, timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise PhoneError(f"adb connect failed: {e}")
    listing = subprocess.run(["adb", "devices"], capture_output=True,
                             timeout=10).stdout.decode("utf-8", "replace")
    for line in listing.splitlines():
        if line.startswith(SERIAL):
            state = line.split()[-1]
            if state == "device":
                return True
            if state == "unauthorized":
                raise PhoneError(
                    "Phone is reachable but not authorised - accept the "
                    "'Allow USB debugging' prompt on the device.")
            raise PhoneError(f"Phone is in state '{state}'")
    raise PhoneError(
        f"Phone not reachable at {SERIAL}. Wireless debugging may be off, or "
        "adbd is not listening on 5555 (see this module's docstring).")


def is_available():
    """Never raises - for callers that want to degrade rather than fail."""
    try:
        return connect()
    except PhoneError:
        return False


# --- reading state --------------------------------------------------------

def battery():
    out = _adb("shell", "dumpsys", "battery")
    info = {}
    for line in out.splitlines():
        if ":" in line:
            key, _, value = line.strip().partition(":")
            info[key.strip()] = value.strip()
    return {
        "level": int(info.get("level", -1)),
        "charging": info.get("AC powered") == "true"
                    or info.get("USB powered") == "true",
        "temperature_c": (int(info["temperature"]) / 10
                          if info.get("temperature", "").isdigit() else None),
    }


def current_app():
    """The package currently in the foreground, or None when the screen is off."""
    out = _adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"(?:mResumedActivity|topResumedActivity).*?\{[^}]*?\s([\w.]+)/", out)
    return m.group(1) if m else None


def screen_on():
    out = _adb("shell", "dumpsys", "power")
    m = re.search(r"mWakefulness=(\w+)", out)
    return (m.group(1) if m else "").lower() == "awake"


NOTIF_RE = re.compile(
    r"NotificationRecord\(.*?pkg=([\w.]+).*?"
    r"android\.title=(?:String\s*\()?([^)\n]*?)\)?\s*$",
    re.M | re.S)


def notifications():
    """-> [{"package", "title", "text"}] for what is on the shade now.

    dumpsys formats notifications for humans, not machines, and the layout
    differs across Android versions - so this parses defensively and returns
    what it can rather than pretending a partial parse is a failure. What it
    is for is triage ("is anything here worth interrupting him for"), which
    survives a missing field; it is not a mail client."""
    out = _adb("shell", "dumpsys", "notification", "--noredact")
    found, current = [], None
    for line in out.splitlines():
        line = line.strip()
        m = re.search(r"pkg=([\w.]+)", line)
        if m and "NotificationRecord" in line:
            if current and (current.get("title") or current.get("text")):
                found.append(current)
            current = {"package": m.group(1), "title": "", "text": ""}
            continue
        if current is None:
            continue
        for key, field in (("android.title=", "title"), ("android.text=", "text")):
            if key in line:
                value = line.split(key, 1)[1].strip()
                value = re.sub(r"^String\s*\(", "", value).rstrip(")").strip()
                if value and value.lower() != "null":
                    current[field] = value[:300]
    if current and (current.get("title") or current.get("text")):
        found.append(current)
    # Deduplicate: an ongoing notification is re-posted on every update and
    # appears many times in one dump.
    seen, unique = set(), []
    for n in found:
        key = (n["package"], n["title"], n["text"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(n)
    return unique


def screenshot(name=None):
    """Grab the screen. -> path on the server.

    exec-out, not `screencap -p > file` then pull: the shell path mangles
    binary on some Android builds by translating newlines, producing a PNG
    that is subtly corrupt and fails to open."""
    os.makedirs(SHOTS_DIR, exist_ok=True)
    data = _adb("exec-out", "screencap", "-p", binary=True)
    if not data.startswith(b"\x89PNG"):
        raise PhoneError("screencap did not return a PNG")
    path = os.path.join(SHOTS_DIR, name or f"screen_{int(time.time())}.png")
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return path


# --- acting ---------------------------------------------------------------

def tap(x, y):
    _adb("shell", "input", "tap", str(int(x)), str(int(y)))
    return True


def swipe(x1, y1, x2, y2, ms=300):
    _adb("shell", "input", "swipe", *(str(int(v)) for v in (x1, y1, x2, y2)),
         str(int(ms)))
    return True


def type_text(text):
    """`input text` cannot express spaces or most punctuation directly - they
    have to be escaped, and an unescaped one silently truncates the rest of
    the string rather than erroring."""
    escaped = text.replace(" ", "%s")
    escaped = re.sub(r"([\\\"'`;&|<>()$])", r"\\\1", escaped)
    _adb("shell", "input", "text", escaped)
    return True


KEYS = {"back": 4, "home": 3, "recents": 187, "power": 26, "enter": 66,
        "volume_up": 24, "volume_down": 25, "wake": 224, "sleep": 223}


def key(name):
    if name not in KEYS:
        raise PhoneError(f"unknown key {name!r}; known: {', '.join(sorted(KEYS))}")
    _adb("shell", "input", "keyevent", str(KEYS[name]))
    return True


def open_app(package):
    """Launch by package name. monkey rather than `am start`: it resolves the
    launcher activity itself, so the caller does not need to know the
    activity name for every app."""
    if not re.fullmatch(r"[\w.]+", package or ""):
        raise PhoneError(f"invalid package name: {package!r}")
    _adb("shell", "monkey", "-p", package, "-c",
         "android.intent.category.LAUNCHER", "1")
    return True


def installed_apps():
    out = _adb("shell", "pm", "list", "packages", "-3")
    return sorted(line.replace("package:", "").strip()
                  for line in out.splitlines() if line.startswith("package:"))


def screen_size():
    """-> (width, height) in device pixels, or None. Same purpose as the
    rooted module's: mapping a tap on a scaled screenshot back to reality."""
    m = re.search(r"Physical size:\s*(\d+)x(\d+)", _adb("shell", "wm", "size"))
    return (int(m.group(1)), int(m.group(2))) if m else None


def status():
    """Everything readable in one call, for the assistant's own use."""
    connect()
    return {
        "reachable": True,
        "battery": battery(),
        "screen_on": screen_on(),
        "current_app": current_app(),
        "notifications": notifications(),
    }


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("notifications")
    sub.add_parser("apps")
    shot = sub.add_parser("screenshot")
    shot.add_argument("--name")
    t = sub.add_parser("tap"); t.add_argument("x", type=int); t.add_argument("y", type=int)
    w = sub.add_parser("type"); w.add_argument("text")
    k = sub.add_parser("key"); k.add_argument("name")
    o = sub.add_parser("open"); o.add_argument("package")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "status":
            print(json.dumps(status(), ensure_ascii=False, indent=2))
        elif args.cmd == "notifications":
            connect()
            for n in notifications():
                print(f"[{n['package']}] {n['title']}: {n['text'][:80]}")
        elif args.cmd == "apps":
            connect()
            print("\n".join(installed_apps()))
        elif args.cmd == "screenshot":
            connect()
            print(screenshot(args.name))
        elif args.cmd == "tap":
            connect(); tap(args.x, args.y); print("ok")
        elif args.cmd == "type":
            connect(); type_text(args.text); print("ok")
        elif args.cmd == "key":
            connect(); key(args.name); print("ok")
        elif args.cmd == "open":
            connect(); open_app(args.package); print("ok")
    except PhoneError as e:
        print(f"Handy nicht erreichbar: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
