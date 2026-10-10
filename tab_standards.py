from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QSpinBox, QVBoxLayout, QWidget
from common import MUTED, TEXT, STANDARDS, Chip, button, card, kv_row, lbl

def make_spin(low, high, value, suffix="", width=56):
    box = QSpinBox()
    box.setRange(low, high)
    box.setValue(value)
    box.setSuffix(suffix)
    box.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.setFixedSize(width, 32)
    return box

def range_row(label_text, spin_lo, spin_hi, unit=""):
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(lbl(label_text, 13, MUTED))
    row.addStretch()
    row.addWidget(spin_lo)
    row.addWidget(lbl("to", 13, MUTED))
    row.addWidget(spin_hi)
    if unit:
        row.addWidget(lbl(unit, 13, MUTED))
    return row

class HueBar(QWidget):
    MIN_H, MAX_H = 32, 75

    def __init__(self, lo, hi):
        super().__init__()
        self.lo, self.hi = lo, hi
        self.setFixedHeight(40)

    def set_range(self, lo, hi):
        self.lo, self.hi = lo, hi
        self.update()

    def _x(self, value):
        span = self.MAX_H - self.MIN_H
        return max(0.0, min(1.0, (value - self.MIN_H) / span)) * self.width()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar = QRectF(0, 0, self.width(), 12)
        clip = QPainterPath()
        clip.addRoundedRect(bar, 6, 6)
        p.setClipPath(clip)
        p.setPen(Qt.PenStyle.NoPen)
        segments = [(self.MIN_H, self.lo - 6, "#ef9f27"), (self.lo - 6, self.lo, "#97c459"),
                    (self.lo, self.hi, "#639922"), (self.hi, self.MAX_H, "#27500a")]
        for a, b, color in segments:
            p.setBrush(QColor(color))
            p.drawRect(QRectF(self._x(a), 0, self._x(b) - self._x(a) + 0.5, 12))
        p.setClipping(False)

        font = p.font()
        font.setPixelSize(10)
        p.setFont(font)
        p.setPen(QColor(MUTED))
        for value in (self.lo, self.hi):
            x = self._x(value)
            p.drawText(QRectF(x - 20, 17, 40, 16), Qt.AlignmentFlag.AlignCenter, str(value))

class StandardsPage(QWidget):
    saved = Signal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.variety = QComboBox()
        self.variety.addItem(f"Variety: {STANDARDS['variety']}")
        top.addWidget(self.variety)
        top.addStretch()
        top.addWidget(Chip("Preliminary · not yet calibrated", "orange"))
        root.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(12)

        hue_card, hl = card(spacing=14)
        hl.addWidget(lbl("Leaf greenness (HSV hue)", 15, TEXT, "700"))
        hl.addWidget(lbl("Demo policy: median Hue for classification; CIELAB is supporting data; thresholds remain preliminary until field-camera calibration.", 11, MUTED))
        self.hue_lo = make_spin(0, 179, STANDARDS["hue"][0])
        self.hue_hi = make_spin(0, 179, STANDARDS["hue"][1])
        self.hue_bar = HueBar(*STANDARDS["hue"])
        hl.addWidget(self.hue_bar)
        hl.addLayout(range_row("Healthy range", self.hue_lo, self.hue_hi))
        hl.addStretch()
        self.hue_lo.valueChanged.connect(self._update_bar)
        self.hue_hi.valueChanged.connect(self._update_bar)
        grid.addWidget(hue_card, 0, 0)

        height_card, gl = card(spacing=14)
        gl.addWidget(lbl("Plant height at PI", 15, TEXT, "700"))
        self.h_lo = make_spin(0, 300, STANDARDS["height"][0])
        self.h_hi = make_spin(0, 300, STANDARDS["height"][1])
        gl.addLayout(range_row("Healthy range", self.h_lo, self.h_hi, "cm"))
        gl.addLayout(kv_row("Camera pole height", lbl(f"{STANDARDS['pole']} m", 13, TEXT, "700")))
        gl.addStretch()
        grid.addWidget(height_card, 0, 1)

        cap_card, cl = card(spacing=14)
        cl.addWidget(lbl("Capture settings", 15, TEXT, "700"))
        self.gps_n = make_spin(1, 30, STANDARDS["gps_n"])
        self.tilt = make_spin(1, 45, STANDARDS["tilt"], "°")
        cl.addLayout(kv_row("GPS readings per capture", self.gps_n))
        cl.addLayout(kv_row("Tilt limit", self.tilt))
        cl.addStretch()
        grid.addWidget(cap_card, 1, 0)

        log_card, ll = card(spacing=14)
        ll.addWidget(lbl("Calibration log", 15, TEXT, "700"))
        ll.addLayout(kv_row("Validated by", lbl("Sir Jasper Talada", 13, TEXT, "700")))
        ll.addLayout(kv_row("Last update", lbl("Pending field test", 13, TEXT, "700")))
        self.save_btn = button("Save standards", "primary")
        self.save_btn.clicked.connect(self._save)
        ll.addWidget(self.save_btn)
        ll.addStretch()
        grid.addWidget(log_card, 1, 1)

        for c in (0, 1):
            grid.setColumnStretch(c, 1)
        root.addLayout(grid)
        root.addStretch()

    def _update_bar(self):
        self.hue_bar.set_range(self.hue_lo.value(), self.hue_hi.value())

    def _save(self):
        STANDARDS["hue"] = tuple(sorted((self.hue_lo.value(), self.hue_hi.value())))
        STANDARDS["height"] = tuple(sorted((self.h_lo.value(), self.h_hi.value())))
        STANDARDS["gps_n"] = self.gps_n.value()
        STANDARDS["tilt"] = self.tilt.value()
        self.saved.emit()
        self.save_btn.setText("Saved ✓")
        QTimer.singleShot(1500, lambda: self.save_btn.setText("Save standards"))