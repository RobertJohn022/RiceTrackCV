import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt


class RoverControlWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiceTrack - Rover Control")
        self.resize(800, 400)

        # ========================================================================================== Setup ===============
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background-color: #d9d9d9;")

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========================================================================================== Header ===============
        title = QLabel("RiceTrack - Rover Control")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 15px; color: black")
        main_layout.addWidget(title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: black;")
        main_layout.addWidget(divider)

        # =========================================================================== Body: left - display. right - controls ===============
        body = QHBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(20)
        main_layout.addLayout(body)

        body.addLayout(self._build_left_panel(), stretch=2)
        body.addLayout(self._build_right_panel(), stretch=1)

    # =========================================================================== LEFT - Display, GPS, IMU  (WIP) ===============
    def _build_left_panel(self):
        layout = QVBoxLayout()

        live_label = QLabel("Display:")
        live_label.setStyleSheet("font-size: 16px; color: black")
        layout.addWidget(live_label)

        camera_box = QLabel("[Camera View]")
        camera_box.setAlignment(Qt.AlignCenter)
        camera_box.setStyleSheet(
            "background-color: white; border: 1px solid black; font-size: 18px; color: black"
        )
        camera_box.setMinimumHeight(400)
        layout.addWidget(camera_box)

        gps_box = QLabel("GPS:")
        gps_box.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        gps_box.setStyleSheet(
            "background-color: white; border: 1px solid black; "
            "font-weight: bold; padding: 8px; color: black"
        )
        gps_box.setFixedHeight(45)
        layout.addWidget(gps_box)

        return layout

    # ========================================================================================== RIGHT - Controls, Short Info (WIP) ===============
    def _build_right_panel(self):
        layout = QVBoxLayout()

        controls_label = QLabel("Controls:")
        controls_label.setStyleSheet("font-size: 16px; color: black")
        layout.addWidget(controls_label)

        # Text Area depending on chosen control mode
        self.status_box = QLabel("[Manual]")
        self.status_box.setAlignment(Qt.AlignCenter)
        self.status_box.setStyleSheet(
            "background-color: white; border: 1px solid black; font-size: 18px; color: black"
        )
        self.status_box.setMinimumHeight(180)
        layout.addWidget(self.status_box)

        # ========================================================================================== Manual / Automatic toggle ===============
        btn_row = QHBoxLayout()

        self.manual_btn = QPushButton("Manual")
        self.automatic_btn = QPushButton("Automatic")

        for btn in (self.manual_btn, self.automatic_btn):
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn_row.addWidget(btn)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.manual_btn)
        self.mode_group.addButton(self.automatic_btn)

        self.manual_btn.setChecked(True)

        # Refresh display when pressed
        self.manual_btn.toggled.connect(self._update_mode_display)
        self.automatic_btn.toggled.connect(self._update_mode_display)

        layout.addLayout(btn_row)

        # ========================================================================================== Capture Image (WIP) ===============
        capture_btn = QPushButton("Capture Image")
        capture_btn.setFixedHeight(35)
        capture_btn.setStyleSheet(
            "background-color: #7cb96f; color: white; border: 1px solid #5c9a4f;"
        )
        layout.addWidget(capture_btn)

        # ========================================================================================== Latest capture box (WIP) ===============
        latest_label = QLabel("LATEST CAPTURE:")
        latest_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        latest_label.setStyleSheet(
            "background-color: white; border: 1px solid black; "
            "font-weight: bold; padding: 8px; color: black"
        )
        latest_label.setMinimumHeight(150)
        layout.addWidget(latest_label)

        # Paint the buttons correctly right from the start
        self._update_mode_display()

        return layout

    # =========================================================================== Called whenever Manual or Automatic pressed: ===============
    def _update_mode_display(self):
        if self.automatic_btn.isChecked():
            self.status_box.setText("[Automatic]")
        else:
            self.status_box.setText("[Manual]")

        active_style = "background-color: #7cb96f; color: white; border: 1px solid #5c9a4f;"
        inactive_style = "background-color: #999999; color: white; border: 1px solid #777777;"

        self.manual_btn.setStyleSheet(
            active_style if self.manual_btn.isChecked() else inactive_style
        )
        self.automatic_btn.setStyleSheet(
            active_style if self.automatic_btn.isChecked() else inactive_style
        )


# =========================================================================== Starts the app idk ===============
def main():
    app = QApplication(sys.argv)
    window = RoverControlWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()