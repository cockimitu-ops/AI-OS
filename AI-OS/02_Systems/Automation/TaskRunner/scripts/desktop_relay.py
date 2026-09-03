#!/usr/bin/env python3
"""Small, bounded relay between AIOS viewers and Felix's laptop agent.

The laptop only makes outbound HTTP requests.  This module stores one latest
frame and a short allowlisted input queue; it never opens a port on Windows.
"""
import collections
import os
import threading
import time


TASK_RUNNER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(TASK_RUNNER_DIR, "phone", "screenshots")
FRAME_PATH = os.path.join(SCREENSHOT_DIR, "desktop_laptop.jpg")
MAX_FRAME_BYTES = 5 * 1024 * 1024
MAX_ACTIONS = 64
ONLINE_S = 8.0
FRAME_FRESH_S = 12.0
CAPTURE_GRACE_S = 4.0

_lock = threading.Lock()
_actions = collections.deque(maxlen=MAX_ACTIONS)
_last_poll = 0.0
_last_frame = 0.0
_width = 0
_height = 0
_demand_until = 0.0
_next_action_id = 1


def _online(now=None):
    return (now or time.monotonic()) - _last_poll <= ONLINE_S


def status():
    with _lock:
        if not _online():
            _actions.clear()
            raise RuntimeError("Laptop-Agent ist nicht verbunden")
        return {"size": (_width, _height) if _width and _height else None,
                "screen_on": True, "current_app": "Windows Desktop"}


def screen_size():
    with _lock:
        return (_width, _height) if _width and _height else None


def screenshot():
    global _demand_until
    with _lock:
        now = time.monotonic()
        if not _online(now):
            _actions.clear()
            raise RuntimeError("Laptop-Agent ist nicht verbunden")
        _demand_until = max(_demand_until, now + CAPTURE_GRACE_S)
        path, fresh = FRAME_PATH, now - _last_frame <= FRAME_FRESH_S
    if not fresh or not os.path.isfile(path):
        raise RuntimeError("Laptop-Bild ist noch nicht verfügbar")
    return path


def stream_start():
    global _demand_until
    with _lock:
        if not _online():
            raise RuntimeError("Laptop-Agent ist nicht verbunden")
        _demand_until = max(_demand_until, time.monotonic() + CAPTURE_GRACE_S)


def stream_stop():
    global _demand_until
    with _lock:
        _demand_until = 0.0
        _actions.clear()


def _queue(action, **fields):
    global _next_action_id, _demand_until
    with _lock:
        now = time.monotonic()
        if not _online(now):
            _actions.clear()
            raise RuntimeError("Laptop-Agent ist nicht verbunden")
        item = {"id": _next_action_id, "action": action, **fields}
        _next_action_id += 1
        _actions.append(item)
        _demand_until = max(_demand_until, now + CAPTURE_GRACE_S)
        return item["id"]


def tap(x, y, button="left", clicks=1):
    return _queue("tap", x=x, y=y, button=button, clicks=clicks)


def swipe(x1, y1, x2, y2, ms=300):
    return _queue("swipe", x1=x1, y1=y1, x2=x2, y2=y2, ms=ms)


def scroll(dy, x=None, y=None):
    return _queue("scroll", dy=dy, x=x, y=y)


def key(value):
    return _queue("key", key=value)


def type_text(value):
    return _queue("text", text=value)


def poll():
    global _last_poll
    with _lock:
        now = time.monotonic()
        _last_poll = now
        batch = list(_actions)
        _actions.clear()
        return {"actions": batch, "capture": now < _demand_until,
                "width": _width or None, "height": _height or None}


def accept_frame(raw, width, height):
    global _last_frame, _width, _height
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError("leeres Bild")
    if len(raw) > MAX_FRAME_BYTES:
        raise ValueError("Bild ist zu groß")
    if not (raw.startswith(b"\xff\xd8\xff") and raw.endswith(b"\xff\xd9")):
        raise ValueError("nur vollständige JPEG-Bilder werden angenommen")
    width, height = int(width), int(height)
    if not (1 <= width <= 16384 and 1 <= height <= 16384):
        raise ValueError("ungültige Bildgröße")
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    tmp = f"{FRAME_PATH}.tmp.{threading.get_ident()}"
    with open(tmp, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, FRAME_PATH)
    with _lock:
        _width, _height = width, height
        _last_frame = time.monotonic()
    return {"ok": True}


def reset_for_test():
    global _last_poll, _last_frame, _width, _height, _demand_until
    with _lock:
        _actions.clear()
        _last_poll = _last_frame = _demand_until = 0.0
        _width = _height = 0
