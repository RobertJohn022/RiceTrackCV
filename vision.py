"""
vision.py
----------
Computer-vision module for RiceTrack.

Demo color-analysis policy:
    - Vegetation segmentation keeps the existing ExG + HSV approach, but
      lowers the minimum HSV Value threshold to 12 based on the preliminary
      LCC image experiment. This is a demo setting, not a field-calibrated
      value yet.
    - Median HSV Hue is used as the primary leaf-color statistic because it
      is less sensitive than the arithmetic mean to localized glare, shadows,
      and other atypical pixels.
    - Median CIELAB L*, a*, and b* are computed as supporting color
      descriptors. They are stored for later validation/calibration but do
      not replace HSV for the preliminary LCC classification.

The Hue standards in common.py remain preliminary demo thresholds and are
still the single source of truth for classification.
"""

from dataclasses import dataclass

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap

from common import STANDARDS

# Preliminary demo segmentation settings informed by the LCC image test.
MIN_HSV_VALUE = 12
MIN_HSV_SATURATION = 40
MAX_HSV_VALUE = 250

_HEALTHY_LO, _HEALTHY_HI = STANDARDS["hue"]
IDEAL_HUE = (_HEALTHY_LO + _HEALTHY_HI) / 2

LCC_TABLE = [
    (30, 41, "Panel 2 - Yellowish", "yellowish", "Needs Inspection"),
    (42, 51, "Panel 3 - Light Green", "light green", "Needs Inspection"),
    (_HEALTHY_LO, _HEALTHY_HI, "Panel 4 - Healthy Green", "healthy green", "Healthy"),
    (66, 85, "Panel 5 - Dark Green", "dark green", "Needs Inspection"),
]

MIN_VEGETATION_COVERAGE_PCT = 3.0


class NoVegetationDetected(Exception):
    """Raised when too little of the frame reads as leaf/canopy."""


@dataclass
class HealthResult:
    coverage_pct: float
    mean_hue: float
    median_hue: float
    lab_l: float
    lab_a: float
    lab_b: float
    panel: str
    tone: str
    status: str
    mask: np.ndarray


def segment_vegetation(img_bgr: np.ndarray) -> np.ndarray:
    """Isolate rice/leaf pixels from sky, soil, dikes, and signage."""
    b, g, r = cv2.split(img_bgr.astype(np.float32))
    exg = 2 * g - r - b
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, mask = cv2.threshold(
        exg_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.bitwise_and(
        mask,
        cv2.inRange(hsv[:, :, 1], MIN_HSV_SATURATION, 255),
    )
    mask = cv2.bitwise_and(
        mask,
        cv2.inRange(hsv[:, :, 2], MIN_HSV_VALUE, MAX_HSV_VALUE),
    )

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def classify_hue(hue: float) -> tuple[str, str, str]:
    """Map the preliminary median Hue to the current demo LCC bands."""
    for lo, hi, panel, tone, status in LCC_TABLE:
        if lo <= hue <= hi:
            return panel, tone, status
    return "Out of range", "out of range", "Needs Inspection"


def evaluate(img_bgr: np.ndarray) -> HealthResult:
    """Run segmentation, robust Hue extraction, and preliminary classification."""
    mask = segment_vegetation(img_bgr)
    vegetation = mask > 0
    coverage_pct = float(np.count_nonzero(vegetation)) / mask.size * 100.0

    if coverage_pct < MIN_VEGETATION_COVERAGE_PCT:
        raise NoVegetationDetected(
            f"Only {coverage_pct:.1f}% of the frame reads as vegetation. "
            "Point the camera at the rice canopy and try again."
        )

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

    hues = hsv[:, :, 0][vegetation].astype(np.float32)
    lab_pixels = lab[vegetation].astype(np.float32)

    mean_hue = float(np.mean(hues))
    median_hue = float(np.median(hues))
    median_lab = np.median(lab_pixels, axis=0)
    lab_l, lab_a, lab_b = (float(v) for v in median_lab)

    # The demo uses median Hue for the actual classification decision.
    panel, tone, status = classify_hue(median_hue)

    return HealthResult(
        coverage_pct=coverage_pct,
        mean_hue=mean_hue,
        median_hue=median_hue,
        lab_l=lab_l,
        lab_a=lab_a,
        lab_b=lab_b,
        panel=panel,
        tone=tone,
        status=status,
        mask=mask,
    )


def overlay_mask(img_bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    """Blend a red highlight over segmented pixels for visual QA."""
    overlay = img_bgr.copy()
    overlay[mask > 0] = (0, 0, 255)
    return cv2.addWeighted(img_bgr, 1 - alpha, overlay, alpha, 0)


def encode_thumbnail(img_bgr: np.ndarray, max_dim: int = 480) -> bytes:
    """Downscale and JPEG-encode a photo before it is stored in SQLite."""
    h, w = img_bgr.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        img_bgr = cv2.resize(
            img_bgr,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )
    ok, buf = cv2.imencode(
        ".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85]
    )
    return buf.tobytes() if ok else b""


def cv_to_qpixmap(img_bgr: np.ndarray) -> QPixmap:
    """Convert an OpenCV BGR ndarray into a QPixmap for display."""
    rgb = np.ascontiguousarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())
