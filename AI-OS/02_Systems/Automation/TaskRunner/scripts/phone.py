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
import concurrent.futures
import os
import re
import socket
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
PREFIX = "screen"
ADB_TIMEOUT = 25

STATE_PATH = os.path.join(STATE_DIR, "nothing_port.json")

# Android's wireless-debugging port is randomised every time the toggle is
# flipped, and the whole service dies on reboot. That makes a hardcoded port
# useless for anything unattended - which is exactly why this phone kept
# "working once and then not".
#
# Three-step recovery, cheapest first:
#   1. the port that worked last time, remembered on disk
#   2. 5555, which is where `adb tcpip 5555` puts it permanently
#   3. a bounded scan of the range Android actually uses
#
# And the important half: the moment a connection succeeds by ANY route, adbd
# is pinned to 5555 so the next reconnect is instant and needs nothing from
# Felix until the phone reboots.
SCAN_RANGE = (30000, 50000)
SCAN_WORKERS = 400
SCAN_TIMEOUT = 0.25


def _remembered_port():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return int(json.load(f).get("port") or 0) or None
    except (OSError, ValueError, TypeError):
        return None


def _remember_port(port):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"port": int(port), "at": time.time()}, f)
    os.replace(tmp, STATE_PATH)


def _port_open(port, timeout=SCAN_TIMEOUT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((PHONE_HOST, port)) == 0


def scan_for_adb(verbose=False, want=6):
    """-> open ports in Android's wireless-debugging range, newest-first.

    Returns SEVERAL, not one. Android opens two ports when wireless debugging
    is on - one for pairing and one for connecting - and they speak different
    protocols. Taking the first open port found gave "device offline" every
    time it happened to land on the pairing port, which reads exactly like a
    broken phone. The caller tries each until one actually reaches `device`
    state.

    Parallel and bounded: 20k ports at a quarter-second each would take over
    an hour serially; in a thread pool it is seconds. It only ever runs
    against Felix's own phone on his own tailnet."""
    lo, hi = SCAN_RANGE
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        futures = {pool.submit(_port_open, p): p for p in range(lo, hi)}
        for fut in concurrent.futures.as_completed(futures):
            try:
                if fut.result():
                    found.append(futures[fut])
                    if len(found) >= want:
                        for f in futures:
                            f.cancel()
                        break
            except Exception:  # noqa: BLE001 - a refused port is not an error
                pass
    # Descending: Android hands out the connect port after the pairing port
    # often enough that the higher number is the better first guess.
    found.sort(reverse=True)
    if verbose:
        print(f"[i] offene Ports: {found or 'keine'}")
    return found


SERIAL = f"{PHONE_HOST}:{PHONE_PORT}"


class PhoneError(RuntimeError):
    """Raised instead of returning a half-answer. A caller that cannot reach
    the phone must be able to tell that apart from a phone that answered and
    said 'nothing'."""


def _attached(serial):
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True,
                             timeout=10).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(l.startswith(serial) and l.rstrip().endswith("device")
               for l in out.splitlines())


def _adb(*args, timeout=ADB_TIMEOUT, binary=False):
    # Re-establish the registration if it was lost. adb forgets a network
    # device whenever the connection drops, and then reports "not found" for
    # a phone that is reachable and listening.
    if _ACTIVE["serial"] and not _attached(_ACTIVE["serial"]):
        try:
            connect()
        except PhoneError:
            pass
    cmd = ["adb", "-s", _active_serial(), *args]
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


def pin_to_5555():
    """Make adbd listen on the fixed port 5555. -> True on success.

    This is what turns a one-off pairing into something durable: after this,
    reconnecting needs no pairing dialog and no scan until the phone reboots.
    Run automatically after every successful connection, because the cost is
    one command and the alternative is asking Felix to fish a random port out
    of a settings screen every time."""
    try:
        subprocess.run(["adb", "-s", _active_serial(), "tcpip", "5555"],
                       capture_output=True, timeout=20)
        time.sleep(2)
        return _port_open(5555, timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        return False


_ACTIVE = {"serial": None}


def _active_serial():
    return _ACTIVE["serial"] or SERIAL


def connect():
    """-> True once the device is authorised and online.

    `adb connect` reports success even for a device that then sits in
    'unauthorized' - the state where the phone is reachable but Felix has not
    accepted the RSA prompt. Treating that as connected produces confusing
    failures later, so it is checked explicitly here."""
    # Try the cheap routes before the expensive one, and stop at the first
    # that answers.
    candidates = []
    remembered = _remembered_port()
    if remembered:
        candidates.append(remembered)
    if PHONE_PORT not in candidates:
        candidates.append(PHONE_PORT)

    open_ports = [p for p in candidates if _port_open(p, timeout=1.5)]
    if not open_ports:
        open_ports = scan_for_adb()
    if not open_ports:
        raise PhoneError(
            f"Kein offener adb-Port auf {PHONE_HOST}. Drahtloses Debugging ist "
            "aus oder das Handy wurde neu gestartet - einmal in den "
            "Entwickleroptionen einschalten, danach nagelt sich die "
            "Verbindung selbst auf 5555 fest.")

    problems = []
    for target in open_ports:
        serial = f"{PHONE_HOST}:{target}"
        # A stale entry from an earlier session answers "offline" forever;
        # dropping it first means each port gets a genuine attempt.
        subprocess.run(["adb", "disconnect", serial],
                       capture_output=True, timeout=10)
        try:
            subprocess.run(["adb", "connect", serial],
                           capture_output=True, timeout=15)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise PhoneError(f"adb connect failed: {e}")
        listing = subprocess.run(["adb", "devices"], capture_output=True,
                                 timeout=10).stdout.decode("utf-8", "replace")
        state = ""
        for line in listing.splitlines():
            if line.startswith(serial + "\t") or line.startswith(serial + " "):
                state = line.split()[-1]
                break
        if state == "device":
            _ACTIVE["serial"] = serial
            _remember_port(target)
            if target != 5555:
                # Opportunistic, never fatal: if it works the next reconnect
                # is instant, and if it does not the remembered port still
                # gets us back in.
                pin_to_5555()
            return True
        if state == "unauthorized":
            raise PhoneError(
                "Handy erreichbar, aber nicht autorisiert - den "
                "'USB-Debugging zulassen'-Dialog auf dem Gerät bestätigen.")
        problems.append(f"{target}:{state or 'keine Antwort'}")
        subprocess.run(["adb", "disconnect", serial],
                       capture_output=True, timeout=10)

    raise PhoneError(
        "Offene Ports gefunden, aber keiner spricht adb: "
        + ", ".join(problems)
        + ". Meist heißt das, die Kopplung ist weg - einmal neu koppeln.")


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

    Captured to a file on the device and pulled, NOT streamed with
    `exec-out`. Measured on the real phone over the tailnet: exec-out took
    11.7s, capture-plus-pull 4.2s for the same image - roughly three times
    faster, and the interactive control panel is unusable at eleven seconds a
    frame.

    The binary-mangling hazard that originally motivated exec-out is real but
    different: it applies to `adb shell "screencap -p" > file`, where the
    SHELL pipes the bytes and some Android builds translate newlines in
    transit. Writing the file on the device and pulling it never puts the
    bytes through a shell, so it is safe - and the result is still checked for
    the PNG magic rather than trusted."""
    shots = os.path.join(STATE_DIR, "screenshots")
    os.makedirs(shots, exist_ok=True)
    remote = f"/sdcard/.aios_screen_{int(time.time() * 1000)}.png"
    path = os.path.join(shots, name or f"{PREFIX}_{int(time.time())}.png")
    try:
        _adb("shell", "screencap", "-p", remote)
        _adb("pull", remote, path)
    finally:
        # Best effort: a leftover file on /sdcard is untidy, not harmful, and
        # must never mask the real error from the capture itself.
        try:
            _adb("shell", "rm", "-f", remote)
        except PhoneError:
            pass
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"\x89PNG":
                raise PhoneError("screencap lieferte kein PNG")
    except OSError as e:
        raise PhoneError(f"Screenshot nicht lesbar: {e}")
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


# One shell invocation instead of five. Each adb round trip over the tailnet
# costs about a second; separately that made status() take ~6s, which is
# enough for two phones probed in parallel to both miss the device panel's
# deadline and be reported offline while perfectly reachable.
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
    connect()
    sections = _split_sections(_adb("shell", _STATUS_CMD))
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
