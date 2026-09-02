#!/usr/bin/env python3
"""Live H.264 screen streaming from an Android device, served as MJPEG.

WHY THIS EXISTS

The device panel used to work by taking a screenshot, waiting for it, and
showing it - one still picture per interaction. Measured on the real phones
over the tailnet on 2026-09-01:

    adb shell "input tap x y"      0.16 s
    screencap -p + adb pull        1.10 - 1.40 s

So the tap was never the slow part. The *picture* was. Every button press
cost more than a second of staring at a dimmed old frame, which is what
Felix meant by "die direkte fernsteuerung ist mir zu langsam".

WHAT REPLACES IT

`screenrecord --output-format=h264` writes a raw H.264 elementary stream to
stdout. adb streams it over the tailnet, ffmpeg decodes it and re-encodes to
MJPEG, and the browser shows that in a plain <img> via
multipart/x-mixed-replace. Measured on the Nothing Phone, 720x1600 at 4 Mbit:
116 frames in 8 seconds - about 15 fps at 227 KB/s. A static screen costs
almost nothing (a 10-second recording of a sleeping display was 287 bytes),
because H.264 spends bits only on what actually changes.

WHY FRAGMENTED MP4 IS THE DEFAULT, AND MJPEG THE FALLBACK

Transcoding was the wrong job for this machine. crypton is a Celeron N4000:
two cores at 1.1 GHz. Decoding the phone's H.264 and re-encoding it to MJPEG
measured 82% of a core and 4.0 MB/s of output, and it could not keep up with
the phone - which is what turns into latency, because a pipeline that runs
slower than its input accumulates a queue.

Remuxing does no decoding at all. The same H.264 is repackaged into fragmented
MP4 (`-c:v copy`) and the browser hardware-decodes it through Media Source
Extensions. Measured against the same phone and the same motion:

    transcode -> MJPEG    4061 KB/s    ~82% CPU
    remux     -> fMP4      437 KB/s    ~30% CPU

Nine times less over the tailnet, on a phone that has a video decoder in
silicon while the server does not.

MJPEG stays as the fallback for a browser without MSE, and as the thing that
still works if the codec string ever stops matching.

WHY NOT WebCodecs

Feeding the H.264 to a WebCodecs VideoDecoder would be lower latency still
and would skip ffmpeg entirely - but WebCodecs requires a secure context, and
this app is
served over plain HTTP on the tailnet because Tailscale HTTPS is not enabled
on Felix's account yet (the same reason crypto.randomUUID is missing on his
phone; see app.js). MJPEG in an <img> needs no secure context at all. If
HTTPS ever gets turned on, swapping the browser side to WebCodecs is a
localized change - this module's job, getting H.264 off the phone, stays. MSE, unlike
WebCodecs, has no secure-context requirement - which is the only reason the
fast path is available at all today.

LIFECYCLE

`screenrecord` has a hard 180-second limit and exits on its own. That is
handled by restarting it inside the same stream, so a viewer sees a
continuous picture and never has to know. A stream with no viewers shuts
itself down after IDLE_TIMEOUT_S rather than recording someone's phone
screen forever into a buffer nobody reads.

Stdlib only, plus adb and ffmpeg.
"""
import json
import os
import select
import shutil
import subprocess
import threading
import time

# JPEG frame delimiters. Both markers are safe to scan for in the raw byte
# stream: inside entropy-coded data every 0xFF byte is followed by 0x00 or a
# restart marker (0xD0-0xD7), so neither 0xFFD8 nor 0xFFD9 can appear except
# as an actual start/end of image.
SOI = b"\xff\xd8"
EOI = b"\xff\xd9"

# screenrecord's own ceiling. It exits when it hits this, so the stream
# restarts it - a few seconds short of the limit would only add pointless
# restarts, and going over is not possible.
SEGMENT_S = 180
# How long a stream stays alive with nobody watching. Long enough to survive
# a tab switch or a screen lock, short enough that a forgotten browser tab
# does not keep a camera on Felix's phone screen indefinitely.
IDLE_TIMEOUT_S = 20
# Target height of the encoded video. The width is derived from the device's
# real aspect ratio, so the picture is never stretched. Both are rounded to a
# multiple of 16: the AVC encoder wants macroblock-aligned dimensions and
# quietly produces garbage or refuses on some devices otherwise.
#
# 1200 rather than 1600 because it is measurably faster, not because it looks
# worse. Same phone, same harness, input to visible pixel:
#
#     720x1600   median 865ms   6 of 8 attempts registered at all
#     544x1200   median 507ms   8 of 8, best 129ms
#
# Half the pixels is less for the phone's encoder to chew through, and the
# encoder is where the remaining latency lives. SHARP_HEIGHT is there for
# reading small text, at the cost of those milliseconds.
DEFAULT_HEIGHT = 1200
SHARP_HEIGHT = 1600
BITRATE = "4M"
# MJPEG quality, 2 (best) to 31. 6 measured at ~45 KB per 720x1600 frame,
# which is the trade that keeps a phone screen readable without turning the
# tailnet link into the new bottleneck.
JPEG_Q = 6
# Frames per second actually sent. The phone encodes at its display rate;
# passing all of that through measured 4.8 MB/s, which is not a sensible
# thing to push at a phone browser. 12 is well past the point where remote
# control feels continuous rather than stepped.
FPS = 12
# A frame older than this means the pipeline is alive but nothing is coming
# through - a phone that went to sleep, or an encoder that stalled.
STALE_FRAME_S = 12


class StreamError(RuntimeError):
    pass


def _align16(n):
    return max(16, int(round(n / 16)) * 16)


def encode_size(width, height, target_height=DEFAULT_HEIGHT):
    """Encoder-safe WIDTHxHEIGHT preserving the device's aspect ratio.

    Never upscales: a device smaller than the target streams at its own
    resolution rather than being blown up and re-encoded for nothing."""
    if not width or not height:
        return f"{_align16(720)}x{_align16(target_height)}"
    h = min(int(target_height), int(height))
    w = _align16(int(width) * h / int(height))
    return f"{w}x{_align16(h)}"


class Stream:
    """One device's live picture. Thread-safe; one instance per device.

    Holds only the most recent frame, deliberately. A queue per viewer would
    make a slow phone browser fall progressively further behind real time,
    which for a remote control is worse than dropping frames - you want to
    see where the phone is NOW, not every frame it has ever drawn."""

    def __init__(self, serial, size=None, bitrate=BITRATE, fps=FPS,
                 quality=JPEG_Q, on_error=None):
        self.serial = serial
        self.size = size
        self.bitrate = bitrate
        self.fps = max(1, int(fps))
        self._min_gap = 1.0 / self.fps
        self.quality = quality
        self._on_error = on_error
        self._lock = threading.Condition()
        self._frame = None
        self._seq = 0
        self._frame_at = 0.0
        self._last_view = time.time()
        self._running = False
        self._error = None
        self._thread = None
        self._awake = False
        self._procs = []

    # --- public ----------------------------------------------------------

    def start(self):
        with self._lock:
            if self._running:
                self._last_view = time.time()
                return
            if not shutil.which("ffmpeg"):
                raise StreamError("ffmpeg ist nicht installiert")
            if not shutil.which("adb"):
                raise StreamError("adb ist nicht installiert")
            self._running = True
            self._error = None
            self._last_view = time.time()
        keep_awake_async(self.serial, True)
        self._awake = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False
            self._lock.notify_all()
        self._kill_procs()

    @property
    def error(self):
        return self._error

    def alive(self):
        return self._running

    def frames(self, timeout=STALE_FRAME_S):
        """Yield every new frame for as long as the stream lives.

        Marks the stream as watched on each iteration, which is what keeps
        the idle shutdown from firing under an active viewer."""
        last = -1
        while True:
            with self._lock:
                self._last_view = time.time()
                if not self._running and self._frame is None:
                    return
                if self._seq == last:
                    self._lock.wait(timeout)
                    if self._seq == last:
                        # Nothing arrived. A running-but-silent stream is
                        # normal (a still screen encodes to nothing), so this
                        # keeps waiting rather than ending the response -
                        # ending it would make the browser show a broken
                        # image for a phone that is merely idle.
                        if not self._running:
                            return
                        continue
                frame, last = self._frame, self._seq
            if frame:
                yield frame

    def latest(self):
        """The most recent frame, or None. For a still snapshot without
        opening a stream response."""
        with self._lock:
            self._last_view = time.time()
            return self._frame

    def idle_for(self):
        return time.time() - self._last_view

    # --- internals -------------------------------------------------------

    def _kill_procs(self):
        for p in self._procs:
            try:
                p.kill()
            except Exception:  # noqa: BLE001 - already dead is the normal case
                pass
        self._procs = []

    def _publish(self, jpeg):
        """Store a frame, at most self.fps of them per second.

        Dropped here rather than earlier: this is the last point before the
        frame would cross the network, and it is the only point that knows
        what time it actually is."""
        now = time.time()
        if self._frame is not None and now - self._frame_at < self._min_gap:
            return
        with self._lock:
            self._frame = jpeg
            self._seq += 1
            self._frame_at = now
            self._lock.notify_all()

    def _run(self):
        """Restart the capture as long as anyone is watching.

        Each pass is one `screenrecord` segment. It ends either because the
        180-second limit was reached (normal, restart immediately) or because
        something failed (record it, and back off so a phone that is simply
        away is not hammered)."""
        backoff = 0.5
        while True:
            with self._lock:
                if not self._running:
                    break
            if self.idle_for() > IDLE_TIMEOUT_S:
                break
            started = time.time()
            try:
                self._segment()
                backoff = 0.5
            except Exception as e:  # noqa: BLE001 - a phone going away is normal
                self._error = str(e)[:200]
                if self._on_error:
                    try:
                        self._on_error(e)
                    except Exception:  # noqa: BLE001
                        pass
                # Only back off on a *fast* failure. A segment that ran for a
                # while and then died is a live device that hiccuped, and
                # should come back at once.
                if time.time() - started < 5:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 8)
        with self._lock:
            self._running = False
            self._frame = None
            self._lock.notify_all()
        self._kill_procs()
        if self._awake:
            self._awake = False
            keep_awake_async(self.serial, False)

    def _segment(self):
        size = self.size or f"720x{DEFAULT_HEIGHT}"
        rec = subprocess.Popen(
            ["adb", "-s", self.serial, "exec-out", "screenrecord",
             "--output-format=h264", "--size", size,
             "--bit-rate", self.bitrate,
             "--time-limit", str(SEGMENT_S), "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Two flags here were found the hard way, both by measuring rather
        # than by reading:
        #
        #   -pix_fmt yuvj420p   ffmpeg 8 refuses to open the mjpeg encoder on
        #                       screenrecord's limited-range YUV at all
        #                       ("Non full-range YUV is non-standard"). The
        #                       whole pipeline started and produced nothing.
        #   NO -fflags nobuffer That flag looks exactly right for a live
        #                       stream and is what every low-latency recipe
        #                       reaches for. With it, this pipeline emitted
        #                       zero bytes for a full segment; without it the
        #                       first frame lands after 1.8s and it runs.
        #
        # The frame rate is capped in _publish, on the wall clock, NOT with
        # ffmpeg's `fps` filter. The filter works on presentation timestamps,
        # and a raw H.264 elementary stream carries none - ffmpeg assumes a
        # rate, and if that assumption is lower than the phone's real display
        # rate then every dropped frame is time the stream falls further
        # behind. Measured: `-vf fps=12` on a 120 Hz phone still delivered
        # 24.6 fps of wall-clock frames, because the filter was pacing a
        # timeline that had nothing to do with the present. A remote control
        # that drifts steadily into the past is worse than a slow one.
        #
        # passthrough leaves timestamps alone; the throttle downstream is
        # exact, and dropping a decoded frame costs only local CPU.
        ff = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-f", "h264", "-i", "pipe:0",
             "-fps_mode", "passthrough",
             "-pix_fmt", "yuvj420p", "-flush_packets", "1",
             "-f", "mjpeg", "-q:v", str(self.quality), "pipe:1"],
            stdin=rec.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Closing our copy lets ffmpeg see EOF when screenrecord ends, rather
        # than hanging on a pipe this process still holds open.
        rec.stdout.close()
        self._procs = [rec, ff]
        try:
            self._pump(ff.stdout)
        finally:
            self._kill_procs()
        err = b""
        try:
            err = rec.stderr.read() or b""
        except Exception:  # noqa: BLE001
            pass
        if not self._frame and err:
            raise StreamError(err.decode("utf-8", "replace").strip()[:200]
                              or "screenrecord lieferte kein Bild")

    def _pump(self, pipe):
        """Split ffmpeg's MJPEG byte stream into whole frames."""
        buf = bytearray()
        while True:
            with self._lock:
                if not self._running:
                    return
            if self.idle_for() > IDLE_TIMEOUT_S:
                return
            # read1, not read: a plain read(n) on a pipe blocks until it has
            # all n bytes, so a quiet screen would sit in the kernel buffer
            # instead of being delivered - the stream looked frozen for
            # exactly this reason on the first live test. read1 returns
            # whatever has already arrived.
            chunk = pipe.read1(65536)
            if not chunk:
                return
            buf += chunk
            while True:
                start = buf.find(SOI)
                if start < 0:
                    # No image has begun yet; anything before a start marker
                    # is not part of one and would only grow forever.
                    buf.clear()
                    break
                end = buf.find(EOI, start + 2)
                if end < 0:
                    del buf[:start]
                    break
                self._publish(bytes(buf[start:end + 2]))
                del buf[:end + 2]


# --- keeping the display on while someone is watching ---------------------

# Ten minutes. Long enough that a remote-control session is never interrupted,
# short enough that a forgotten restore is not a flat battery by morning.
AWAKE_TIMEOUT_MS = 600000
_awake_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "phone", "awake_state.json")
_awake_lock = threading.Lock()
_awake_refs = {}


# Short: this is housekeeping, and it runs while adb is already busy carrying
# video. A settings write that takes longer than this has lost anyway.
SETTINGS_TIMEOUT_S = 6


def _settings_get(serial, key):
    out = subprocess.run(["adb", "-s", serial, "shell", "settings", "get", "system", key],
                         capture_output=True, timeout=SETTINGS_TIMEOUT_S)
    return out.stdout.decode("utf-8", "replace").strip()


def _settings_put(serial, key, value, root=True):
    # Through `su` first: MIUI refuses some writes from the shell user, the
    # same restriction that blocks input injection there.
    cmd = f"settings put system {key} {value}"
    for attempt in ([f"su -c '{cmd}'"] if root else []) + [cmd]:
        try:
            subprocess.run(["adb", "-s", serial, "shell", attempt],
                           capture_output=True, timeout=SETTINGS_TIMEOUT_S)
            if _settings_get(serial, key) == str(value):
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


def _load_awake():
    try:
        with open(_awake_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_awake(state):
    try:
        os.makedirs(os.path.dirname(_awake_path), exist_ok=True)
        tmp = _awake_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, _awake_path)
    except OSError:
        pass


def keep_awake_async(serial, on):
    """keep_awake, off the caller's thread.

    Always used by the streams. It is three adb round trips against a device
    that is at that moment being asked for video, and blocking the start of a
    stream on housekeeping made the first picture arrive tens of seconds late
    - the panel just said "verbinde…" while nothing was wrong with the video
    at all."""
    threading.Thread(target=keep_awake, args=(serial, on), daemon=True).start()


def keep_awake(serial, on):
    """Hold the phone's display awake for as long as anyone is watching.

    Without this the remote control dies after a minute, and not for any
    reason the user can see: MIUI's screen timeout is 60 seconds, and
    KEYCODE_WAKEUP does NOT reset it - waking a device is not the same as
    using one. The display goes off, Android stops compositing, screenrecord
    stops producing frames, and the panel simply freezes mid-session.

    Reference-counted, because two viewers must not undo each other. The
    original value is written to disk before it is changed, so a webapp that
    dies mid-stream leaves a note behind rather than a phone whose screen
    never sleeps again - the next call repairs it."""
    with _awake_lock:
        state = _load_awake()
        if on:
            _awake_refs[serial] = _awake_refs.get(serial, 0) + 1
            if _awake_refs[serial] > 1:
                return
            previous = state.get(serial)
            if previous is None:
                previous = _settings_get(serial, "screen_off_timeout")
                if not previous or not previous.isdigit():
                    return
                state[serial] = previous
                _save_awake(state)
            if int(previous) < AWAKE_TIMEOUT_MS:
                _settings_put(serial, "screen_off_timeout", AWAKE_TIMEOUT_MS)
        else:
            _awake_refs[serial] = max(0, _awake_refs.get(serial, 0) - 1)
            if _awake_refs[serial]:
                return
            previous = state.pop(serial, None)
            if previous:
                _settings_put(serial, "screen_off_timeout", previous)
                _save_awake(state)


def repair_awake():
    """Restore any timeout a crashed process left raised. Called at startup."""
    state = _load_awake()
    for serial, previous in list(state.items()):
        if _settings_put(serial, "screen_off_timeout", previous):
            state.pop(serial, None)
    _save_awake(state)


_streams = {}
_streams_lock = threading.Lock()


def get(serial, size=None, fps=FPS, quality=JPEG_Q):
    """The running stream for a device, started if it is not."""
    with _streams_lock:
        st = _streams.get(serial)
        if st is None or not st.alive():
            st = Stream(serial, size=size, fps=fps, quality=quality)
            _streams[serial] = st
    st.start()
    return st


def stop(serial):
    with _streams_lock:
        st = _streams.pop(serial, None)
    if st:
        st.stop()


def stop_all():
    with _streams_lock:
        items = list(_streams.values())
        _streams.clear()
    for st in items:
        st.stop()


# --- fragmented MP4, for Media Source Extensions -------------------------

# Fragment per frame. A fragment is the smallest thing MSE can be handed, so
# anything coarser means the browser waits for frames it has already been
# sent - which is latency bought for nothing, since the overhead is about a
# hundred bytes of moof per frame.
MP4_MOVFLAGS = "+frag_every_frame+empty_moov+default_base_moof"
# What the timestamps are written as. The phone composites at whatever rate it
# feels like - measured about 28 fps under continuous scrolling - so this is a
# declaration, not a measurement, and it is deliberately BELOW the real rate.
# Stamped at 30 the player drained the buffer slightly faster than it filled
# and stalled every few seconds (readyState fell to 1 mid-measurement).
# Stamped low, the buffer grows instead, and the client trims it by seeking -
# drift in the safe direction costs nothing, drift in the other costs the
# picture.
NOMINAL_FPS = 24
# How long to wait for ffmpeg to describe the video, the FIRST time a device
# is ever streamed. After that the answer is remembered - a phone does not
# change its H.264 profile - and the wait disappears from the critical path
# entirely, which is what it deserved: it was costing four seconds of
# "verbinde…" before a single byte could be sent, on every single open.
CODEC_WAIT_S = 12
_codec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "phone", "codecs.json")


def _remembered_codec(serial):
    try:
        with open(_codec_path, encoding="utf-8") as f:
            return json.load(f).get(serial)
    except (OSError, ValueError):
        return None


def _remember_codec(serial, codec):
    try:
        data = {}
        try:
            with open(_codec_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        if data.get(serial) == codec:
            return
        data[serial] = codec
        os.makedirs(os.path.dirname(_codec_path), exist_ok=True)
        tmp = _codec_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, _codec_path)
    except OSError:
        pass
# Where the codec string lives: the avcC box carries profile, compatibility
# and level as three bytes, which is exactly what `avc1.PPCCLL` is made of.
_AVCC = b"avcC"
# Yielded when the phone has gone quiet, so the caller gets a turn even while
# no video is arriving. It exists for one reason: a socket that is never
# written to never reports that the other end has gone, and closing a browser
# tab while the screen was off left screenrecord, ffmpeg and a raised display
# timeout running until the service was restarted.
#
# EMPTY, deliberately. The first version yielded an MP4 `free` padding box on
# the theory that every parser skips it. That turned out not to be what broke
# the picture - the real culprit was a proactive SourceBuffer.remove() on the
# client - but writing housekeeping bytes into a live media stream is still
# the wrong mechanism: ffmpeg's output arrives in arbitrary chunks, so there
# is no guarantee the padding does not land between a fragment's moof and its
# mdat. The caller inspects its own socket instead; see server.py.
HEARTBEAT = b""
HEARTBEAT_S = 1.0


# Android hands out one screen recorder at a time, and the loser does not get
# an error - it gets silence, which looks exactly like a phone with its screen
# off. Two things take that slot: a `screenrecord` left behind by a killed adb
# connection, and MIUI's own recorder app, which holds it while merely
# resident. Both cost hours to find and seconds to clear.
RECORDER_APPS = ("com.miui.screenrecorder",)


# SurfaceFlinger's "repaint everything" transaction. Android only encodes a
# frame when something composites, so a screen that is on but perfectly still
# produces no video at all - the panel then shows a frozen picture and, after
# a few seconds, claims the display is off. One repaint costs nothing and
# gives the encoder something to send.
REPAINT_CALL = "service call SurfaceFlinger 1004"
REPAINT_EVERY_S = 1.5


def _repaint(serial):
    try:
        subprocess.run(["adb", "-s", serial, "shell", f"su -c '{REPAINT_CALL}'"],
                       capture_output=True, timeout=SETTINGS_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        pass


def _clear_recorders(serial, force_apps=False):
    """Free the device's screen recorder. -> what had to be cleared."""
    cleared = []
    try:
        # -x, not -f: match the `screenrecord` binary itself and nothing that
        # merely mentions it.
        subprocess.run(["adb", "-s", serial, "shell", "su -c 'pkill -x screenrecord'"],
                       capture_output=True, timeout=SETTINGS_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        pass
    if not force_apps:
        return cleared
    for pkg in RECORDER_APPS:
        try:
            out = subprocess.run(["adb", "-s", serial, "shell", f"pidof {pkg}"],
                                 capture_output=True, timeout=SETTINGS_TIMEOUT_S)
            if not out.stdout.strip():
                continue
            subprocess.run(["adb", "-s", serial, "shell", f"su -c 'am force-stop {pkg}'"],
                           capture_output=True, timeout=SETTINGS_TIMEOUT_S)
            cleared.append(pkg)
        except (OSError, subprocess.SubprocessError):
            pass
    return cleared


# One capture per device, enforced. See Mp4Session.open().
_captures = {}
_captures_lock = threading.Lock()


def _claim_capture(serial, session):
    with _captures_lock:
        previous = _captures.get(serial)
        _captures[serial] = session
    if previous is not None and previous is not session:
        previous.close()
    # The MJPEG stream is a screen recorder too, and it is the same device.
    stop(serial)


def _release_capture(serial, session):
    with _captures_lock:
        if _captures.get(serial) is session:
            _captures.pop(serial, None)


class Mp4Session:
    """One viewer's own capture, remuxed to fragmented MP4.

    Deliberately NOT shared between viewers, unlike Stream. A client that
    joins an MP4 stream partway through arrives mid-GOP and shows nothing
    until the next keyframe - and telling where the keyframes are means
    parsing sample flags out of every trun box. There is one person using
    this. Giving them their own pipeline costs one screenrecord and removes
    the whole problem.
    """

    def __init__(self, serial, size=None, bitrate=BITRATE):
        self.serial = serial
        self.size = size or f"720x{DEFAULT_HEIGHT}"
        self.bitrate = bitrate
        self.codec = None
        self._procs = []
        self._closed = False
        self._awake = False
        self._last_repaint = 0.0
        self._head = b""

    def _spawn(self):
        rec = subprocess.Popen(
            ["adb", "-s", self.serial, "exec-out", "screenrecord",
             "--output-format=h264", "--size", self.size,
             "--bit-rate", self.bitrate,
             "--time-limit", str(SEGMENT_S), "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ff = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             # -r BEFORE -i, and it is not optional. A raw H.264 elementary
             # stream carries no timestamps, and without a declared input rate
             # ffmpeg's demuxer stops advancing them after about fifty frames:
             # every packet afterwards is stamped with the same DTS. Copied
             # into MP4 that produced a file whose duration was 2.0 seconds no
             # matter how long the capture ran, and in the browser it looked
             # like a picture that appeared once and froze while megabytes
             # kept arriving. Measured on one 10-second capture: 2.000s of
             # media without it, 9.400s with `-r 30`.
             #
             # A fixed rate is a lie in both directions - the phone composites
             # about 28 fps while something scrolls and about 11 when the
             # screen is merely on - so the media timeline never matches real
             # time. -use_wallclock_as_timestamps looks like the answer and is
             # not: MSE stopped buffering anything at all with epoch-sized
             # timestamps. The client solves it instead, by never trying to
             # play in real time - it sits on the newest frame. See app.js.
             "-r", str(NOMINAL_FPS),
             "-f", "h264", "-i", "pipe:0",
             "-c:v", "copy", "-f", "mp4",
             "-movflags", MP4_MOVFLAGS,
             "-flush_packets", "1", "pipe:1"],
            stdin=rec.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rec.stdout.close()
        self._procs = [rec, ff]
        return rec, ff

    def open(self):
        """Start capturing and work out the codec. -> the codec string.

        Any capture already running on this device is stopped first. Android
        gives out one screen recorder at a time, and the second one does not
        fail - it simply produces nothing, which reads as a phone with its
        screen off. A page reload, a device switch, or a browser that has not
        yet noticed its connection died all leave a previous session behind,
        so this is the normal case rather than the exotic one.

        The codec has to be known before a single byte reaches the client:
        MSE wants it when the SourceBuffer is created, which is before the
        client has seen any of the stream. So the first chunks are read here,
        held, and handed back by chunks() afterwards."""
        if not shutil.which("ffmpeg"):
            raise StreamError("ffmpeg ist nicht installiert")
        if not shutil.which("adb"):
            raise StreamError("adb ist nicht installiert")
        _claim_capture(self.serial, self)
        keep_awake_async(self.serial, True)
        self._awake = True
        _clear_recorders(self.serial)
        # Already know this phone? Then answer now and let the video catch up.
        # Whether the display is actually awake is the client's question, and
        # it can see the answer sooner than this can: it has the picture.
        remembered = _remembered_codec(self.serial)
        if remembered:
            self.codec = remembered
            self._spawn()
            threading.Thread(target=_repaint, args=(self.serial,), daemon=True).start()
            return remembered
        codec = self._try_open()
        if codec:
            _remember_codec(self.serial, codec)
            return codec
        # Nothing came. Before blaming the display, take the slot back from
        # whatever else is holding it - on this phone that is MIUI's recorder,
        # which blocks every capture while doing nothing visible itself.
        self._kill()
        if _clear_recorders(self.serial, force_apps=True):
            codec = self._try_open()
            if codec:
                _remember_codec(self.serial, codec)
                return codec
        self.close()
        raise StreamError("Kein Videostrom vom Gerät - Bildschirm aus?")

    def _try_open(self):
        """One attempt at starting a capture. -> codec string, or None."""
        _, ff = self._spawn()
        deadline = time.time() + CODEC_WAIT_S
        head = b""
        while time.time() < deadline:
            # select, not a bare read: read1() on a pipe blocks until
            # something arrives, so the deadline above was unreachable in the
            # exact case it exists for. A sleeping phone produces no video at
            # all, and the panel sat on "verbinde…" indefinitely instead of
            # saying "Bildschirm aus" after six seconds.
            ready, _, _ = select.select([ff.stdout], [], [],
                                        max(0.2, deadline - time.time()))
            if not ready:
                continue
            chunk = ff.stdout.read1(65536)
            if not chunk:
                break
            head += chunk
            i = head.find(_AVCC)
            # configurationVersion, then the three bytes that name the codec.
            if i >= 0 and len(head) >= i + 8:
                p = head[i + 4:i + 8]
                self.codec = "avc1.%02X%02X%02X" % (p[1], p[2], p[3])
                self._head = head
                return self.codec
        return None

    def chunks(self):
        """Every byte of the stream, starting with what open() already read.

        screenrecord stops on its own after its 180-second limit, so the
        capture is restarted here and the client simply receives a second
        initialisation segment. MSE accepts that as long as the codec has not
        changed, and the SourceBuffer runs in sequence mode, which re-bases
        the timestamps ffmpeg restarts from zero."""
        if self._head:
            yield self._head
            self._head = b""
        while not self._closed:
            ff = self._procs[1] if self._procs else None
            if ff is None:
                break
            ended = False
            while not ended:
                # Waited on with a timeout rather than read straight, so a
                # silent phone still gives the caller something to write and
                # therefore something to fail on if the viewer has left.
                ready, _, _ = select.select([ff.stdout], [], [], HEARTBEAT_S)
                if not ready:
                    # Nothing composited for a moment. Ask for a repaint so a
                    # still screen keeps producing a picture rather than
                    # looking like a dead one, then give the caller its turn
                    # to notice whether anyone is still watching.
                    now = time.time()
                    if now - self._last_repaint > REPAINT_EVERY_S:
                        self._last_repaint = now
                        threading.Thread(target=_repaint, args=(self.serial,),
                                         daemon=True).start()
                    yield HEARTBEAT
                    continue
                chunk = ff.stdout.read1(65536)
                if not chunk:
                    ended = True
                    break
                yield chunk
            if self._closed:
                break
            self._kill()
            try:
                _, ff = self._spawn()
            except Exception:  # noqa: BLE001 - the phone left; end the stream
                break

    def close(self):
        self._closed = True
        _release_capture(self.serial, self)
        self._kill()
        if self._awake:
            self._awake = False
            keep_awake_async(self.serial, False)

    def _kill(self):
        for proc in self._procs:
            try:
                proc.kill()
            except Exception:  # noqa: BLE001 - already dead is the normal case
                pass
        self._procs = []
