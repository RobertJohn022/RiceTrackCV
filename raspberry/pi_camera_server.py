#!/usr/bin/env python3
"""RiceTrack camera server for Raspberry Pi 4 + Camera Module v2.1.

Endpoints:
  GET /status   -> camera availability
  GET /preview  -> small, compressed live-preview JPEG (performance only)
  GET /imu      -> MPU-6050 roll/pitch JSON over I2C
  GET /capture  -> full-resolution, high-quality still JPEG for crop analysis

Run on the Raspberry Pi with: python3 pi_camera_server.py
"""
import io
import json
import math
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None

from libcamera import Transform
from picamera2 import Picamera2

HOST, PORT = "0.0.0.0", 8000
PREVIEW_SIZE = (640, 480)
PREVIEW_JPEG_QUALITY = 45       # affects /preview only
CAPTURE_JPEG_QUALITY = 95       # affects /capture only
ROTATE_180 = False              # set True if camera is mounted upside down

picam2 = Picamera2()
RESOLUTION = tuple(picam2.camera_properties["PixelArraySize"])
CAMERA_MODEL = picam2.camera_properties.get("Model", "unknown")
HAS_AUTOFOCUS = "AfMode" in picam2.camera_controls  # Camera Module v2.1 is fixed-focus
transform = Transform(hflip=ROTATE_180, vflip=ROTATE_180)

# The camera runs in a lightweight video mode for live preview. Still capture
# temporarily switches to a full-resolution still configuration and then
# returns to this preview configuration.
preview_config = picam2.create_video_configuration(
    main={"size": PREVIEW_SIZE, "format": "RGB888"},
    # Request the sensor full output area so the preview uses the same wider
    # field of view as the full-resolution still capture.
    sensor={"output_size": RESOLUTION},
    transform=transform,
    controls={"FrameRate": 30},
)
still_config = picam2.create_still_configuration(
    main={"size": RESOLUTION, "format": "RGB888"},
    transform=transform,
)
picam2.configure(preview_config)
picam2.options["quality"] = CAPTURE_JPEG_QUALITY
picam2.start()
time.sleep(2)  # allow auto-exposure and white balance to settle
camera_lock = threading.Lock()

# MPU-6050 is now connected directly to the Raspberry Pi's I2C bus.
# The desktop app reads these values through GET /imu.
imu_lock = threading.Lock()
imu_bus = None
imu_address = None
imu_last_roll = 0.0
imu_last_pitch = 0.0
imu_has_sample = False
IMU_SMOOTHING = 0.2
IMU_ADDRESSES = (0x68, 0x69)


def _signed16(high, low):
    value = (high << 8) | low
    return value - 65536 if value & 0x8000 else value


def _read_imu():
    """Return (ok, roll, pitch); angles follow the existing ESP32 firmware formula."""
    global imu_bus, imu_address, imu_last_roll, imu_last_pitch, imu_has_sample
    if SMBus is None:
        return False, 0.0, 0.0

    with imu_lock:
        try:
            if imu_bus is None:
                imu_bus = SMBus(1)
                for address in IMU_ADDRESSES:
                    try:
                        imu_bus.write_byte_data(address, 0x6B, 0x00)  # wake MPU-6050
                        imu_address = address
                        break
                    except OSError:
                        continue
                if imu_address is None:
                    imu_bus.close()
                    imu_bus = None
                    return False, 0.0, 0.0

            raw = imu_bus.read_i2c_block_data(imu_address, 0x3B, 6)
            ax = _signed16(raw[0], raw[1]) / 16384.0
            ay = _signed16(raw[2], raw[3]) / 16384.0
            az = _signed16(raw[4], raw[5]) / 16384.0
            roll = math.degrees(math.atan2(ay, az))
            pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))

            if not imu_has_sample:
                imu_last_roll, imu_last_pitch = roll, pitch
                imu_has_sample = True
            else:
                imu_last_roll += IMU_SMOOTHING * (roll - imu_last_roll)
                imu_last_pitch += IMU_SMOOTHING * (pitch - imu_last_pitch)
            return True, imu_last_roll, imu_last_pitch
        except OSError:
            # Close a stale bus and retry discovery on the next request.
            try:
                if imu_bus is not None:
                    imu_bus.close()
            except Exception:
                pass
            imu_bus = None
            imu_address = None
            return False, 0.0, 0.0


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype, headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Avoid printing one line for every preview frame request.
        if self.path.split("?")[0] != "/preview":
            super().log_message(fmt, *args)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/status":
            self._send(200, b'{"ok": true}', "application/json")
        elif path == "/imu":
            try:
                ok, roll, pitch = _read_imu()
                body = json.dumps({"ok": ok, "roll": round(roll, 2), "pitch": round(pitch, 2)}).encode()
                self._send(200, body, "application/json", {"Cache-Control": "no-store"})
            except Exception as exc:
                body = json.dumps({"ok": False, "error": str(exc)}).encode()
                self._send(200, body, "application/json", {"Cache-Control": "no-store"})
        elif path == "/preview":
            try:
                # This is the low-resolution, low-JPEG-quality preview only.
                with camera_lock:
                    frame = picam2.capture_array("main")
                # Picamera2's RGB888 stream is delivered in BGR byte order on
                # this platform; cv2.imencode expects BGR. Do not swap channels,
                # or the preview will have red/blue colours inverted.
                ok, encoded = cv2.imencode(
                    ".jpg", frame,
                    [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY],
                )
                if not ok:
                    raise RuntimeError("Could not encode preview frame")
                self._send(200, encoded.tobytes(), "image/jpeg", {"Cache-Control": "no-store"})
            except Exception as exc:
                self._send(500, str(exc).encode(), "text/plain")
        elif path == "/capture":
            try:
                # This endpoint switches to the sensor's full still resolution.
                # Preview compression/resolution settings do not affect this image.
                with camera_lock:
                    # Explicitly retain high JPEG quality for the still capture.
                    picam2.options["quality"] = CAPTURE_JPEG_QUALITY
                    focus_ok = picam2.autofocus_cycle() if HAS_AUTOFOCUS else None
                    buf = io.BytesIO()
                    meta = picam2.switch_mode_and_capture_file(
                        still_config, buf, format="jpeg"
                    )
                info = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "camera_model": CAMERA_MODEL,
                    "resolution": list(RESOLUTION),
                    "capture_jpeg_quality": CAPTURE_JPEG_QUALITY,
                    "autofocus_ok": None if focus_ok is None else bool(focus_ok),
                    "exposure_us": meta.get("ExposureTime") if isinstance(meta, dict) else None,
                    "analogue_gain": meta.get("AnalogueGain") if isinstance(meta, dict) else None,
                    "lens_position": meta.get("LensPosition") if isinstance(meta, dict) else None,
                    "colour_temperature_k": meta.get("ColourTemperature") if isinstance(meta, dict) else None,
                    "colour_gains": meta.get("ColourGains") if isinstance(meta, dict) else None,
                    "lux": meta.get("Lux") if isinstance(meta, dict) else None,
                }
                self._send(200, buf.getvalue(), "image/jpeg",
                           {"X-Capture-Info": json.dumps(info, default=str)})
            except Exception as exc:
                self._send(500, str(exc).encode(), "text/plain")
        else:
            self._send(404, b"not found", "text/plain")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"RiceTrack camera server listening on port {PORT}")
    print(f"Preview: {PREVIEW_SIZE[0]}x{PREVIEW_SIZE[1]}, JPEG quality {PREVIEW_JPEG_QUALITY}")
    print(f"Still capture: {RESOLUTION[0]}x{RESOLUTION[1]}, JPEG quality {CAPTURE_JPEG_QUALITY}")
    print("IMU endpoint: /imu (MPU-6050 over I2C, address 0x68 or 0x69)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        picam2.stop()
