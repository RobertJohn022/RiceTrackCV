import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QScrollArea,
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

# Demo calibration experiment only:
# - The source image is an LCC image, not a RiceTrack camera capture.
# - The displayed panel labels are corrected to the LCC's actual numbering:
#   detected index 1 -> Panel 2, index 2 -> Panel 3, etc.
# - V >= 12 is a preliminary segmentation setting from the demo test.
# - Median Hue is the primary statistic; CIELAB is supporting information.


class LccSegmentAnalysis(QWidget):
    def __init__(self, default_image_path="images/lcc.jpg"):
        super().__init__()
        self.setWindowTitle("Leaf Color Chart - Demo Calibration")
        self.resize(760, 880)

        main_layout = QVBoxLayout(self)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.img_label)

        upload_btn = QPushButton("Select Image")
        upload_btn.setFixedHeight(40)
        upload_btn.clicked.connect(self._upload_image)
        main_layout.addWidget(upload_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.stats_label = QLabel()
        self.stats_label.setTextFormat(Qt.TextFormat.RichText)
        self.stats_label.setWordWrap(True)
        self.scroll.setWidget(self.stats_label)
        main_layout.addWidget(self.scroll)

        self.process_and_display(default_image_path)

    def process_and_display(self, file_path):
        image = cv2.imread(file_path)
        if image is None:
            self.img_label.setText(f"Could not load image at '{file_path}'.")
            self.stats_label.setText("")
            return

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Preliminary demo thresholds from the LCC test.
        lower_green = np.array([25, 30, 12])
        upper_green = np.array([85, 255, 255])
        raw_mask = cv2.inRange(hsv, lower_green, upper_green)

        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned_mask = cv2.morphologyEx(
            raw_mask, cv2.MORPH_OPEN, kernel_clean
        )

        contours, _ = cv2.findContours(
            cleaned_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        min_area = image.shape[0] * image.shape[1] * 0.015
        panel_contours = [
            c for c in contours if cv2.contourArea(c) > min_area
        ]
        panel_contours = sorted(
            panel_contours,
            key=lambda c: cv2.boundingRect(c)[0],
        )

        final_mask = np.zeros_like(cleaned_mask)
        kernel_erode = cv2.getStructuringElement(
            cv2.MORPH_RECT, (15, 15)
        )

        stats_html = (
            "<h2>LCC Demo Calibration</h2>"
            "<p><b>Method:</b> median HSV Hue + median CIELAB. "
            "The hue ranges shown here are observed image values, not final "
            "RiceTrack standards.</p>"
        )

        for idx, cnt in enumerate(panel_contours):
            single_mask = np.zeros_like(cleaned_mask)
            cv2.drawContours(single_mask, [cnt], -1, 255, thickness=cv2.FILLED)

            eroded_single = cv2.erode(
                single_mask, kernel_erode, iterations=2
            )
            final_mask = cv2.bitwise_or(final_mask, eroded_single)

            p_hsv = hsv[eroded_single > 0]
            p_lab = lab[eroded_single > 0]

            if p_hsv.size == 0:
                continue

            panel_id = idx + 2  # Correct LCC numbering: 2, 3, 4, 5.
            hues = p_hsv[:, 0].astype(np.float32)
            sat = p_hsv[:, 1].astype(np.float32)
            val = p_hsv[:, 2].astype(np.float32)
            lab_pixels = p_lab.astype(np.float32)

            median_h = float(np.median(hues))
            mean_h = float(np.mean(hues))
            hue_sd = float(np.std(hues))
            hue_min = int(np.min(hues))
            hue_max = int(np.max(hues))
            hue_q1, hue_q3 = np.percentile(hues, [25, 75])
            med_s = float(np.median(sat))
            med_v = float(np.median(val))
            med_l, med_a, med_b = np.median(lab_pixels, axis=0)

            stats_html += (
                f"<b>PANEL {panel_id}:</b><br>"
                f"<b>Median HSV:</b> H: {median_h:.1f}, "
                f"S: {med_s:.1f}, V: {med_v:.1f}<br>"
                f"<b>Hue distribution:</b> mean {mean_h:.1f}, "
                f"SD {hue_sd:.2f}, IQR {hue_q1:.1f}–{hue_q3:.1f}, "
                f"min {hue_min}, max {hue_max}<br>"
                f"<b>Median Lab:</b> L*: {med_l:.1f}, "
                f"a*: {med_a:.1f}, b*: {med_b:.1f}<br><br>"
            )

        if not panel_contours:
            stats_html = (
                "<p>No LCC panels detected. Check the preliminary HSV bounds "
                "or image quality.</p>"
            )

        self.stats_label.setText(stats_html)

        segmented = cv2.bitwise_and(image, image, mask=final_mask)
        rgb = cv2.cvtColor(segmented, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaledToHeight(
            350, Qt.TransformationMode.SmoothTransformation
        )
        self.img_label.setPixmap(pixmap)

    def _upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select LCC Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            self.process_and_display(file_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LccSegmentAnalysis("images/lcc.jpg")
    window.show()
    sys.exit(app.exec())
