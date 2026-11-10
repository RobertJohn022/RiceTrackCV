"""RiceTrack - Pi camera capture (laptop side).

Press "Capture image": the Pi autofocuses, takes a 12 MP photo, sends it over
the network, and this app saves it (plus a small .json with the camera settings)
into the chosen folder on the laptop.

Keep this file in the same folder as common.py from the RiceTrack project.
Run:  python capture_app.py
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QSizePolicy, QVBoxLayout, QWidget
)
from common import APP_QSS, BG, LINE, MUTED, TEXT, Chip, button, card, lbl

DEFAULT_HOST = "raspberrypi.local"      # or the Pi's IP address, e.g. 192.168.1.50
DEFAULT_PORT = 8000
DEFAULT_FOLDER = Path.home() / "Pictures" / "RiceTrack"
CAPTURE_TIMEOUT_S = 30                  # autofocus + 12 MP capture + transfer

EXTRA_QSS = f"""
QLineEdit {{ background: {BG}; border: 1px solid {LINE}; border-radius: 8px;
    color: {TEXT}; padding: 7px 10px; font-size: 13px; }}
"""


class HttpWorker(QThread):
    """Does one GET request off the UI thread."""
    done = Signal(bytes, str)      # response body, X-Capture-Info header
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


class Preview(QLabel):
    """Shows the last captured image, scaled to fit."""

    def __init__(self):
        super().__init__("No image yet. Press Capture image.")
        self._pm = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setStyleSheet(
            f"background: {BG}; color: {MUTED}; border: 1.5px dashed {LINE}; border-radius: 10px;")

    def set_image(self, pixmap):
        self._pm = pixmap
        self._refresh()

    def _refresh(self):
        if self._pm is not None and not self._pm.isNull():
            self.setPixmap(self._pm.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()


class CaptureWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiceTrack - Pi Camera Capture")
        self.resize(940, 720)
        self.folder = DEFAULT_FOLDER
        self._worker = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # --- connection + folder card -------------------------------------
        top, tl = card(spacing=10)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(lbl("Pi address", 13, MUTED))
        self.host = QLineEdit(DEFAULT_HOST)
        self.port = QLineEdit(str(DEFAULT_PORT))
        self.port.setFixedWidth(70)
        row.addWidget(self.host, 1)
        row.addWidget(lbl(":", 13, MUTED))
        row.addWidget(self.port)
        self.check_btn = button("Check", "dark", "wifi")
        self.check_btn.clicked.connect(self._check)
        row.addWidget(self.check_btn)
        self.status = Chip("Not checked", "gray", "wifi")
        row.addWidget(self.status)
        tl.addLayout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(lbl("Save to", 13, MUTED))
        self.folder_label = lbl(str(self.folder), 13, TEXT)
        row2.addWidget(self.folder_label, 1)
        browse = button("Browse", "dark", "file")
        browse.clicked.connect(self._browse)
        row2.addWidget(browse)
        tl.addLayout(row2)
        layout.addWidget(top)

        # --- capture button + preview -------------------------------------
        self.capture_btn = button("Capture image", "primary", "target", "#ffffff")
        self.capture_btn.clicked.connect(self._capture)
        layout.addWidget(self.capture_btn)

        self.preview = Preview()
        layout.addWidget(self.preview, 1)

        self.note = lbl("Ready.", 13, MUTED, wrap=True)
        layout.addWidget(self.note)

        QTimer.singleShot(300, self._check)

    # ------------------------------------------------------------------
    def _url(self, path):
        return f"http://{self.host.text().strip()}:{self.port.text().strip()}{path}"

    def _busy(self):
        return self._worker is not None and self._worker.isRunning()

    def _start(self, path, timeout, on_done):
        if self._busy():
            return
        self._worker = HttpWorker(self._url(path), timeout)
        self._worker.done.connect(on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _set_idle(self):
        self.capture_btn.setEnabled(True)
        self.capture_btn.setText("Capture image")
        self.check_btn.setEnabled(True)

    def _browse(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select save folder", str(self.folder))
        if chosen:
            self.folder = Path(chosen)
            self.folder_label.setText(chosen)

    # --- connection check -----------------------------------------------
    def _check(self):
        if self._busy():
            return
        self.status.set_text("Checking...", "orange")
        self._start("/status", 5, self._on_checked)

    def _on_checked(self, _body, _info):
        self.status.set_text("Pi connected", "green")
        self.note.setText("Ready.")

    # --- capture -----------------------------------------------------------
    def _capture(self):
        if self._busy():
            return
        self.capture_btn.setEnabled(False)
        self.capture_btn.setText("Focusing and capturing...")
        self.check_btn.setEnabled(False)
        self.status.set_text("Capturing...", "orange")
        self.note.setText("Autofocusing and taking a 12 MP photo. This takes a few seconds.")
        self._start("/capture", CAPTURE_TIMEOUT_S, self._on_captured)

    def _on_captured(self, body, info_header):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            path = self.folder / f"rice_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            path.write_bytes(body)
        except OSError as exc:
            self._set_idle()
            self.status.set_text("Save failed", "red")
            self.note.setText(f"Could not save the image: {exc}")
            return

        extra = ""
        if info_header:
            try:
                info = json.loads(info_header)
                path.with_suffix(".json").write_text(json.dumps(info, indent=2))
                exposure = info.get("exposure_us")
                extra = (f"  |  exposure {exposure / 1000:.1f} ms, gain {info.get('analogue_gain', 0):.1f}")
                if info.get("autofocus_ok") is not None:      # None = fixed-focus camera
                    extra += f", focus {'OK' if info['autofocus_ok'] else 'not locked'}"
            except (ValueError, TypeError, OSError):
                pass

        pixmap = QPixmap()
        pixmap.loadFromData(body)
        self.preview.set_image(pixmap)
        self._set_idle()
        self.status.set_text("Saved", "green")
        self.note.setText(f"Saved {path}{extra}")

    def _on_failed(self, message):
        self._set_idle()
        self.status.set_text("Pi offline", "red")
        self.note.setText(message)

    def closeEvent(self, event):
        if self._busy():
            self._worker.wait(2000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS + EXTRA_QSS)
    window = CaptureWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()