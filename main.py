import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLineEdit, QTextEdit, QLabel
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Rice Track')
        self.resize(500, 400)

        self.serial_conn = None  # will hold the pyserial connection

        # ---- Widgets ----
        self.port_dropdown = QComboBox()

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
        # self.refresh_btn.clicked.connect(self.refresh_ports)
        # self.connect_btn.clicked.connect(self.toggle_connection)
        # self.send_btn.clicked.connect(self.send_data)
        # self.input_line.returnPressed.connect(self.send_data)

app = QApplication()
window = MainWindow()
window.show()
app.exec()


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec())