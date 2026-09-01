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

WHY MJPEG AND NOT WebCodecs

Decoding the H.264 in the browser would be lower latency and would skip
ffmpeg entirely - but WebCodecs requires a secure context, and this app is
served over plain HTTP on the tailnet because Tailscale HTTPS is not enabled
on Felix's account yet (the same reason crypto.randomUUID is missing on his
phone; see app.js). MJPEG in an <img> needs no secure context at all. If
HTTPS ever gets turned on, swapping the browser side to WebCodecs is a
localized change - this module's job, getting H.264 off the phone, stays.

LIFECYCLE

`screenrecord` has a hard 180-second limit and exits on its own. That is
handled by restarting it inside the same stream, so a viewer sees a
continuous picture and never has to know. A stream with no viewers shuts
itself down after IDLE_TIMEOUT_S rather than recording someone's phone
screen forever into a buffer nobody reads.

Stdlib only, plus adb and ffmpeg.
"""
import os
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
DEFAULT_HEIGHT = 1600
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
