"""RiceTrack remote IMU reader.

The MPU-6050 is connected to the Raspberry Pi, while the Qt application runs
on the desktop. The Pi camera server exposes GET /imu and returns JSON:
{"ok": true, "roll": ..., "pitch": ...} or {"ok": false, ...}.

This class preserves the same signal interface used by the Control tab.
"""
import json
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, QThread, QTimer, Signal

PI_HOST = "Group4-4ITC.local"  # use the same host/IP as pi_camera.py
PI_PORT = 8000
POLL_INTERVAL_MS = 100
REQUEST_TIMEOUT_S = 1.0


class _ImuRequest(QThread):
    result = Signal(bool, float, float)
    failed = Signal(str)

    def __init__(self, url, timeout=REQUEST_TIMEOUT_S):
        super().__init__()
        self.url = url
        self.timeout = timeout

    def run(self):
        try:
            request = urllib.request.Request(
                self.url, headers={"Cache-Control": "no-cache"}
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            if data.get("ok"):
                self.result.emit(True, float(data["roll"]), float(data["pitch"]))
            else:
                self.result.emit(False, 0.0, 0.0)
        except Exception as exc:
            self.failed.emit(str(exc))


class IMUReader(QObject):
    """Poll the Pi's I2C-backed IMU endpoint and emit roll/pitch in degrees."""

    reading = Signal(float, float)
    state_changed = Signal(bool)

    def __init__(self, host=PI_HOST, port=PI_PORT, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self._ok = False
        self._job = None
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    def start(self):
        self._poll()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        if self._job is not None and self._job.isRunning():
            self._job.wait(1500)

    def _poll(self):
        if self._job is not None and self._job.isRunning():
            return
        self._job = _ImuRequest(f"http://{self.host}:{self.port}/imu")
        self._job.result.connect(self._on_result)
        self._job.failed.connect(self._on_failed)
        self._job.start()

    def _set_ok(self, ok):
        if ok != self._ok:
            self._ok = ok
            self.state_changed.emit(ok)

    def _on_result(self, ok, roll, pitch):
        self._set_ok(ok)
        if ok:
            self.reading.emit(roll, pitch)

    def _on_failed(self, _message):
        self._set_ok(False)
