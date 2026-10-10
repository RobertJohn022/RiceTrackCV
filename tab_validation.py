import csv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QVBoxLayout, QWidget,
)

import database
from common import RED_TEXT, TEXT, Chip, DataTable, STANDARDS, button, card, lbl

ERROR_LIMIT_CM = 2.0
HUE_ERROR_DISPLAY_LIMIT = 5.0


class ValidationPage(QWidget):
    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        self.summary_chip = Chip("0 paired samples", "gray")
        top = QHBoxLayout()
        top.addWidget(self.summary_chip)
        top.addStretch()

        export = button(" Export CSV", "dark", "download")
        export.clicked.connect(self._export)
        top.addWidget(export)
        root.addLayout(top)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.metric_labels = {}

        for name, key, suffix in (
            ("Height MAE", "height_mae", " cm"),
            ("Height RMSE", "height_rmse", " cm"),
            ("Hue MAE", "hue_mae", ""),
            ("Hue RMSE", "hue_rmse", ""),
        ):
            tile = QFrame()
            tile.setObjectName("metric")
            color = "#1d9e75" if "Height" in name else "#639922"
            tile.setStyleSheet(
                f"QFrame#metric {{ background: {color}; border-radius: 12px; }}"
            )
            tl = QVBoxLayout(tile)
            tl.setContentsMargins(16, 12, 16, 12)
            tl.setSpacing(2)
            tl.addWidget(lbl(name, 13, "#f4f8ee"))
            value_label = lbl("--", 24, "#ffffff", "700")
            tl.addWidget(value_label)
            self.metric_labels[key] = (value_label, suffix)
            tiles.addWidget(tile, 1)

        root.addLayout(tiles)

        panel, pl = card(margins=(14, 14, 14, 14), spacing=8)
        head = QHBoxLayout()
        head.setContentsMargins(4, 0, 0, 0)
        head.addWidget(lbl("Paired measurements", 16, TEXT, "700"))
        head.addStretch()

        add = button("+  Add manual reading", "dark")
        add.clicked.connect(self._open_manual_reading)
        head.addWidget(add)
        pl.addLayout(head)

        self.table = DataTable(
            [
                "Capture", "CV height", "Ref height", "Height err",
                "CV hue", "Ref hue", "Hue err", "Status",
            ],
            [1, 1, 1, 0.9, 1, 1, 0.8, 1.45],
        )
        pl.addWidget(self.table)

        self.empty_label = lbl(
            "No validation pairs yet. Add a manual reading to begin testing.",
            13, "#78786f",
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl.addWidget(self.empty_label)

        root.addWidget(panel)
        root.addStretch()
        self.refresh()

    def refresh(self):
        metrics = database.validation_metrics()
        self.summary_chip.set_text(f"{metrics['n']} paired samples")

        for key, (label, suffix) in self.metric_labels.items():
            value = metrics[key]
            label.setText("--" if value is None else f"{value:.2f}{suffix}")

        rows = database.fetch_validation_pairs()
        table_rows = []

        for row in rows:
            height_color = RED_TEXT if row["height_error"] > ERROR_LIMIT_CM else TEXT
            hue_color = RED_TEXT if row["hue_error"] > HUE_ERROR_DISPLAY_LIMIT else TEXT
            status_color = TEXT if row["status"] == "Test - Healthy" else RED_TEXT

            table_rows.append(
                [
                    (row["record_id"], TEXT, True),
                    f"{row['cv_height']:.1f} cm",
                    f"{row['manual_height']:.1f} cm",
                    (f"{row['height_error']:.1f}", height_color),
                    str(int(round(row["cv_hue"]))),
                    str(int(round(row["manual_hue"]))),
                    (f"{row['hue_error']:.1f}", hue_color),
                    (row["status"], status_color),
                ]
            )

        self.table.set_rows(table_rows)
        self.empty_label.setVisible(not rows)

    def _open_manual_reading(self):
        records = database.fetch_records()
        if not records:
            QMessageBox.information(
                self,
                "No CV Records",
                "Evaluate at least one crop image from the Control tab before "
                "adding a manual validation reading.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Manual Validation Reading")
        dialog.setMinimumWidth(540)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        intro = lbl(
            "Enter a reference/manual measurement for an existing CV result. "
            "The manual values are stored in the validation database and do "
            "not modify the original CV record.",
            12, TEXT,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(10)

        record_combo = QComboBox()
        for record in records:
            record_combo.addItem(
                f"{record['id']} · {record['plot']} · "
                f"CV height {record['avg_height']:.1f} cm · "
                f"CV hue {record['avg_hue']:.0f}",
                record["id"],
            )
        form.addRow("CV record", record_combo)

        manual_height = QDoubleSpinBox()
        manual_height.setRange(1.0, 300.0)
        manual_height.setDecimals(1)
        manual_height.setSuffix(" cm")
        manual_height.setSingleStep(0.5)
        manual_height.setValue(99.5)
        form.addRow("Manual height", manual_height)

        manual_hue = QDoubleSpinBox()
        manual_hue.setRange(0.0, 179.0)
        manual_hue.setDecimals(1)
        manual_hue.setSingleStep(1.0)
        manual_hue.setValue(58.5)
        form.addRow("Manual hue", manual_hue)

        notes = QLineEdit()
        notes.setPlaceholderText("Optional observer or field-test note")
        form.addRow("Notes", notes)
        layout.addLayout(form)

        status_label = QLabel()
        status_label.setWordWrap(True)
        layout.addWidget(status_label)

        def update_preview():
            h = manual_height.value()
            hue = manual_hue.value()
            status = database.compute_test_status(h, hue)
            color_ok = STANDARDS["hue"][0] <= hue <= STANDARDS["hue"][1]
            height_ok = STANDARDS["height"][0] <= h <= STANDARDS["height"][1]

            if color_ok and height_ok:
                detail = "Color and height are within the configured healthy ranges."
            elif not color_ok and not height_ok:
                detail = "Color and height are outside the configured healthy ranges."
            elif not color_ok:
                detail = "Leaf hue is outside the configured healthy range."
            else:
                detail = "Plant height is outside the configured healthy range."
            status_label.setText(f"{status} · {detail}")

        manual_height.valueChanged.connect(update_preview)
        manual_hue.valueChanged.connect(update_preview)
        update_preview()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            database.insert_validation_reading(
                record_id=record_combo.currentData(),
                manual_height=manual_height.value(),
                manual_hue=manual_hue.value(),
                notes=notes.text(),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Unable to Save Validation Reading",
                str(exc),
            )
            return

        self.refresh()

    def _export(self):
        rows = database.fetch_validation_pairs()
        if not rows:
            QMessageBox.information(
                self,
                "Nothing to Export",
                "There are no validation pairs to export yet.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            "validation.csv",
            "CSV files (*.csv)",
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "validation_id", "capture", "captured_at", "plot",
                "cv_height_cm", "manual_height_cm", "height_error_cm",
                "cv_hue", "manual_hue", "hue_error", "color_score",
                "height_score", "health_index", "status", "notes",
            ])
            for row in rows:
                writer.writerow([
                    row["validation_id"], row["record_id"], row["captured_at"],
                    row["plot"], row["cv_height"], row["manual_height"],
                    round(row["height_error"], 2), row["cv_hue"],
                    row["manual_hue"], round(row["hue_error"], 2),
                    round(row["color_score"], 2), round(row["height_score"], 2),
                    round(row["health_index"], 2), row["status"], row["notes"],
                ])
