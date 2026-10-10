"""USB-serial link to the ESP32 (MPU-6050 tilt sensor + NEO-6M GPS).

The ESP32 firmware (esp32_link/esp32_link.ino) prints these lines:

    $IMU,<roll>,<pitch>             MPU-6050 found, degrees, 20 Hz
    $NOIMU                          ESP32 alive, MPU-6050 not answering
    $GPS,1,<lat>,<lon>,<sats>       GPS has a position fix, 1 Hz
    $GPS,0,,,<sats>                 GPS module talking but no fix yet
    $NOGPS                          no data from the GPS module (not wired / unplugged)

ESP32Link finds the board by itself, reconnects when it is unplugged and emits:

    imu_reading(roll, pitch)
    imu_state(bool)                 True = ESP32 + MPU-6050 delivering data
    gps_changed(state, lat, lon, sats)
                                    state is "none" (no ESP32 / no GPS module),
                                    "searching" (no fix yet) or "fix"

Needs:  pip install pyserial   (NOT the package called "serial")
"""
import time

from PySide6.QtCore import QObject, QTimer, Signal

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # app still runs, it just reports "no sensors"
    serial = None
    list_ports = None

BAUD = 115200
# USB-serial chips found on ESP32 dev boards: CP210x, CH340, FTDI, Espressif native USB
ESP_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}


class ESP32Link(QObject):
    imu_reading = Signal(float, float)       # roll, pitch (degrees)
    imu_state = Signal(bool)
    gps_changed = Signal(str, float, float, int)   # state, lat, lon, satellites

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
        self._imu_ok = False
        self._gps_state = "none"
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
        self._set_imu(False)
        self._set_gps("none")

    # ---- state helpers ---------------------------------------------------
    def _set_imu(self, ok):
        if ok != self._imu_ok:
            self._imu_ok = ok
            self.imu_state.emit(ok)

    def _set_gps(self, state, lat=0.0, lon=0.0, sats=0):
        if state == "none" and self._gps_state == "none":
            return
        self._gps_state = state
        self.gps_changed.emit(state, lat, lon, sats)

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
            self._set_imu(True)
            self.imu_reading.emit(roll, pitch)
        elif line == "$NOIMU":
            self._mark_seen()
            self._set_imu(False)
        elif line.startswith("$GPS,"):
            self._handle_gps(line)
        elif line == "$NOGPS":
            self._mark_seen()
            self._set_gps("none")

    def _handle_gps(self, line):
        try:
            _, fix, lat, lon, sats = line.split(",")
            sats = int(sats)
            if fix == "1":
                lat, lon = float(lat), float(lon)
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    return
            elif fix != "0":
                return
        except ValueError:
            return
        self._mark_seen()
        if fix == "1":
            self._set_gps("fix", lat, lon, sats)
        else:
            self._set_gps("searching", 0.0, 0.0, sats)

    def _mark_seen(self):
        self._seen = True
        self._last_line = time.monotonic()
