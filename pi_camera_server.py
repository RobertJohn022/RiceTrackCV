#!/usr/bin/env python3
"""RiceTrack - Pi camera server.  Runs ON the Raspberry Pi 4.

Endpoints
  GET /status   -> {"ok": true}                      (connection check)
  GET /capture  -> JPEG image (autofocus first); capture settings are returned
                   in the X-Capture-Info header as JSON

Run:  python3 pi_camera_server.py
"""
import io
import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from libcamera import Transform
from picamera2 import Picamera2

HOST, PORT = "0.0.0.0", 8000
JPEG_QUALITY = 95
ROTATE_180 = False          # set True if the camera is mounted upside down

picam2 = Picamera2()
# Full sensor size: 3280x2464 on Camera V2.1 (IMX219), 4608x2592 on Module 3 (IMX708)
RESOLUTION = tuple(picam2.camera_properties["PixelArraySize"])
CAMERA_MODEL = picam2.camera_properties.get("Model", "unknown")
HAS_AUTOFOCUS = "AfMode" in picam2.camera_controls   # False on the fixed-focus V2.1
config = picam2.create_still_configuration(
    main={"size": RESOLUTION},
    transform=Transform(hflip=ROTATE_180, vflip=ROTATE_180),
)
picam2.configure(config)
picam2.options["quality"] = JPEG_QUALITY
picam2.start()
time.sleep(2)               # let auto-exposure / white balance settle
camera_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype, headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/status":
            self._send(200, b'{"ok": true}', "application/json")
        elif path == "/capture":
            try:
                with camera_lock:
                    focus_ok = picam2.autofocus_cycle() if HAS_AUTOFOCUS else None
                    buf = io.BytesIO()
                    meta = picam2.capture_file(buf, format="jpeg")
                info = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "camera_model": CAMERA_MODEL,
                    "resolution": list(RESOLUTION),
                    "autofocus_ok": None if focus_ok is None else bool(focus_ok),
                    "exposure_us": meta.get("ExposureTime"),
                    "analogue_gain": meta.get("AnalogueGain"),
                    "lens_position": meta.get("LensPosition"),
                    "colour_temperature_k": meta.get("ColourTemperature"),
                    "colour_gains": meta.get("ColourGains"),
                    "lux": meta.get("Lux"),
                }
                self._send(200, buf.getvalue(), "image/jpeg",
                           {"X-Capture-Info": json.dumps(info, default=str)})
            except Exception as exc:  # report the problem back to the laptop
                self._send(500, str(exc).encode(), "text/plain")
        else:
            self._send(404, b"not found", "text/plain")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Camera server listening on port {PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        picam2.stop()