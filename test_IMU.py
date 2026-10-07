import sys
import serial
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import QTimer

# change depending on port
PORT = "COM6"

esp = serial.Serial(PORT, 115200, timeout=0.1)
app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("Tilt Checker")
window.resize(250, 150)

layout = QVBoxLayout()

status_label = QLabel("Waiting...")
tilt_label = QLabel("Roll: 0 | Pitch: 0")

layout.addWidget(status_label)
layout.addWidget(tilt_label)
window.setLayout(layout)


def update():
    raw_data = esp.readline()

    if not raw_data:
        return

    # Safely decode UTF-8, ignoring non-ASCII/corrupted noise bytes
    try:
        line = raw_data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return

    if line == "":
        return

    try:
        roll, pitch = line.split(",")
        roll = float(roll)
        pitch = float(pitch)
    except ValueError:
        # Ignore lines that don't match the "roll,pitch" format
        return

    tilt_label.setText("Roll: " + str(round(roll, 1)) + "   ||   Pitch: " + str(round(pitch, 1)))

    if pitch < -20:
        status_label.setText("Tilted Left")
    elif pitch > 20:
        status_label.setText("Tilted Right")
    elif roll < -20:
        status_label.setText("Tilted Forward")
    elif roll > 20:
        status_label.setText("Tilted Backward")
    else:
        status_label.setText("Safe")
        
# run update() every 100 ms
timer = QTimer()
timer.timeout.connect(update)
timer.start(100)

window.show()
app.exec()