import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QScrollArea)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

# ========================================================================================== Build UI
class LccSegmentAnalysis(QWidget):
    def __init__(self, default_image_path='images/lcc.jpg'):
        super().__init__()
        self.setWindowTitle("Leaf Color Chart - Advanced Segmentation")
        self.resize(600, 800)
        
        main_layout = QVBoxLayout(self)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.img_label)

        upload_btn = QPushButton("Select Image")
        upload_btn.setFixedHeight(40)
        upload_btn.clicked.connect(self._upload_image)
        main_layout.addWidget(upload_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.stats_label = QLabel()
        self.stats_label.setTextFormat(Qt.RichText)
        self.scroll.setWidget(self.stats_label)
        main_layout.addWidget(self.scroll)

        self.process_and_display(default_image_path)

    def process_and_display(self, file_path):
        image = cv2.imread(file_path)
        if image is None:
            self.img_label.setText(f"Could not load image at '{file_path}'.")
            self.stats_label.setText("")
            return

        # ================================================================================ Segment green regions w/ HSV
        # Convert selected image to HSV and LAB
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Define HSV Thresholds
        lower_green = np.array([25, 30, 12])
        upper_green = np.array([85, 255, 255])
        raw_mask = cv2.inRange(hsv, lower_green, upper_green)

        # Clean up mask noise, removes samll noise artifacts in 5x5 area
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel_clean)

        # Find and filter individual panel contours
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (image.shape[0] * image.shape[1]) * 0.015  # min 1.5% of total area
        panel_contours = [c for c in contours if cv2.contourArea(c) > min_area]

        # Sort panels
        panel_contours = sorted(panel_contours, key=lambda c: cv2.boundingRect(c)[0])

        # Core Erosion & Per-Panel Statistics
        final_mask = np.zeros_like(cleaned_mask)
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        stats_html = "<h2>Panel Color and Hue Testing</h2>"

        for idx, cnt in enumerate(panel_contours):
            # Mask single panel
            single_mask = np.zeros_like(cleaned_mask)
            cv2.drawContours(single_mask, [cnt], -1, 255, thickness=cv2.FILLED)

            # Erode boundary inward by ~15 pixels to strip edges/shadows automatically
            eroded_single = cv2.erode(single_mask, kernel_erode, iterations=2)
            final_mask = cv2.bitwise_or(final_mask, eroded_single)

            # ================================================================================ Compute results for each segmented panel
            # Extract pixels inside the clean core
            p_bgr = image[eroded_single > 0]
            p_hsv = hsv[eroded_single > 0]
            p_lab = lab[eroded_single > 0]

            if p_bgr.size > 0:
                # Use Median to resist glare/specular highlights
                med_b, med_g, med_r = np.median(p_bgr, axis=0)
                med_h, med_s, med_v = np.median(p_hsv, axis=0)
                med_l, med_a, med_b_lab = np.median(p_lab, axis=0)
                hues = p_hsv[:, 0]

                panel_id = idx + 1
                stats_html += (
                    f"<b>PANEL {panel_id}:</b><br>"
                    f"<b>Median BGR:</b> B: {med_b:.1f}, G: {med_g:.1f}, R: {med_r:.1f}<br>"
                    f"<b>Median HSV:</b> H: {med_h:.1f}, S: {med_s:.1f}, V: {med_v:.1f}<br>"
                    f"<b>Median Lab:</b> L*: {med_l:.1f}, a*: {med_a:.1f}, b*: {med_b_lab:.1f}<br>"
                    f"<b>Hue Range:</b> Avg: {hues.mean():.1f} | Min: {hues.min()} | Max: {hues.max()}<br><br>"
                )

        if not panel_contours:
            stats_html = "<p>No green panels detected. Check HSV bounds or image quality.</p>"

        self.stats_label.setText(stats_html)

        # ================================================================================ Render segmented visual output
        segmented = cv2.bitwise_and(image, image, mask=final_mask)
        rgb = cv2.cvtColor(segmented, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaledToHeight(300, Qt.SmoothTransformation)
        self.img_label.setPixmap(pixmap)

    def _upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select LCC Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.process_and_display(file_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LccSegmentAnalysis('images/lcc.jpg')
    window.show()
    sys.exit(app.exec())