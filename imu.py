"""ESP32 + MPU-6050 tilt sensor, read over USB serial.

The ESP32 firmware (esp32_imu/esp32_imu.ino) prints one of these lines:

    $IMU,<roll>,<pitch>     MPU-6050 found, angles in degrees (20 Hz)
    $NOIMU                  ESP32 is alive but the MPU-6050 did not answer

IMUReader finds the board by itself, reconnects when it is unplugged and
reports two things to the GUI:

    reading(roll, pitch)    every new sample
    state_changed(bool)     True  = ESP32 + MPU-6050 are delivering data
                            False = no ESP32, or ESP32 without a working MPU-6050

Needs:  pip install pyserial   (NOT the package called "serial")
"""
import time

from PySide6.QtCore import QObject, QTimer, Signal

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # app still runs, it just reports "No IMU sensors detected"
    serial = None
    list_ports = None

BAUD = 115200
# USB-serial chips found on ESP32 dev boards: CP210x, CH340, FTDI, Espressif native USB
ESP_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}


class IMUReader(QObject):
    reading = Signal(float, float)   # roll, pitch (degrees)
    state_changed = Signal(bool)

    SCAN_MS = 2000        # how often to look for a board while none is connected
    POLL_MS = 20          # how often to drain the serial buffer
    BOOT_GRACE_S = 4.0    # opening the port resets most ESP32 boards; wait for the first line
    TIMEOUT_S = 1.5       # silence this long after the first line = board unplugged / hung

    def __init__(self, port=None, parent=None):
        """port=None -> auto-detect. Pass e.g. "COM5" or "/dev/ttyUSB0" to force one."""
        super().__init__(parent)
        self._fixed_port = port
        self._port = None
        self._buf = bytearray()
        self._ok = False
        self._seen = False        # got at least one protocol line on this connection
        self._last_line = 0.0

        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._try_open)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)

    # ---- lifecycle -------------------------------------------------------
    def start(self):
        self._try_open()
        self._scan_timer.start(self.SCAN_MS)
        self._poll_timer.start(self.POLL_MS)

    def stop(self):
        self._scan_timer.stop()
        self._poll_timer.stop()
        self._drop()

    # ---- connection ------------------------------------------------------
    def _candidates(self):
        if serial is None:
            return []
        if self._fixed_port:
            return [self._fixed_port]
        return [p.device for p in list_ports.comports() if p.vid in ESP_VIDS]

    def _try_open(self):
        if self._port is not None:
            return
        for device in self._candidates():
            try:
                self._port = serial.Serial(device, BAUD, timeout=0)
            except (serial.SerialException, OSError):
                continue  # busy (Serial Monitor open?) or vanished
            self._buf.clear()
            self._seen = False
            self._last_line = time.monotonic()
            return

    def _drop(self):
        if self._port is not None:
            try:
                self._port.close()
            except (serial.SerialException, OSError):
                pass
            self._port = None
        self._set_ok(False)

    def _set_ok(self, ok):
        if ok != self._ok:
            self._ok = ok
            self.state_changed.emit(ok)

    # ---- reading ---------------------------------------------------------
    def _poll(self):
        if self._port is None:
            return
        try:
            data = self._port.read(4096)
        except (serial.SerialException, OSError):
            self._drop()
            return
        if data:
            self.feed(data)

        limit = self.TIMEOUT_S if self._seen else self.BOOT_GRACE_S
        if time.monotonic() - self._last_line > limit:
            self._drop()

    def feed(self, data):
        """Accepts raw bytes from the port. Public so it can be unit-tested without hardware."""
        self._buf += data
        while True:
            line, sep, rest = self._buf.partition(b"\n")
            if not sep:
                break
            self._buf = rest
            self._handle_line(line.decode("ascii", "ignore").strip())
        if len(self._buf) > 4096:   # boot-ROM garbage with no newline
            self._buf.clear()

    def _handle_line(self, line):
        if line.startswith("$IMU,"):
            try:
                _, roll, pitch = line.split(",")
                roll, pitch = float(roll), float(pitch)
            except ValueError:
                return
            self._mark_seen()
            self._set_ok(True)
            self.reading.emit(roll, pitch)
        elif line == "$NOIMU":
            self._mark_seen()
            self._set_ok(False)

    def _mark_seen(self):
        self._seen = True
        self._last_line = time.monotonic()
