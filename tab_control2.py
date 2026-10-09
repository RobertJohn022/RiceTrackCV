import cv2

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPolygonF, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QMessageBox,
    QProgressBar, QStackedWidget, QVBoxLayout, QWidget
)
from common import (
    BG, BLUE, GOOD, GREEN, MUTED, RED_BG, RED_TEXT, TEXT, STANDARDS,
    Chip, banner, button, card, kv_row, lbl, make_pixmap, set_prop
)
from vision import NoVegetationDetected, cv_to_qpixmap, encode_thumbnail, evaluate, overlay_mask
import database

class AttitudeTile(QFrame):
    def __init__(self, name):
        super().__init__()
        self.setObjectName("tile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(1)
        self.name = lbl(name, 12, MUTED)
        self.value = lbl("--", 17, TEXT, "700")
        layout.addWidget(self.name)
        layout.addWidget(self.value)
        self.set_value("--", False)

    def set_value(self, text, danger):
        bg = RED_BG if danger else BG
        self.setStyleSheet(f"QFrame#tile {{ background: {bg}; border-radius: 10px; }}")
        self.name.setStyleSheet(f"font-size: 12px; color: {'#dd7575' if danger else MUTED};")
        self.value.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {RED_TEXT if danger else TEXT};")
        self.value.setText(text)

class CameraView(QWidget):
    BLADES = [
        (.07, .95, .11, .42), (.18, .97, .22, .28), (.29, .98, .30, .36), (.40, .97, .37, .27),
        (.52, .98, .56, .33), (.64, .96, .67, .20), (.77, .94, .74, .16)]

    clicked = Signal()

    def __init__(self):
        super().__init__()
        self._roll = 0.0
        self._frame = None
        self.setMinimumSize(300, 220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_roll(self, roll):
        self._roll = roll
        self.update()

    def set_frame(self, pixmap):
        self._frame = pixmap
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
        p.setClipPath(clip)

        if self._frame is not None and not self._frame.isNull():
            scaled = self._frame.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((w - scaled.width()) // 2, (h - scaled.height()) // 2, scaled)
            return

        p.fillRect(QRectF(0, 0, w, h), QColor("#eaf3de"))

        diff = max(-0.4, min(0.4, 0.19 * self._roll / 17.0)) * h
        mid = 0.56 * h
        ground = QPolygonF([QPointF(0, mid + diff / 2), QPointF(w, mid - diff / 2),
                            QPointF(w, h), QPointF(0, h)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#c0dd97"))
        p.drawPolygon(ground)

        pen = QPen(QColor("#173404"), 3.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for bx, by, tx, ty in self.BLADES:
            path = QPainterPath(QPointF(bx * w, by * h))
            path.quadTo(QPointF((bx + (tx - bx) * 0.15 - 0.03) * w, (by + ty) / 2 * h),
                        QPointF(tx * w, ty * h))
            p.drawPath(path)

class RouteMap(QWidget):
    def __init__(self):
        super().__init__()
        self.current, self.total = 4, 8
        self.setMinimumHeight(150)

    def set_progress(self, current, total):
        self.current, self.total = current, total
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#c0dd97"))
        p.drawRoundedRect(QRectF(0, 0, w, h), 10, 10)
        p.setBrush(QColor("#d3d1c7"))
        p.drawRect(QRectF(0, h * 0.44, w, h * 0.12))

        p.setPen(QColor(GREEN))
        font = p.font()
        font.setPixelSize(11)
        p.setFont(font)
        p.drawText(QPointF(w * 0.05, h * 0.24), "Plot A-01")
        p.drawText(QPointF(w * 0.05, h * 0.82), "Plot A-02")

        y = h * 0.5
        xs = [w * (0.07 + i * (0.85 / max(1, self.total - 1))) for i in range(self.total)]
        cur = max(0, min(self.total - 1, self.current - 1))

        pen = QPen(QColor(GREEN), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(xs[0], y), QPointF(xs[cur], y))
        dash = QPen(QColor("#8f8f87"), 1.6, Qt.PenStyle.DashLine)
        p.setPen(dash)
        p.drawLine(QPointF(xs[cur], y), QPointF(xs[-1], y))

        fov = QPen(QColor(BLUE), 1.4, Qt.PenStyle.DotLine)
        p.setPen(fov)
        p.drawLine(QPointF(xs[cur], y), QPointF(xs[cur] - 15, h * 0.20))
        p.drawLine(QPointF(xs[cur], y), QPointF(xs[cur] + 15, h * 0.20))
        p.setPen(QColor(BLUE))
        p.drawText(QPointF(xs[cur] - 22, h * 0.15), "L")
        p.drawText(QPointF(xs[cur] + 13, h * 0.15), "R")

        for i, x in enumerate(xs):
            if i < cur:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(GREEN))
                p.drawEllipse(QPointF(x, y), 4.5, 4.5)
            elif i == cur:
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.setBrush(QColor(BLUE))
                p.drawEllipse(QPointF(x, y), 6, 6)
            else:
                p.setPen(QPen(QColor("#8f8f87"), 1.4))
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(x, y), 4.5, 4.5)

class StepIcon(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.setFixedSize(20, 20)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(2.5, 2.5, 15, 15)
        if self.state == "done":
            p.setPen(QPen(QColor(GOOD), 1.6))
            p.drawEllipse(rect)
            path = QPainterPath(QPointF(6.5, 10.3))
            path.lineTo(9, 12.8)
            path.lineTo(13.5, 7.5)
            p.drawPath(path)
        elif self.state == "active":
            pen = QPen(QColor(BLUE), 1.8, Qt.PenStyle.DotLine)
            p.setPen(pen)
            p.drawEllipse(rect)
        else:
            p.setPen(QPen(QColor("#6c6c6c"), 1.6))
            p.drawEllipse(rect)

class StepList(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)

    def set_steps(self, names, current):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, name in enumerate(names):
            state = "done" if i < current else "active" if i == current else "todo"
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(10)
            rl.addWidget(StepIcon(state))
            rl.addWidget(lbl(name, 13, TEXT if state != "todo" else MUTED), 1)
            self._layout.addWidget(row)

class ManualView(QWidget):
    switch_auto = Signal()
    command = Signal(str)
    record_saved = Signal(str)

    def __init__(self):
        super().__init__()
        self.tilt_limit = STANDARDS["tilt"]
        self._roll, self._pitch, self._speed = 0.0, 0.0, 0.0
        self.image_bgr = None
        self.segmented_bgr = None
        self.showing_segmented = False
        self.last_result = None
        self.record_saved_for_image = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        status = QHBoxLayout()
        status.setSpacing(8)
        status.addWidget(Chip("Link 142 m", "green", "signal"))
        status.addWidget(Chip("Feed 24 fps", "green", "wifi"))
        status.addWidget(Chip("9 sats", "green", "target"))
        status.addStretch()
        self.battery = Chip("46% · ~40 min", "orange", "battery")
        status.addWidget(self.battery)
        root.addLayout(status)

        self.alert, self.alert_text = banner("red")
        root.addWidget(self.alert)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_left(), 5)
        body.addWidget(self._build_right(), 4)
        root.addLayout(body, 1)

        for key, cmd in (("W", "forward"), ("S", "backward"), ("A", "left"), ("D", "right"), ("Space", "stop")):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda c=cmd: self.command.emit(c))
        QShortcut(QKeySequence("C"), self).activated.connect(self._capture)

        self.set_attitude(17, 4, 0.0)
        self.set_capture_progress("A-02-03", True, 3, STANDARDS["gps_n"], "Waiting for GPS")

    def _build_left(self):
        frame, lay = card(spacing=12)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(Chip("<span style='color:#e24b4a'>●</span> Live", "gray"))
        top.addWidget(Chip("Plot A-02", "gray"))
        top.addStretch()
        self.status_chip = Chip("No image", "gray")
        top.addWidget(self.status_chip)
        lay.addLayout(top)

        self.camera = CameraView()
        self.camera.setToolTip("Click to upload a photo")
        self.camera.clicked.connect(self._on_camera_clicked)
        lay.addWidget(self.camera, 1)

        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        self.roll_tile, self.pitch_tile, self.speed_tile = (
            AttitudeTile("Roll"), AttitudeTile("Pitch"), AttitudeTile("Speed"))
        for tile in (self.roll_tile, self.pitch_tile, self.speed_tile):
            tiles.addWidget(tile, 1)
        lay.addLayout(tiles)
        return frame

    def _build_right(self):
        holder = QWidget()
        col = QVBoxLayout(holder)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)

        controls, cl = card(spacing=14)

        seg = QFrame()
        seg.setObjectName("seg")
        seg.setStyleSheet(f"QFrame#seg {{ background: {BG}; border-radius: 17px; }}")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(0)
        self.manual_btn = button("Manual", "seg", checkable=True)
        self.auto_btn = button("Automatic", "seg", checkable=True)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for b in (self.manual_btn, self.auto_btn):
            group.addButton(b)
            sl.addWidget(b)
        self.manual_btn.setChecked(True)
        self.auto_btn.clicked.connect(self._to_auto)
        cl.addWidget(seg, 0, Qt.AlignmentFlag.AlignHCenter)

        pad = QGridLayout()
        pad.setSpacing(8)
        for glyph, cmd, r, c in (("↑", "forward", 0, 1), ("←", "left", 1, 0), ("▢", "stop", 1, 1),
                                 ("→", "right", 1, 2), ("↓", "backward", 2, 1)):
            b = button(glyph, "pad")
            b.setFixedSize(36, 36)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if cmd == "stop":
                b.clicked.connect(lambda _=False: self.command.emit("stop"))
            else:
                b.pressed.connect(lambda k=cmd: self.command.emit(k))
                b.released.connect(lambda: self.command.emit("stop"))
            pad.addWidget(b, r, c)
        pad_row = QHBoxLayout()
        pad_row.addStretch()
        pad_row.addLayout(pad)
        pad_row.addStretch()
        cl.addLayout(pad_row)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.upload_btn = button(" Upload Photo", "dark", "download")
        self.upload_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.upload_btn.clicked.connect(self._on_upload_button)
        self.capture_btn = button("Capture", "primary")
        self.capture_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.capture_btn.clicked.connect(self._on_capture_button)
        actions.addWidget(self.upload_btn, 1)
        actions.addWidget(self.capture_btn, 1)
        cl.addLayout(actions)

        self.capture_note = lbl("", 11, MUTED, align=Qt.AlignmentFlag.AlignHCenter)
        cl.addWidget(self.capture_note)
        col.addWidget(controls)

        status, sl2 = card(spacing=10)
        head = QHBoxLayout()
        head.addWidget(lbl("Capturing", 16, TEXT, "700"))
        head.addStretch()
        self.capture_id = Chip("A-02-03", "gray")
        head.addWidget(self.capture_id)
        sl2.addLayout(head)

        self.image_value = lbl("", 13, GOOD, "600")
        sl2.addLayout(kv_row("Image", self.image_value, TEXT))
        self.gps_value = lbl("", 13, TEXT, "600")
        sl2.addLayout(kv_row("GPS burst", self.gps_value, TEXT))
        self.gps_bar = QProgressBar()
        self.gps_bar.setTextVisible(False)
        sl2.addWidget(self.gps_bar)
        self.analysis_value = lbl("", 13, MUTED)
        sl2.addLayout(kv_row("Analysis", self.analysis_value, TEXT))
        col.addWidget(status)
        col.addStretch()
        return holder

    def _to_auto(self):
        self.manual_btn.setChecked(True)
        self.switch_auto.emit()

    def _on_camera_clicked(self):
        if self.image_bgr is None:
            self._upload_image()
        else:
            self._toggle_view()

    def _on_upload_button(self):
        if self.image_bgr is None:
            self._upload_image()
        else:
            self._cancel_image()

    def _on_capture_button(self):
        # An uploaded photo is evaluated locally; it must not fall through to
        # the rover capture command just because CV has not run yet.
        if self.image_bgr is not None:
            if not self.record_saved_for_image:
                self._evaluate_and_save()
            return
        self._capture()

    def _upload_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Rice Crop Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if not path:
            return

        img = cv2.imread(path)
        if img is None:
            QMessageBox.warning(self, "Unable to Load Image", f"Could not read:\n{path}")
            return

        self.image_bgr = img
        self.segmented_bgr = None
        self.showing_segmented = False
        self.last_result = None
        self.record_saved_for_image = False

        self.camera.set_frame(cv_to_qpixmap(img))
        self.image_value.setText("✓ Loaded")
        self.status_chip.set_text("Ready", "gray")
        self.analysis_value.setText("Photo loaded. Press Evaluate to analyze and save it.")
        self.capture_note.setText("Ready to evaluate")
        self._set_image_mode(True)
        self._update_capture_enabled()

    def _cancel_image(self):
        self.image_bgr = None
        self.segmented_bgr = None
        self.showing_segmented = False
        self.last_result = None
        self.camera.set_frame(None)
        self.camera.setToolTip("Click to upload a photo")
        self.image_value.setText("")
        self.status_chip.set_text("No image", "gray")
        self.analysis_value.setText("")
        self.capture_note.setText("")
        self.record_saved_for_image = False
        self._set_image_mode(False)

    def _set_image_mode(self, active):
        if active:
            self.upload_btn.setText(" Cancel")
            self.upload_btn.setIcon(QIcon(make_pixmap("close", TEXT, 16)))
            self.capture_btn.setText("Evaluate")
            self.camera.setToolTip("Click to toggle the segmented view")
        else:
            self.upload_btn.setText(" Upload Photo")
            self.upload_btn.setIcon(QIcon(make_pixmap("download", TEXT, 16)))
            self.capture_btn.setText("Capture")

    def _toggle_view(self):
        if self.segmented_bgr is None or self.image_bgr is None:
            return
        self.showing_segmented = not self.showing_segmented
        frame = self.segmented_bgr if self.showing_segmented else self.image_bgr
        self.camera.set_frame(cv_to_qpixmap(frame))

    def _evaluate_and_save(self):
        if self.image_bgr is None:
            self.analysis_value.setText("Upload a photo before evaluating.")
            return

        self.status_chip.set_text("Evaluating…", "gray")
        self.analysis_value.setText("Segmenting and evaluating leaf color…")
        self.capture_note.setText("Evaluating…")

        try:
            result = evaluate(self.image_bgr)
        except NoVegetationDetected as exc:
            self.last_result = None
            self.segmented_bgr = None
            self.showing_segmented = False
            self.status_chip.set_text("No vegetation", "orange")
            self.analysis_value.setText(str(exc))
            self.capture_note.setText("Evaluation failed. Upload a clearer rice-canopy photo.")
            return
        except Exception as exc:
            self.last_result = None
            self.segmented_bgr = None
            self.showing_segmented = False
            self.status_chip.set_text("Evaluation error", "red")
            self.analysis_value.setText(f"Could not evaluate the image: {exc}")
            self.capture_note.setText("Evaluation failed.")
            return

        self.last_result = result
        self.segmented_bgr = overlay_mask(self.image_bgr, result.mask)
        self.showing_segmented = True
        self.camera.set_frame(cv_to_qpixmap(self.segmented_bgr))

        healthy = result.status == "Healthy"
        self.status_chip.set_text(result.status, "green" if healthy else "red")
        self.analysis_value.setText(
            f"{result.panel} · hue {result.mean_hue:.0f} · "
            f"coverage {result.coverage_pct:.0f}%"
        )

        record = {
            "avg_hue": result.mean_hue,
            "leaf_report": result.tone,
            "image": encode_thumbnail(self.image_bgr),
        }

        try:
            record_id = database.insert_record(record)
        except Exception as exc:
            self.status_chip.set_text("Database error", "red")
            self.analysis_value.setText(
                f"Evaluation succeeded, but saving failed: {exc}"
            )
            self.capture_note.setText("Record was not saved.")
            return

        # Keep the evaluated/segmented image visible after saving and show the
        # requested confirmation in the lower-right status area.
        self.record_saved_for_image = True
        self.capture_btn.setEnabled(False)
        self.analysis_value.setText(
            "Report saved to database. View results at the Records tab."
        )
        self.capture_note.setText("Report saved to database. View results at the Records tab.")
        self.record_saved.emit(record_id)

    def _capture(self):
        if self.capture_btn.isEnabled():
            self.command.emit("capture")

    def set_tilt_limit(self, limit):
        self.tilt_limit = limit
        self.set_attitude(self._roll, self._pitch, self._speed)

    def _update_capture_enabled(self):
        # Rover tilt locks physical capture, but an uploaded photo must still
        # be evaluable. The button is "Evaluate" whenever an image is loaded.
        tilted = max(abs(self._roll), abs(self._pitch)) > self.tilt_limit
        self.capture_btn.setEnabled(
            (self.image_bgr is not None and not self.record_saved_for_image) or
            (self.image_bgr is None and not tilted)
        )

    def set_attitude(self, roll, pitch, speed):
        self._roll, self._pitch, self._speed = roll, pitch, speed
        limit = self.tilt_limit
        self.roll_tile.set_value(f"{roll:.0f}°", abs(roll) > limit)
        self.pitch_tile.set_value(f"{pitch:.0f}°", abs(pitch) > limit)
        self.speed_tile.set_value(f"{speed:.1f} m/s", False)
        self.camera.set_roll(roll)

        tilt = max(abs(roll), abs(pitch))
        tilted = tilt > limit
        self.alert.setVisible(tilted)
        self.alert_text.setText(
            f"Rover tilted {tilt:.0f}°, above the {limit}° limit. "
            "Reposition before capturing."
        )
        self._update_capture_enabled()

        if self.image_bgr is None:
            self.capture_note.setText(
                "Capture locked until rover is stable" if tilted else "Ready to capture"
            )
        elif self.record_saved_for_image:
            self.capture_note.setText("Report saved to database. View results at the Records tab.")
        else:
            self.capture_note.setText("Ready to evaluate")

    def set_capture_progress(self, capture_id, image_saved, gps_done, gps_total, analysis):
        self.capture_id.set_text(capture_id)
        self.image_value.setText("✓ Saved" if image_saved else "Saving…")
        self.gps_value.setText(f"{gps_done} of {gps_total} readings")
        self.gps_bar.setRange(0, gps_total)
        self.gps_bar.setValue(gps_done)
        self.analysis_value.setText(analysis)

class AutoView(QWidget):
    take_over = Signal()
    paused_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.tilt_limit = STANDARDS["tilt"]
        self.total = 8
        self.stop, self.step = 4, 2
        self.paused = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        status = QHBoxLayout()
        status.addWidget(Chip("Automatic · Dike route B", "blue", "target"))
        status.addStretch()
        status.addWidget(Chip("71% · ~64 min", "green", "battery"))
        root.addLayout(status)

        body = QHBoxLayout()
        body.setSpacing(12)

        route_card, rl = card(spacing=12)
        head = QHBoxLayout()
        head.addWidget(lbl("Route", 17, TEXT, "700"))
        head.addStretch()
        self.stop_chip = Chip("", "gray")
        head.addWidget(self.stop_chip)
        rl.addLayout(head)
        self.route = RouteMap()
        rl.addWidget(self.route, 1)
        body.addWidget(route_card, 3)

        stop_card, sl = card(spacing=14)
        self.stop_title = lbl("", 17, TEXT, "700")
        sl.addWidget(self.stop_title)
        self.steps = StepList()
        sl.addWidget(self.steps)
        sl.addStretch()
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.pause_btn = button(" Pause", "dark", "pause")
        self.pause_btn.clicked.connect(self._toggle_pause)
        takeover = button(" Take over", "dark", "hand")
        takeover.clicked.connect(self.take_over)
        buttons.addWidget(self.pause_btn, 1)
        buttons.addWidget(takeover, 1)
        sl.addLayout(buttons)
        body.addWidget(stop_card, 2)
        root.addLayout(body, 1)

        self.warn, self.warn_text = banner("orange", "info")
        root.addWidget(self.warn)

        self.set_tilt_limit(self.tilt_limit)
        self.set_progress(self.stop, self.step)

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.setText(" Resume" if self.paused else " Pause")
        self.pause_btn.setIcon(QIcon(make_pixmap("play" if self.paused else "pause", TEXT, 16)))
        self.paused_changed.emit(self.paused)

    def set_tilt_limit(self, limit):
        self.tilt_limit = limit
        self.warn_text.setText(
            f"If tilt goes over {limit}°, the rover pauses on its own and resumes once stable.")

    def set_progress(self, stop, step):
        self.stop, self.step = stop, step
        self.stop_chip.set_text(f"Stop {stop} of {self.total}")
        self.stop_title.setText(f"At stop {stop}")
        self.route.set_progress(stop, self.total)
        self.steps.set_steps(["Stopped, legs down", "Capture left side", "Capture right side",
                              f"GPS burst ({STANDARDS['gps_n']} readings)", f"Move to stop {stop + 1}"], step)

class ControlPage(QWidget):
    command = Signal(str)
    record_saved = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.manual = ManualView()
        self.auto = AutoView()
        self.stack.addWidget(self.manual)
        self.stack.addWidget(self.auto)
        layout.addWidget(self.stack)

        self.manual.switch_auto.connect(lambda: self.stack.setCurrentWidget(self.auto))
        self.auto.take_over.connect(lambda: self.stack.setCurrentWidget(self.manual))
        self.manual.command.connect(self.command)
        self.manual.record_saved.connect(self.record_saved)

    def set_attitude(self, roll, pitch, speed):
        self.manual.set_attitude(roll, pitch, speed)

    def set_tilt_limit(self, limit):
        self.manual.set_tilt_limit(limit)
        self.auto.set_tilt_limit(limit)