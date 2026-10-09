"""
vision.py
----------
Computer-vision module for RiceTrack.

Two jobs, kept separate from the UI code on purpose (same split the
capstone proposal describes between the "Computer Vision" module and the
"Operator Workstation/Desktop Application"):

    1. segment_vegetation() - isolate rice/leaf pixels from sky, soil,
       concrete dikes, and signage boards in a field photo.
    2. evaluate() - measure the segmented leaves' average Hue, map it to
       an IRRI/PhilRice Leaf Color Chart (LCC) panel, and return a
       preliminary Healthy / Needs Inspection verdict.

The "healthy" hue band is pulled from common.STANDARDS so the one
reference table in common.py stays the single source of truth for both
the UI (Standards tab) and this module.
"""

from dataclasses import dataclass

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap

from common import STANDARDS

# Healthy band comes straight from STANDARDS["hue"] = (52, 65).
_HEALTHY_LO, _HEALTHY_HI = STANDARDS["hue"]
IDEAL_HUE = (_HEALTHY_LO + _HEALTHY_HI) / 2  # 58.5

# Fixed LCC reference bands for the two "too far off" directions, taken
# from the capstone proposal's Leaf Color Chart table. "tone" is the
# plain-language leaf-color description stored alongside each record.
LCC_TABLE = [
    (30, 41, "Panel 2 - Yellowish", "yellowish", "Needs Inspection"),
    (42, 51, "Panel 3 - Light Green", "light green", "Needs Inspection"),
    (_HEALTHY_LO, _HEALTHY_HI, "Panel 4 - Healthy Green", "healthy green", "Healthy"),
    (66, 85, "Panel 5 - Dark Green", "dark green", "Needs Inspection"),
]

# Below this, the frame is probably sky, a dike, or too far from the
# canopy to trust the hue reading.
MIN_VEGETATION_COVERAGE_PCT = 3.0


class NoVegetationDetected(Exception):
    """Raised when too little of the frame reads as leaf/canopy."""


@dataclass
class HealthResult:
    coverage_pct: float
    mean_hue: float
    panel: str
    tone: str             # e.g. "light green", "healthy green"
    status: str           # "Healthy" or "Needs Inspection"
    mask: np.ndarray      # uint8, 255 where vegetation was detected


def segment_vegetation(img_bgr: np.ndarray) -> np.ndarray:
    """Isolate rice/leaf pixels from sky, soil, dikes, and signage."""
    b, g, r = cv2.split(img_bgr.astype(np.float32))
    exg = 2 * g - r - b
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, mask = cv2.threshold(exg_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.bitwise_and(mask, cv2.inRange(hsv[:, :, 1], 40, 255))  # saturation
    mask = cv2.bitwise_and(mask, cv2.inRange(hsv[:, :, 2], 30, 250))  # value

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def classify_hue(mean_hue: float) -> tuple[str, str, str]:
    for lo, hi, panel, tone, status in LCC_TABLE:
        if lo <= mean_hue <= hi:
            return panel, tone, status
    return "Out of range", "out of range", "Needs Inspection"


def evaluate(img_bgr: np.ndarray) -> HealthResult:
    """Run segmentation + hue classification on one field photo."""
    mask = segment_vegetation(img_bgr)
    coverage_pct = float(np.count_nonzero(mask)) / mask.size * 100.0

    if coverage_pct < MIN_VEGETATION_COVERAGE_PCT:
        raise NoVegetationDetected(
            f"Only {coverage_pct:.1f}% of the frame reads as vegetation. "
            "Point the camera at the rice canopy and try again."
        )

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mean_hue = float(np.mean(hsv[:, :, 0][mask > 0]))
    panel, tone, status = classify_hue(mean_hue)

    return HealthResult(coverage_pct, mean_hue, panel, tone, status, mask)


def overlay_mask(img_bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    """Blend a red highlight over segmented pixels for visual QA."""
    overlay = img_bgr.copy()
    overlay[mask > 0] = (0, 0, 255)  # red in BGR
    return cv2.addWeighted(img_bgr, 1 - alpha, overlay, alpha, 0)


def encode_thumbnail(img_bgr: np.ndarray, max_dim: int = 480) -> bytes:
    """
    Downscale + JPEG-encode a photo before it goes into the database, so
    records stay lightweight. Used for the image stored with each record,
    not for the live on-screen preview (which uses the full-resolution
    frame via cv_to_qpixmap).
    """
    h, w = img_bgr.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes() if ok else b""


def cv_to_qpixmap(img_bgr: np.ndarray) -> QPixmap:
    """Convert an OpenCV BGR ndarray into a QPixmap for display."""
    rgb = np.ascontiguousarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())
