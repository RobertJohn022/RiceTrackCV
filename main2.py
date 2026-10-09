import sys
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget
)
from common import APP_QSS, GREEN, GREEN_DARK, STANDARDS, lbl, make_pixmap
from tab_control import ControlPage
from tab_field_map import FieldMapPage
from tab_records import RecordsPage
from tab_validation import ValidationPage
from tab_standards import StandardsPage

class Sidebar(QFrame):
    navigate = Signal(int)
    ITEMS = [("Control", "wheel"), ("Field map", "map"), ("Records", "list"),
             ("Validation", "chart"), ("Standards", "sliders")]

    def __init__(self, session="Session 07", user="PhilRice Muñoz", mode="Offline mode"):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self.setStyleSheet(f"QFrame#sidebar {{ background: {GREEN}; border-radius: 22px; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 14)
        layout.setSpacing(4)

        logo = QHBoxLayout()
        logo.setContentsMargins(6, 0, 0, 0)
        logo.setSpacing(8)
        leaf = QLabel()
        leaf.setPixmap(make_pixmap("leaf", "#ffffff", 20))
        logo.addWidget(leaf)
        logo.addWidget(lbl("RiceTrack", 17, "#ffffff", "700"))
        logo.addStretch()
        layout.addLayout(logo)
        layout.addSpacing(16)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for index, (name, icon) in enumerate(self.ITEMS):
            btn = QPushButton(name)
            btn.setProperty("nav", "true")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            icon_obj = QIcon()
            icon_obj.addPixmap(make_pixmap(icon, "#ffffff", 18), QIcon.Mode.Normal, QIcon.State.Off)
            icon_obj.addPixmap(make_pixmap(icon, GREEN_DARK, 18), QIcon.Mode.Normal, QIcon.State.On)
            btn.setIcon(icon_obj)
            btn.setIconSize(QSize(18, 18))
            self.group.addButton(btn, index)
            layout.addWidget(btn)
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(self.navigate)

        layout.addStretch()

        footer = QFrame()
        footer.setObjectName("session")
        footer.setStyleSheet(f"QFrame#session {{ background: {GREEN_DARK}; border-radius: 12px; }}")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(1)
        for text in (session, user, mode):
            fl.addWidget(lbl(text, 12, "#ffffff", "600"))
        layout.addWidget(footer)

    def set_current(self, index):
        self.group.button(index).setChecked(True)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiceTrack")
        self.resize(1280, 780)
        self.setMinimumSize(1040, 660)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)

        self.control_page = ControlPage()
        self.map_page = FieldMapPage()
        self.records_page = RecordsPage()
        self.control_page.record_saved.connect(lambda _record_id: self.records_page.refresh())
        self.validation_page = ValidationPage()
        self.standards_page = StandardsPage()
        
        for page in (self.control_page, self.map_page, self.records_page,
                     self.validation_page, self.standards_page):
            self.stack.addWidget(page)

        self.sidebar.navigate.connect(self._navigate)
        self.map_page.open_record.connect(self._open_record)
        self.standards_page.saved.connect(self._standards_saved)

    def _navigate(self, index):
        self.stack.setCurrentIndex(index)
        if self.stack.widget(index) is self.records_page:
            self.records_page.refresh()

    def _open_record(self, record_id):
        self.records_page.select(record_id)
        self.stack.setCurrentWidget(self.records_page)
        self.sidebar.set_current(2)

    def _standards_saved(self):
        self.control_page.set_tilt_limit(STANDARDS["tilt"])
        self.control_page.auto.set_progress(self.control_page.auto.stop, self.control_page.auto.step)
        self.records_page.refresh()

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()