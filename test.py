import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLineEdit, QTextEdit, QLabel
)
import serial
import serial.tools.list_ports


class ESP32SerialWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP32 Serial Monitor")
        self.resize(500, 400)

        self.serial_conn = None  # will hold the pyserial connection

        # ---- Widgets ----
        self.port_dropdown = QComboBox()
        self.refresh_ports()

        self.refresh_btn = QPushButton("Refresh")
        self.connect_btn = QPushButton("Connect")

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type a command to send...")
        self.send_btn = QPushButton("Send")

        # ---- Layout ----
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Port:"))
        top_row.addWidget(self.port_dropdown)
        top_row.addWidget(self.refresh_btn)
        top_row.addWidget(self.connect_btn)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.input_line)
        bottom_row.addWidget(self.send_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_row)
        main_layout.addWidget(self.output_box)
        main_layout.addLayout(bottom_row)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # ---- Signal connections ----
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.send_btn.clicked.connect(self.send_data)
        self.input_line.returnPressed.connect(self.send_data)

        # ---- Timer to poll for incoming serial data ----
        self.poll_timer = QTimer()
        self.poll_timer.setInterval(50)  # check every 50 ms
        self.poll_timer.timeout.connect(self.read_serial)

    def refresh_ports(self):
        """Scan the system for available COM/serial ports and list them."""
        self.port_dropdown.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_dropdown.addItem(p.device)

    def toggle_connection(self):
        """Connect to or disconnect from the selected serial port."""
        if self.serial_conn is None:
            port = self.port_dropdown.currentText()
            if not port:
                self.output_box.append("[!] No port selected.")
                return
            try:
                self.serial_conn = serial.Serial(port, baudrate=115200, timeout=0)
                self.output_box.append(f"[+] Connected to {port}")
                self.connect_btn.setText("Disconnect")
                self.poll_timer.start()
            except serial.SerialException as e:
                self.output_box.append(f"[!] Failed to connect: {e}")
                self.serial_conn = None
        else:
            self.poll_timer.stop()
            self.serial_conn.close()
            self.serial_conn = None
            self.output_box.append("[-] Disconnected.")
            self.connect_btn.setText("Connect")

    def send_data(self):
        """Send whatever is typed in the input box to the ESP32."""
        if self.serial_conn is None:
            self.output_box.append("[!] Not connected.")
            return
        text = self.input_line.text()
        if not text:
            return
        self.serial_conn.write((text + "\n").encode("utf-8"))
        self.output_box.append(f">> {text}")
        self.input_line.clear()

    def read_serial(self):
        """Called repeatedly by the timer; reads any waiting bytes."""
        if self.serial_conn and self.serial_conn.in_waiting:
            raw = self.serial_conn.readline()
            try:
                line = raw.decode("utf-8", errors="replace").strip()
            except Exception:
                line = str(raw)
            if line:
                self.output_box.append(line)

    def closeEvent(self, event):
        """Make sure the serial port is closed cleanly when the window shuts."""
        if self.serial_conn:
            self.serial_conn.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ESP32SerialWindow()
    window.show()
    sys.exit(app.exec())