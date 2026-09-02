#!/usr/bin/env python3
"""Request handlers for the AI-OS web client. Every handler returns
(http_status, json_serializable_payload) - server.py owns all HTTP mechanics,
this file only ever touches the data.

Every dashboard handler is a live read through the SAME functions the CLI
tools already use (money_board.py, dmarc_prospector.py, flip_log.py) -
nothing here re-implements scoring, ranking, or table parsing. If a number
looks wrong here, the fix belongs in that module, not in this one - see the
approved plan (~/.claude/plans/virtual-tumbling-locket.md) for why that
separation matters.

The chat handler builds a task file the exact same way dispatch_task.py does
(read that file if this one is ever unclear) and blocks on the result the
same way - single user, one message in flight, no reason for anything
fancier.
"""
import concurrent.futures
import threading
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import agents
import claude_chat
import conversation_store
import cost_board
import engines
import gemini_chat
import knowledge_store
import memory
import money_board
import dmarc_prospector
import flip_log
import notifications
import safety_controls
import phone
import phone_root
import phone_stream
import pico
import proposals
import shared_briefing
import snipe_rank
import study_agent
import vault_write
import watch_health

TASK_RUNNER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
LOGS = os.path.join(TASK_RUNNER_DIR, "tasks", "logs")
CHAT_TIMEOUT_S = 170  # stays under the 180s dispatch_task.py/telegram_bridge.py already use
UPLOAD_DIR = os.path.join(TASK_RUNNER_DIR, "uploads")
# Passed to voice_import.py explicitly rather than letting it fall back to
# its own default. Its default is the same directory, so this changes nothing
# in production - but it makes the destination something a caller can point
# elsewhere, and a test that could not do that wrote a profile built from
# fixture data straight into the live one.
VOICE_DIR = os.path.join(TASK_RUNNER_DIR, "voice")
# A WhatsApp export without media is a few hundred KB of text; 25 MB is
# already generous. The cap exists because this endpoint reads the body into
# memory before writing it - server.py refuses on Content-Length before any
# of it is read, so an oversized POST costs nothing.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# Deliberately narrow: the only thing this is for is getting chat exports and
# similar plain data onto the server. Anything executable or web-servable
# would be a genuinely different feature with genuinely different questions
# to answer first.
ALLOWED_UPLOAD_EXT = (".txt", ".zip", ".csv", ".json", ".md",
                      # Photos: needed both for sending a design reference and
                      # for the photo-to-notes path (Felix does not type notes
                      # on his phone, he photographs slides and boards).
                      ".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf")
UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ ()\u00c0-\u024f-]")


# --- phone ---------------------------------------------------------------

# Notification packages that are never worth surfacing: system plumbing and
# persistent media controls. An assistant that reports "Android System" and a
# paused Spotify track as things needing attention teaches you to ignore it.
PHONE_NOISE = {
    "android", "com.android.systemui", "com.android.settings",
    "com.miui.securitycenter", "com.miui.powerkeeper", "com.xiaomi.misettings",
    "com.google.android.gms", "com.android.providers.downloads",
    "com.spotify.music", "com.miui.player", "com.google.android.apps.youtube.music",
}


def get_phone(_body):
    """Live state of the rooted phone: battery, foreground app, notifications
    worth seeing.

    Degrades rather than fails. The phone is frequently unreachable - out of
    the house on mobile data with the tailnet asleep, rebooted since the last
    `adb tcpip`, or simply off - and none of that should make the home screen
    show an error. Unreachable is a normal state for a phone, not a fault."""
    try:
        state = phone_root.status()
    except Exception as e:  # noqa: BLE001 - see docstring
        return 200, {"reachable": False, "reason": str(e)[:160]}

    try:
        notes = phone_root.notifications()
    except Exception:  # noqa: BLE001
        notes = []
    signal = [n for n in notes if n.get("package") not in PHONE_NOISE]
    return 200, {
        "reachable": True,
        "battery": state.get("battery"),
        "screen_on": state.get("screen_on"),
        "current_app": state.get("current_app"),
        "notifications": signal[:12],
        "notification_total": len(notes),
        "filtered": len(notes) - len(signal),
    }


# --- compute nodes -------------------------------------------------------

NODES_DIR = os.path.join(TASK_RUNNER_DIR, "nodes")
JOBS_DIR = os.path.join(TASK_RUNNER_DIR, "jobs")
# A node that has not checked in for this long is treated as gone. Two minutes
# rather than seconds: a laptop lid closes, a wifi switches, and neither of
# those should mark it dead while a job is still running on it.
NODE_STALE_S = 120


def _nodes_state():
    os.makedirs(NODES_DIR, exist_ok=True)
    out = []
    now = time.time()
    for name in os.listdir(NODES_DIR):
        if not name.endswith(".json"):
            continue
        data = _load_json(os.path.join(NODES_DIR, name))
        if not data:
            continue
        seen = data.get("last_seen", 0)
        data["online"] = (now - seen) < NODE_STALE_S
        data["seen_ago"] = int(now - seen)
        out.append(data)
    return sorted(out, key=lambda n: (not n["online"], n.get("id", "")))


def post_node_register(body):
    """A compute node checking in. Also serves as its heartbeat.

    The node connects OUT to the server rather than the server reaching in.
    That is deliberate: a laptop moves between networks, sleeps, and goes to
    university, and none of that should require inbound connectivity, a port
    forward, or a working VPN. It also means this keeps working the moment
    Tailscale is sorted out, without changing anything here."""
    body = body or {}
    node_id = (body.get("id") or "").strip()
    if not re.fullmatch(r"[\w-]{1,40}", node_id):
        return 400, {"error": "invalid node id"}
    os.makedirs(NODES_DIR, exist_ok=True)
    record = {
        "id": node_id,
        "label": str(body.get("label") or node_id)[:60],
        "os": str(body.get("os") or "")[:60],
        "cpu": str(body.get("cpu") or "")[:80],
        "cores": body.get("cores"),
        "ram_gb": body.get("ram_gb"),
        "capabilities": [str(c)[:30] for c in (body.get("capabilities") or [])][:20],
        "last_seen": time.time(),
    }
    path = os.path.join(NODES_DIR, f"{node_id}.json")
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return 200, {"ok": True, "node": node_id}


def get_nodes(_body):
    return 200, {"nodes": _nodes_state()}


def post_job_claim(body):
    """A node asking for work. -> one job, or nothing.

    Claiming renames the file, which on a POSIX filesystem is atomic - two
    nodes racing for the same job cannot both win, without needing a lock or a
    database."""
    body = body or {}
    node_id = (body.get("id") or "").strip()
    if not re.fullmatch(r"[\w-]{1,40}", node_id):
        return 400, {"error": "invalid node id"}
    caps = set(body.get("capabilities") or [])
    queued = os.path.join(JOBS_DIR, "queued")
    running = os.path.join(JOBS_DIR, "running")
    for d in (queued, running):
        os.makedirs(d, exist_ok=True)

    for name in sorted(os.listdir(queued)):
        if not name.endswith(".json"):
            continue
        job = _load_json(os.path.join(queued, name))
        need = job.get("needs")
        # A job that needs a capability this node lacks is left for one that
        # has it, rather than failing on the wrong machine.
        if need and need not in caps:
            continue
        try:
            os.rename(os.path.join(queued, name), os.path.join(running, name))
        except OSError:
            continue  # another node got it first
        job["claimed_by"] = node_id
        job["claimed_at"] = time.time()
        with open(os.path.join(running, name), "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False)
        return 200, {"job": job}
    return 200, {"job": None}


def post_job_result(body):
    """A node returning a finished job."""
    body = body or {}
    job_id = (body.get("job_id") or "").strip()
    if not re.fullmatch(r"[\w.-]{1,80}\.json", job_id):
        return 400, {"error": "invalid job_id"}
    running = os.path.join(JOBS_DIR, "running", job_id)
    done_dir = os.path.join(JOBS_DIR, "done")
    os.makedirs(done_dir, exist_ok=True)
    job = _load_json(running) or {"id": job_id}
    job.update({
        "finished_at": time.time(),
        "ok": bool(body.get("ok")),
        "output": str(body.get("output") or "")[:20000],
    })
    with open(os.path.join(done_dir, job_id), "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    if os.path.exists(running):
        os.remove(running)
    return 200, {"ok": True}


def post_node_run(body):
    """Queue a shell command for one node and return a ticket.

    This is remote access to Felix's laptop through the web client. It is
    genuinely that - an arbitrary command on his own machine, behind his own
    token, on his own network. Worth being plain about rather than dressing
    up: whoever holds the token can run code on any online node.

    Queued rather than executed: the server never reaches into the laptop, the
    laptop asks for work. So this returns immediately with a ticket and the
    client polls, which also means a command survives the laptop being asleep
    - it runs when the machine comes back rather than failing now."""
    body = body or {}
    node = (body.get("node") or "").strip()
    command = (body.get("command") or "").strip()
    if not re.fullmatch(r"[\w-]{1,40}", node):
        return 400, {"error": "invalid node"}
    if not command:
        return 400, {"error": "kein Befehl"}

    known = {n["id"]: n for n in _nodes_state()}
    if node not in known:
        return 400, {"error": f"unbekannter Knoten: {node}"}
    if not known[node]["online"]:
        return 400, {"error": f"{node} ist offline (zuletzt vor "
                              f"{known[node]['seen_ago']}s gesehen)"}

    job_id = f"run_{node}_{int(time.time() * 1000)}.json"
    queued = os.path.join(JOBS_DIR, "queued")
    os.makedirs(queued, exist_ok=True)
    job = {
        "id": job_id,
        "kind": "shell",
        # Pinned to the node Felix picked. Without this the job would go to
        # whichever node claimed it first, and "run this on the laptop" would
        # sometimes silently run on the server.
        "needs": node,
        "payload": {"command": command,
                    "timeout": min(int(body.get("timeout") or 300), 900)},
        "queued_at": time.time(),
    }
    tmp = os.path.join(queued, job_id + ".part")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(queued, job_id))
    return 200, {"ok": True, "job_id": job_id}


def get_node_result(body):
    """Collect a queued command's output, or report that it is still waiting."""
    job_id = ((body or {}).get("job_id") or "").strip()
    if not re.fullmatch(r"[\w.-]{1,80}\.json", job_id):
        return 400, {"error": "invalid job_id"}
    done = os.path.join(JOBS_DIR, "done", job_id)
    if os.path.exists(done):
        job = _load_json(done)
        return 200, {"ready": True, "ok": job.get("ok"),
                     "output": job.get("output", ""),
                     "node": job.get("claimed_by")}
    running = os.path.exists(os.path.join(JOBS_DIR, "running", job_id))
    queued = os.path.exists(os.path.join(JOBS_DIR, "queued", job_id))
    if not running and not queued:
        return 200, {"ready": False, "lost": True,
                     "error": "Job nicht mehr auffindbar"}
    return 200, {"ready": False, "state": "läuft" if running else "wartet"}


# --- device control ------------------------------------------------------

SCREENSHOT_DIR = os.path.join(TASK_RUNNER_DIR, "phone", "screenshots")

# Two phones, two capability levels. The module is what differs - everything
# below is written against whichever one this table names, so adding a third
# device is a row here rather than a branch everywhere.
DEVICES = {
    "poco": {"label": "Poco X3 Pro", "module": phone_root, "rooted": True},
    "nothing": {"label": "Nothing Phone 2a", "module": phone, "rooted": False},
    # Listed before it is reachable, on purpose. An absent row would read as
    # "not supported"; a row that says why it is offline reads as "one cable
    # away", which is what it is - see scripts/pico_setup.sh.
    "pico": {"label": "Pico 4", "module": pico, "rooted": False,
             "extra": {"install"}},
}

# A panel is an at-a-glance view; waiting longer than this for a phone that
# is probably asleep makes the whole screen feel broken.
# Raised from 9s once the probes themselves dropped from ~6s to under a
# second, then lowered again once the panel stopped waiting for it: the client
# opens on what it already knew and corrects itself when this lands, so the
# deadline is now only about how long a phone gets to answer, not about how
# long anyone stares at a blank screen.
DEVICE_PROBE_S = 8

# Actions the panel may perform, in four groups.
#
# An allowlist, not a passthrough. The request body reaches a device with
# root, and "whatever the client sent" is not an acceptable definition of
# what may run there - so every verb is named here or it does not exist.
#
# The grouping is what decides which phone may do what. The Nothing Phone has
# no root, so the ROOT_ACTIONS simply are not possible there and are refused
# with a reason rather than attempted and failed with a stack trace.
BASE_ACTIONS = {"screenshot", "tap", "swipe", "key", "text", "open", "status",
                "notifications", "apps", "stream_start", "stream_stop"}
# Root-only because dismissing the keyguard needs it. Listed separately from
# the read verbs because it is the one thing that makes live control usable at
# all - see phone_root.unlock().
ROOT_ACTIONS = {"info", "sms", "calls", "clipboard", "ls", "read", "pull",
                "shell", "setting", "record", "app_info", "unlock"}
# Verbs that can cost Felix the device or its data. Present, because it is his
# phone and he asked for a toolkit without restrictions - but each one has to
# arrive with confirm=true, which the UI only sends after a second, explicit
# press. That gate lives in phone_root.py itself; this set is what tells the
# panel to render the second press at all.
DANGEROUS_ACTIONS = {"uninstall", "rm", "reboot", "wipe"}
# Verbs a single device has that the others do not - sideloading an APK is
# the whole point of a headset and meaningless on a phone Felix carries.
EXTRA_ACTIONS = {"install"}
DEVICE_ACTIONS = BASE_ACTIONS | ROOT_ACTIONS | DANGEROUS_ACTIONS | EXTRA_ACTIONS

# A shell command from the panel is interactive - Felix is watching it. A long
# one belongs in the task queue, not in a request a phone browser is holding
# open.
DEVICE_SHELL_TIMEOUT_S = 25
# Screen recording blocks the request for its whole duration, so the web path
# caps it well below phone_root.record()'s own 180s limit. Longer recordings
# are still available from the CLI.
MAX_RECORD_S = 15
DEVICE_LIST_LIMIT = 200


def _device(name):
    entry = DEVICES.get(name)
    if not entry:
        raise ValueError(f"unknown device: {name!r}")
    return entry


# A phone's resolution does not change, and asking for it costs an adb round
# trip against a device that is usually busy carrying video by then. Measured
# consequence of not caching it: the stream request sat behind a `wm size`
# call and the panel said "verbinde…" for tens of seconds.
_SIZE_CACHE = {}


def device_size(entry):
    key = entry["label"]
    if key not in _SIZE_CACHE:
        size = entry["module"].screen_size()
        if not size:
            return None
        _SIZE_CACHE[key] = size
    return _SIZE_CACHE[key]


def _device_serial(entry):
    """The adb serial for a device, asked of the module that owns it.

    phone.py resolves its own serial at runtime (it scans for a moved adb
    port and remembers what it found), so reading a module constant would be
    wrong for exactly the case that module exists to handle."""
    mod = entry["module"]
    getter = getattr(mod, "_active_serial", None)
    if callable(getter):
        try:
            return getter()
        except Exception:  # noqa: BLE001 - fall through to the constant
            pass
    return getattr(mod, "DEVICE", None) or getattr(mod, "SERIAL", None)


def get_devices(_body):
    """Every device and whether it is currently reachable.

    Each is probed independently and a failure is reported per device: one
    phone being off must not blank the panel for the other."""
    def probe(item):
        key, entry = item
        row = {"id": key, "label": entry["label"], "rooted": entry["rooted"]}
        try:
            state = entry["module"].status()
            # From the same round trip status() already made. A separate
            # screen_size() call doubled the probe cost for a number that
            # arrives free with everything else.
            size = state.get("size") or entry["module"].screen_size()
            row.update({
                "reachable": True,
                "battery": state.get("battery"),
                "screen_on": state.get("screen_on"),
                "current_app": state.get("current_app"),
                "width": size[0] if size else None,
                "height": size[1] if size else None,
                "actions": sorted(BASE_ACTIONS | entry.get("extra", set()) | (
                    ROOT_ACTIONS | DANGEROUS_ACTIONS if entry["rooted"] else set())),
            })
        except Exception as e:  # noqa: BLE001 - a device being away is normal
            row.update({"reachable": False, "reason": str(e)[:140]})
        return row

    # Probed in parallel AND on a deadline. Sequentially, one sleeping phone
    # hitting its 40s adb timeout held the whole panel hostage; in parallel the
    # total is still the slowest device, which was the same 40 seconds. For a
    # panel, a phone that has not answered in a few seconds is simply away -
    # that is a more useful answer than a correct one nobody waited for.
    #
    # A stale adb entry is the specific case this catches: the daemon reports
    # `device` while every shell command times out, so nothing looks wrong
    # until the whole request hangs.
    out, pending = [], {}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(DEVICES) or 1)
    try:
        for item in DEVICES.items():
            pending[pool.submit(probe, item)] = item[0]
        for fut in concurrent.futures.as_completed(pending, timeout=DEVICE_PROBE_S):
            try:
                out.append(fut.result())
            except Exception as e:  # noqa: BLE001
                out.append({"id": pending[fut], "reachable": False,
                            "reason": str(e)[:140]})
    except concurrent.futures.TimeoutError:
        pass
    finally:
        # Not waited on: a hung adb call would otherwise keep the request open
        # for its full timeout anyway, which is the thing being avoided.
        pool.shutdown(wait=False, cancel_futures=True)

    answered = {r["id"] for r in out}
    for key, entry in DEVICES.items():
        if key not in answered:
            out.append({"id": key, "label": entry["label"],
                        "rooted": entry["rooted"], "reachable": False,
                        "reason": f"keine Antwort in {DEVICE_PROBE_S}s"})
    return 200, {"devices": sorted(out, key=lambda r: (not r["reachable"], r["id"]))}


def _keep_for_download(src, prefix):
    """Move a file the phone produced into the Downloads list.

    Everything pulled off a phone lands where the Dateien tab already looks,
    rather than in a directory only the CLI knows about - a file Felix cannot
    reach from the app he pulled it with is not really pulled."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    name = safe_upload_name(f"{prefix}_{os.path.basename(src)}")
    dest = os.path.join(DOWNLOADS_DIR, name)
    n = 1
    stem, ext = os.path.splitext(dest)
    while os.path.exists(dest):
        dest = f"{stem}_{n}{ext}"
        n += 1
    os.replace(src, dest)
    return {"name": os.path.basename(dest), "url": f"/downloads/{os.path.basename(dest)}",
            "size": os.path.getsize(dest)}


def post_device_action(body):
    """Perform one allowlisted action on one device."""
    body = body or {}
    action = (body.get("action") or "").strip()
    if action not in DEVICE_ACTIONS:
        return 400, {"error": f"unknown action: {action!r}"}
    try:
        entry = _device((body.get("device") or "").strip())
    except ValueError as e:
        return 400, {"error": str(e)}
    mod = entry["module"]
    extra = entry.get("extra", set())
    if action in extra:
        pass       # a verb this device has and the others do not
    elif action in (ROOT_ACTIONS | DANGEROUS_ACTIONS) and not entry["rooted"]:
        return 200, {"ok": False,
                     "error": f"{entry['label']} hat kein root - '{action}' geht dort nicht"}

    def _num(name, default=None):
        try:
            return int(body.get(name))
        except (TypeError, ValueError):
            return default

    def _str(name):
        return (body.get(name) or "").strip()

    confirm = bool(body.get("confirm"))

    try:
        if action == "status":
            return 200, {"ok": True, "status": mod.status()}

        if action == "screenshot":
            path = mod.screenshot()
            size = mod.screen_size()
            # A cache-busting name, because the browser would otherwise show
            # the previous screen after every refresh - which looks exactly
            # like a frozen phone.
            return 200, {"ok": True,
                         "url": f"/device-screen/{os.path.basename(path)}",
                         "width": size[0] if size else None,
                         "height": size[1] if size else None}

        # --- live video ---------------------------------------------------
        if action == "stream_start":
            size = device_size(entry)
            serial = _device_serial(entry)
            enc = phone_stream.encode_size(size[0] if size else None,
                                           size[1] if size else None)
            phone_stream.get(serial, size=enc)
            return 200, {"ok": True, "serial": serial, "encode_size": enc,
                         "width": size[0] if size else None,
                         "height": size[1] if size else None}
        if action == "stream_stop":
            phone_stream.stop(_device_serial(entry))
            return 200, {"ok": True}

        # --- reading ------------------------------------------------------
        if action == "notifications":
            notes = mod.notifications()
            return 200, {"ok": True, "notifications": notes[:60],
                         "total": len(notes)}
        if action == "apps":
            names = (mod.packages(third_party=True) if entry["rooted"]
                     else mod.installed_apps())
            return 200, {"ok": True, "apps": sorted(names)[:DEVICE_LIST_LIMIT],
                         "total": len(names)}
        if action == "info":
            return 200, {"ok": True, "info": mod.device_info(),
                         "root": mod.has_root()}
        if action == "app_info":
            return 200, {"ok": True, "app": mod.app_info(_str("package"))}
        if action == "sms":
            return 200, {"ok": True, "messages": mod.sms(limit=_num("limit", 20))}
        if action == "calls":
            return 200, {"ok": True, "calls": mod.call_log(limit=_num("limit", 20))}
        if action == "install":
            return 200, {"ok": True, "output": mod.install(_str("path"))}
        if action == "unlock":
            mod.unlock()
            return 200, {"ok": True}
        if action == "clipboard":
            return 200, {"ok": True, "clipboard": mod.clipboard()}
        if action == "ls":
            path = _str("path") or "/sdcard"
            return 200, {"ok": True, "path": path,
                         "entries": mod.ls(path, root=bool(body.get("root")))[:DEVICE_LIST_LIMIT]}
        if action == "read":
            return 200, {"ok": True,
                         "text": mod.read_file(_str("path"), root=bool(body.get("root")))}
        if action == "pull":
            local = mod.pull(_str("path"))
            return 200, {"ok": True, "file": _keep_for_download(local, entry["id"])}
        if action == "record":
            secs = max(1, min(_num("seconds", 8) or 8, MAX_RECORD_S))
            local = mod.record(seconds=secs)
            return 200, {"ok": True, "file": _keep_for_download(local, entry["id"])}
        if action == "shell":
            cmd = _str("command")
            if not cmd:
                return 400, {"error": "shell braucht ein command"}
            out = mod.sh(cmd, root=bool(body.get("root")),
                         timeout=DEVICE_SHELL_TIMEOUT_S)
            return 200, {"ok": True, "output": out}
        if action == "setting":
            value = body.get("value")
            return 200, {"ok": True,
                         "value": mod.setting(_str("namespace") or "system",
                                              _str("key"),
                                              value if value not in (None, "") else None)}

        # --- destructive, each needs its own confirm ----------------------
        if action == "uninstall":
            return 200, {"ok": True, "output": mod.uninstall(_str("package"), confirm=confirm)}
        if action == "wipe":
            return 200, {"ok": True,
                         "output": mod.wipe_package_data(_str("package"), confirm=confirm)}
        if action == "rm":
            return 200, {"ok": True, "output": mod.remove_file(_str("path"), confirm=confirm)}
        if action == "reboot":
            return 200, {"ok": True, "output": mod.reboot(_str("mode") or None, confirm=confirm)}

        # --- input --------------------------------------------------------
        if action == "tap":
            x, y = _num("x"), _num("y")
            if x is None or y is None:
                return 400, {"error": "tap needs x and y"}
            mod.tap(x, y)
        elif action == "swipe":
            coords = [_num(k) for k in ("x1", "y1", "x2", "y2")]
            if any(c is None for c in coords):
                return 400, {"error": "swipe needs x1,y1,x2,y2"}
            mod.swipe(*coords, ms=_num("ms") or 300)
        elif action == "key":
            mod.key(_str("key"))
        elif action == "text":
            value = body.get("text") or ""
            if not value:
                return 400, {"error": "text is empty"}
            mod.type_text(value[:500])
        elif action == "open":
            mod.open_app(_str("package"))
        return 200, {"ok": True}
    except Exception as e:  # noqa: BLE001 - surface the device's own message
        return 200, {"ok": False, "error": str(e)[:400]}


# --- snipes --------------------------------------------------------------

SNIPE_LIMIT = 60


def get_snipes(body):
    """Sniper finds, ranked into tiers, with filters.

    The tier is a TRIAGE order - which listing to open first - and explicitly
    not a valuation. LocalArbitrage's Valuation_Method.md opens with its own
    rule in bold: "AI does not estimate resale prices. Sold listings do." A
    tier here says "look at this before the others", never "this is worth more
    than it costs"; the resale number still comes from sold comps, by hand.
    Every score ships with the reasons that produced it, because a ranking
    Felix cannot audit is one he is right not to trust."""
    body = body or {}
    tier = body.get("tier") or None
    if isinstance(tier, str):
        tier = [t for t in tier.split(",") if t.strip()]

    def _int(name):
        value = body.get(name)
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    rows = snipe_rank.rank(
        watch=body.get("watch") or None,
        tier=tier,
        max_price=_int("max_price"),
        max_distance=_int("max_distance"),
        limit=min(_int("limit") or SNIPE_LIMIT, SNIPE_LIMIT),
    )
    counts = {}
    everything = snipe_rank.rank()
    for row in everything:
        counts[row["tier"]] = counts.get(row["tier"], 0) + 1

    # Per category, because "how are the snipes doing" is really five
    # questions. A watch with forty finds and no S tier is a different
    # problem from one with no finds at all, and the second is usually not a
    # market - see watch_health.py.
    health = {h["watch"]: h for h in watch_health.report()}
    by_watch = {}
    for row in everything:
        name = row.get("watch") or "?"
        agg = by_watch.setdefault(name, {"watch": name, "finds": 0, "tiers": {},
                                         "best": None, "cheapest": None})
        agg["finds"] += 1
        agg["tiers"][row["tier"]] = agg["tiers"].get(row["tier"], 0) + 1
        if agg["best"] is None or row.get("score", 0) > agg["best"].get("score", 0):
            agg["best"] = {"title": row.get("title"), "tier": row["tier"],
                           "price": row.get("price"), "url": row.get("url"),
                           "score": row.get("score", 0)}
        price = row.get("price")
        if price is not None and (agg["cheapest"] is None or price < agg["cheapest"]):
            agg["cheapest"] = price
    # Every configured watch appears, including the ones with nothing to show:
    # an empty category is exactly the case worth seeing.
    for name in snipe_rank.watches():
        by_watch.setdefault(name, {"watch": name, "finds": 0, "tiers": {},
                                   "best": None, "cheapest": None})
    for name, agg in by_watch.items():
        row = health.get(name) or {}
        agg["status"] = row.get("status", "unknown")
        agg["last_listings"] = row.get("last_listings")
        agg["consecutive_zero"] = row.get("consecutive_zero", 0)
        agg["hours_since_ok"] = row.get("hours_since_ok")

    order = {"blind": 0, "stale": 1, "quiet": 2, "ok": 3, "unknown": 4}
    return 200, {
        "snipes": rows,
        "watches": snipe_rank.watches(),
        # Unfiltered tier totals, so the filter chips can show what exists
        # rather than what survived the current filter.
        "tier_counts": counts,
        "total": sum(counts.values()),
        "by_watch": sorted(by_watch.values(),
                           key=lambda a: (order.get(a["status"], 9), -a["finds"])),
        "health_problems": [h["watch"] for h in watch_health.problems()],
    }


# --- vault ---------------------------------------------------------------

VAULT = vault_write.VAULT
# Bounded on purpose. These are read by MCP clients whose whole cost model is
# tokens: an unbounded grep over 280+ vault files would hand a model tens of
# thousands of tokens of context to answer "what is the DMARC project", which
# is both expensive and worse than a focused answer.
VAULT_MAX_HITS = 20
VAULT_SNIPPET_CHARS = 240
VAULT_MAX_PAGE_CHARS = 20_000
# Folders that are machine state or vendored code, not knowledge. Searching
# them returns noise (node_modules) or churn (task logs) and buries the notes.
VAULT_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "backups", "tasks",
                   "uploads", "voice", "spend", "prospects", "study", "techscout"}


def _vault_files():
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in VAULT_SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name.endswith(".md"):
                yield os.path.join(root, name)


def get_vault_search(body):
    """Keyword search across the vault's Markdown. -> ranked hits with
    snippets.

    Reads the real files rather than Notion. The existing AI-OSmcp server
    queried Notion, which is a copy: everything that actually matters now -
    the money board, the leads, the flip log, proposals - lives in files here
    and was never in Notion at all. A search that answers from the copy would
    confidently describe a system that no longer exists."""
    query = (body.get("query") or "").strip()
    if len(query) < 2:
        return 400, {"error": "query must be at least 2 characters"}
    limit = min(int(body.get("limit") or VAULT_MAX_HITS), VAULT_MAX_HITS)
    needle = query.lower()
    hits = []
    for path in _vault_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        low = text.lower()
        count = low.count(needle)
        if not count:
            continue
        where = low.find(needle)
        start = max(0, where - VAULT_SNIPPET_CHARS // 3)
        snippet = text[start:start + VAULT_SNIPPET_CHARS].replace("\n", " ").strip()
        hits.append({
            "page": os.path.relpath(path, VAULT),
            "matches": count,
            "snippet": ("..." if start else "") + snippet + "...",
        })
    # Most matches first: a page that mentions the term twenty times is
    # almost always the page about it, and a title match is worth more than
    # a passing mention, so exact-name hits get pushed to the top.
    hits.sort(key=lambda h: (needle in os.path.basename(h["page"]).lower(),
                             h["matches"]), reverse=True)
    return 200, {"query": query, "total": len(hits), "hits": hits[:limit]}


def get_vault_page(body):
    """One page's full Markdown, by vault-relative path or bare name."""
    name = (body.get("page") or "").strip()
    if not name:
        return 400, {"error": "page is required"}
    # Same containment check vault_write.py uses for writes: resolve first,
    # then verify the result is still inside the vault, so "../../.ssh/id_rsa"
    # cannot be read back through an endpoint meant for notes.
    candidates = []
    direct = os.path.realpath(os.path.join(VAULT, name))
    if direct.startswith(os.path.realpath(VAULT) + os.sep) and os.path.isfile(direct):
        candidates.append(direct)
    if not candidates:
        stem = name.lower().removesuffix(".md")
        for path in _vault_files():
            if os.path.basename(path).lower().removesuffix(".md") == stem:
                candidates.append(path)
                break
    if not candidates:
        return 404, {"error": f"no vault page matching {name!r}"}
    try:
        with open(candidates[0], encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        return 500, {"error": str(e)}
    truncated = len(text) > VAULT_MAX_PAGE_CHARS
    return 200, {
        "page": os.path.relpath(candidates[0], VAULT),
        "truncated": truncated,
        "content": text[:VAULT_MAX_PAGE_CHARS],
    }


# --- today ---------------------------------------------------------------

def _load_json(path):
    """Never raises: a missing or half-written state file means that one
    signal is unknown, not that the home screen fails to render."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _sniper_state():
    """Last sniper run and how many ads it has ever flagged. Never raises -
    a missing state file means the sniper has not run, not that the home
    screen is broken."""
    state = _load_json(os.path.join(TASK_RUNNER_DIR, "watches", "state.json"))
    alerted = state.get("alerted") or {}
    return {
        "last_run": state.get("last_run"),
        "alerted": len(alerted) if isinstance(alerted, (dict, list)) else 0,
    }


def get_today(_body):
    """Everything the home screen shows, in one request.

    One endpoint rather than five: this is the first screen on a phone, and
    five round trips over a tailnet is the difference between "instant" and
    "loading". Every field is a live read through the same modules the CLI
    uses - nothing here keeps its own copy of anything.

    Every section degrades on its own. A broken flip log must not blank the
    money board next to it, because the home screen is the one view that has
    to be trustworthy at a glance."""
    signals = money_board.live_signals()
    actions = money_board.sorted_actions()
    top = actions[0] if actions else None

    try:
        review = proposals.load_review() or {}
        pending_proposals = len(review.get("items") or [])
    except Exception:  # noqa: BLE001 - optional signal, never fatal
        pending_proposals = 0

    try:
        study_pending = study_agent.pending_count()
    except Exception:  # noqa: BLE001
        study_pending = 0

    return 200, {
        "next_action": None if not top else {
            "action": top[1], "euros": top[2], "minutes": top[3],
            "note": top[4], "gates": top[0] == "felix-first",
        },
        "open_actions": len(actions),
        "signals": signals,
        "proposals_pending": pending_proposals,
        "study_pending": study_pending,
        "sniper": _sniper_state(),
    }


# --- dashboards --------------------------------------------------------

def get_money_board(_body):
    # money_board.sorted_actions() owns the ordering - gating rows first,
    # then euros descending. This handler used to re-implement the sort
    # (`sorted(felix_actions(), key=-euros)`), which was itself the fix for a
    # real bug where it did not sort at all; keeping a second copy of the rule
    # here meant the dashboard silently disagreed with the CLI the moment the
    # rule changed. One function, three callers.
    actions = [
        {"action": action, "euros": euros, "minutes": minutes, "note": note,
         "gates": who == "felix-first"}
        for who, action, euros, minutes, note in money_board.sorted_actions()
    ]
    return 200, {"actions": actions, "signals": money_board.live_signals()}


def get_dmarc_leads(_body):
    domains = dmarc_prospector._load(dmarc_prospector.DOMAINS_PATH, {})
    results = dmarc_prospector._load(dmarc_prospector.RESULTS_PATH, {})
    # 100, not the CLI's default 5 - a dashboard has room to scroll a real
    # list; the top-5 default belongs to the terse morning-brief message, not
    # a screen built to be looked at directly.
    top = dmarc_prospector.rank(results, domains, limit=100)
    leads = [{
        "domain": result["domain"],
        "name": (entry or {}).get("name", result["domain"]),
        "category": (entry or {}).get("category"),
        "score": result.get("score"),
        "dmarc": result.get("dmarc"),
        "spf": result.get("spf"),
        "provider": result.get("provider"),
        "address": (entry or {}).get("address"),
        "phone": (entry or {}).get("phone"),
    } for result, entry in top]
    total_qualified = sum(1 for r in results.values() if r.get("score", 0) >= 6)
    return 200, {"leads": leads, "total_qualified": total_qualified}


def get_flip_log(_body):
    rows = flip_log.read_log()
    for row in rows:
        row["open"] = not bool(row.get("Sold €"))
    return 200, {"rows": rows}


DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "static", "downloads")


def get_downloads(_body):
    """Files the worker generated for Felix to pull down - PDFs from a chat
    request most commonly, per how this was actually asked for ("let the
    workers pull data and create pdfs i can download"). Served by
    server.py's existing static-file path (already path-traversal-tested)
    at /downloads/<name> - this endpoint only lists what's there, it does
    not serve the bytes itself."""
    try:
        names = [n for n in os.listdir(DOWNLOADS_DIR) if not n.startswith(".")]
    except OSError:
        names = []
    files = []
    for name in names:
        full = os.path.join(DOWNLOADS_DIR, name)
        try:
            stat = os.stat(full)
        except OSError:
            continue
        files.append({
            "name": name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "url": f"/downloads/{name}",
        })
    files.sort(key=lambda f: f["modified"], reverse=True)
    return 200, {"files": files}


# --- uploads -------------------------------------------------------------

def safe_upload_name(raw):
    """-> a filename that can only ever land directly in UPLOAD_DIR.

    basename() first so "../../.ssh/authorized_keys" becomes
    "authorized_keys", then the extension allowlist, then a character scrub.
    Order matters: checking the extension before stripping directories would
    happily accept "../../x.txt"."""
    name = os.path.basename((raw or "").strip().replace("\\", "/"))
    # Strips leading dots and surrounding spaces (no hidden files, no
    # trailing-space names) but NOT underscores: iOS names every WhatsApp
    # export literally "_chat.txt", and silently renaming his files is a
    # confusing thing for an upload button to do.
    name = UNSAFE_NAME_RE.sub("_", name).strip(" ").lstrip(".")
    if not name or len(name) > 120:
        return None
    if not name.lower().endswith(ALLOWED_UPLOAD_EXT):
        return None
    return name


def _unique_path(name):
    """Never silently overwrite. Four WhatsApp exports can arrive as four
    files called "_chat.txt" - iOS names every single one of them that -
    and losing three of them to the fourth would be invisible until the
    voice profile came out built on a quarter of the data."""
    base, ext = os.path.splitext(name)
    candidate, n = name, 2
    while os.path.exists(os.path.join(UPLOAD_DIR, candidate)):
        candidate = f"{base}_{n}{ext}"
        n += 1
    return os.path.join(UPLOAD_DIR, candidate), candidate


def post_upload(query, raw):
    """Raw request body -> one file in uploads/.

    Deliberately not multipart/form-data: this client is the only thing that
    will ever call this endpoint, so there is no interop reason to hand-roll
    a multipart parser (the stdlib's cgi module, which used to do it, was
    removed in Python 3.13 - this service runs 3.14). One file per request,
    filename in the query string, bytes in the body. The frontend loops."""
    name = safe_upload_name((query.get("name") or [""])[0])
    if not name:
        return 400, {"error": "invalid or unsupported filename "
                              f"(allowed: {', '.join(ALLOWED_UPLOAD_EXT)})"}
    if not raw:
        return 400, {"error": "empty file"}
    if len(raw) > MAX_UPLOAD_BYTES:
        return 413, {"error": "file too large"}
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path, final_name = _unique_path(name)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, path)  # atomic, same reason dispatch_task.py does it
    return 200, {"name": final_name, "size": len(raw)}


def get_uploads(_body):
    try:
        names = [n for n in os.listdir(UPLOAD_DIR)
                 if not n.startswith(".") and not n.endswith(".part")]
    except OSError:
        names = []
    files = []
    for name in names:
        try:
            stat = os.stat(os.path.join(UPLOAD_DIR, name))
        except OSError:
            continue
        files.append({
            "name": name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        })
    files.sort(key=lambda f: f["modified"], reverse=True)
    # No download URL, unlike get_downloads: these are Felix's own private
    # chat exports. He uploaded them, he has them - re-serving them over
    # HTTP would add exposure for no use.
    return 200, {"files": files}


def post_voice_import(_body):
    """Rebuild the voice profile from every .txt currently in uploads/.

    Runs voice_import.py as a subprocess rather than importing it: it is a
    CLI tool with its own argument handling, and a crash in a chat-export
    parser must not be able to take the web server down with it. Fixed argv,
    never a shell string. No model is involved - this is pure parsing and
    arithmetic, so it costs nothing and cannot hallucinate a profile."""
    try:
        txts = sorted(os.path.join(UPLOAD_DIR, n) for n in os.listdir(UPLOAD_DIR)
                      if n.lower().endswith(".txt"))
    except OSError:
        txts = []
    if len(txts) < 2:
        return 400, {"error": "Mindestens 2 Chat-Exporte nötig - aus einem "
                              "einzigen Chat wird das Profil eine Karikatur "
                              "einer Beziehung, nicht deine Stimme."}
    script = os.path.join(TASK_RUNNER_DIR, "scripts", "voice_import.py")
    try:
        proc = subprocess.run([sys.executable, script] + txts
                              + ["--out", VOICE_DIR],
                              capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return 500, {"error": "Import hat zu lange gebraucht"}
    if proc.returncode != 0:
        return 400, {"error": (proc.stderr or "Import fehlgeschlagen").strip()[:500]}
    return 200, {"files": len(txts), "output": proc.stdout.strip()}


# --- chat ----------------------------------------------------------------

def post_chat(body):
    message = (body.get("message") or "").strip()
    thread_id = (body.get("thread_id") or "").strip()
    if not message:
        return 400, {"error": "message is required"}
    if not thread_id:
        return 400, {"error": "thread_id is required"}

    # Same @agent-prefix convention telegram_bridge.py already uses: an
    # unresolved leading word is left alone rather than treated as a failed
    # agent selection, so "@felix should I..." stays a normal sentence.
    agent = None
    if message.startswith("@"):
        head, _, rest = message.partition(" ")
        resolved = agents.resolve(head)
        if resolved:
            agent, message = resolved, rest.strip()
    if not message:
        return 400, {"error": "no message text after the @agent prefix"}

    # Every user turn, on every channel, before it is dispatched anywhere -
    # see shared_briefing.py's module docstring for why.
    shared_briefing.record_event("web-chat", message, engine="aios")

    # `web_` prefix on the client-generated id keeps this namespace distinct
    # from Telegram's `tg_<chat_id>` threads on disk - two front doors, never
    # the same conversation by accident.
    memory_thread = f"web_{thread_id}"
    body_text = (memory.directive(memory_thread)
                + (agents.directive(agent) if agent else "")
                + message)

    for d in (INBOX, LOGS):
        os.makedirs(d, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"task_web_{timestamp}.md"
    task_path = os.path.join(INBOX, filename)
    log_path = os.path.join(LOGS, f"{filename}.log")

    tmp_path = f"{task_path}.part"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(body_text)
    os.replace(tmp_path, task_path)  # atomic enqueue, same reason dispatch_task.py does this

    # Returns immediately with a ticket instead of holding the connection open
    # until the worker finishes.
    #
    # Why this changed: a real message on 2026-09-01 took 93 seconds to answer.
    # The worker produced a perfectly good reply and wrote it to its log - and
    # Felix saw "failed to fetch", because a phone browser does not keep a
    # request open that long. Screen off, app backgrounded, or a network switch
    # and the fetch dies. The answer existed and was unreachable, which is the
    # worst of both outcomes.
    #
    # Polling also makes the reply survive a reload: the ticket is the task
    # filename, so a client that comes back later can still collect it.
    return 200, {"task_id": filename, "pending": True, "agent": agent}


def get_chat_result(body):
    """Collect a queued chat reply. -> pending, ready, or failed.

    Deliberately reports elapsed seconds: the client shows it, so a slow model
    reads as "still thinking, 40s" rather than as a frozen app. That ambiguity
    is what made the old behaviour feel broken."""
    task_id = (body or {}).get("task_id") or ""
    # The ticket becomes a filesystem path, so it is validated as a plain
    # task filename and nothing else.
    if not re.fullmatch(r"task_web_[\w.-]{1,60}\.md", task_id):
        return 400, {"error": "invalid task_id"}

    log_path = os.path.join(LOGS, f"{task_id}.log")
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            return 200, {"ready": True, "reply": f.read().strip()}

    queued = os.path.join(INBOX, task_id)
    running = os.path.join(TASK_RUNNER_DIR, "tasks", "completed", task_id)
    if not os.path.exists(queued) and not os.path.exists(running):
        # Neither waiting, nor finished, nor recorded as done: the task is
        # gone. Saying so beats polling forever against a task that will
        # never produce a log.
        return 200, {"ready": False, "lost": True,
                     "error": "Task nicht mehr auffindbar"}

    try:
        age = int(time.time() - os.path.getmtime(queued if os.path.exists(queued)
                                                 else running))
    except OSError:
        age = 0
    return 200, {"ready": False, "elapsed": age,
                 "timed_out": age > CHAT_TIMEOUT_S}


# --- costs ---------------------------------------------------------------

def get_costs(_body):
    """What the whole thing costs. See cost_board.py for why the two halves
    are reported separately and only one of them is a bill.

    The subscription allowances are NOT in here - they cost seconds, and the
    screen should not wait on them to show a balance it already knows."""
    return 200, cost_board.board()


def get_provider_limits(_body):
    """What is left per provider. Slow on purpose: it asks each account."""
    return 200, {"providers": cost_board.provider_limits()}


# --- Claude Code sessions ------------------------------------------------
#
# The other chat. api.post_chat above talks to the local worker; this talks to
# a real Claude Code session and continues it, which is what Felix asked for:
# the same conversation he has at the desk, carried on from his phone. See
# claude_chat.py for the permission decision behind it.

def get_claude_sessions(_body):
    return 200, {"sessions": claude_chat.list_sessions(limit=15)}


def get_claude_transcript(body):
    body = body or {}
    session_id = (body.get("session_id") or "").strip()
    if not session_id:
        # No session named: the most recent one, which is what "immer vom
        # letzten genutzten chat" asks for - open the app and you are where
        # you left off, without choosing anything.
        recent = claude_chat.list_sessions(limit=1)
        if not recent:
            return 200, {"messages": [], "session_id": None,
                         "error": "keine Claude-Sitzungen gefunden"}
        session_id = recent[0]["id"]
    try:
        limit = int(body.get("limit") or 14)
    except (TypeError, ValueError):
        limit = 14
    try:
        return 200, claude_chat.transcript(session_id, limit=max(4, min(limit, 400)))
    except (ValueError, FileNotFoundError) as e:
        return 400, {"error": str(e)}


def post_claude_send(body):
    body = body or {}
    message = body.get("message") or ""
    shared_briefing.record_event("web-claude", message, engine="claude")
    try:
        job_id = claude_chat.send((body.get("session_id") or "").strip(), message,
                                  model=(body.get("model") or None))
    except ValueError as e:
        return 400, {"error": str(e)}
    return 200, {"job_id": job_id, "pending": True}


def get_claude_result(body):
    try:
        return 200, claude_chat.result(((body or {}).get("job_id") or "").strip())
    except ValueError as e:
        return 400, {"error": str(e)}


# --- proposals: the accept/decline gate, on a screen ----------------------
#
# The propose/approve gate has existed since the agents got the ability to
# suggest work, and until now the only way to say yes was a Telegram message
# reading "approve 1 3". That is a fine interface for a phone notification
# and a poor one for deciding: the proposals scroll away, the numbers have to
# be counted, and there is no way to see what was already decided. Same
# lifecycle underneath - proposals.py owns it, and dispatch() is shared with
# the bridge so an approval means exactly one thing either way.

def get_proposals(_body):
    review = proposals.load_review()
    return 200, {
        "review": [{"n": i, "agent": p.get("agent", "worker"),
                    "kind": p.get("kind", "human"), "text": p.get("text", ""),
                    "created": p.get("created", "")}
                   for i, p in enumerate(review, 1)],
        # Waiting for the next review round rather than decidable now. Shown
        # as a count, because the point of the nightly round is that Felix is
        # not asked about things one at a time as they occur to an agent.
        "pending": len(proposals.load(proposals.PENDING_PATH)),
        "todos": [{"n": i, "agent": t.get("agent", "worker"),
                   "text": t.get("text", ""), "added": t.get("added", "")}
                  for i, t in enumerate(proposals.load_todos(), 1)],
    }


def post_proposal_decide(body):
    """Accept or decline one proposal."""
    body = body or {}
    approve = bool(body.get("approve"))
    item, error = proposals.decide_one(body.get("index"), approve)
    if error:
        return 400, {"error": error}
    queued = proposals.dispatch([item]) if approve else 0
    return 200, {"ok": True, "approved": approve, "queued": queued,
                 "kind": item.get("kind", "human"), "text": item.get("text", "")}


def post_proposal_open(_body):
    """Move everything pending into a decidable round.

    The evening job does this at 20:00; this is for the other twenty-three
    hours, when something has been proposed and Felix wants to look at it
    now rather than wait to be asked."""
    opened = proposals.open_review()
    return 200, {"ok": True, "opened": len(opened)}


def post_todo_done(body):
    done, error = proposals.complete_todo(str((body or {}).get("index", "")))
    if error:
        return 400, {"error": error}
    return 200, {"ok": True, "done": [d.get("text", "") for d in done]}


# --- engines: four things that can answer -----------------------------------
#
# The chat used to be wired to one of them. On 2026-09-02 Felix wrote twice
# from his phone and got "You've hit your session limit · resets 11:30am"
# both times - three hours of nothing from a machine with three other engines
# idle on it. engines.py is the switch; this is its front door.

def get_engines(_body):
    return 200, {"engines": engines.catalogue()}


def post_engine_send(body):
    body = body or {}
    engine = (body.get("engine") or "claude").strip()
    message = body.get("message") or ""
    conversation_id = (body.get("conversation_id") or "").strip() or None
    # Before dispatch, unconditionally - see shared_briefing.py.
    shared_briefing.record_event("web-engine", message, engine=engine)
    try:
        ticket = engines.send(
            engine, message,
            model=(body.get("model") or None),
            thread=(body.get("thread") or None),
            session=(body.get("session") or None),
            conversation_id=conversation_id)
    except ValueError as e:
        return 400, {"error": str(e)}
    return 200, {"pending": True, **ticket}


def post_engine_result(body):
    body = body or {}
    try:
        return 200, engines.result(
            (body.get("engine") or "").strip(),
            (body.get("job") or "").strip(),
            conversation_id=(body.get("conversation_id") or "").strip() or None)
    except ValueError as e:
        return 400, {"error": str(e)}


def post_background_task(body):
    """Same engine dispatch as post_engine_send, plus a server-side watcher so
    the completion is there even if the browser that started it never polls
    again - the whole reason Felix asked for this being that a background
    task is supposed to be exactly that: started, then left alone."""
    body = body or {}
    engine = (body.get("engine") or "claude").strip()
    if engine not in engines.ENGINES:
        return 400, {"error": f"unbekannte Engine: {engine!r}"}
    message = (body.get("message") or "").strip()
    if not message:
        return 400, {"error": "message is required"}
    conversation_id = (body.get("conversation_id") or "").strip() or None
    if conversation_id and not conversation_store.exists(conversation_id):
        return 400, {"error": f"unbekannte conversation_id: {conversation_id!r}"}
    if not conversation_id:
        try:
            conversation_id = conversation_store.create(engine, title=message)
        except ValueError as e:
            return 400, {"error": str(e)}
    shared_briefing.record_event("background-task", message, engine=engine)
    try:
        ticket = engines.send(engine, message, conversation_id=conversation_id)
    except ValueError as e:
        return 400, {"error": str(e)}
    notifications.watch_job(ticket["engine"], ticket["job"],
                            conversation_id=conversation_id,
                            preview=message[:120])
    return 200, {"pending": True, "background": True, **ticket}


def get_notifications(body):
    unread_only = bool((body or {}).get("unread_only"))
    limit = min(int((body or {}).get("limit") or 50), 200)
    return 200, {"notifications": notifications.list_notifications(
        unread_only=unread_only, limit=limit)}


def post_notification_read(body):
    ok = notifications.mark_read((body or {}).get("id"))
    if not ok:
        return 400, {"error": "unbekannte notification id"}
    return 200, {"ok": True}


def post_knowledge_save(body):
    """The manual half of knowledge capture - the automatic half runs after
    every successful engine reply, see engines._record_conversation(). Both
    end up in the same store with the same source references."""
    body = body or {}
    conversation_id = (body.get("conversation_id") or "").strip() or None
    if not conversation_id:
        return 400, {"error": "conversation_id is required"}
    if not conversation_store.exists(conversation_id):
        return 400, {"error": f"unbekannte conversation_id: {conversation_id!r}"}
    record = conversation_store.read(conversation_id)
    text = body.get("text")
    saved = knowledge_store.save(conversation_id, record.get("engine"),
                                 text=(text.strip() if isinstance(text, str) and text.strip()
                                       else None))
    return 200, {"ok": True, "saved": saved}


# --- conversations: one picker across all four engines ----------------------

def post_conversations(body):
    """list / create / read, all through one endpoint and one action field -
    three tiny handlers were not worth three routes for what is, underneath,
    one small store. See conversation_store.py for the persistence itself."""
    body = body or {}
    action = (body.get("action") or "").strip()
    engine = (body.get("engine") or "").strip() or None

    if action == "list":
        return 200, {"conversations": conversation_store.list_conversations(
            engine=engine, limit=min(int(body.get("limit") or 50), 200))}

    if action == "create":
        if not engine:
            return 400, {"error": "engine is required"}
        if engine not in engines.ENGINES:
            return 400, {"error": f"unbekannte Engine: {engine!r}"}
        try:
            conversation_id = conversation_store.create(
                engine, title=(body.get("title") or "").strip() or None)
        except ValueError as e:
            return 400, {"error": str(e)}
        return 200, {"conversation": conversation_store.read(conversation_id)}

    if action == "read":
        conversation_id = (body.get("conversation_id") or "").strip()
        if not conversation_id:
            return 400, {"error": "conversation_id is required"}
        record = conversation_store.read(conversation_id)
        if not record:
            return 404, {"error": f"unbekannte conversation_id: {conversation_id!r}"}
        return 200, {"conversation": record}

    return 400, {"error": f"unbekannte action: {action!r} (list|create|read)"}


def get_gemini_thread(body):
    """Google keeps its own conversation, so it can be re-read like Claude's.

    Without this, switching engines would look like the history had been
    thrown away - it had not, it just lives somewhere else."""
    turns = gemini_chat.load_thread(((body or {}).get("thread") or "web").strip())
    return 200, {"messages": [{"role": "user" if t["role"] == "user" else "assistant",
                               "text": t.get("text", ""), "ts": t.get("ts"),
                               "tool": False}
                              for t in turns],
                 "total_messages": len(turns)}
