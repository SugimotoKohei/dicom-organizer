from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest
from pydicom.uid import generate_uid

from test_dicom_organizer import args_for, write_dicom


def _qt_app() -> object:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    widgets = pytest.importorskip("PySide6.QtWidgets")
    return widgets.QApplication.instance() or widgets.QApplication([])


def test_gui_initial_state_shows_safety_guidance() -> None:
    _qt_app()
    from dicom_organizer.gui import MainWindow

    window = MainWindow()
    try:
        assert window.status_label.text().startswith("Ready.")
        assert "PatientName" in window.patient_warning_label.text()
        assert not window.advanced_group.isChecked()
        assert window.series_template_edit.isHidden()

        window.action_combo.setCurrentText("move")
        assert "move will relocate" in window.unsafe_action_label.text()

        window.exists_combo.setCurrentText("overwrite")
        assert "overwrite can replace" in window.unsafe_action_label.text()
    finally:
        window.close()


def test_gui_dry_run_payload_updates_summary(tmp_path: Path) -> None:
    _qt_app()
    from dicom_organizer.core import run
    from dicom_organizer.gui import MainWindow

    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "mr.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        modality="MR",
    )
    write_dicom(
        input_root / "ct.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        modality="CT",
    )

    result = run(args_for(input_root, output_root, dry_run=True))
    window = MainWindow()
    try:
        window._worker_finished(
            {
                "items": result.items,
                "stats": Counter(result.stats),
                "output_root": result.output_root,
                "dry_run": result.dry_run,
                "profile": result.profile,
                "summary": result.summary,
            }
        )

        assert "No files were written" in window.status_label.text()
        assert window.summary_labels["organized_files"].text() == "2"
        assert window.summary_labels["csv_target_files"].text() == "2"
        assert window.summary_labels["organized_by_modality"].text() == "CT 1 / MR 1"
        assert window.table.rowCount() == 2
    finally:
        window.close()
