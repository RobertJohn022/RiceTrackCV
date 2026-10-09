import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFrame, QButtonGroup, QStackedWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QSizePolicy, QFileDialog)

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

GREEN_BUTTON_STYLE = (
    "font-size: 16px; background-color: #7cb96f; color: white; border: 1px solid #5c9a4f;")
GRAY_BUTTON_STYLE = (
    "font-size: 16px; background-color: #999999; color: white; border: 1px solid #777777;")

def make_header(text): # Header
    """Returns (title_label, divider_line) for the header of a page."""
    title = QLabel(text)
    title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 12px; background-color: white;")
 
    divider = QFrame()
    divider.setFrameShape(QFrame.HLine)
    divider.setStyleSheet("color: black;")
 
    return title, divider
 
def make_vline():
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setStyleSheet("color: black;")
    return line

class ControlsPage(QWidget):
    def __init__(self, go_to_results):
        super().__init__()
        self.go_to_results = go_to_results  # switch pages
        self.setStyleSheet("background-color: #DDDDDD; color: black")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.latest_image_path = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
 
        title, divider = make_header("RiceTrack - Rover Control")
        main_layout.addWidget(title)
        main_layout.addWidget(divider)
 
        body = QHBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(20)
        main_layout.addLayout(body)
 
        body.addLayout(self._build_left_panel(), stretch=2)
        body.addLayout(self._build_right_panel(), stretch=1)
 
        main_layout.addStretch()

    # ========================================================================================== LEFT PANEL
    # ========================================================================================== Camera Display, GPS, IMU  (WIP) 
    def _build_left_panel(self):
        layout = QVBoxLayout()

        live_label = QLabel("Display:")
        live_label.setStyleSheet("font-size: 16px; color: black; border: 1px solid black")
        live_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        layout.addWidget(live_label)

        camera_box = QLabel("[Camera View]")
        camera_box.setAlignment(Qt.AlignCenter)
        camera_box.setStyleSheet(
            "background-color: white; border: 1px solid black; font-size: 18px; color: black"
        )
        camera_box.setMinimumHeight(480)
        layout.addWidget(camera_box)

        gps_box = QLabel("GPS: 15.671251° N, 120.894321° E")
        gps_box.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        gps_box.setStyleSheet(
            "background-color: white; border: 1px solid black; "
            "font-weight: bold; padding: 8px; color: black"
        )
        gps_box.setFixedHeight(40)
        layout.addWidget(gps_box)
        layout.setSpacing(12)

        return layout

    # ========================================================================================== RIGHT PANEL
    # ========================================================================================== Controls
    def _build_right_panel(self):
        layout = QVBoxLayout()

        self.controls_label = QLabel("Controls:")
        self.controls_label.setStyleSheet("font-size: 16px; color: black; border: 1px solid black")
        self.controls_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        layout.addWidget(self.controls_label)

        self.control_box = QLabel("[Manual]")
        # self.control_box.setAlignment(Qt.AlignTop)
        self.control_box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.control_box.setStyleSheet(
            "background-color: white; border: 1px solid black; font-size: 16px; color: black")
        self.control_box.setMinimumHeight(200)

        layout.addWidget(self.control_box)

        # ========================================================================================== Manual / Automatic toggle 
        btn_row = QHBoxLayout()
        self.manual_btn = QPushButton("Manual")
        self.automatic_btn = QPushButton("Automatic")

        for btn in (self.manual_btn, self.automatic_btn):
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn_row.addWidget(btn)
            btn_row.setAlignment(Qt.AlignBottom)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.manual_btn)
        self.mode_group.addButton(self.automatic_btn)
        self.manual_btn.setChecked(True)

        self.manual_btn.toggled.connect(self._update_mode_display)
        self.automatic_btn.toggled.connect(self._update_mode_display)

        # layout.addLayout(btn_row)
        self.control_box.setLayout(btn_row)

        # ========================================================================================== Capture/Upload Image (WIP) 
        img_row = QHBoxLayout()

        capture_btn = QPushButton("Capture Image")
        capture_btn.setStyleSheet(GRAY_BUTTON_STYLE)
        capture_btn.setFixedHeight(40)
        img_row.addWidget(capture_btn)
        
        upload_btn = QPushButton("Upload Image")
        upload_btn.setStyleSheet(GRAY_BUTTON_STYLE)
        upload_btn.setFixedHeight(40)
        img_row.addWidget(upload_btn)
        upload_btn.clicked.connect(self._upload_image)

        layout.addLayout(img_row)

        # ========================================================================================== Latest capture box (WIP) 
        self.capture_label = QLabel("Latest Capture:")
        self.capture_label.setStyleSheet("font-size: 16px; color: black; border: 1px solid black; margin-top: 20px")
        self.capture_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        layout.addWidget(self.capture_label)
        
        self.capture_display = QLabel("No image uploaded yet")
        self.capture_display.setAlignment(Qt.AlignCenter)
        self.capture_display.setStyleSheet(
            "background-color: white; border: 1px solid black; color: black")
        self.capture_display.setMinimumHeight(150)
        self.capture_display.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.capture_display)

        results_btn = QPushButton("Results Tab")
        results_btn.setFixedHeight(40)
        results_btn.setMinimumWidth(400)
        results_btn.setStyleSheet(GREEN_BUTTON_STYLE)
        results_btn.clicked.connect(self.go_to_results)
        layout.addWidget(results_btn)
        
        self._update_mode_display()
        layout.setSpacing(12)
        return layout

    # ========================================================================================== BUTTON FUNCTIONALITIES
    # ========================================================================================== Manual / Automatic toggle: 
    def _update_mode_display(self):
        if self.automatic_btn.isChecked():
            self.controls_label.setText("Control: Automatic")
            self.control_box.setText("\nSet Distance: _5m_\n1. Idle\n2. Moving\n3. Capturing\n4. Analyzing")
        else:
            self.controls_label.setText("Control: Manual")
            self.control_box.setText("\nCONTROLS: \nForward/Backward: W/S\nLeft/Right: A/D\nCapture: Space")

        active_style = "font-size: 16px; background-color: #7cb96f; color: white; border: 1px solid #5c9a4f;"
        inactive_style = "font-size: 16px; background-color: #999999; color: white; border: 1px solid #777777;"

        self.manual_btn.setStyleSheet(
            active_style if self.manual_btn.isChecked() else inactive_style)
        self.automatic_btn.setStyleSheet(
            active_style if self.automatic_btn.isChecked() else inactive_style)

    # ========================================================================================== Upload and display img
    def _upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select an Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)" )
 
        if not file_path:
            return
 
        self.latest_image_path = file_path  # stores img
 
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.capture_display.setText("Could not load image")
            return
 
        scaled_pixmap = pixmap.scaled(
            self.capture_display.width(),
            self.capture_display.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.capture_display.setPixmap(scaled_pixmap)

# ==============================================================================================================
# ========================================================================================== Field Results
class ResultsPage(QWidget):
    def __init__(self, go_to_controls):
        super().__init__()
        self.go_to_controls = go_to_controls
        self.setStyleSheet("background-color: #DDDDDD; color: black")
        self.setAttribute(Qt.WA_StyledBackground, True)
 
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
 
        title, divider = make_header("RiceTrack - Survey Results")
        main_layout.addWidget(title)
        main_layout.addWidget(divider)
 
        main_layout.addLayout(self._build_stats_row())
 
        stats_divider = QFrame()
        stats_divider.setFrameShape(QFrame.HLine)
        stats_divider.setStyleSheet("color: black;")
        main_layout.addWidget(stats_divider)
 
        table_container = QVBoxLayout()
        table_container.setContentsMargins(0, 0, 0, 0)
        table_container.addWidget(self._build_table())
        main_layout.addLayout(table_container)
 
        main_layout.addStretch()
        main_layout.addLayout(self._build_nav_row())

 # ========================================================================================== Overview
    def _build_stats_row(self):
        row = QHBoxLayout()
        row.setSpacing(0)
        row.setContentsMargins(0, 0, 0, 0)
 
        row.addWidget(self._make_stat_column("Total Captures", 2))
        row.addWidget(make_vline())
        row.addWidget(self._make_stat_column("Healthy", 1))
        row.addWidget(make_vline())
        row.addWidget(self._make_stat_column("Needs Inspection", 1))
        return row
 
    def _make_stat_column(self, title, value):
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(25, 15, 25, 15)
 
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px;")
 
        value_label = QLabel(str(value))
        value_label.setStyleSheet("font-size: 30px;")
 
        col.addWidget(title_label)
        col.addWidget(value_label)
        return box

 # ========================================================================================== Table
    def _build_table(self):
        columns = ["Time", "Location", "Rice Variety", "Height", "Leaf Color", "Status"]
        # Placeholder rows
        data = [
            ("00:00 PM", "Plot A-02", "Tubigan 18", "100 cm", "Green", "Healthy"),
            ("00:00 PM", "Plot A-02", "Tubigan 18", "100 cm", "Yellow Green", "Needs Inspection"), ]
 
        table = QTableWidget(len(data), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setShowGrid(False)
 
        table.horizontalHeader().setStyleSheet(
            "QHeaderView::section {"
            "  background-color: #AAAAAA; font-weight: bold;"
            "  padding: 8px; border: none;"
            "}" )
        table.setStyleSheet(
            "QTableWidget { background-color: #DDDDDD; border: none; }"
            "QTableWidget::item { padding: 8px; border-bottom: 1px solid black; }" )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
 
        row_height = 40
        table.verticalHeader().setDefaultSectionSize(row_height)
        for r, entries in enumerate(data):
            for c, text in enumerate(entries):
                table.setItem(r, c, QTableWidgetItem(text))
 
        table.setFixedHeight(table.horizontalHeader().sizeHint().height() + row_height * len(data) + 4)
        return table
 
    def _build_nav_row(self):
        row = QHBoxLayout()
        row.setContentsMargins(20, 10, 20, 20)
 
        controls_btn = QPushButton("Controls Tab")
        controls_btn.setFixedHeight(35)
        controls_btn.setMinimumWidth(400)
        controls_btn.setStyleSheet(GREEN_BUTTON_STYLE)
        controls_btn.clicked.connect(self.go_to_controls)
 
        row.addStretch()
        row.addWidget(controls_btn)
        row.addStretch()
        return row

# ========================================================================================== Main Window - switche between pages
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiceTrack")
        self.resize(1250, 700)
 
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
 
        self.controls_page = ControlsPage(go_to_results=self.show_results)
        self.results_page = ResultsPage(go_to_controls=self.show_controls)
 
        self.stack.addWidget(self.controls_page)  # index 0
        self.stack.addWidget(self.results_page)   # index 1
 
    def show_results(self):
        self.stack.setCurrentWidget(self.results_page)
 
    def show_controls(self):
        self.stack.setCurrentWidget(self.controls_page)

# ========================================================================================== Starts the app idk 
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()