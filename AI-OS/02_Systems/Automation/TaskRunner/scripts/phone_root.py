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


def _adb(*args, timeout=ADB_TIMEOUT, binary=False, check=True):
    cmd = ["adb", "-s", DEVICE, *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise PhoneError("adb is not installed")
    except subprocess.TimeoutExpired:
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


def status():
    info = device_info()
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
