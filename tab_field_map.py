from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolTip, QVBoxLayout, QWidget
from common import GREEN, GREEN_DARK, MUTED, RED_PIN, Chip, button, lbl

class FieldMap(QWidget):
    open_record = Signal(str)

    PINS = [
        dict(id="A-01-03", x=.153, y=.46, bad=False, r=6, acc=1.6, when="10:12 AM", detail="99.4 cm · hue 58 · green"),
        dict(id="A-03-01", x=.231, y=.54, bad=False, r=6, acc=1.9, when="10:31 AM", detail="99.9 cm · hue 60 · green"),
        dict(id="A-03-02", x=.328, y=.47, bad=False, r=6, acc=1.4, when="10:44 AM", detail="98.7 cm · hue 55 · green"),
        dict(id="A-02-02", x=.634, y=.48, bad=True, r=6, acc=2.1, when="10:59 AM", detail="100.1 cm · hue 68 · dark green"),
        dict(id="A-02-06", x=.823, y=.54, bad=True, r=9, acc=1.8, when="11:53 AM", detail="96.2 cm · hue 47 · light green"),
    ]

    def __init__(self):
        super().__init__()
        self.selected = "A-02-06"
        self.setMouseTracking(True)
        self.setMinimumHeight(240)

    def counts(self):
        bad = sum(1 for pin in self.PINS if pin["bad"])
        return len(self.PINS) - bad, bad

    def select(self, pin_id):
        self.selected = pin_id
        self.update()

    def _pos(self, pin):
        return QPointF(pin["x"] * self.width(), pin["y"] * self.height())

    def _pin_at(self, point):
        for pin in reversed(self.PINS):
            c = self._pos(pin)
            if (c.x() - point.x()) ** 2 + (c.y() - point.y()) ** 2 <= (pin["r"] + 4) ** 2:
                return pin
        return None

    def _selected_pin(self):
        return next((pin for pin in self.PINS if pin["id"] == self.selected), None)

    def _popup_rect(self, pin):
        pw, ph = 180, 56
        c = self._pos(pin)
        x = min(max(c.x() - pw * 0.61, 6), self.width() - pw - 6)
        y = c.y() + pin["r"] + 8
        if y + ph > self.height() - 6:
            y = c.y() - pin["r"] - 8 - ph
        return QRectF(x, y, pw, ph)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#eaf3de"))
        p.drawRoundedRect(QRectF(0, 0, w, h), 14, 14)

        plots = {
            "A-01": QRectF(.022 * w, .06 * h, .459 * w, .37 * h),
            "A-02": QRectF(.519 * w, .06 * h, .459 * w, .37 * h),
            "A-03": QRectF(.022 * w, .555 * h, .459 * w, .385 * h),
            "A-04": QRectF(.519 * w, .555 * h, .459 * w, .385 * h),
        }
        font = p.font()
        font.setPixelSize(11)
        font.setBold(True)
        p.setFont(font)
        for name, rect in plots.items():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#c0dd97"))
            p.drawRoundedRect(rect, 7, 7)
            p.setPen(QColor(GREEN_DARK))
            p.drawText(rect.adjusted(8, 6, 0, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, name)

        p.setPen(QPen(QColor("#8f8f87"), 1.4, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(w * 0.02, h * 0.505), QPointF(w * 0.98, h * 0.505))

        for pin in self.PINS:
            c = self._pos(pin)
            p.setPen(QPen(QColor("#eaf3de"), 2))
            p.setBrush(QColor(RED_PIN if pin["bad"] else GREEN))
            p.drawEllipse(c, pin["r"], pin["r"])

        sel = self._selected_pin()
        if sel:
            rect = self._popup_rect(sel)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ffffff"))
            p.drawRoundedRect(rect, 9, 9)

            body = rect.adjusted(10, 6, -8, -4)
            f1 = p.font()
            f1.setPixelSize(11)
            f1.setBold(True)
            p.setFont(f1)
            p.setPen(QColor("#1d1d1b"))
            p.drawText(body, Qt.AlignmentFlag.AlignTop, f"{sel['id']} · {sel['when']}")
            f2 = p.font()
            f2.setPixelSize(10)
            f2.setBold(False)
            p.setFont(f2)
            p.setPen(QColor("#5f5e5a"))
            p.drawText(body.adjusted(0, 16, 0, 0), Qt.AlignmentFlag.AlignTop, sel["detail"])
            p.setPen(QColor(RED_PIN if sel["bad"] else GREEN))
            verdict = "Needs inspection" if sel["bad"] else "Healthy"
            p.drawText(body.adjusted(0, 31, 0, 0), Qt.AlignmentFlag.AlignTop, f"{verdict} · open record")

    def mouseMoveEvent(self, event):
        pos = event.position()
        pin = self._pin_at(pos)
        sel = self._selected_pin()
        over_popup = bool(sel and self._popup_rect(sel).contains(pos))
        if pin:
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"{pin['id']}  ± {pin['acc']:.1f} m GPS accuracy", self)
        else:
            QToolTip.hideText()
        self.setCursor(Qt.CursorShape.PointingHandCursor if (pin or over_popup) else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        pos = event.position()
        sel = self._selected_pin()
        if sel and self._popup_rect(sel).contains(pos):
            self.open_record.emit(sel["id"])
            return
        pin = self._pin_at(pos)
        if pin:
            self.select(pin["id"])

class FieldMapPage(QWidget):
    open_record = Signal(str)

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(button("Jul 15, 2026  ▾", "filter"))
        top.addWidget(button("All statuses  ▾", "filter"))
        top.addStretch()
        top.addWidget(Chip("Cached tiles", "gray", "download"))
        root.addLayout(top)

        self.map = FieldMap()
        self.map.open_record.connect(self.open_record)
        root.addWidget(self.map, 1)

        healthy, needs = self.map.counts()
        legend = QHBoxLayout()
        legend.setSpacing(18)
        legend.addWidget(lbl(f"<span style='color:{GREEN}'>●</span> Healthy ({healthy})", 12, MUTED))
        legend.addWidget(lbl(f"<span style='color:{RED_PIN}'>●</span> Needs inspection ({needs})", 12, MUTED))
        legend.addWidget(lbl("± accuracy shown per pin on hover", 12, MUTED))
        legend.addStretch()
        root.addLayout(legend)

    def select(self, pin_id):
        self.map.select(pin_id)