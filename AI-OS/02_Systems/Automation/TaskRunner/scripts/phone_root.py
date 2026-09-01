#!/usr/bin/env python3
"""Extended phone toolkit for the rooted Poco X3 Pro (vayu).

Two phones, two capability levels, deliberately in two modules:

  phone.py       Nothing Phone 2a Plus, unrooted, over the tailnet. Narrow by
                 necessity - no root, so no more is possible.
  phone_root.py  this one. Poco X3 Pro, bootloader unlocked, root available.
                 Much wider, because the device allows it.

WHAT "NO RESTRICTIONS" MEANS HERE, AND WHAT IT DOES NOT

Felix asked for a toolkit without restrictions on his own rooted phone. It is
his device and that is his call, so this exposes the full range: root shell,
filesystem access, package management, settings, SMS/call logs, sensors,
screen recording, file push/pull.

What it still does NOT do is hand those verbs to an autonomous agent without a
gate. That is not a restriction on Felix - every one of them is one CLI call
away for him - it is a restriction on *unattended automation*. The difference
matters: a scheduled agent that misreads an instruction and calls `wipe` costs
him the phone, and no amount of "he asked for no restrictions" makes that the
outcome he wanted. So the destructive verbs live behind DANGEROUS and require
confirm=True passed explicitly at the call site.

Same pattern the paid model tier already uses (OPENROUTER_PAID_ENABLED) and the
MCP dispatch tool (AIOS_MCP_ALLOW_DISPATCH): capability present, default off,
enabling it is a decision rather than an accident.

CONNECTION

USB for setup; `adb tcpip 5555` afterwards makes it reachable over the tailnet
like the other phone, so the cable is only needed once.

Stdlib only, plus adb.
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
PULL_DIR = os.path.join(STATE_DIR, "pulled")

# The rooted phone. Serial by default (USB), overridable to host:port once it
# is on the tailnet.
# The tailnet address, not the USB serial. Verified working 2026-09-01: root
# over Tailscale from the server, cable unplugged. A USB serial only resolves
# while the cable is in, which makes it useless for anything scheduled.
DEVICE = os.environ.get("AIOS_ROOT_PHONE", "100.97.248.22:5555")
ADB_TIMEOUT = 40

# Verbs that can cost him the device or its data. Present, but never callable
# without an explicit confirm at the call site.
DANGEROUS = {"uninstall", "wipe_package_data", "reboot_recovery",
             "reboot_bootloader", "remove_file"}


class PhoneError(RuntimeError):
    pass


def reconnect():
    """Drop and re-establish the adb connection. -> True if the device answers.

    adb over the network goes stale: the daemon keeps reporting `device` while
    every shell command times out, usually after the phone sleeps or changes
    network. Nothing looks wrong until a caller hangs for the full timeout.
    Disconnecting first is what clears it - a bare `adb connect` on an
    already-registered stale entry is a no-op."""
    for verb in ("disconnect", "connect"):
        try:
            subprocess.run(["adb", verb, DEVICE], capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return False
    try:
        proc = subprocess.run(["adb", "-s", DEVICE, "shell", "echo", "ok"],
                              capture_output=True, timeout=10)
        return b"ok" in proc.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def _adb(*args, timeout=ADB_TIMEOUT, binary=False, check=True, _retried=False):
    cmd = ["adb", "-s", DEVICE, *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise PhoneError("adb is not installed")
    except subprocess.TimeoutExpired:
        # One automatic recovery attempt. A stale connection is the common
        # cause and it is fixable without Felix; a genuinely absent phone
        # fails the retry too and reports honestly.
        if not _retried and reconnect():
            return _adb(*args, timeout=timeout, binary=binary, check=check,
                        _retried=True)
        raise PhoneError(f"adb timed out after {timeout}s")
    if check and proc.returncode != 0:
        raise PhoneError(proc.stderr.decode("utf-8", "replace").strip()
                         or "adb failed")
    return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")


def sh(command, root=False, timeout=ADB_TIMEOUT):
    """Run a shell command on the phone. -> stdout.

    root=True wraps it in `su -c`. Kept as one function rather than two so
    there is exactly one place where a command reaches the device, which is
    the place worth auditing."""
    if root:
        return _adb("shell", "su", "-c", command, timeout=timeout)
    return _adb("shell", command, timeout=timeout)


def has_root():
    """Does `su` actually grant root? Checked by asking who we are, not by
    looking for the binary - Magisk can be installed and still deny the
    request, and a denied su returns success with empty output."""
    try:
        out = sh("id", root=True, timeout=20)
    except PhoneError:
        return False
    return "uid=0" in out


def device_info():
    props = {}
    for line in sh("getprop").splitlines():
        m = re.match(r"\[([^\]]+)\]:\s*\[([^\]]*)\]", line.strip())
        if m:
            props[m.group(1)] = m.group(2)
    return {
        "model": props.get("ro.product.model"),
        "device": props.get("ro.product.device"),
        "android": props.get("ro.build.version.release"),
        "sdk": props.get("ro.build.version.sdk"),
        "security_patch": props.get("ro.build.version.security_patch"),
        "rooted": has_root(),
    }


# --- filesystem -----------------------------------------------------------

def ls(path, root=False):
    return sh(f"ls -la {_q(path)}", root=root)


def read_file(path, root=False, max_bytes=200_000):
    """Read a file off the phone, root-owned ones included."""
    out = sh(f"cat {_q(path)}", root=root)
    return out[:max_bytes]


def pull(remote, local_name=None):
    """Copy a file to the server. Root-owned paths are staged through
    /sdcard first, because `adb pull` itself runs unprivileged and would
    fail on anything outside the shell user's reach."""
    os.makedirs(PULL_DIR, exist_ok=True)
    name = local_name or os.path.basename(remote.rstrip("/")) or "pulled.bin"
    dest = os.path.join(PULL_DIR, name)
    staged = f"/sdcard/.aios_pull_{int(time.time())}"
    try:
        sh(f"cp {_q(remote)} {_q(staged)}", root=True)
        sh(f"chmod 644 {_q(staged)}", root=True)
        _adb("pull", staged, dest)
    finally:
        try:
            sh(f"rm -f {_q(staged)}", root=True)
        except PhoneError:
            pass
    return dest


def push(local, remote):
    if not os.path.isfile(local):
        raise PhoneError(f"no such local file: {local}")
    _adb("push", local, remote)
    return remote


# --- communications -------------------------------------------------------

def sms(limit=20):
    """Recent SMS. Root-only: the SMS database is not readable otherwise.

    Reads the content provider rather than the sqlite file directly - the
    file is locked while Android holds it open, and copying a live sqlite
    database is how you get a truncated read that looks like data."""
    out = sh(f"content query --uri content://sms/inbox "
             f"--projection address:date:body --sort 'date DESC' ", root=True)
    rows = []
    for line in out.splitlines():
        if "address=" not in line:
            continue
        entry = {}
        for field in ("address", "date", "body"):
            m = re.search(rf"{field}=(.*?)(?=,\s+\w+=|$)", line)
            if m:
                entry[field] = m.group(1).strip()
        if entry:
            rows.append(entry)
        if len(rows) >= limit:
            break
    return rows


def call_log(limit=20):
    out = sh(f"content query --uri content://call_log/calls "
             f"--projection number:date:duration:type --sort 'date DESC'", root=True)
    rows = []
    for line in out.splitlines():
        if "number=" not in line:
            continue
        entry = {}
        for field in ("number", "date", "duration", "type"):
            m = re.search(rf"{field}=(.*?)(?=,\s+\w+=|$)", line)
            if m:
                entry[field] = m.group(1).strip()
        rows.append(entry)
        if len(rows) >= limit:
            break
    return rows


def clipboard():
    """Only readable with root on modern Android - the clipboard is
    deliberately restricted to the focused app otherwise."""
    return sh("service call clipboard 2", root=True)


# --- apps and settings ----------------------------------------------------

def packages(third_party=True):
    flag = "-3" if third_party else ""
    return sorted(l.replace("package:", "").strip()
                  for l in sh(f"pm list packages {flag}").splitlines()
                  if l.startswith("package:"))


def app_info(package):
    _check_package(package)
    out = sh(f"dumpsys package {package}")
    version = re.search(r"versionName=(\S+)", out)
    installed = re.search(r"firstInstallTime=(.+)", out)
    return {
        "package": package,
        "version": version.group(1) if version else None,
        "installed": installed.group(1).strip() if installed else None,
        "permissions": re.findall(r"(android\.permission\.\w+): granted=true", out),
    }


def setting(namespace, key, value=None):
    """Read or write a system setting. namespace: system|secure|global."""
    if namespace not in ("system", "secure", "global"):
        raise PhoneError("namespace must be system, secure or global")
    if not re.fullmatch(r"[\w.]+", key or ""):
        raise PhoneError(f"invalid setting key: {key!r}")
    if value is None:
        return sh(f"settings get {namespace} {key}").strip()
    sh(f"settings put {namespace} {key} {_q(str(value))}", root=True)
    return sh(f"settings get {namespace} {key}").strip()


# --- capture --------------------------------------------------------------

def screenshot(name=None):
    os.makedirs(os.path.join(STATE_DIR, "screenshots"), exist_ok=True)
    data = _adb("exec-out", "screencap", "-p", binary=True)
    if not data.startswith(b"\x89PNG"):
        raise PhoneError("screencap did not return a PNG")
    path = os.path.join(STATE_DIR, "screenshots",
                        name or f"vayu_{int(time.time())}.png")
    with open(path, "wb") as f:
        f.write(data)
    return path


def record(seconds=10, name=None):
    """Screen recording. Capped: screenrecord's own limit is 180s and an
    unbounded call would block the caller for minutes."""
    seconds = max(1, min(int(seconds), 180))
    remote = f"/sdcard/.aios_rec_{int(time.time())}.mp4"
    sh(f"screenrecord --time-limit {seconds} {remote}",
       timeout=seconds + 45)
    os.makedirs(PULL_DIR, exist_ok=True)
    dest = os.path.join(PULL_DIR, name or os.path.basename(remote))
    _adb("pull", remote, dest)
    sh(f"rm -f {remote}")
    return dest


# --- dangerous, gated -----------------------------------------------------

def uninstall(package, confirm=False):
    _check_package(package)
    _require_confirm("uninstall", confirm)
    return sh(f"pm uninstall --user 0 {package}")


def wipe_package_data(package, confirm=False):
    _check_package(package)
    _require_confirm("wipe_package_data", confirm)
    return sh(f"pm clear {package}")


def remove_file(path, confirm=False):
    _require_confirm("remove_file", confirm)
    return sh(f"rm -f {_q(path)}", root=True)


def reboot(mode=None, confirm=False):
    """mode: None (normal), 'recovery', or 'bootloader'. Normal reboot needs
    no confirmation - it costs a minute. The other two drop him somewhere he
    has to get out of by hand."""
    if mode in ("recovery", "bootloader"):
        _require_confirm(f"reboot_{mode}", confirm)
        return _adb("reboot", mode, check=False)
    return _adb("reboot", check=False)


# --- networking -----------------------------------------------------------

def enable_tcpip(port=5555):
    """Make adbd listen on TCP so the cable becomes unnecessary. Binds all
    interfaces, tailnet included."""
    out = _adb("tcpip", str(int(port)), timeout=25, check=False)
    return out.decode() if isinstance(out, bytes) else out


def tailnet_address():
    """The phone's own tailnet IP, if Tailscale is installed on it."""
    for iface in ("tailscale0", "tun0"):
        try:
            out = sh(f"ip -4 addr show {iface}")
        except PhoneError:
            continue
        m = re.search(r"inet (100\.[\d.]+)", out)
        if m:
            return m.group(1)
    return None


# --- helpers --------------------------------------------------------------

def _q(value):
    """Single-quote for the phone's shell. Everything that reaches `adb
    shell` is re-parsed by a shell on the device, so a path with a space or a
    semicolon is not a formatting problem, it is a command injection."""
    return "'" + str(value).replace("'", "'\\''") + "'"


def _check_package(package):
    if not re.fullmatch(r"[\w.]+", package or ""):
        raise PhoneError(f"invalid package name: {package!r}")


def _require_confirm(action, confirm):
    if not confirm:
        raise PhoneError(
            f"{action} is destructive and needs confirm=True. Felix can call "
            f"it directly; it is gated so unattended automation cannot reach "
            f"it by accident.")


def notifications():
    """-> [{"package", "title", "text"}] currently on the shade.

    Root matters here: `dumpsys notification --noredact` only returns the
    actual message text to a privileged caller. Unprivileged, the interesting
    fields come back redacted, which produces a list of packages with no
    content - technically a notification list, useless for deciding whether
    something needs attention.

    Parses defensively: dumpsys formats for humans and the layout shifts
    between Android versions. This is triage, not a mail client, so a missing
    field is worth less than a crash."""
    try:
        out = sh("dumpsys notification --noredact", root=True)
    except PhoneError:
        return []
    found, current = [], None
    for line in out.splitlines():
        line = line.strip()
        m = re.search(r"pkg=([\w.]+)", line)
        if m and "NotificationRecord" in line:
            if current and (current["title"] or current["text"]):
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
    if current and (current["title"] or current["text"]):
        found.append(current)
    # An ongoing notification is re-posted on every update and appears many
    # times in one dump - a music player would otherwise fill the whole list.
    seen, unique = set(), []
    for n in found:
        key = (n["package"], n["title"], n["text"])
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique


def screen_on():
    m = re.search(r"mWakefulness=(\w+)", sh("dumpsys power"))
    return (m.group(1) if m else "").lower() == "awake"


def battery():
    info = {}
    for line in sh("dumpsys battery").splitlines():
        if ":" in line:
            k, _, v = line.strip().partition(":")
            info[k.strip()] = v.strip()
    return {
        "level": int(info["level"]) if info.get("level", "").isdigit() else None,
        "charging": info.get("AC powered") == "true" or info.get("USB powered") == "true",
    }


def current_app():
    m = re.search(r"(?:mResumedActivity|topResumedActivity).*?\{[^}]*?\s([\w.]+)/",
                  sh("dumpsys activity activities"))
    return m.group(1) if m else None


# --- input ----------------------------------------------------------------
# These were missing entirely until the device panel's buttons were tried
# against a real phone: this module was built around filesystem, SMS and
# settings access, and simply never got the input verbs the unrooted module
# already had. Nothing in the code failed - the functions just were not there.

# Every input verb runs as ROOT, and that is not incidental. MIUI blocks event
# injection from the adb shell user - `input keyevent` returns
# "SecurityException: Injecting input events requires INJECT_EVENTS" - the same
# family of restriction that blocks adb app installs on this ROM. Through `su`
# it works. Verified live 2026-09-01: identical command, denied as shell,
# accepted as root, screen went from Asleep to Awake. This is one of the few
# places where rooting this phone buys a capability outright rather than just
# more convenience.
KEYS = {"back": 4, "home": 3, "recents": 187, "power": 26, "enter": 66,
        "volume_up": 24, "volume_down": 25, "wake": 224, "sleep": 223,
        "menu": 82, "delete": 67, "tab": 61, "search": 84}


def tap(x, y):
    sh(f"input tap {int(x)} {int(y)}", root=True)
    return True


def swipe(x1, y1, x2, y2, ms=300):
    sh(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(ms)}", root=True)
    return True


def key(name):
    if name not in KEYS:
        raise PhoneError(f"unknown key {name!r}; known: {', '.join(sorted(KEYS))}")
    sh(f"input keyevent {KEYS[name]}", root=True)
    return True


def type_text(text):
    """`input text` cannot take a raw space, and an unescaped one silently
    truncates the rest of the string rather than erroring. Quoted through the
    same _q() the rest of this module uses, so a semicolon in the text is a
    character and not a command on the device."""
    if not text:
        return False
    sh("input text " + _q(text.replace(" ", "%s")), root=True)
    return True


def open_app(package):
    """Launch by package. monkey rather than `am start`: it resolves the
    launcher activity itself, so the caller does not need to know the activity
    name for every app."""
    _check_package(package)
    sh(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", root=True)
    return True


def screen_size():
    """-> (width, height) in device pixels, or None.

    Needed to map a tap on a scaled screenshot back to real coordinates: the
    web client shows the screen at whatever width the phone browser gives it,
    and a tap at 40% across has to become 40% of 1080, not 40% of the CSS
    width."""
    m = re.search(r"Physical size:\s*(\d+)x(\d+)", sh("wm size"))
    return (int(m.group(1)), int(m.group(2))) if m else None


def status():
    info = device_info()
    info["battery"] = battery()
    info["screen_on"] = screen_on()
    info["current_app"] = current_app()
    info["tailnet"] = tailnet_address()
    return info


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("packages")
    sub.add_parser("tcpip")
    sub.add_parser("sms")
    sub.add_parser("calls")
    c = sub.add_parser("sh"); c.add_argument("command"); c.add_argument("--root", action="store_true")
    r = sub.add_parser("read"); r.add_argument("path"); r.add_argument("--root", action="store_true")
    p = sub.add_parser("pull"); p.add_argument("remote")
    s = sub.add_parser("screenshot"); s.add_argument("--name")
    v = sub.add_parser("record"); v.add_argument("--seconds", type=int, default=10)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "status":
            print(json.dumps(status(), ensure_ascii=False, indent=2))
        elif args.cmd == "packages":
            print("\n".join(packages()))
        elif args.cmd == "tcpip":
            print(enable_tcpip())
        elif args.cmd == "sms":
            print(json.dumps(sms(), ensure_ascii=False, indent=2))
        elif args.cmd == "calls":
            print(json.dumps(call_log(), ensure_ascii=False, indent=2))
        elif args.cmd == "sh":
            print(sh(args.command, root=args.root))
        elif args.cmd == "read":
            print(read_file(args.path, root=args.root))
        elif args.cmd == "pull":
            print(pull(args.remote))
        elif args.cmd == "screenshot":
            print(screenshot(args.name))
        elif args.cmd == "record":
            print(record(args.seconds))
    except PhoneError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
