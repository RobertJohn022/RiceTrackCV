"""
database.py
-------------
Tiny SQLite-backed store for RiceTrack inspection records.

    - tab_control.py calls insert_record() when the operator presses
      "Evaluate" on a loaded photo.
    - tab_records.py calls fetch_records() / distinct() / distinct_months()
      to populate the Records table and its filters.

Only avg_hue, leaf_report and the image are actually measured by the
current computer-vision pipeline (see vision.py). Plot, variant, GPS,
average height and the height report don't have a real sensor behind
them yet, so every insert falls back to the stub defaults below unless
the caller supplies real values later on.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from common import STANDARDS

DB_PATH = Path(__file__).resolve().parent / "ricetrack.db"

# Stub defaults for fields the current prototype can't measure yet.
DEFAULT_PLOT = "A-01"
DEFAULT_VARIANT = "NSIC Rc 222"
DEFAULT_GPS = "15.67170, 120.89280"
DEFAULT_AVG_HEIGHT = 100.0
DEFAULT_HEIGHT_REPORT = "healthy"

_DISTINCT_ALLOWED = {"plot", "variant", "status"}


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                captured_at TEXT NOT NULL,
                plot TEXT NOT NULL,
                variant TEXT NOT NULL,
                gps TEXT NOT NULL,
                avg_height REAL NOT NULL,
                avg_hue REAL NOT NULL,
                height_report TEXT NOT NULL,
                leaf_report TEXT NOT NULL,
                status TEXT NOT NULL,
                image BLOB
            )
            """
        )


def _compute_status(color_ok: bool, height_ok: bool) -> str:
    if color_ok and height_ok:
        return "Healthy"
    if not color_ok and not height_ok:
        return "Needs Inspection - both"
    return "Needs Inspection - " + ("color" if not color_ok else "height")


def _next_id(conn, plot: str) -> str:
    count = conn.execute(
        "SELECT COUNT(*) FROM records WHERE plot = ?", (plot,)
    ).fetchone()[0]
    return f"{plot}-{count + 1:02d}"


def insert_record(record: dict) -> str:
    """
    Insert one inspection record and return its generated ID.

    Required keys: "avg_hue" (float), "leaf_report" (str), "image" (bytes
    or None). Everything else falls back to the stub defaults above if
    not provided.
    """
    plot = record.get("plot", DEFAULT_PLOT)
    variant = record.get("variant", DEFAULT_VARIANT)
    gps = record.get("gps", DEFAULT_GPS)
    avg_height = record.get("avg_height", DEFAULT_AVG_HEIGHT)
    height_report = record.get("height_report", DEFAULT_HEIGHT_REPORT)
    avg_hue = record["avg_hue"]
    leaf_report = record["leaf_report"]
    image_bytes = record.get("image")
    captured_at = record.get("captured_at") or datetime.now().isoformat(timespec="seconds")

    height_ok = STANDARDS["height"][0] <= avg_height <= STANDARDS["height"][1]
    color_ok = STANDARDS["hue"][0] <= avg_hue <= STANDARDS["hue"][1]
    status = _compute_status(color_ok, height_ok)

    with _connect() as conn:
        record_id = _next_id(conn, plot)
        conn.execute(
            """
            INSERT INTO records
                (id, captured_at, plot, variant, gps, avg_height, avg_hue,
                 height_report, leaf_report, status, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (record_id, captured_at, plot, variant, gps, avg_height, avg_hue,
             height_report, leaf_report, status, image_bytes),
        )
    return record_id


def fetch_records(month=None, plot=None, variant=None, status=None) -> list:
    """Return matching records, newest first, as a list of dicts."""
    query = "SELECT * FROM records WHERE 1=1"
    params = []
    if month and month != "All":
        query += " AND strftime('%Y-%m', captured_at) = ?"
        params.append(month)
    if plot and plot != "All":
        query += " AND plot = ?"
        params.append(plot)
    if variant and variant != "All":
        query += " AND variant = ?"
        params.append(variant)
    if status and status != "All":
        if status == "Needs Inspection":
            query += " AND status LIKE 'Needs Inspection%'"
        else:
            query += " AND status = ?"
            params.append(status)
    query += " ORDER BY captured_at DESC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def distinct(column: str) -> list:
    if column not in _DISTINCT_ALLOWED:
        raise ValueError(f"Unsupported column for distinct(): {column}")
    with _connect() as conn:
        rows = conn.execute(f"SELECT DISTINCT {column} FROM records ORDER BY {column}").fetchall()
    return [row[0] for row in rows]


def distinct_months() -> list:
    """Distinct 'YYYY-MM' strings present in captured_at, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y-%m', captured_at) AS m FROM records ORDER BY m DESC"
        ).fetchall()
    return [row[0] for row in rows]


init_db()
