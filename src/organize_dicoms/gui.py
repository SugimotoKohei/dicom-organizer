"""PySide6 GUI for organize-dicoms."""

from __future__ import annotations

import argparse
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

from organize_dicoms.core import (
    DEFAULT_FILE_TEMPLATE,
    DEFAULT_SERIES_DIR_TEMPLATE,
    OrganizedItem,
    build_series_summary,
    run,
)

try:
    from PySide6.QtCore import QObject, QThread, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    PYSIDE_IMPORT_ERROR: ImportError | None = exc

    class _MissingQt:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __call__(self, *args: object, **kwargs: object) -> "_MissingQt":
            return self

        def __getattr__(self, name: str) -> "_MissingQt":
            return self

    QObject = _MissingQt
    QThread = _MissingQt
    QUrl = _MissingQt
    Signal = _MissingQt
    QDesktopServices = _MissingQt
    QApplication = _MissingQt
    QCheckBox = _MissingQt
    QComboBox = _MissingQt
    QFileDialog = _MissingQt
    QFormLayout = _MissingQt
    QGridLayout = _MissingQt
    QGroupBox = _MissingQt
    QHBoxLayout = _MissingQt
    QLabel = _MissingQt
    QLineEdit = _MissingQt
    QMainWindow = _MissingQt
    QMessageBox = _MissingQt
    QPlainTextEdit = _MissingQt
    QProgressBar = _MissingQt
    QPushButton = _MissingQt
    QTableWidget = _MissingQt
    QTableWidgetItem = _MissingQt
    QVBoxLayout = _MissingQt
    QWidget = _MissingQt
else:
    PYSIDE_IMPORT_ERROR = None


PREVIEW_COLUMNS = [
    "AcquisitionDate",
    "SeriesNumber",
    "SeriesDescription",
    "ProtocolName",
    "FileCount",
    "EchoCount",
    "EchoTimes_ms",
    "CoilElementCount",
    "Rows",
    "Columns",
    "FOV_HxW_mm",
    "PhaseEncodingDirection",
    "Manufacturer",
    "ManufacturerModelName",
]


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, args: argparse.Namespace, dry_run_only: bool) -> None:
        super().__init__()
        self.args = args
        self.dry_run_only = dry_run_only

    def run(self) -> None:
        try:
            result = run(self.args, dry_run=True) if self.dry_run_only else run(self.args)
            self.finished.emit(
                {
                    "items": result.items,
                    "stats": result.stats,
                    "output_root": result.output_root,
                    "dry_run": result.dry_run,
                    "summary": result.summary,
                }
            )
        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("organize-dicoms")
        self.resize(1180, 760)
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self.last_output_root: Path | None = None

        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.action_combo = QComboBox()
        self.action_combo.addItems(["copy", "symlink", "hardlink", "move"])
        self.exists_combo = QComboBox()
        self.exists_combo.addItems(["error", "skip", "overwrite", "rename"])
        self.patient_combo = QComboBox()
        self.patient_combo.addItems(["keep", "hash", "drop"])
        self.force_read_check = QCheckBox("force-read")
        self.include_hidden_check = QCheckBox("include-hidden")
        self.include_organized_check = QCheckBox("include-organized")
        self.series_template_edit = QLineEdit(DEFAULT_SERIES_DIR_TEMPLATE)
        self.file_template_edit = QLineEdit(DEFAULT_FILE_TEMPLATE)
        self.limit_edit = QLineEdit("0")

        self.dry_run_button = QPushButton("Dry Run")
        self.run_button = QPushButton("Run")
        self.open_output_button = QPushButton("Open Output")
        self.open_output_button.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        self.table = QTableWidget(0, len(PREVIEW_COLUMNS))
        self.table.setHorizontalHeaderLabels(PREVIEW_COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)

        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        paths_group = QGroupBox("Paths")
        paths_layout = QGridLayout(paths_group)
        input_button = QPushButton("Browse")
        output_button = QPushButton("Browse")
        input_button.clicked.connect(self._choose_input)
        output_button.clicked.connect(self._choose_output)
        paths_layout.addWidget(QLabel("Input"), 0, 0)
        paths_layout.addWidget(self.input_edit, 0, 1)
        paths_layout.addWidget(input_button, 0, 2)
        paths_layout.addWidget(QLabel("Output"), 1, 0)
        paths_layout.addWidget(self.output_edit, 1, 1)
        paths_layout.addWidget(output_button, 1, 2)

        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)
        options_layout.addRow("Action", self.action_combo)
        options_layout.addRow("If exists", self.exists_combo)
        options_layout.addRow("Patient mode", self.patient_combo)
        options_layout.addRow("Series dir template", self.series_template_edit)
        options_layout.addRow("File template", self.file_template_edit)
        options_layout.addRow("Limit", self.limit_edit)
        checks = QHBoxLayout()
        checks.addWidget(self.force_read_check)
        checks.addWidget(self.include_hidden_check)
        checks.addWidget(self.include_organized_check)
        checks.addStretch()
        options_layout.addRow("Read options", checks)

        button_row = QHBoxLayout()
        button_row.addWidget(self.dry_run_button)
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.open_output_button)
        button_row.addWidget(self.progress)

        layout.addWidget(paths_group)
        layout.addWidget(options_group)
        layout.addLayout(button_row)
        layout.addWidget(QLabel("Series preview"))
        layout.addWidget(self.table, stretch=2)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log, stretch=1)
        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.dry_run_button.clicked.connect(self._start_dry_run)
        self.run_button.clicked.connect(self._start_run)
        self.open_output_button.clicked.connect(self._open_output)

    def _choose_input(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Input folder")
        if path:
            self.input_edit.setText(path)
            if not self.output_edit.text().strip():
                self.output_edit.setText(str(Path(path) / "organized"))

    def _choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Output folder")
        if path:
            self.output_edit.setText(path)

    def _build_args(self, dry_run: bool) -> argparse.Namespace | None:
        input_text = self.input_edit.text().strip()
        if not input_text:
            QMessageBox.warning(self, "Input required", "Input folder を選択してください。")
            return None
        output_text = self.output_edit.text().strip()
        try:
            limit = int(self.limit_edit.text().strip() or "0")
        except ValueError:
            QMessageBox.warning(self, "Invalid limit", "Limit は整数で入力してください。")
            return None
        return argparse.Namespace(
            input=Path(input_text),
            output=Path(output_text) if output_text else None,
            action=self.action_combo.currentText(),
            confirm_move=self.action_combo.currentText() == "move",
            if_exists=self.exists_combo.currentText(),
            dry_run=dry_run,
            force_read=self.force_read_check.isChecked(),
            include_hidden=self.include_hidden_check.isChecked(),
            include_organized=self.include_organized_check.isChecked(),
            limit=limit,
            series_dir_template=self.series_template_edit.text().strip()
            or DEFAULT_SERIES_DIR_TEMPLATE,
            file_template=self.file_template_edit.text().strip() or DEFAULT_FILE_TEMPLATE,
            patient_mode=self.patient_combo.currentText(),
            dicom_tags=(),
            verbose=False,
        )

    def _start_dry_run(self) -> None:
        args = self._build_args(dry_run=True)
        if args is None:
            return
        self._start_worker(args, dry_run_only=True)

    def _start_run(self) -> None:
        args = self._build_args(dry_run=False)
        if args is None:
            return
        if args.action == "move" or args.if_exists == "overwrite":
            answer = QMessageBox.warning(
                self,
                "Confirm unsafe action",
                f"action={args.action}, if-exists={args.if_exists} で実行します。",
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Ok:
                return
        self._start_worker(args, dry_run_only=False)

    def _start_worker(self, args: argparse.Namespace, dry_run_only: bool) -> None:
        self._set_busy(True)
        self.table.setRowCount(0)
        self.log.appendPlainText(
            f"{'Dry run' if dry_run_only else 'Run'} started: input={args.input}"
        )
        self.thread = QThread(self)
        self.worker = Worker(args, dry_run_only=dry_run_only)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._worker_finished)
        self.worker.failed.connect(self._worker_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _worker_finished(self, payload: dict[str, Any]) -> None:
        self._set_busy(False)
        items: list[OrganizedItem] = payload["items"]
        stats: Counter[str] = payload["stats"]
        output_root: Path = payload["output_root"]
        summary: dict[str, Any] = payload["summary"]
        self.last_output_root = output_root
        self.open_output_button.setEnabled(output_root.exists())
        self._fill_table(items)
        self.log.appendPlainText(
            "Completed: "
            f"organized_files={summary['organized_files']}, "
            f"series_count={summary['series_count']}, "
            f"skipped_non_dicom={stats['skipped_non_dicom']}, "
            f"skipped_existing={stats['skipped_existing']}, "
            f"output={output_root}"
        )
        if not items:
            QMessageBox.information(self, "No DICOM files", "整理対象のDICOMが見つかりませんでした。")

    def _worker_failed(self, details: str) -> None:
        self._set_busy(False)
        self.log.appendPlainText(details)
        QMessageBox.critical(self, "Failed", details.splitlines()[-1] if details else "Failed")

    def _set_busy(self, busy: bool) -> None:
        self.dry_run_button.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.progress.setRange(0, 0 if busy else 1)
        self.progress.setValue(0)

    def _fill_table(self, items: list[OrganizedItem]) -> None:
        rows = build_series_summary([item.row for item in items])
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, column in enumerate(PREVIEW_COLUMNS):
                self.table.setItem(row_index, col_index, QTableWidgetItem(row.get(column, "")))
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def _open_output(self) -> None:
        if self.last_output_root is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output_root)))


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print("usage: organize-dicoms-gui")
        print()
        print("Launch the PySide6 GUI for organize-dicoms.")
        return 0
    if PYSIDE_IMPORT_ERROR is not None:
        print(
            "PySide6 が見つかりません。GUIを使うには次でインストールしてください: "
            "uv tool install --editable '.[gui]' --force",
            file=sys.stderr,
        )
        print(f"詳細: {PYSIDE_IMPORT_ERROR}", file=sys.stderr)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
