from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

from organize_dicoms.core import build_items, run


def write_dicom(
    path: Path,
    *,
    series_uid: str,
    sop_uid: str,
    series_number: int,
    instance_number: int,
    patient_name: str = "Test^Patient",
    acquisition_date: str = "20260515",
    echo_time: float = 10.0,
    phase_encoding_direction: str = "ROW",
    protocol_name: str | None = None,
) -> None:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.Modality = "MR"
    ds.AcquisitionDate = acquisition_date
    ds.StudyDate = acquisition_date
    ds.SeriesDate = acquisition_date
    ds.SeriesNumber = series_number
    ds.InstanceNumber = instance_number
    ds.SeriesDescription = f"Series {series_number}"
    ds.ProtocolName = protocol_name or f"Protocol {series_number}"
    ds.PatientName = patient_name
    ds.PatientID = "PID001"
    ds.RepetitionTime = 1000
    ds.EchoTime = echo_time
    ds.InPlanePhaseEncodingDirection = phase_encoding_direction
    ds.Rows = 16
    ds.Columns = 16
    ds.PixelSpacing = [1.5, 1.5]
    ds.Manufacturer = "UnitTest"
    ds.ManufacturerModelName = "Synthetic"
    ds.ImageType = ["ORIGINAL", "PRIMARY"]
    ds.save_as(path, enforce_file_format=True)


def args_for(input_root: Path, output_root: Path, **overrides: object) -> argparse.Namespace:
    values = {
        "input": input_root,
        "output": output_root,
        "action": "copy",
        "confirm_move": False,
        "if_exists": "error",
        "dry_run": False,
        "force_read": False,
        "include_hidden": False,
        "include_organized": False,
        "limit": 0,
        "series_dir_template": "{series_number}_{protocol_name}",
        "file_template": "{instance_number_6}.dcm",
        "patient_mode": "keep",
        "dicom_tags": (),
        "verbose": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_dry_run_builds_series_without_writing(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "one.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=7,
        instance_number=1,
    )

    items, stats = build_items(args_for(input_root, output_root, dry_run=True))

    assert len(items) == 1
    assert stats["candidate_files"] == 1
    assert stats["skipped_non_dicom"] == 0
    assert not output_root.exists()
    assert items[0].destination.name == "000001.dcm"
    assert items[0].destination.parent.name == "000007_Protocol-7"


def test_run_dry_run_does_not_write_output(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=7,
        instance_number=1,
    )

    result = run(args_for(input_root, output_root, dry_run=True))

    assert result.dry_run is True
    assert result.summary["organized_files"] == 1
    assert not output_root.exists()


def test_run_writes_files_and_metadata(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    uid_a = generate_uid()
    uid_b = generate_uid()
    write_dicom(
        input_root / "a1.dcm",
        series_uid=uid_a,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        echo_time=10,
    )
    write_dicom(
        input_root / "b1.dcm",
        series_uid=uid_b,
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        echo_time=20,
    )

    result = run(args_for(input_root, output_root))

    assert result.summary["organized_files"] == 2
    assert result.summary["series_count"] == 2
    assert (output_root / "organize_summary.json").exists()
    date_dir = output_root / "20260515"
    assert (date_dir / "mri_parameters.csv").exists()
    assert (date_dir / "series_summary.csv").exists()

    with (date_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["SeriesNumber"] for row in rows] == ["000001", "000002"]
    assert [row["FileCount"] for row in rows] == ["1", "1"]
    assert rows[0]["EchoTimes_ms"] == "10.0"
    assert rows[0]["FOV_HxW_mm"] == "24x24"
    assert rows[0]["Matrix_RowsxCols"] == "16x16"
    assert rows[0]["TR_ms"] == "1000.0"
    assert rows[0]["PhaseEncodingDirection"] == "ROW"
    assert rows[0]["InPlanePhaseEncodingDirection"] == "ROW"
    assert all("(" not in column and ")" not in column for column in rows[0])

    with (date_dir / "mri_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        metadata_row = next(csv.DictReader(handle))
    assert metadata_row["TE_ms"] == "10.0"
    assert metadata_row["PixelBandwidth_Hz_per_px"] == "N/A"
    assert metadata_row["PhaseEncodingDirection"] == "ROW"
    assert metadata_row["InPlanePhaseEncodingDirection"] == "ROW"
    assert all("(" not in column and ")" not in column for column in metadata_row)


def test_default_series_directory_uses_protocol_name(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=3,
        instance_number=1,
        protocol_name="T2 TSE axial (fast)",
    )

    result = run(args_for(input_root, output_root))

    assert result.items[0].destination.parent.name == "000003_T2-TSE-axial-fast"
    assert result.items[0].row["OrganizedFileName"].startswith(
        "20260515/000003_T2-TSE-axial-fast/"
    )


def test_duplicate_protocol_series_get_distinct_directories(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "a.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=4,
        instance_number=1,
        protocol_name="Repeated Protocol",
    )
    write_dicom(
        input_root / "b.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=4,
        instance_number=1,
        protocol_name="Repeated Protocol",
    )

    result = run(args_for(input_root, output_root))
    parents = [item.destination.parent.name for item in result.items]

    assert parents == ["000004_Repeated-Protocol_01", "000004_Repeated-Protocol_02"]


def test_run_rejects_missing_input_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run(args_for(tmp_path / "missing", tmp_path / "organized"))


def test_run_rejects_output_equal_to_input(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()

    with pytest.raises(ValueError, match="Output directory must be different"):
        run(args_for(input_root, input_root))


def test_patient_mode_keep_hash_and_drop(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    keep_output = tmp_path / "keep"
    run(args_for(input_root, keep_output, patient_mode="keep"))
    with (keep_output / "20260515" / "mri_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        keep_row = next(csv.DictReader(handle))
    assert keep_row["PatientName"] == "Test^Patient"
    assert keep_row["PatientID"] == "PID001"
    assert keep_row["PatientNameHash"] != "N/A"
    assert keep_row["PatientIDHash"] != "N/A"

    hash_output = tmp_path / "hash"
    run(args_for(input_root, hash_output, patient_mode="hash"))
    with (hash_output / "20260515" / "mri_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        hash_row = next(csv.DictReader(handle))
    assert hash_row["PatientName"].startswith("sha256:")
    assert hash_row["PatientID"].startswith("sha256:")
    assert hash_row["PatientNameHash"] != "N/A"
    assert hash_row["PatientIDHash"] != "N/A"

    drop_output = tmp_path / "drop"
    run(args_for(input_root, drop_output, patient_mode="drop"))
    with (drop_output / "20260515" / "mri_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        drop_row = next(csv.DictReader(handle))
    assert drop_row["PatientName"] == "N/A"
    assert drop_row["PatientID"] == "N/A"
    assert drop_row["PatientNameHash"] != "N/A"
    assert drop_row["PatientIDHash"] != "N/A"


def test_custom_dicom_tags_are_written_to_metadata_csv(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    run(
        args_for(
            input_root,
            output_root,
            dicom_tags=(
                "EchoTime",
                "0018,0080",
                "CustomPhase=(0018,1312)",
                "PrivateMissing=0021,9999",
            ),
        )
    )

    with (output_root / "20260515" / "mri_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))

    assert row["DICOM_EchoTime"] == "10.0"
    assert row["DICOM_RepetitionTime"] == "1000.0"
    assert row["CustomPhase"] == "ROW"
    assert row["PrivateMissing"] == "N/A"

    with (output_root / "organize_summary.json").open(encoding="utf-8") as handle:
        assert "EchoTime" in handle.read()


def test_invalid_custom_dicom_tag_is_rejected(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()

    with pytest.raises(ValueError, match="Unsupported DICOM tag format"):
        run(args_for(input_root, tmp_path / "organized", dicom_tags=("not-a-tag",)))


def test_if_exists_modes_error_skip_rename_and_overwrite(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    first = run(args_for(input_root, output_root))
    original = first.items[0].destination
    assert original.exists()

    with pytest.raises(FileExistsError):
        run(args_for(input_root, output_root, if_exists="error"))

    skipped = run(args_for(input_root, output_root, if_exists="skip"))
    assert skipped.summary["organized_files"] == 0
    assert skipped.stats["skipped_existing"] == 1

    renamed = run(args_for(input_root, output_root, if_exists="rename"))
    assert renamed.summary["organized_files"] == 1
    assert renamed.items[0].destination.name == "000001_02.dcm"
    assert renamed.items[0].destination.exists()

    overwritten = run(args_for(input_root, output_root, if_exists="overwrite"))
    assert overwritten.summary["organized_files"] == 1
    assert overwritten.items[0].destination == original
    assert original.exists()


def test_cli_alias_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "organize_dicoms.core", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--input" in result.stdout
