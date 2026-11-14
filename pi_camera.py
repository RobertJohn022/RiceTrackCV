"""RiceTrack - laptop-side client for pi_camera_server.py (which runs on the Raspberry Pi).

Used by the Control tab (tab_control.py):
  * polls the Pi every few seconds so the app knows if the camera is online
  * capture() asks the Pi for one full-resolution JPEG and saves a copy + metadata
  * preview_frame() fetches one low-quality frame for the in-tab live preview
"""
import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

PI_HOST = "Group4-4ITC.local"        # the Pi's IP address, or e.g. "Group4-4ITC.local"
PI_PORT = 8000
CAPTURE_DIR = Path.home() / "Pictures" / "RiceTrack"
STATUS_INTERVAL_MS = 5000        # how often to check that the Pi is reachable
STATUS_TIMEOUT_S = 4
PREVIEW_TIMEOUT_S = 3
CAPTURE_TIMEOUT_S = 30           # capture + transfer of a full-resolution JPEG


class _Request(QThread):
    """One HTTP GET, run off the UI thread."""
    done = Signal(bytes, str)    # response body, X-Capture-Info header
    failed = Signal(str)

    def __init__(self, url, timeout):
        super().__init__()
        self.url, self.timeout = url, timeout

    def run(self):
        try:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as resp:
                self.done.emit(resp.read(), resp.headers.get("X-Capture-Info", ""))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:200]
            self.failed.emit(f"Pi returned error {exc.code}: {detail}")
        except Exception as exc:
            self.failed.emit(f"Cannot reach the Pi: {exc}")


class PiCamera(QObject):
    online_changed = Signal(bool)         # emitted only when the state changes
    captured = Signal(bytes, object, str)  # JPEG bytes, camera info (dict), saved path ("" if not saved)
    capture_failed = Signal(str)
    preview_frame_ready = Signal(bytes)
    preview_failed = Signal(str)

    def __init__(self, host=PI_HOST, port=PI_PORT, parent=None):
        super().__init__(parent)
        self.host, self.port = host, port
        self.online = False
        self._status_job = None
        self._capture_job = None
        self._preview_job = None
        self._timer = QTimer(self)
        self._timer.setInterval(STATUS_INTERVAL_MS)
        self._timer.timeout.connect(self.check)

    # --- lifecycle ---------------------------------------------------------
    def start(self):
        self.check()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        for job in (self._status_job, self._capture_job, self._preview_job):
            if job is not None and job.isRunning():
                job.wait(2000)

    def _url(self, path):
        return f"http://{self.host}:{self.port}{path}"

    def _set_online(self, ok):
        if ok != self.online:
            self.online = ok
            self.online_changed.emit(ok)

    # --- connection check --------------------------------------------------
    def check(self):
        if self.capturing or (self._status_job is not None and self._status_job.isRunning()):
            return
        self._status_job = _Request(self._url("/status"), STATUS_TIMEOUT_S)
        self._status_job.done.connect(self._on_status_ok)
        self._status_job.failed.connect(self._on_status_failed)
        self._status_job.start()

    def _on_status_ok(self, _body, _info):
        self._set_online(True)

    def _on_status_failed(self, _message):
        self._set_online(False)

    # --- live preview ------------------------------------------------------
    @property
    def previewing(self):
        return self._preview_job is not None and self._preview_job.isRunning()

    def preview_frame(self):
        """Fetch one small JPEG frame; the UI timer calls this several times/sec."""
        if self.previewing or not self.online:
            return
        self._preview_job = _Request(self._url("/preview"), PREVIEW_TIMEOUT_S)
        self._preview_job.done.connect(self._on_preview_ok)
        self._preview_job.failed.connect(self._on_preview_failed)
        self._preview_job.start()

    def _on_preview_ok(self, body, _info):
        self._set_online(True)
        self.preview_frame_ready.emit(body)

    def _on_preview_failed(self, message):
        if message.startswith("Cannot reach"):
            self._set_online(False)
        self.preview_failed.emit(message)

    # --- capture -----------------------------------------------------------
    @property
    def capturing(self):
        return self._capture_job is not None and self._capture_job.isRunning()

    def capture(self):
        if self.capturing:
            return
        self._capture_job = _Request(self._url("/capture"), CAPTURE_TIMEOUT_S)
        self._capture_job.done.connect(self._on_capture_ok)
        self._capture_job.failed.connect(self._on_capture_failed)
        self._capture_job.start()

    def _on_capture_ok(self, body, info_header):
        self._set_online(True)
        info = {}
        if info_header:
            try:
                info = json.loads(info_header)
            except ValueError:
                pass
        self.captured.emit(body, info, self._save(body, info))

    def _on_capture_failed(self, message):
        if message.startswith("Cannot reach"):
            self._set_online(False)
        self.capture_failed.emit(message)

    def _save(self, body, info):
        """Keep the full-resolution original (and its camera settings) on the laptop."""
        try:
            CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
            path = CAPTURE_DIR / f"rice_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            path.write_bytes(body)
            if info:
                path.with_suffix(".json").write_text(json.dumps(info, indent=2))
            return str(path)
        except OSError:
            return ""
