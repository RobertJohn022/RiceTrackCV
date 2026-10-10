from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
)

BG = "#151515"
CARD = "#1a1a19"
LINE = "#2d2d2d"
TEXT = "#f0efec"
MUTED = "#b9b8ae"
GREEN = "#3b6d11"
GREEN_DARK = "#27500a"
GOOD = "#12a812"

RED_BG, RED_TEXT, RED_LINE, RED_PIN = "#3c0e0e", "#ec7e7e", "#5a1c1c", "#a32d2d"
WARN_BG, WARN_TEXT, WARN_LINE = "#311a00", "#d89400", "#4a2c00"
BLUE_BG, BLUE_TEXT, BLUE = "#032042", "#6b9fdc", "#378add"

CHIP_COLORS = {
    "gray":   (CARD, MUTED),
    "green":  ("#11260f", GOOD),
    "orange": (WARN_BG, WARN_TEXT),
    "red":    (RED_BG, RED_TEXT),
    "blue":   (BLUE_BG, BLUE_TEXT),
}

# Calibrated to IRRI 4-panel LCC standards for standard inbreds (NSIC Rc 222 / Tubigan 18)
STANDARDS = {
    "variety": "NSIC Rc 222 (Tubigan 18)",
    "hue": (50, 75),  # Healthy/Optimal greenness band (LCC Panels 4 & 5)
    "height": (98, 101),
    "pole": 1.2,
    "gps_n": 5,
    "tilt": 15,
}

APP_QSS = f"""
* {{ font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif; }}
QWidget#root {{ background: {BG}; }}
QStackedWidget {{ background: transparent; }}
QLabel {{ background: transparent; color: {TEXT}; font-size: 13px; }}

QFrame[card="true"]  {{ background: {CARD}; border-radius: 14px; }}
QFrame[inset="true"] {{ background: {BG};   border-radius: 10px; }}

QPushButton[nav="true"] {{
    text-align: left; padding: 9px 12px; color: #e3eed8; background: transparent;
    border: none; border-radius: 17px; font-size: 13px; font-weight: 600; }}
QPushButton[nav="true"]:hover   {{ background: rgba(255,255,255,0.10); }}
QPushButton[nav="true"]:checked {{ background: #ffffff; color: {GREEN_DARK}; }}

QPushButton[btn="dark"] {{
    background: {BG}; color: {TEXT}; border: 1px solid {LINE}; border-radius: 10px;
    padding: 9px 14px; font-size: 13px; font-weight: 600; }}
QPushButton[btn="dark"]:hover {{ background: #232322; }}
QPushButton[btn="primary"] {{
    background: {GREEN}; color: #ffffff; border: none; border-radius: 10px;
    padding: 11px 14px; font-size: 14px; font-weight: 600; }}
QPushButton[btn="primary"]:hover    {{ background: #4a8516; }}
QPushButton[btn="primary"]:disabled {{ background: #293f16; color: #818181; }}
QPushButton[btn="pad"] {{
    background: {BG}; color: {TEXT}; border: 1px solid {LINE}; border-radius: 17px; font-size: 15px; }}
QPushButton[btn="pad"]:hover   {{ background: #252524; }}
QPushButton[btn="pad"]:pressed {{ background: {GREEN}; }}
QPushButton[btn="seg"] {{
    background: transparent; color: {MUTED}; border: none; border-radius: 14px;
    padding: 6px 18px; font-size: 13px; font-weight: 600; }}
QPushButton[btn="seg"]:checked {{ background: {GREEN}; color: #ffffff; }}
QPushButton[btn="filter"] {{
    background: {CARD}; color: {MUTED}; border: none; border-radius: 14px;
    padding: 6px 14px; font-size: 12px; font-weight: 600; }}
QPushButton[btn="filter"]:hover {{ background: #232322; }}
QPushButton[btn="filter-red"] {{
    background: {RED_BG}; color: {RED_TEXT}; border: none; border-radius: 14px;
    padding: 6px 14px; font-size: 12px; font-weight: 600; }}

QFrame[row="true"] {{ background: transparent; border: none; border-bottom: 1px solid {LINE}; }}
QFrame[row="true"][selected="true"] {{ background: {BG}; border-radius: 8px; border-bottom: 1px solid {LINE}; }}

QProgressBar {{ background: #333332; border: none; border-radius: 2px; min-height: 4px; max-height: 4px; }}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 2px; }}
QSpinBox {{ background: {CARD}; border: 1px solid #555554; border-radius: 8px; color: {TEXT};
    padding: 2px 4px; font-size: 13px; }}
QComboBox {{ background: {CARD}; border: none; border-radius: 14px; padding: 6px 14px;
    color: {MUTED}; font-size: 12px; font-weight: 600; }}
QComboBox QAbstractItemView {{ background: {CARD}; color: {TEXT}; selection-background-color: {GREEN}; }}
QToolTip {{ background: #ffffff; color: #222222; border: none; padding: 4px 6px; }}
"""

def set_prop(widget, name, value):
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)

def lbl(text="", size=13, color=TEXT, weight=None, align=None, wrap=False):
    label = QLabel(text)
    css = f"font-size: {size}px; color: {color};"
    if weight:
        css += f" font-weight: {weight};"
    label.setStyleSheet(css)
    if align is not None:
        label.setAlignment(align)
    label.setWordWrap(wrap)
    return label

def card(margins=(18, 16, 18, 16), spacing=12):
    frame = QFrame()
    frame.setProperty("card", "true")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout

def kv_row(name, value_widget, name_color=MUTED):
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(lbl(name, 13, name_color))
    row.addStretch()
    row.addWidget(value_widget)
    return row

def button(text, kind="dark", icon=None, icon_color=TEXT, checkable=False):
    btn = QPushButton(text)
    btn.setProperty("btn", kind)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon:
        btn.setIcon(QIcon(make_pixmap(icon, icon_color, 16)))
        btn.setIconSize(QSize(16, 16))
    btn.setCheckable(checkable)
    return btn

def make_pixmap(kind, color, size=18):
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 18.0, size / 18.0)
    c = QColor(color)
    pen = QPen(c, 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    def poly(*pts, closed=False):
        path = QPainterPath(QPointF(*pts[0]))
        for pt in pts[1:]:
            path.lineTo(QPointF(*pt))
        if closed:
            path.closeSubpath()
        p.drawPath(path)

    def line(x1, y1, x2, y2):
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def filled():
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)

    if kind == "leaf":
        path = QPainterPath(QPointF(3, 15))
        path.cubicTo(1.5, 5.5, 9, 2, 16, 2.5)
        path.cubicTo(16, 10, 10.5, 15.5, 3, 15)
        p.drawPath(path)
        line(3, 15, 10, 8)
    elif kind == "wheel":
        p.drawEllipse(QRectF(2, 2, 14, 14))
        p.drawEllipse(QRectF(7.5, 7.5, 3, 3))
        line(2.5, 9, 7.5, 9)
        line(10.5, 9, 15.5, 9)
        line(9, 10.5, 9, 15.5)
    elif kind == "map":
        poly((2, 4.5), (6.5, 3), (11.5, 5), (16, 3.5), (16, 13.5), (11.5, 15), (6.5, 13), (2, 14.5), closed=True)
        line(6.5, 3, 6.5, 13)
        line(11.5, 5, 11.5, 15)
    elif kind == "list":
        for y in (5, 9, 13):
            p.drawEllipse(QRectF(2.8, y - 0.7, 1.4, 1.4))
            line(7, y, 15.5, y)
    elif kind == "chart":
        poly((2.5, 2.5), (2.5, 15.5), (15.5, 15.5))
        poly((5.5, 12), (9, 8), (11.5, 10), (15, 5))
    elif kind == "sliders":
        for x, y in ((4, 6), (9, 12), (14, 8)):
            line(x, 3, x, 15)
            p.setBrush(c)
            p.drawEllipse(QPointF(x, y), 2, 2)
            p.setBrush(Qt.BrushStyle.NoBrush)
    elif kind == "battery":
        p.drawRoundedRect(QRectF(1.5, 5, 12, 8), 1.8, 1.8)
        filled()
        p.drawRect(QRectF(14, 7.5, 1.8, 3))
        p.drawRoundedRect(QRectF(3.3, 6.8, 5, 4.4), 0.8, 0.8)
    elif kind == "signal":
        filled()
        for x, top in ((2.5, 11), (6.3, 8), (10.1, 5), (13.9, 2)):
            p.drawRoundedRect(QRectF(x, top, 2.4, 15 - top), 0.8, 0.8)
    elif kind == "wifi":
        for r in (3, 6.5, 10):
            p.drawArc(QRectF(9 - r, 14 - r, 2 * r, 2 * r), 45 * 16, 90 * 16)
        filled()
        p.drawEllipse(QPointF(9, 14), 1, 1)
    elif kind == "target":
        p.drawEllipse(QRectF(3.5, 3.5, 11, 11))
        line(9, 0.8, 9, 3.5)
        line(9, 14.5, 9, 17.2)
        line(0.8, 9, 3.5, 9)
        line(14.5, 9, 17.2, 9)
        filled()
        p.drawEllipse(QPointF(9, 9), 1.5, 1.5)
    elif kind == "download":
        line(9, 2.5, 9, 11.5)
        poly((5, 8), (9, 12), (13, 8))
        line(3, 15.5, 15, 15.5)
    elif kind == "file":
        poly((4, 2), (10.5, 2), (14.5, 6), (14.5, 16), (4, 16), closed=True)
        poly((10.5, 2), (10.5, 6), (14.5, 6))
    elif kind == "info":
        p.drawEllipse(QRectF(2, 2, 14, 14))
        line(9, 8, 9, 12.5)
        filled()
        p.drawEllipse(QPointF(9, 5.6), 0.9, 0.9)
    elif kind == "hand":
        p.drawRoundedRect(QRectF(4.5, 8, 9, 7.5), 2, 2)
        for x in (6.75, 9, 11.25):
            line(x, 3.5, x, 8)
    elif kind == "pause":
        filled()
        p.drawRoundedRect(QRectF(4.5, 3.5, 3, 11), 1, 1)
        p.drawRoundedRect(QRectF(10.5, 3.5, 3, 11), 1, 1)
    elif kind == "play":
        filled()
        p.drawPolygon(QPolygonF([QPointF(5, 3.5), QPointF(14, 9), QPointF(5, 14.5)]))
    elif kind == "check":
        poly((4, 9.5), (7.5, 13), (14, 5.5))
    elif kind == "close":
        line(4.5, 4.5, 13.5, 13.5)
        line(13.5, 4.5, 4.5, 13.5)

    p.end()
    return pm

class Chip(QFrame):
    def __init__(self, text, kind="gray", icon=None):
        super().__init__()
        bg, fg = CHIP_COLORS[kind]
        self.setObjectName("chip")
        self.setStyleSheet(f"QFrame#chip {{ background: {bg}; border-radius: 13px; }}")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 5, 11, 5)
        layout.setSpacing(6)
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(make_pixmap(icon, fg, 14))
            icon_label.setFixedSize(14, 14)
            layout.addWidget(icon_label)
        self._text = lbl(text, 12, fg, "600")
        layout.addWidget(self._text)

    def set_kind(self, kind):
        bg, fg = CHIP_COLORS[kind]
        self.setStyleSheet(f"QFrame#chip {{ background: {bg}; border-radius: 13px; }}")
        self._text.setStyleSheet("font-size: 12px; font-weight: 600; color: " + fg + ";")

    def set_text(self, text, kind=None):
        if kind is not None:
            self.set_kind(kind)
        self._text.setText(text)

def pill(text, kind):
    bg, fg = CHIP_COLORS[kind]
    label = QLabel(text)
    label.setStyleSheet(
        f"background: {bg}; color: {fg}; border-radius: 11px; padding: 3px 11px; "
        f"font-size: 12px; font-weight: 600;")
    holder = QWidget()
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(label)
    lay.addStretch()
    return holder

def banner(kind, icon=None):
    bg, line_c, fg = {"red": (RED_BG, RED_LINE, RED_TEXT),
                      "orange": (WARN_BG, WARN_LINE, WARN_TEXT)}[kind]
    frame = QFrame()
    frame.setObjectName("banner")
    frame.setStyleSheet(
        f"QFrame#banner {{ background: {bg}; border: 1px solid {line_c}; border-radius: 10px; }}")
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(8)
    if icon:
        icon_label = QLabel()
        icon_label.setPixmap(make_pixmap(icon, fg, 16))
        lay.addWidget(icon_label)
    text = lbl("", 13, fg)
    lay.addWidget(text, 1)
    return frame, text

class _Row(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class DataTable(QWidget):
    row_selected = Signal(int)

    def __init__(self, columns, weights, selectable=False, row_height=46):
        super().__init__()
        self.weights = weights
        self.selectable = selectable
        self.row_height = row_height
        self._rows = []
        self._selected = -1

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        header = _Row()
        header.setProperty("row", "true")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 14, 0)
        hl.setSpacing(8)
        header.setFixedHeight(38)
        for name, weight in zip(columns, weights):
            label = lbl(name, 12, MUTED)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            hl.addWidget(label, weight)
        self._layout.addWidget(header)

    @staticmethod
    def _cell(spec):
        if isinstance(spec, QWidget):
            spec.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            return spec
        if isinstance(spec, tuple):
            text, color, bold = (list(spec) + [None, None])[:3]
        else:
            text, color, bold = spec, None, False
        label = lbl(str(text), 13, color or TEXT, "600" if bold else None)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        return label

    def set_rows(self, rows):
        for row in self._rows:
            self._layout.removeWidget(row)
            row.deleteLater()
        self._rows = []
        self._selected = -1

        for index, cells in enumerate(rows):
            row = _Row()
            row.setProperty("row", "true")
            row.setFixedHeight(self.row_height)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 0, 14, 0)
            rl.setSpacing(8)
            for spec, weight in zip(cells, self.weights):
                rl.addWidget(self._cell(spec), weight)
            if self.selectable:
                row.setCursor(Qt.CursorShape.PointingHandCursor)
                row.clicked.connect(lambda i=index: self.select(i))
            self._layout.addWidget(row)
            self._rows.append(row)

    def select(self, index):
        if not self.selectable or not (0 <= index < len(self._rows)):
            return
        if 0 <= self._selected < len(self._rows):
            set_prop(self._rows[self._selected], "selected", "false")
        self._selected = index
        set_prop(self._rows[index], "selected", "true")
        self.row_selected.emit(index)