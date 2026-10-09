import sys

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


def segment_vegetation(img_bgr: np.ndarray) -> np.ndarray:
    b, g, r = cv2.split(img_bgr.astype(np.float32))
    exg = 2 * g - r - b
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, mask = cv2.threshold(exg_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.bitwise_and(mask, cv2.inRange(hsv[:, :, 1], 30, 255))  # saturation
    mask = cv2.bitwise_and(mask, cv2.inRange(hsv[:, :, 2], 15, 250))  # value

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def overlay_mask(img_bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    overlay = img_bgr.copy()
    overlay[mask > 0] = (0, 0, 255)  # highlight segmented
    return cv2.addWeighted(img_bgr, 1 - alpha, overlay, alpha, 0)


def cv_to_qpixmap(img_bgr: np.ndarray) -> QPixmap:
    rgb = np.ascontiguousarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


class SegmentationViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiceTrack - Segmentation Viewer")
        self.resize(900, 650)

        self.original_bgr: np.ndarray | None = None
        self.segmented_bgr: np.ndarray | None = None
        self.showing_segmented = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        buttons = QHBoxLayout()
        self.select_btn = QPushButton("Select Image")
        self.select_btn.clicked.connect(self.select_image)
        buttons.addWidget(self.select_btn)

        self.segment_btn = QPushButton("Segment Image")
        self.segment_btn.clicked.connect(self.segment_image)
        self.segment_btn.setEnabled(False)
        buttons.addWidget(self.segment_btn)

        self.toggle_btn = QPushButton("Toggle Segmented View")
        self.toggle_btn.clicked.connect(self.toggle_view)
        self.toggle_btn.setEnabled(False)
        buttons.addWidget(self.toggle_btn)

        buttons.addStretch()
        layout.addLayout(buttons)

        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color:#222; color:#ccc; border:1px solid #444;"
        )
        self.image_label.setMinimumSize(500, 400)
        layout.addWidget(self.image_label, stretch=1)

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            QMessageBox.warning(self, "Error:", "No image")
            return

        self.original_bgr = img
        self.segmented_bgr = None
        self.showing_segmented = False
        self.toggle_btn.setEnabled(False)
        self.segment_btn.setEnabled(True)
        self._display(img)

    def segment_image(self):
        if self.original_bgr is None:
            return
        mask = segment_vegetation(self.original_bgr)
        self.segmented_bgr = overlay_mask(self.original_bgr, mask)
        self.showing_segmented = True
        self.toggle_btn.setEnabled(True)
        self._display(self.segmented_bgr)

    def toggle_view(self):
        if self.segmented_bgr is None:
            return
        self.showing_segmented = not self.showing_segmented
        self._display(self.segmented_bgr if self.showing_segmented else self.original_bgr)

    def _display(self, img_bgr: np.ndarray):
        pixmap = cv_to_qpixmap(img_bgr)
        scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_bgr is not None:
            current = self.segmented_bgr if (self.showing_segmented and self.segmented_bgr is not None) else self.original_bgr
            self._display(current)


def main():
    app = QApplication(sys.argv)
    window = SegmentationViewer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()