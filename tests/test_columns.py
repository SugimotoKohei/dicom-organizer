"""Tests for column dictionary and machine-readable schema (WP3b)."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.tag import Tag
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

import dicom_organizer.core as core
from dicom_organizer.columns import (
    COLUMN_SPECS,
    ColumnSpec,
    column_spec,
)
from tests.test_dicom_organizer import write_dicom

UNIT_SUFFIXES = {
    "_ms": "ms",
    "_mm": "mm",
    "_deg": "deg",
    "_T": "T",
    "_kV": "kV",
    "_mA": "mA",
    "_Bq": "Bq",
    "_s": "s",
}


def write_minimal_dicom(path: Path, modality: str) -> None:
    """Create a minimal synthetic DICOM file with only required UIDs and Modality."""
    sop_class_map = {
        "MR": "1.2.840.10008.5.1.4.1.1.4",
        "CT": "1.2.840.10008.5.1.4.1.1.2",
        "US": "1.2.840.10008.5.1.4.1.1.6.1",
        "XA": "1.2.840.10008.5.1.4.1.1.12.1",
        "PT": "1.2.840.10008.5.1.4.1.1.128",
    }
    sop_uid = generate_uid()
    sop_class = sop_class_map[modality]
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = sop_class
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SOPClassUID = sop_class
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.Modality = modality
    ds.save_as(str(path))


def test_column_coverage(tmp_path: Path) -> None:
    """Verify that all CSV headers from actual runs and ALL_METADATA_COLUMNS match COLUMN_SPECS."""
    names = {spec.name for spec in COLUMN_SPECS}
    assert len(names) == len(COLUMN_SPECS), "duplicate column specs"

    input_root = tmp_path / "in"
    input_root.mkdir()
    for number, modality in enumerate(("MR", "CT", "US", "XA", "PT"), start=1):
        write_dicom(
            input_root / f"{modality}.dcm",
            series_uid=generate_uid(),
            sop_uid=generate_uid(),
            series_number=number,
            instance_number=1,
            modality=modality,
        )

    seen: set[str] = set()
    out = tmp_path / "out"
    core.run(core.OrganizeOptions(input_root=input_root, output_root=out))
    for path in out.rglob("*.csv"):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            seen.update(next(csv.reader(handle)))

    listed = tmp_path / "list"
    core.run(core.OrganizeOptions(input_root=input_root, output_root=listed, list_only=True))
    for path in listed.rglob("*.csv"):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            seen.update(next(csv.reader(handle)))

    seen.update(core.ALL_METADATA_COLUMNS)

    missing = sorted(seen - names)
    unused = sorted(names - seen)
    assert not missing, f"Columns without ColumnSpec: {missing}"
    assert not unused, f"ColumnSpecs never written to CSV: {unused}"


def test_column_unit_suffixes() -> None:
    """Verify that column name suffixes match declared units."""
    for spec in COLUMN_SPECS:
        for suffix, unit in UNIT_SUFFIXES.items():
            if spec.name.endswith(suffix):
                assert spec.unit == unit, f"{spec.name}: unit={spec.unit!r} expected {unit!r}"


def test_column_descriptions_and_missing() -> None:
    """Verify that all specs have descriptions in English and Japanese, and missing condition."""
    japanese_pattern = re.compile(r"[぀-ヿ一-鿿]")
    for spec in COLUMN_SPECS:
        assert spec.description_en.strip(), f"{spec.name} missing description_en"
        assert spec.description_ja.strip(), f"{spec.name} missing description_ja"
        assert japanese_pattern.search(spec.description_ja), (
            f"{spec.name} description_ja does not contain Japanese characters"
        )
        assert spec.missing.strip(), f"{spec.name} missing missing condition"
        assert spec.source.strip(), f"{spec.name} missing source"
        assert spec.level in {"image", "series", "file"}, f"{spec.name} invalid level {spec.level}"


def test_column_spec_lookup() -> None:
    """Verify column_spec helper lookup by name."""
    spec = column_spec("TR_ms")
    assert isinstance(spec, ColumnSpec)
    assert spec.name == "TR_ms"
    assert spec.unit == "ms"

    with pytest.raises(KeyError):
        column_spec("NonExistentColumn")


def test_generate_column_docs_check() -> None:
    """Verify generate_column_docs.py --check passes (docs/csv-columns.md is up to date)."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "generate_column_docs.py"
    completed = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, (
        f"generate_column_docs.py --check failed: {completed.stdout} {completed.stderr}"
    )


def test_print_schema_cli() -> None:
    """Verify --print-schema CLI output is valid JSON matching OUTPUT_SCHEMA_VERSION and conventions."""
    stdout, stderr = io.StringIO(), io.StringIO()
    original_argv = sys.argv
    sys.argv = ["dicom-organizer", "--print-schema"]
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = core.main()
            except SystemExit as exc:
                code = int(exc.code or 0)
    finally:
        sys.argv = original_argv

    assert code == 0, f"exit={code} {stderr.getvalue()}"
    data = json.loads(stdout.getvalue())
    assert data["output_schema_version"] == core.OUTPUT_SCHEMA_VERSION

    conventions_str = json.dumps(data["conventions"], ensure_ascii=False)
    for needle in ("N/A", "|", "\\\\", "UTF-8"):
        assert needle in conventions_str, f"conventions missing {needle!r}"

    for expected_file in (
        "dicom_parameters.csv",
        "series_summary.csv",
        "all_series_summary.csv",
        "all_dicom_parameters.csv",
        "file_report.csv",
    ):
        assert expected_file in data["files"]

    assert data["columns"]["TR_ms"]["unit"] == "ms"
    assert len(data["columns"]) == len(COLUMN_SPECS)


def test_absent_value_matching(tmp_path: Path) -> None:
    """R2: Process minimal DICOMs and verify that columns match absent_value when attributes are missing."""
    input_root = tmp_path / "minimal_in"
    input_root.mkdir()
    for modality in ("MR", "CT", "US", "XA", "PT"):
        write_minimal_dicom(input_root / f"{modality}_min.dcm", modality=modality)

    out = tmp_path / "minimal_out"
    core.run(core.OrganizeOptions(input_root=input_root, output_root=out))

    # Check all_dicom_parameters.csv and per-study dicom_parameters.csv
    param_files = list(out.rglob("dicom_parameters.csv")) + [out / "all_dicom_parameters.csv"]
    for param_file in param_files:
        if not param_file.is_file():
            continue
        with param_file.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col_name, val in row.items():
                    spec = column_spec(col_name)
                    if spec.absent_value is not None:
                        assert val == spec.absent_value, (
                            f"Column {col_name} value '{val}' does not match "
                            f"expected absent_value '{spec.absent_value}' in {param_file.name}"
                        )

    # Check series summaries as well
    summary_files = list(out.rglob("series_summary.csv")) + [out / "all_series_summary.csv"]
    for summary_file in summary_files:
        if not summary_file.is_file():
            continue
        with summary_file.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col_name, val in row.items():
                    spec = column_spec(col_name)
                    if spec.absent_value is not None:
                        assert val == spec.absent_value, (
                            f"Summary column {col_name} value '{val}' does not match "
                            f"expected absent_value '{spec.absent_value}' in {summary_file.name}"
                        )


def test_us_thermal_indices(tmp_path: Path) -> None:
    """R3: Verify that US thermal indices appear in CSV outputs when populated."""
    input_root = tmp_path / "us_in"
    input_root.mkdir()
    dcm_path = input_root / "us_thermal.dcm"
    write_minimal_dicom(dcm_path, modality="US")

    # Add thermal index attributes to the DICOM dataset
    import pydicom

    ds = pydicom.dcmread(dcm_path)
    ds.SoftTissueThermalIndex = 0.5
    ds.BoneThermalIndex = 0.8
    ds.CranialThermalIndex = 0.3
    ds.save_as(str(dcm_path))

    out = tmp_path / "us_out"
    core.run(core.OrganizeOptions(input_root=input_root, output_root=out))

    param_files = list(out.rglob("dicom_parameters.csv"))
    assert param_files, f"No dicom_parameters.csv found in {out}"
    params_path = param_files[0]
    with params_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row["SoftTissueThermalIndex"] == "0.5"
        assert row["BoneThermalIndex"] == "0.8"
        assert row["CranialThermalIndex"] == "0.3"


def test_siemens_private_tags_require_siemens_manufacturer(tmp_path: Path) -> None:
    """R4: Verify Siemens private tags are N/A unless Manufacturer contains 'siemens'."""
    input_root = tmp_path / "mfg_in"
    input_root.mkdir()

    # 1. GE MR with (0021, 114F) element
    ge_path = input_root / "ge.dcm"
    write_minimal_dicom(ge_path, modality="MR")
    import pydicom

    ds_ge = pydicom.dcmread(ge_path)
    ds_ge.Manufacturer = "GE Medical Systems"
    ds_ge[Tag(0x0021, 0x114F)] = pydicom.dataelem.DataElement(
        Tag(0x0021, 0x114F), "SH", "GE_Coil_1"
    )
    ds_ge.save_as(str(ge_path))

    # 2. Siemens MR with (0021, 114F) element
    siemens_path = input_root / "siemens.dcm"
    write_minimal_dicom(siemens_path, modality="MR")
    ds_siemens = pydicom.dcmread(siemens_path)
    ds_siemens.Manufacturer = "Siemens Healthineers"
    ds_siemens[Tag(0x0021, 0x114F)] = pydicom.dataelem.DataElement(
        Tag(0x0021, 0x114F), "SH", "HEA;HEP"
    )
    ds_siemens.save_as(str(siemens_path))

    out = tmp_path / "mfg_out"
    core.run(core.OrganizeOptions(input_root=input_root, output_root=out))

    rows: list[dict[str, str]] = []
    for param_file in out.rglob("dicom_parameters.csv"):
        with param_file.open(encoding="utf-8-sig", newline="") as f:
            rows.extend(csv.DictReader(f))
    assert rows, f"No rows found in {out}"
    by_mfg = {row["Manufacturer"]: row for row in rows}

    # GE row must have SiemensCoilElement as N/A
    ge_row = by_mfg["GE Medical Systems"]
    assert ge_row["SiemensCoilElement"] == "N/A"

    # Siemens row must read the private tag value
    siemens_row = by_mfg["Siemens Healthineers"]
    assert siemens_row["SiemensCoilElement"] == "HEA;HEP"
