from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    CTImageStorage,
    EnhancedMRImageStorage,
    ExplicitVRLittleEndian,
    MRImageStorage,
    PositronEmissionTomographyImageStorage,
    UltrasoundImageStorage,
    XRayAngiographicImageStorage,
    generate_uid,
)

from dicom_organizer.core import (
    CONFIG_KEYS,
    DEFAULT_FILE_TEMPLATE,
    DEFAULT_SERIES_DIR_TEMPLATE,
    FILE_REPORT_COLUMNS,
    InsufficientSpaceError,
    IntegrityError,
    OrganizeOptions,
    ProgressEvent,
    build_items,
    classify_dicom_file,
    config_to_toml,
    diagnostics_lines,
    ensure_within_output_root,
    format_duration,
    load_config,
    materialize,
    normalize_options,
    normalize_vendor_name,
    parallel_reduction_factor_in_plane_value,
    parse_args,
    phase_encoding_direction_patient,
    print_summary,
    run,
    run_self_test,
    safe_date,
    scan_duration_fields,
)
from dicom_organizer.sample_data import create_sample_dataset


def write_dicom(
    path: Path,
    *,
    series_uid: str,
    sop_uid: str,
    series_number: int,
    instance_number: int,
    patient_name: str = "Test^Patient",
    patient_id: str = "PID001",
    acquisition_date: str = "20260515",
    echo_time: float = 10.0,
    phase_encoding_direction: str | None = "ROW",
    image_orientation_patient: tuple[float, ...] | list[float] | None = (
        1.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
    ),
    patient_position: str | None = "HFS",
    anatomical_orientation_type: str | None = None,
    parallel_reduction_factor_in_plane: float | None = None,
    siemens_private_parallel_reduction_factor: float | None = None,
    protocol_name: str | None = None,
    series_description: str | None = None,
    manufacturer: str = "UnitTest",
    image_type: tuple[str, ...] | list[str] | None = None,
    sop_class_uid: str | None = None,
    echo_numbers: int | None = 1,
    acquisition_number: int | None = None,
    modality: str = "MR",
    sequence_name: str | None = "tse",
    philips_private_pulse_sequence_name: str | None = None,
    acquisition_time: str | None = None,
    study_time: str | None = None,
    series_time: str | None = None,
    study_uid: str | None = None,
    acquisition_duration: float | None = None,
    ge_acquisition_duration_us: float | None = None,
    ge_private_creator: str = "GEMS_ACQU_01",
    siemens_total_scan_time_sec: float | None = None,
    issuer_of_patient_id: str | None = None,
    specific_character_set: str | None = None,
) -> None:
    if sop_class_uid is None:
        sop_class_uid = {
            "MR": str(MRImageStorage),
            "CT": str(CTImageStorage),
            "US": str(UltrasoundImageStorage),
            "XA": str(XRayAngiographicImageStorage),
            "PT": str(PositronEmissionTomographyImageStorage),
        }.get(modality, str(MRImageStorage))
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = sop_class_uid
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    if specific_character_set is not None:
        ds.SpecificCharacterSet = specific_character_set
    ds.SOPClassUID = sop_class_uid
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = study_uid or generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.Modality = modality
    ds.AcquisitionDate = acquisition_date
    ds.StudyDate = acquisition_date
    ds.SeriesDate = acquisition_date
    if acquisition_time is not None:
        ds.AcquisitionTime = acquisition_time
    if study_time is not None:
        ds.StudyTime = study_time
    if series_time is not None:
        ds.SeriesTime = series_time
    ds.SeriesNumber = series_number
    ds.InstanceNumber = instance_number
    if acquisition_number is not None:
        ds.AcquisitionNumber = acquisition_number
    ds.SeriesDescription = series_description or f"Series {series_number}"
    ds.ProtocolName = protocol_name or f"Protocol {series_number}"
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    if issuer_of_patient_id is not None:
        ds.IssuerOfPatientID = issuer_of_patient_id
    ds.Rows = 16
    ds.Columns = 16
    ds.PixelSpacing = [1.5, 1.5]
    ds.Manufacturer = manufacturer
    ds.ManufacturerModelName = "Synthetic"
    ds.SliceThickness = 4
    ds.SpacingBetweenSlices = 4.5
    ds.SliceLocation = 12.0
    if image_orientation_patient is not None:
        ds.ImageOrientationPatient = list(image_orientation_patient)
    if patient_position is not None:
        ds.PatientPosition = patient_position
    if anatomical_orientation_type is not None:
        ds.AnatomicalOrientationType = anatomical_orientation_type
    if image_type is None:
        ds.ImageType = ["ORIGINAL", "PRIMARY"]
    elif image_type:
        ds.ImageType = list(image_type)
    if modality == "MR":
        ds.RepetitionTime = 1000
        ds.EchoTime = echo_time
        if phase_encoding_direction is not None:
            ds.InPlanePhaseEncodingDirection = phase_encoding_direction
        if sequence_name is not None:
            ds.SequenceName = sequence_name
        ds.InversionTime = 120
        if echo_numbers is not None:
            ds.EchoNumbers = echo_numbers
        ds.AcquisitionMatrix = [0, 16, 16, 0]
        ds.NumberOfPhaseEncodingSteps = 12
        ds.PercentSampling = 80
        ds.PercentPhaseFieldOfView = 75
        if parallel_reduction_factor_in_plane is not None:
            ds.ParallelReductionFactorInPlane = parallel_reduction_factor_in_plane
        ds.SAR = 0.42
    if modality == "CT":
        ds.KVP = 120
        ds.XRayTubeCurrent = 220
        ds.ExposureTime = 800
        ds.ConvolutionKernel = "B30f"
        ds.ReconstructionDiameter = 240
    if modality == "US":
        ds.TransducerData = "L12-5"
        ds.TransducerType = "LINEAR"
        ds.MechanicalIndex = 0.8
        ds.UltrasoundColorDataPresent = 0
    if modality == "XA":
        ds.KVP = 70
        ds.XRayTubeCurrent = 125
        ds.ExposureTime = 12
        ds.FrameTime = 33.3
        ds.DistanceSourceToDetector = 950
        ds.DistanceSourceToPatient = 700
    if modality == "PT":
        item = Dataset()
        item.Radiopharmaceutical = "FDG"
        item.RadionuclideTotalDose = 123456789
        item.RadionuclideHalfLife = 6586.2
        ds.RadiopharmaceuticalInformationSequence = Sequence([item])
        ds.DecayCorrection = "START"
    if philips_private_pulse_sequence_name is not None:
        item = Dataset()
        item.PulseSequenceName = philips_private_pulse_sequence_name
        ds.add_new((0x2005, 0x140F), "SQ", Sequence([item]))
    if acquisition_duration is not None:
        ds.AcquisitionDuration = acquisition_duration
    if ge_acquisition_duration_us is not None:
        block = ds.private_block(0x0019, ge_private_creator, create=True)
        block.add_new(0x5A, "FL", float(ge_acquisition_duration_us))
    ascconv_lines: list[str] = []
    if siemens_private_parallel_reduction_factor is not None:
        ascconv_lines.append(
            f"sPat.lAccelFactPE = {siemens_private_parallel_reduction_factor:g}"
        )
    if siemens_total_scan_time_sec is not None:
        ascconv_lines.append(f"lTotalScanTimeSec = {siemens_total_scan_time_sec:g}")
    if ascconv_lines:
        protocol = (
            "### ASCCONV BEGIN ###\n"
            + "\n".join(ascconv_lines)
            + "\n### ASCCONV END ###\n"
        ).encode()
        ds.add_new((0x0021, 0x1019), "OB", protocol)
    ds.save_as(path, enforce_file_format=True)


def find_study_dir(output_root: Path, date: str = "20260515", device: str | None = None) -> Path:
    if device:
        p = output_root / device / date
        if p.exists():
            return p
    matches = sorted(output_root.glob(f"*/{date}"))
    if matches:
        return matches[0]
    return output_root / (device or "UnitTest_Synthetic") / date


def args_for(input_root: Path, output_root: Path, **overrides: object) -> argparse.Namespace:
    values = {
        "input": input_root,
        "output": output_root,
        "action": "copy",
        "confirm_move": False,
        "if_exists": "error",
        "dry_run": False,
        "force_read": True,
        "include_hidden": False,
        "include_organized": False,
        "limit": 0,
        "series_dir_template": DEFAULT_SERIES_DIR_TEMPLATE,
        "file_template": DEFAULT_FILE_TEMPLATE,
        "profile": "auto",
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
    assert result.summary["profile"] == "auto"
    assert result.summary["csv_target_files"] == 1
    assert result.summary["csv_excluded_files"] == 0
    assert result.summary["csv_excluded_non_image_files"] == 0
    assert result.summary["organized_files_by_modality"] == {"MR": 1}
    assert result.summary["csv_target_files_by_modality"] == {"MR": 1}
    assert result.summary["csv_excluded_files_by_modality"] == {}
    assert not output_root.exists()


def test_dry_run_summary_lists_planned_metadata_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
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

    result = run(args_for(input_root, output_root, dry_run=True))
    print_summary(
        result.items,
        result.stats,
        result.output_root,
        result.profile,
        dry_run=result.dry_run,
    )

    output = capsys.readouterr().out
    assert "organized_files_by_modality=MR=1" in output
    assert "csv_target_files_by_modality=MR=1" in output
    assert "csv_excluded_files_by_modality=(none)" in output
    assert "planned_metadata_outputs:" in output
    assert "dicom_parameters.csv" in output
    assert "series_summary.csv" in output
    assert "organize_summary.json" in output


def test_default_scan_prunes_existing_organized_directory(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = input_root / "organized"
    input_root.mkdir()
    output_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        output_root / "old.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=99,
        instance_number=1,
    )

    result = run(args_for(input_root, output_root, dry_run=True))

    assert result.summary["candidate_files"] == 1
    assert result.summary["organized_files"] == 1


def test_default_scan_prunes_organized_backup_directory(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = input_root / "organized"
    backup_root = input_root / "organized.before-rerun"
    input_root.mkdir()
    backup_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        backup_root / "old.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=99,
        instance_number=1,
    )

    result = run(args_for(input_root, output_root, dry_run=True))

    assert result.summary["candidate_files"] == 1
    assert result.summary["organized_files"] == 1


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
    date_dir = find_study_dir(output_root)
    assert (date_dir / "dicom_parameters.csv").exists()
    assert (date_dir / "series_summary.csv").exists()

    with (date_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["SeriesNumber"] for row in rows] == ["000001", "000002"]
    assert [row["FileCount"] for row in rows] == ["1", "1"]
    assert rows[0]["EchoTimes_ms"] == "10.0"
    assert rows[0]["FOV_HxW_mm"] == "24x24"
    assert rows[0]["Matrix_RowsxCols"] == "16x16"
    assert rows[0]["TR_ms"] == "1000.0"
    assert rows[0]["InversionTime_ms"] == "120.0"
    assert rows[0]["EchoNumbers"] == "1"
    assert rows[0]["AcquisitionMatrix"] == "0\\16\\16\\0"
    assert rows[0]["NumberOfPhaseEncodingSteps"] == "12"
    assert rows[0]["PercentSampling"] == "80.0"
    assert rows[0]["PercentPhaseFOV"] == "75.0"
    assert rows[0]["ParallelReductionFactorInPlane"] == "N/A"
    assert rows[0]["SAR"] == "0.42"
    assert rows[0]["InPlanePhaseEncodingDirection"] == "ROW"
    assert rows[0]["PhaseEncodingDirectionPatient"] == "R→L"
    assert all("(" not in column and ")" not in column for column in rows[0])

    with (date_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        metadata_row = next(csv.DictReader(handle))
    assert metadata_row["TE_ms"] == "10.0"
    assert metadata_row["PixelBandwidth_Hz_per_px"] == "N/A"
    assert metadata_row["SequenceName"] == "tse"
    assert metadata_row["InversionTime_ms"] == "120.0"
    assert metadata_row["EchoNumbers"] == "1"
    assert metadata_row["AcquisitionMatrix"] == "0\\16\\16\\0"
    assert metadata_row["NumberOfPhaseEncodingSteps"] == "12"
    assert metadata_row["PercentSampling"] == "80.0"
    assert metadata_row["PercentPhaseFOV"] == "75.0"
    assert metadata_row["ParallelReductionFactorInPlane"] == "N/A"
    assert metadata_row["SAR"] == "0.42"
    assert metadata_row["InPlanePhaseEncodingDirection"] == "ROW"
    assert metadata_row["PhaseEncodingDirectionPatient"] == "R→L"
    assert metadata_row["PatientPosition"] == "HFS"
    assert all("(" not in column and ")" not in column for column in metadata_row)


def test_series_summary_columns_and_aggregates_share_parameter_rows(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    for instance_number, echo_time in ((1, 10), (2, 20)):
        write_dicom(
            input_root / f"echo{instance_number}.dcm",
            series_uid=series_uid,
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=instance_number,
            echo_time=echo_time,
            manufacturer="SIEMENS",
        )

    run(args_for(input_root, output_root))

    date_dir = find_study_dir(output_root)
    with (date_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        parameter_reader = csv.DictReader(handle)
        parameter_rows = list(parameter_reader)
        parameter_columns = set(parameter_reader.fieldnames or [])
    with (date_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        summary_reader = csv.DictReader(handle)
        summary_row = next(summary_reader)
        summary_columns = set(summary_reader.fieldnames or [])

    assert summary_columns <= parameter_columns
    assert "SeriesUIDHash" not in parameter_columns
    assert "SeriesUIDHash" not in summary_columns
    assert {
        "OrganizedFileName",
        "SOPInstanceUID",
        "InstanceNumber",
        "SliceLocation_mm",
        "SourceFileName",
        "ImagePositionPatient",
    }.isdisjoint(summary_columns)
    assert {row["TE_ms"] for row in parameter_rows} == {"10.0", "20.0"}
    assert summary_row["TE_ms"] == "10.0|20.0"
    for row in parameter_rows:
        assert row["FileCount"] == summary_row["FileCount"] == "2"
        assert row["EchoCount"] == summary_row["EchoCount"] == "2"
        assert row["EchoTimes_ms"] == summary_row["EchoTimes_ms"] == "10.0|20.0"
    for column in (
        "PixelBandwidth_Hz_per_px",
        "FlipAngle_deg",
        "MagneticFieldStrength_T",
        "ScanningSequence",
        "SequenceVariant",
        "SequenceName",
        "ImageOrientationPatient",
        "PatientPosition",
        "ParallelReductionFactorInPlane",
        "SiemensIceDims",
    ):
        assert column in parameter_columns
        assert column in summary_columns


@pytest.mark.parametrize(
    (
        "plane",
        "phase_axis",
        "image_orientation_patient",
        "patient_position",
        "expected_direction",
    ),
    [
        ("TRA", "ROW", (1, 0, 0, 0, 1, 0), "HFS", "R→L"),
        ("COR", "COL", (1, 0, 0, 0, 0, -1), "FFS", "H→F"),
        ("SAG", "ROW", (0, 1, 0, 0, 0, -1), "HFP", "A→P"),
    ],
)
def test_siemens_patient_phase_encoding_direction_for_cardinal_planes(
    tmp_path: Path,
    plane: str,
    phase_axis: str,
    image_orientation_patient: tuple[int, ...],
    patient_position: str,
    expected_direction: str,
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / f"{plane.lower()}.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="SIEMENS",
        series_description=f"Siemens {plane}",
        phase_encoding_direction=phase_axis,
        image_orientation_patient=image_orientation_patient,
        patient_position=patient_position,
    )

    run(args_for(input_root, output_root))

    date_dir = find_study_dir(output_root)
    with (date_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        metadata_row = next(csv.DictReader(handle))
    assert metadata_row["InPlanePhaseEncodingDirection"] == phase_axis
    assert metadata_row["PhaseEncodingDirectionPatient"] == expected_direction
    assert metadata_row["PatientPosition"] == patient_position

    with (date_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        summary_row = next(csv.DictReader(handle))
    assert summary_row["InPlanePhaseEncodingDirection"] == phase_axis
    assert summary_row["PhaseEncodingDirectionPatient"] == expected_direction


def test_siemens_parallel_reduction_factor_is_written_to_both_csvs(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "parallel.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="SIEMENS",
        parallel_reduction_factor_in_plane=2.0,
        siemens_private_parallel_reduction_factor=3.0,
    )

    run(args_for(input_root, output_root))

    date_dir = find_study_dir(output_root)
    for csv_name in ("dicom_parameters.csv", "series_summary.csv"):
        with (date_dir / csv_name).open(encoding="utf-8-sig", newline="") as handle:
            row = next(csv.DictReader(handle))
        assert row["ParallelReductionFactorInPlane"] == "2.0"


def test_siemens_private_parallel_reduction_factor_fallback_is_written(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "parallel_private.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="Siemens Healthineers",
        siemens_private_parallel_reduction_factor=3.0,
    )

    run(args_for(input_root, output_root))

    date_dir = find_study_dir(output_root)
    for csv_name in ("dicom_parameters.csv", "series_summary.csv"):
        with (date_dir / csv_name).open(encoding="utf-8-sig", newline="") as handle:
            row = next(csv.DictReader(handle))
        assert row["ParallelReductionFactorInPlane"] == "3.0"


def test_siemens_private_parallel_reduction_factor_is_vendor_scoped() -> None:
    ds = Dataset()
    ds.Manufacturer = "Other Vendor"
    ds.add_new((0x0021, 0x1019), "OB", b"sPat.lAccelFactPE = 4")

    assert parallel_reduction_factor_in_plane_value(ds) is None


@pytest.mark.parametrize(
    ("phase_axis", "image_orientation_patient", "anatomical_orientation_type"),
    [
        (None, (1, 0, 0, 0, 1, 0), None),
        ("ROW", None, None),
        ("OTHER", (1, 0, 0, 0, 1, 0), None),
        ("ROW", (1, 0, 0, 0, 1, 0), "QUADRUPED"),
    ],
)
def test_patient_phase_encoding_direction_is_na_when_not_derivable(
    tmp_path: Path,
    phase_axis: str | None,
    image_orientation_patient: tuple[int, ...] | None,
    anatomical_orientation_type: str | None,
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        phase_encoding_direction=phase_axis,
        image_orientation_patient=image_orientation_patient,
        anatomical_orientation_type=anatomical_orientation_type,
    )

    run(args_for(input_root, output_root))

    with (find_study_dir(output_root) / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))
    assert row["PhaseEncodingDirectionPatient"] == "N/A"


def test_enhanced_mr_functional_groups_supply_patient_phase_direction() -> None:
    orientation = Dataset()
    orientation.ImageOrientationPatient = [1, 0, 0, 0, 0, -1]
    geometry = Dataset()
    geometry.InPlanePhaseEncodingDirection = "COLUMN"
    modifier = Dataset()
    modifier.ParallelReductionFactorInPlane = 3.0
    shared = Dataset()
    shared.PlaneOrientationSequence = Sequence([orientation])
    shared.MRFOVGeometrySequence = Sequence([geometry])
    shared.MRModifierSequence = Sequence([modifier])
    ds = Dataset()
    ds.SharedFunctionalGroupsSequence = Sequence([shared])

    assert phase_encoding_direction_patient(ds) == "H→F"
    assert float(parallel_reduction_factor_in_plane_value(ds)) == 3.0


def test_metadata_tables_exclude_non_image_objects(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "image.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        input_root / "pr.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=2,
        sop_class_uid="1.2.840.10008.5.1.4.1.1.11.1",
        modality="PR",
        image_type=(),
        echo_numbers=None,
        sequence_name=None,
    )

    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        metadata_rows = list(csv.DictReader(handle))
    assert len(metadata_rows) == 1
    assert metadata_rows[0]["SOPClassUID"] == str(MRImageStorage)

    with (study_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["FileCount"] == "1"


def test_philips_sequence_name_falls_back_to_private_sequence(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="Philips",
        sequence_name=None,
        philips_private_pulse_sequence_name="TSE",
    )

    run(args_for(input_root, output_root))

    with (find_study_dir(output_root) / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        metadata_row = next(csv.DictReader(handle))
    assert metadata_row["SequenceName"] == "TSE"


def test_auto_profile_writes_mixed_modality_union_csv(tmp_path: Path) -> None:
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

    run(args_for(input_root, output_root, profile="auto"))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    assert {row["Modality"] for row in rows} == {"CT", "MR"}
    assert "TE_ms" in fieldnames
    assert "KVP_kV" in fieldnames
    mr_row = next(row for row in rows if row["Modality"] == "MR")
    ct_row = next(row for row in rows if row["Modality"] == "CT")
    assert mr_row["TE_ms"] == "10.0"
    assert ct_row["KVP_kV"] == "120.0"
    assert ct_row["TE_ms"] == "N/A"

    with (study_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        summary_rows = list(reader)
        summary_fieldnames = reader.fieldnames or []
    assert {row["Modality"] for row in summary_rows} == {"CT", "MR"}
    assert "KVP_kV" in summary_fieldnames
    assert "EchoCount" in summary_fieldnames


def test_auto_profile_writes_all_supported_modality_union_and_summary(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    modalities = ("MR", "CT", "US", "XA", "PT")
    for index, modality in enumerate(modalities, start=1):
        write_dicom(
            input_root / f"{modality.lower()}.dcm",
            series_uid=generate_uid(),
            sop_uid=generate_uid(),
            series_number=index,
            instance_number=1,
            modality=modality,
        )

    run(args_for(input_root, output_root, profile="auto"))

    with (find_study_dir(output_root) / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    assert {row["Modality"] for row in rows} == set(modalities)
    for column in (
        "TE_ms",
        "KVP_kV",
        "TransducerData",
        "FrameTime_ms",
        "Radiopharmaceutical",
    ):
        assert column in fieldnames
    mr_row = next(row for row in rows if row["Modality"] == "MR")
    ct_row = next(row for row in rows if row["Modality"] == "CT")
    us_row = next(row for row in rows if row["Modality"] == "US")
    xa_row = next(row for row in rows if row["Modality"] == "XA")
    pt_row = next(row for row in rows if row["Modality"] == "PT")
    assert mr_row["TE_ms"] == "10.0"
    assert mr_row["KVP_kV"] == "N/A"
    assert ct_row["KVP_kV"] == "120.0"
    assert ct_row["TE_ms"] == "N/A"
    assert us_row["TransducerData"] == "L12-5"
    assert us_row["Radiopharmaceutical"] == "N/A"
    assert xa_row["FrameTime_ms"] == "33.3"
    assert xa_row["TransducerData"] == "N/A"
    assert pt_row["Radiopharmaceutical"] == "FDG"
    assert pt_row["FrameTime_ms"] == "N/A"

    with (output_root / "organize_summary.json").open(encoding="utf-8") as handle:
        summary = json.load(handle)
    expected_counts = {modality: 1 for modality in modalities}
    assert summary["organized_files_by_modality"] == expected_counts
    assert summary["csv_target_files_by_modality"] == expected_counts
    assert summary["csv_excluded_files_by_modality"] == {}


def test_generic_profile_uses_common_columns_only(tmp_path: Path) -> None:
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

    run(args_for(input_root, output_root, profile="generic"))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    assert len(rows) == 2
    assert "TE_ms" not in fieldnames
    assert "KVP_kV" not in fieldnames
    assert "Modality" in fieldnames

    with (study_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        summary_rows = list(reader)
        summary_fieldnames = reader.fieldnames or []
    assert len(summary_rows) == 2
    assert "EchoCount" not in summary_fieldnames
    assert "KVP_kV" not in summary_fieldnames


def test_ct_profile_filters_to_ct_image_rows(tmp_path: Path) -> None:
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
    write_dicom(
        input_root / "pr.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=3,
        instance_number=1,
        sop_class_uid="1.2.840.10008.5.1.4.1.1.11.1",
        modality="PR",
    )

    run(args_for(input_root, output_root, profile="ct"))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["Modality"] == "CT"
    assert rows[0]["SOPClassUID"] == str(CTImageStorage)

    with (study_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["Modality"] == "CT"


def test_auto_profile_reports_non_image_modality_exclusions(tmp_path: Path) -> None:
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
    write_dicom(
        input_root / "pr.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=3,
        instance_number=1,
        sop_class_uid="1.2.840.10008.5.1.4.1.1.11.1",
        modality="PR",
    )

    result = run(args_for(input_root, output_root, profile="auto"))

    assert result.summary["organized_files_by_modality"] == {"CT": 1, "MR": 1, "PR": 1}
    assert result.summary["csv_target_files_by_modality"] == {"CT": 1, "MR": 1}
    assert result.summary["csv_excluded_files_by_modality"] == {"PR": 1}
    with (output_root / "organize_summary.json").open(encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["csv_excluded_files_by_modality"] == {"PR": 1}


def test_summary_counts_profile_csv_targets_and_non_image_exclusions(tmp_path: Path) -> None:
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
    write_dicom(
        input_root / "pr.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=3,
        instance_number=1,
        sop_class_uid="1.2.840.10008.5.1.4.1.1.11.1",
        modality="PR",
    )

    result = run(args_for(input_root, output_root, profile="ct"))

    assert result.summary["profile"] == "ct"
    assert result.summary["organized_files"] == 3
    assert result.summary["csv_target_files"] == 1
    assert result.summary["csv_excluded_non_image_files"] == 2
    assert result.summary["organized_files_by_modality"] == {"CT": 1, "MR": 1, "PR": 1}
    assert result.summary["csv_target_files_by_modality"] == {"CT": 1}
    assert result.summary["csv_excluded_files_by_modality"] == {"MR": 1, "PR": 1}
    with (output_root / "organize_summary.json").open(encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["profile"] == "ct"
    assert summary["csv_target_files"] == 1
    assert summary["csv_excluded_non_image_files"] == 2
    assert summary["csv_excluded_files_by_modality"] == {"MR": 1, "PR": 1}


@pytest.mark.parametrize(
    ("profile", "modality", "expected_column", "expected_value"),
    [
        ("ct", "CT", "KVP_kV", "120.0"),
        ("us", "US", "TransducerData", "L12-5"),
        ("xa", "XA", "FrameTime_ms", "33.3"),
        ("pt", "PT", "Radiopharmaceutical", "FDG"),
    ],
)
def test_non_mr_profiles_write_supported_metadata(
    tmp_path: Path,
    profile: str,
    modality: str,
    expected_column: str,
    expected_value: str,
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        modality=modality,
    )

    run(args_for(input_root, output_root, profile=profile))

    with (find_study_dir(output_root) / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))
    assert row["Modality"] == modality
    assert row[expected_column] == expected_value


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
        "UnitTest_Synthetic/20260515/000003_T2-TSE-axial-fast/"
    )


def test_default_series_directory_prefers_series_description_for_philips(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=8,
        instance_number=1,
        manufacturer="Philips",
        series_description="B1 fast named by operator",
        protocol_name="WIP B1 fast named by operator",
    )

    result = run(args_for(input_root, output_root))

    assert result.items[0].destination.parent.name == "000008_B1-fast-named-by-operator"
    assert result.items[0].row["SeriesDescription"] == "B1 fast named by operator"
    assert result.items[0].row["ProtocolName"] == "WIP B1 fast named by operator"


def test_default_series_directory_prefers_series_description_for_ge(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=8,
        instance_number=1,
        manufacturer="GE MEDICAL SYSTEMS",
        series_description="T2 F-sat Cor FRFSE",
        protocol_name="004 Wrist (GP-Flex)",
    )

    result = run(args_for(input_root, output_root))

    assert result.items[0].destination.parent.name == "000008_T2-F-sat-Cor-FRFSE"
    assert result.items[0].row["SeriesDescription"] == "T2 F-sat Cor FRFSE"
    assert result.items[0].row["ProtocolName"] == "004 Wrist (GP-Flex)"


def test_philips_numeric_series_label_inherits_anchor_name(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    study_uid = generate_uid()
    write_dicom(
        input_root / "anchor.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=4,
        instance_number=1,
        manufacturer="Philips",
        acquisition_number=4,
        series_description="T2W Echose 30*32.",
        protocol_name="WIP T2W Echose 30*32.",
        image_type=("ORIGINAL", "PRIMARY", "M_SE", "M", "SE"),
        study_uid=study_uid,
    )
    write_dicom(
        input_root / "numeric.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=6,
        instance_number=1,
        manufacturer="Philips",
        acquisition_number=4,
        series_description="2",
        protocol_name="WIP 2",
        image_type=("ORIGINAL", "PRIMARY", "M_SE", "M", "SE"),
        study_uid=study_uid,
    )

    result = run(args_for(input_root, output_root))

    parents = sorted(item.destination.parent.name for item in result.items)
    assert parents == ["000004_T2W-Echose-30-32", "000006_T2W-Echose-30-32_2"]


def test_philips_series_splits_reconstructions_by_image_type(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "m1.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=10,
        instance_number=1,
        manufacturer="Philips",
        series_description="B1 fast named by operator",
        protocol_name="WIP B1 fast named by operator",
        image_type=("ORIGINAL", "PRIMARY", "M_B1", "M", "B1"),
        echo_time=0,
    )
    write_dicom(
        input_root / "m2.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=10,
        instance_number=2,
        manufacturer="Philips",
        series_description="B1 fast named by operator",
        protocol_name="WIP B1 fast named by operator",
        image_type=("ORIGINAL", "PRIMARY", "M_B1", "M", "B1"),
        echo_time=0,
    )
    write_dicom(
        input_root / "phase.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=10,
        instance_number=3,
        manufacturer="Philips",
        series_description="B1 fast named by operator",
        protocol_name="WIP B1 fast named by operator",
        image_type=("ORIGINAL", "PRIMARY", "PHASE MAP", "P", "B1"),
        echo_time=0,
    )
    write_dicom(
        input_root / "xx.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=10,
        instance_number=4,
        manufacturer="Philips",
        series_description="B1 fast named by operator",
        protocol_name="WIP B1 fast named by operator",
        image_type=(),
        sop_class_uid="1.3.46.670589.11.0.0.12.2",
        echo_numbers=None,
    )

    result = run(args_for(input_root, output_root))

    parents = [item.destination.parent.name for item in result.items]
    assert parents.count("000010_B1-fast-named-by-operator_M_B1") == 3
    assert parents.count("000010_B1-fast-named-by-operator_PHASE-MAP-B1") == 1
    assert result.summary["series_count"] == 2

    with (find_study_dir(output_root) / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert sorted(row["FileCount"] for row in rows) == ["1", "2"]


def test_philips_non_mr_series_does_not_split_reconstructions(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "ct_axial.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=11,
        instance_number=1,
        manufacturer="Philips",
        modality="CT",
        image_type=("ORIGINAL", "PRIMARY", "AXIAL"),
    )
    write_dicom(
        input_root / "ct_derived.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=11,
        instance_number=2,
        manufacturer="Philips",
        modality="CT",
        image_type=("DERIVED", "PRIMARY", "AXIAL"),
    )

    result = run(args_for(input_root, output_root, profile="auto"))

    parents = [item.destination.parent.name for item in result.items]
    assert parents == ["000011_Series-11", "000011_Series-11"]
    assert result.summary["series_count"] == 1


def test_protocol_name_template_key_still_uses_raw_protocol_name(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=9,
        instance_number=1,
        manufacturer="Philips",
        series_description="Chosen name",
        protocol_name="WIP Chosen name",
    )

    result = run(
        args_for(
            input_root,
            output_root,
            series_dir_template="{series_number}_{protocol_name}",
        )
    )

    assert result.items[0].destination.parent.name == "000009_WIP-Chosen-name"


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
    with (find_study_dir(keep_output) / "dicom_parameters.csv").open(
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
    with (find_study_dir(hash_output) / "dicom_parameters.csv").open(
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
    with (find_study_dir(drop_output) / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        drop_row = next(csv.DictReader(handle))
    assert drop_row["PatientName"] == "N/A"
    assert drop_row["PatientID"] == "N/A"
    assert drop_row["PatientNameHash"] == "N/A"
    assert drop_row["PatientIDHash"] == "N/A"


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
                "InPlanePhaseEncodingDirection",
                "PrivateMissing=0021,9999",
            ),
        )
    )

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))

    assert row["DICOM_EchoTime"] == "10.0"
    assert row["DICOM_RepetitionTime"] == "1000.0"
    assert row["CustomPhase"] == "ROW"
    assert row["DICOM_InPlanePhaseEncodingDirection"] == "ROW"
    assert row["PrivateMissing"] == "N/A"

    with (study_dir / "series_summary.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        summary_row = next(csv.DictReader(handle))
    assert summary_row["DICOM_EchoTime"] == "10.0"
    assert summary_row["DICOM_RepetitionTime"] == "1000.0"
    assert summary_row["CustomPhase"] == "ROW"
    assert summary_row["DICOM_InPlanePhaseEncodingDirection"] == "ROW"
    assert summary_row["PrivateMissing"] == "N/A"

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


def test_package_imports() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import dicom_organizer; import dicom_organizer.core"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_cli_accepts_positional_input(tmp_path: Path) -> None:
    args = parse_args([str(tmp_path), "--dry-run"])

    assert args.input == tmp_path
    assert args.dry_run is True
    assert args.force_read is True


def test_cli_can_disable_default_force_read(tmp_path: Path) -> None:
    args = parse_args([str(tmp_path), "--no-force-read"])

    assert args.force_read is False


def test_cli_keeps_input_option_for_compatibility(tmp_path: Path) -> None:
    args = parse_args(["--input", str(tmp_path), "--dry-run"])

    assert args.input == tmp_path
    assert args.dry_run is True


def test_cli_accepts_short_input_option(tmp_path: Path) -> None:
    args = parse_args(["-i", str(tmp_path), "--dry-run"])

    assert args.input == tmp_path
    assert args.dry_run is True


def test_cli_accepts_common_short_options(tmp_path: Path) -> None:
    output_root = tmp_path / "organized"
    args = parse_args(
        [
            str(tmp_path),
            "-o",
            str(output_root),
            "-n",
            "-f",
            "-l",
            "3",
            "-p",
            "ct",
            "-t",
            "EchoTime",
            "-v",
        ]
    )

    assert args.output == output_root
    assert args.dry_run is True
    assert args.force_read is True
    assert args.limit == 3
    assert args.profile == "ct"
    assert args.dicom_tags == ["EchoTime"]
    assert args.verbose is True


def test_cli_rejects_duplicate_input_forms(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args([str(tmp_path), "--input", str(tmp_path)])


def test_cli_version_prints_package_version() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from dicom_organizer.core import main; "
                "sys.argv=['dicom-organizer','--version']; "
                "raise SystemExit(main())"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip().startswith("dicom-organizer ")


def test_version_matches_pyproject() -> None:
    import dicom_organizer

    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    assert dicom_organizer.__version__ == data["project"]["version"]


def test_csv_formats_time_fields(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()

    series_uid = generate_uid()
    write_dicom(
        input_root / "img1.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        acquisition_time="190429.500000",
        study_time="182752.265186",
        series_time="190410.990000",
    )

    run(args_for(input_root, output_root))

    date_dir = find_study_dir(output_root)
    with (date_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["AcquisitionTime"] == "190429.500000"
    assert rows[0]["StudyTime"] == "182752.265186"
    assert rows[0]["SeriesTime"] == "190410.990000"

    with (date_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["AcquisitionTime"] == "190429.500000"
    assert summary_rows[0]["StudyTime"] == "182752.265186"
    assert summary_rows[0]["SeriesTime"] == "190410.990000"


def test_device_and_study_date_hierarchy(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()

    # Create two series from same study spanning midnight (StudyDate 20260718, but series 2 has AcquisitionDate 20260719)
    study_uid = generate_uid()
    write_dicom(
        input_root / "s1.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="GE MEDICAL SYSTEMS",
        acquisition_date="20260718",
    )
    # Give it specific model name
    ds1 = pydicom.dcmread(input_root / "s1.dcm")
    ds1.ManufacturerModelName = "SIGNA Architect"
    ds1.StudyInstanceUID = study_uid
    ds1.StudyDate = "20260718"
    ds1.save_as(input_root / "s1.dcm")

    write_dicom(
        input_root / "s2.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        manufacturer="GE MEDICAL SYSTEMS",
        acquisition_date="20260719",  # Next day acquisition
    )
    ds2 = pydicom.dcmread(input_root / "s2.dcm")
    ds2.ManufacturerModelName = "SIGNA Architect"
    ds2.StudyInstanceUID = study_uid
    ds2.StudyDate = "20260718"  # Same study date
    ds2.save_as(input_root / "s2.dcm")

    run(args_for(input_root, output_root))

    # Expect folder: output_root / "GE_SIGNA-Architect" / "20260718"
    expected_study_dir = output_root / "GE_SIGNA-Architect" / "20260718"
    assert expected_study_dir.exists()
    assert (expected_study_dir / "dicom_parameters.csv").exists()
    assert (expected_study_dir / "series_summary.csv").exists()

    with (expected_study_dir / "series_summary.csv").open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    # Both series must be in the same StudyDate folder (midnight span resolved!)
    assert len(rows) == 2
    assert {row["SeriesNumber"] for row in rows} == {"000001", "000002"}
    # Verify SeriesUIDHash is not in CSV
    assert "SeriesUIDHash" not in fieldnames


def test_ensure_within_output_root_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ValueError, match="Output path escapes the output root"):
        ensure_within_output_root(root, root / ".." / "x")


def test_safe_date_validation() -> None:
    assert safe_date("20260515") == "20260515"
    assert safe_date("2026-05-15") == "20260515"
    assert safe_date("invalid") == "unknown_date"
    assert safe_date("../../escaped") == "unknown_date"
    assert safe_date("20260230") == "unknown_date"


def test_invalid_study_date_is_sanitized(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    dcm_path = input_root / "one.dcm"
    write_dicom(
        dcm_path,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    ds = pydicom.dcmread(dcm_path)
    ds.StudyDate = "../../escaped"
    ds.save_as(dcm_path)

    result = run(args_for(input_root, output_root))

    assert len(result.items) == 1
    dest = result.items[0].destination
    assert dest.resolve().is_relative_to(output_root.resolve())
    assert dest.parent.parent.name == "unknown_date"
    assert not (output_root.parent / "escaped").exists()

    # CSV preserves the raw value
    study_dir = dest.parent.parent
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["StudyDate"] == "../../escaped"


def test_series_dir_suffix_does_not_collide_with_existing_label(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()

    for name, label in (("a.dcm", "A"), ("b.dcm", "A"), ("c.dcm", "A_01")):
        write_dicom(
            input_root / name,
            series_uid=generate_uid(),
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=1,
            protocol_name=label,
        )

    result = run(args_for(input_root, output_root))
    dirs = [item.destination.parent for item in result.items]
    counts = {d: len(list(d.glob("*.dcm"))) for d in set(dirs)}

    assert len(set(dirs)) == 3
    assert all(count == 1 for count in counts.values())
    assert result.summary["series_count"] == 3


def test_materialize_failure_keeps_previous_output(tmp_path: Path) -> None:
    root = tmp_path / "atomic"
    root.mkdir()
    dest = root / "dest.dcm"
    dest.write_text("previous output")
    with pytest.raises(Exception):
        materialize(root / "missing.dcm", dest, action="copy", overwrite=True)
    assert dest.exists()
    assert dest.read_text() == "previous output"
    assert [p.name for p in root.iterdir() if p.name != "dest.dcm"] == []


def test_move_keeps_source_when_copy_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src.txt"
    dest = tmp_path / "dest.txt"
    src.write_text("source content")

    def fake_replace(s: Path, d: Path) -> None:
        err = OSError()
        err.errno = errno.EXDEV
        raise err

    monkeypatch.setattr("dicom_organizer.core.os.replace", fake_replace)

    def fake_copy2(s: Path, d: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr("dicom_organizer.core.shutil.copy2", fake_copy2)

    with pytest.raises(OSError, match="copy failed"):
        materialize(src, dest, action="move", overwrite=False)

    assert src.exists()
    assert src.read_text() == "source content"
    assert not dest.exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_materialize_move_success(tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    dest = tmp_path / "dest.txt"
    src.write_text("move content")
    materialize(src, dest, action="move", overwrite=False)
    assert not src.exists()
    assert dest.exists()
    assert dest.read_text() == "move content"


def test_skip_rerun_keeps_existing_rows_in_csv(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()

    write_dicom(
        input_root / "one.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    run(args_for(input_root, output_root))

    write_dicom(
        input_root / "two.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=2,
    )
    run(args_for(input_root, output_root, if_exists="skip"))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["FileCount"] for row in rows} == {"2"}

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["FileCount"] == "2"


def test_metadata_csv_drops_rows_for_missing_files(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()

    write_dicom(
        input_root / "one.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        input_root / "two.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=2,
    )
    run(args_for(input_root, output_root))

    # 手で one.dcm の入出力を削除する
    (input_root / "one.dcm").unlink()
    study_dir = find_study_dir(output_root)
    dcm_files = sorted(study_dir.rglob("*.dcm"))
    assert len(dcm_files) == 2
    dcm_files[0].unlink()

    # 別ファイル three.dcm を追加して再実行
    write_dicom(
        input_root / "three.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=3,
    )
    run(args_for(input_root, output_root, if_exists="skip"))

    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["InstanceNumber"] for row in rows} == {"2", "3"}
    assert {row["FileCount"] for row in rows} == {"2"}


def test_cli_dicom_tag_option_reaches_metadata_csv(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    write_dicom(
        input_root / "one.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        echo_time=12.5,
    )
    args = parse_args([str(input_root), "-o", str(output_root), "-t", "EchoTime"])
    run(args)

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert "DICOM_EchoTime" in rows[0]
    assert rows[0]["DICOM_EchoTime"] == "12.5"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert "DICOM_EchoTime" in summary_rows[0]
    assert summary_rows[0]["DICOM_EchoTime"] == "12.5"


def test_options_paths_are_resolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    options = OrganizeOptions(input_root=Path("input"), output_root=Path("organized"))
    normalized = normalize_options(options)
    assert normalized.input_root.is_absolute()
    assert normalized.output_root.is_absolute()
    assert normalized.input_root == (tmp_path / "input").resolve()
    assert normalized.output_root == (tmp_path / "organized").resolve()


def test_relative_options_produce_valid_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    inp = Path("input")
    inp.mkdir()
    target = inp / "a.dcm"
    write_dicom(
        target,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    result = run(
        OrganizeOptions(input_root=Path("input"), output_root=Path("organized"), action="symlink")
    )
    dest = result.items[0].destination
    assert dest.exists()
    assert dest.is_symlink()
    link_target = dest.readlink()
    assert link_target.is_absolute()


def test_philips_anchor_label_is_scoped_to_study(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()

    write_dicom(
        input_root / "a1.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="Philips Medical Systems",
        series_description="Brain",
        acquisition_number=3,
        image_type=("ORIGINAL", "PRIMARY", "M", "FFE"),
        acquisition_date="20260515",
        study_uid=generate_uid(),
    )
    write_dicom(
        input_root / "b1.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        manufacturer="Philips Medical Systems",
        series_description="123",
        acquisition_number=3,
        image_type=("ORIGINAL", "PRIMARY", "M", "FFE"),
        acquisition_date="20260515",
        study_uid=generate_uid(),
    )

    result = run(args_for(input_root, output_root))
    names = sorted(item.destination.parent.name for item in result.items)
    numeric = [name for name in names if name.startswith("000002")]
    assert len(numeric) == 1
    assert "Brain" not in numeric[0]


def test_format_duration() -> None:
    assert format_duration(48.2) == "00:00:48"
    assert format_duration(54.0) == "00:00:54"
    assert format_duration(108) == "00:01:48"
    assert format_duration(323) == "00:05:23"
    assert format_duration(498.039808) == "00:08:18"
    assert format_duration(528.0) == "00:08:48"
    assert format_duration(3661) == "01:01:01"
    assert format_duration(0) == "N/A"
    assert format_duration(-5) == "N/A"
    assert format_duration(None) == "N/A"
    assert format_duration("abc") == "N/A"


def test_scan_duration_fields_direct() -> None:
    ds = Dataset()
    assert scan_duration_fields(ds) == ("N/A", "N/A")

    ds.AcquisitionDuration = 54.0
    assert scan_duration_fields(ds) == ("00:00:54", "0018,9073")


def test_scan_duration_from_standard_tag(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "scan.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        acquisition_duration=528.0,
    )
    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["ScanDuration"] == "00:08:48"
    assert rows[0]["ScanDurationSource"] == "0018,9073"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["ScanDuration"] == "00:08:48"
    assert summary_rows[0]["ScanDurationSource"] == "0018,9073"


def test_scan_duration_from_ge_private_tag(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "scan.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="GE MEDICAL SYSTEMS",
        ge_acquisition_duration_us=48200000.0,
    )
    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["ScanDuration"] == "00:00:48"
    assert rows[0]["ScanDurationSource"] == "0019,105A"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["ScanDuration"] == "00:00:48"
    assert summary_rows[0]["ScanDurationSource"] == "0019,105A"


def test_scan_duration_from_siemens_protocol(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "scan.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="SIEMENS",
        siemens_total_scan_time_sec=323.0,
    )
    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["ScanDuration"] == "00:05:23"
    assert rows[0]["ScanDurationSource"] == "0021,1019:lTotalScanTimeSec"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["ScanDuration"] == "00:05:23"
    assert summary_rows[0]["ScanDurationSource"] == "0021,1019:lTotalScanTimeSec"


def test_scan_duration_is_vendor_scoped(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "scan.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="UnitTest",
        ge_acquisition_duration_us=48200000.0,
        ge_private_creator="NOT_GEMS_ACQU_01",
        siemens_total_scan_time_sec=323.0,
    )
    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["ScanDuration"] == "N/A"
    assert rows[0]["ScanDurationSource"] == "N/A"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["ScanDuration"] == "N/A"
    assert summary_rows[0]["ScanDurationSource"] == "N/A"


def test_scan_duration_missing_is_na(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "scan.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["ScanDuration"] == "N/A"
    assert rows[0]["ScanDurationSource"] == "N/A"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["ScanDuration"] == "N/A"
    assert summary_rows[0]["ScanDurationSource"] == "N/A"


def test_scan_duration_priority_standard_over_ge_private(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "organized"
    input_root.mkdir()
    series_uid = generate_uid()
    write_dicom(
        input_root / "scan.dcm",
        series_uid=series_uid,
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="GE MEDICAL SYSTEMS",
        acquisition_duration=528.0,
        ge_acquisition_duration_us=48200000.0,
    )
    run(args_for(input_root, output_root))

    study_dir = find_study_dir(output_root)
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["ScanDuration"] == "00:08:48"
    assert rows[0]["ScanDurationSource"] == "0018,9073"

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert len(summary_rows) == 1
    assert summary_rows[0]["ScanDuration"] == "00:08:48"
    assert summary_rows[0]["ScanDurationSource"] == "0018,9073"


def test_skip_reasons_classification(tmp_path: Path) -> None:
    # 1. Non-DICOM text
    text_file = tmp_path / "notes.txt"
    text_file.write_text("Hello DICOM", encoding="utf-8")
    res = classify_dicom_file(text_file, force=True)
    assert res.reason == "not_dicom"

    # 2. Empty file
    empty_file = tmp_path / "empty.bin"
    empty_file.write_bytes(b"")
    res = classify_dicom_file(empty_file, force=True)
    assert res.reason == "not_dicom"

    # 3. Truncated DICOM (has DICM prefix but truncated)
    valid_dcm = tmp_path / "valid.dcm"
    write_dicom(
        valid_dcm,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    raw = valid_dcm.read_bytes()
    truncated_file = tmp_path / "truncated.dcm"
    truncated_file.write_bytes(raw[:200])
    res = classify_dicom_file(truncated_file, force=True)
    assert res.reason == "read_error"

    # 4. Missing required UID (has DICOM attributes but no SeriesInstanceUID/SOPInstanceUID)
    nouid_file = tmp_path / "nouid.dcm"
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = MRImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(nouid_file), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = MRImageStorage
    ds.Modality = "MR"
    ds.save_as(nouid_file, enforce_file_format=True)
    res = classify_dicom_file(nouid_file, force=True)
    assert res.reason == "missing_required_uid"

    # 5. Permission denied (if non-root and POSIX)
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0:
        noperm_file = tmp_path / "noperm.dcm"
        shutil.copy2(valid_dcm, noperm_file)
        os.chmod(noperm_file, 0)
        try:
            res = classify_dicom_file(noperm_file, force=True)
            assert res.reason == "permission_denied"
        finally:
            os.chmod(noperm_file, 0o644)

    # 6. Valid DICOM
    res = classify_dicom_file(valid_dcm, force=True)
    assert res.reason == "N/A"
    assert res.dataset is not None


def test_file_report_csv_columns_and_content(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    dcm = input_root / "img.dcm"
    s_uid = generate_uid()
    sop_uid = generate_uid()
    write_dicom(
        dcm,
        series_uid=s_uid,
        sop_uid=sop_uid,
        series_number=1,
        instance_number=1,
        modality="MR",
    )
    (input_root / "readme.txt").write_text("plain text", encoding="utf-8")
    (input_root / ".hidden.dcm").write_bytes(b"some hidden bytes")

    result = run(OrganizeOptions(input_root=input_root, output_root=output_root))
    assert result.status == "completed"

    report_path = output_root / "file_report.csv"
    assert report_path.exists()
    with report_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    assert headers == FILE_REPORT_COLUMNS
    by_src = {r["SourceFileName"]: r for r in rows}
    assert "img.dcm" in by_src
    assert by_src["img.dcm"]["Status"] == "organized"
    assert by_src["img.dcm"]["Reason"] == "N/A"
    assert by_src["img.dcm"]["SOPInstanceUID"] == sop_uid
    assert by_src["img.dcm"]["Modality"] == "MR"

    assert "readme.txt" in by_src
    assert by_src["readme.txt"]["Status"] == "skipped"
    assert by_src["readme.txt"]["Reason"] == "not_dicom"

    assert ".hidden.dcm" in by_src
    assert by_src[".hidden.dcm"]["Status"] == "skipped"
    assert by_src[".hidden.dcm"]["Reason"] == "excluded_hidden"


def test_duplicates_handling_identical_and_conflict(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    s1 = generate_uid()
    sop1 = generate_uid()
    write_dicom(
        input_root / "img1.dcm",
        series_uid=s1,
        sop_uid=sop1,
        series_number=1,
        instance_number=1,
    )
    shutil.copy2(input_root / "img1.dcm", input_root / "img1_dup.dcm")

    s2 = generate_uid()
    conflict_sop = generate_uid()
    write_dicom(
        input_root / "conflict1.dcm",
        series_uid=s2,
        sop_uid=conflict_sop,
        series_number=2,
        instance_number=1,
        patient_name="Patient^One",
    )
    write_dicom(
        input_root / "conflict2.dcm",
        series_uid=s2,
        sop_uid=conflict_sop,
        series_number=2,
        instance_number=1,
        patient_name="Patient^Two",
    )

    result = run(OrganizeOptions(input_root=input_root, output_root=output_root))
    assert result.status == "completed"

    placed_dcm = list(output_root.rglob("*.dcm"))
    assert len(placed_dcm) == 3

    with (output_root / "organize_summary.json").open(encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["duplicate_conflicts"] == 1
    assert summary["skipped_by_reason"].get("duplicate_identical") == 1


def test_progress_events_sequence(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    s_uid = generate_uid()
    for i in range(1, 3):
        write_dicom(
            input_root / f"img_{i}.dcm",
            series_uid=s_uid,
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=i,
        )

    events: list[ProgressEvent] = []
    run(
        OrganizeOptions(input_root=input_root, output_root=output_root),
        progress=events.append,
    )
    stages = []
    for e in events:
        if not stages or stages[-1] != e.stage:
            stages.append(e.stage)
    assert stages == ["discover", "read", "plan", "copy", "write"]
    copy_events = [e for e in events if e.stage == "copy"]
    assert copy_events[0].done == 0
    assert copy_events[-1].done == copy_events[-1].total == 2

    dry_events: list[ProgressEvent] = []
    run(
        OrganizeOptions(input_root=input_root, output_root=tmp_path / "dry"),
        dry_run=True,
        progress=dry_events.append,
    )
    dry_stages = []
    for e in dry_events:
        if not dry_stages or dry_stages[-1] != e.stage:
            dry_stages.append(e.stage)
    assert dry_stages == ["discover", "read", "plan"]


def test_cancel_during_copy_and_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    s_uid = generate_uid()
    for i in range(1, 5):
        write_dicom(
            input_root / f"img_{i}.dcm",
            series_uid=s_uid,
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=i,
        )

    cancel = threading.Event()
    call_count = 0
    import dicom_organizer.core as core

    original_mat = core.materialize

    def _mat(*args, **kwargs):
        nonlocal call_count
        res = original_mat(*args, **kwargs)
        call_count += 1
        if call_count == 2:
            cancel.set()
        return res

    monkeypatch.setattr(core, "materialize", _mat)
    result = run(
        OrganizeOptions(input_root=input_root, output_root=output_root),
        cancel_event=cancel,
    )
    assert result.status == "cancelled"
    assert len(list(output_root.rglob("*.dcm"))) == 2

    summary = json.loads((output_root / "organize_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "cancelled"
    assert summary["organized_files"] == 2
    assert summary["not_processed_files"] == 2

    monkeypatch.undo()
    resumed = run(OrganizeOptions(input_root=input_root, output_root=output_root, if_exists="skip"))
    assert resumed.status == "completed"
    assert resumed.previous_run_status == "cancelled"
    assert len(list(output_root.rglob("*.dcm"))) == 4


def test_failure_during_copy_and_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    s_uid = generate_uid()
    for i in range(1, 4):
        write_dicom(
            input_root / f"img_{i}.dcm",
            series_uid=s_uid,
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=i,
        )

    call_count = 0
    import dicom_organizer.core as core

    original_mat = core.materialize

    def _failing_mat(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("synthetic copy crash")
        return original_mat(*args, **kwargs)

    monkeypatch.setattr(core, "materialize", _failing_mat)
    with pytest.raises(RuntimeError, match="synthetic copy crash"):
        run(OrganizeOptions(input_root=input_root, output_root=output_root))

    summary = json.loads((output_root / "organize_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert "synthetic copy crash" in summary["error"]

    monkeypatch.undo()
    preview = run(OrganizeOptions(input_root=input_root, output_root=output_root), dry_run=True)
    assert preview.previous_run_status == "failed"
    assert any("--if-exists skip" in w for w in preview.warnings)


def test_insufficient_space_error_and_bypass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    write_dicom(
        input_root / "img.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    from collections import namedtuple

    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: usage(10**10, 10**10 - 10, 10))

    with pytest.raises(InsufficientSpaceError):
        run(OrganizeOptions(input_root=input_root, output_root=output_root))

    assert not output_root.exists()

    res = run(OrganizeOptions(input_root=input_root, output_root=output_root, space_check=False))
    assert res.status == "completed"


def test_checksum_verification_and_integrity_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    dcm = input_root / "img.dcm"
    write_dicom(
        dcm,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    res = run(OrganizeOptions(input_root=input_root, output_root=output_root, checksum=True))
    assert res.status == "completed"
    with (output_root / "file_report.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_hash = hashlib.sha256(dcm.read_bytes()).hexdigest()
    assert rows[0]["SHA256"] == expected_hash

    corrupt_root = tmp_path / "corrupt_out"

    def _bad_copy(src, dst, *args, **kwargs):
        Path(dst).write_bytes(Path(src).read_bytes()[:-5])
        return dst

    monkeypatch.setattr(shutil, "copy2", _bad_copy)
    with pytest.raises(IntegrityError):
        run(OrganizeOptions(input_root=input_root, output_root=corrupt_root))
    assert not list(corrupt_root.rglob("*.dcm"))


def test_cli_wp1_options_and_interrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    write_dicom(
        input_root / "img.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    parsed = parse_args([str(input_root), "--checksum", "--no-space-check", "--no-progress"])
    assert parsed.checksum is True
    assert parsed.space_check is False
    assert parsed.progress is False

    import io
    import dicom_organizer.core as core

    output_root = tmp_path / "out_interrupt"

    def _interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(core, "materialize", _interrupt)
    monkeypatch.setattr(
        sys,
        "argv",
        ["dicom-organizer", str(input_root), "-o", str(output_root), "--no-progress"],
    )
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)

    code = core.main()
    assert code == 130
    assert "--if-exists skip" in stderr.getvalue()


def test_dicomdir_classification(tmp_path: Path) -> None:
    from pydicom.fileset import FileSet

    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    staging = tmp_path / "staging"
    staging.mkdir(parents=True)
    input_root.mkdir(parents=True)

    img_path = staging / "img.dcm"
    write_dicom(
        img_path,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        study_time="120000",
    )
    ds = pydicom.dcmread(img_path)
    ds.StudyID = "1"
    file_set = FileSet()
    try:
        file_set.add(ds)
        file_set.write(input_root / "disc")
    finally:
        # Clean up pydicom FileSet staging directory to prevent ResourceWarning.
        if hasattr(file_set, "_stage") and "t" in file_set._stage:
            file_set._stage["t"].cleanup()

    dicomdir_file = input_root / "disc" / "DICOMDIR"
    assert dicomdir_file.exists()

    result = classify_dicom_file(dicomdir_file, force=True)
    assert result.reason == "dicomdir"

    res = run(OrganizeOptions(input_root=input_root, output_root=output_root))
    assert res.stats["skip_dicomdir"] == 1
    with (output_root / "file_report.csv").open(encoding="utf-8-sig", newline="") as h:
        rows = list(csv.DictReader(h))
    dicomdir_row = next(r for r in rows if "DICOMDIR" in r["SourceFileName"])
    assert dicomdir_row["Status"] == "skipped"
    assert dicomdir_row["Reason"] == "dicomdir"


def test_four_file_duplicate_chain_r2(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    sop_uid = generate_uid()
    series_uid = generate_uid()

    # A: original
    write_dicom(
        input_root / "a.dcm",
        series_uid=series_uid,
        sop_uid=sop_uid,
        series_number=1,
        instance_number=1,
        patient_name="PatientA",
    )
    # B: identical to A
    shutil.copy2(input_root / "a.dcm", input_root / "b.dcm")

    # C: same SOPInstanceUID, different content
    write_dicom(
        input_root / "c.dcm",
        series_uid=series_uid,
        sop_uid=sop_uid,
        series_number=1,
        instance_number=1,
        patient_name="PatientC",
    )
    # D: identical to C
    shutil.copy2(input_root / "c.dcm", input_root / "d.dcm")

    res = run(OrganizeOptions(input_root=input_root, output_root=output_root))
    assert res.status == "completed"
    assert len(res.items) == 2  # Only A and C are organized, not D!
    assert res.stats["duplicate_conflicts"] == 1
    assert res.stats["skip_duplicate_identical"] == 2

    with (output_root / "file_report.csv").open(encoding="utf-8-sig", newline="") as h:
        rows = {r["SourceFileName"]: r for r in csv.DictReader(h)}

    assert rows["a.dcm"]["Status"] == "organized"
    assert rows["a.dcm"]["DuplicateOf"] == "N/A"

    assert rows["b.dcm"]["Status"] == "skipped"
    assert rows["b.dcm"]["Reason"] == "duplicate_identical"
    assert rows["b.dcm"]["DuplicateOf"] == "a.dcm"

    assert rows["c.dcm"]["Status"] == "organized"
    assert rows["c.dcm"]["Reason"] == "duplicate_conflict"
    assert rows["c.dcm"]["DuplicateOf"] == "a.dcm"

    # D must match C, NOT re-copied!
    assert rows["d.dcm"]["Status"] == "skipped"
    assert rows["d.dcm"]["Reason"] == "duplicate_identical"
    assert rows["d.dcm"]["DuplicateOf"] == "c.dcm"


def test_organize_result_summary_status_r3(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    write_dicom(
        input_root / "img.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    # 1. Normal run
    res_completed = run(OrganizeOptions(input_root=input_root, output_root=output_root / "out1"))
    assert res_completed.status == "completed"
    assert res_completed.summary["status"] == "completed"

    # 2. Dry run
    res_dry = run(OrganizeOptions(input_root=input_root, output_root=output_root / "out2", dry_run=True))
    assert res_dry.status == "dry_run"
    assert res_dry.summary["status"] == "dry_run"

    # 3. Cancelled run
    cancel_evt = threading.Event()
    cancel_evt.set()
    res_cancelled = run(
        OrganizeOptions(input_root=input_root, output_root=output_root / "out3"),
        cancel_event=cancel_evt,
    )
    assert res_cancelled.status == "cancelled"
    assert res_cancelled.summary["status"] == "cancelled"


def test_dry_run_existing_output_conflict_r4(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    write_dicom(
        input_root / "img.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )

    # First do a real run so output files exist
    res_real = run(OrganizeOptions(input_root=input_root, output_root=output_root))
    assert res_real.status == "completed"

    # Now do a dry-run with if_exists="error" on the same output directory
    res_dry = run(OrganizeOptions(input_root=input_root, output_root=output_root, dry_run=True, if_exists="error"))
    assert res_dry.status == "dry_run"
    assert res_dry.stats["existing_output_conflicts"] == 1
    assert res_dry.summary["existing_output_conflicts"] == 1
    assert any("--if-exists skip" in w for w in res_dry.warnings)
    colliding_rec = next(r for r in res_dry.file_records if r.source.name == "img.dcm")
    assert colliding_rec.status == "planned"
    assert "already exists" in colliding_rec.detail


def test_duplicate_sha256_recorded_without_checksum_r5(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    sop_uid = generate_uid()
    series_uid = generate_uid()

    write_dicom(
        input_root / "a.dcm",
        series_uid=series_uid,
        sop_uid=sop_uid,
        series_number=1,
        instance_number=1,
        patient_name="PatientA",
    )
    shutil.copy2(input_root / "a.dcm", input_root / "b.dcm")
    write_dicom(
        input_root / "other.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
    )

    res = run(OrganizeOptions(input_root=input_root, output_root=output_root, checksum=False))
    assert res.status == "completed"

    with (output_root / "file_report.csv").open(encoding="utf-8-sig", newline="") as h:
        rows = {r["SourceFileName"]: r for r in csv.DictReader(h)}

    # A and B were involved in duplicate detection -> both must have SHA256 recorded
    assert rows["a.dcm"]["SHA256"] != "N/A"
    assert len(rows["a.dcm"]["SHA256"]) == 64
    assert rows["b.dcm"]["SHA256"] == rows["a.dcm"]["SHA256"]

    # other.dcm had no duplicates and checksum=False -> SHA256 must be N/A
    assert rows["other.dcm"]["SHA256"] == "N/A"


def test_limit_read_progress_r6(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    for idx in range(1, 4):
        write_dicom(
            input_root / f"img_{idx}.dcm",
            series_uid=generate_uid(),
            sop_uid=generate_uid(),
            series_number=idx,
            instance_number=1,
        )

    events: list[ProgressEvent] = []
    run(
        OrganizeOptions(input_root=input_root, output_root=output_root, limit=1),
        progress=events.append,
    )

    read_events = [e for e in events if e.stage == "read"]
    assert read_events
    final_read = read_events[-1]
    assert final_read.done == 1
    assert final_read.total == 1
    assert "limit" in final_read.message.lower()


def test_copy_progress_no_duplicates_r7(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    for idx in range(1, 3):
        write_dicom(
            input_root / f"img_{idx}.dcm",
            series_uid=generate_uid(),
            sop_uid=generate_uid(),
            series_number=idx,
            instance_number=1,
        )

    events: list[ProgressEvent] = []
    run(
        OrganizeOptions(input_root=input_root, output_root=output_root),
        progress=events.append,
    )

    copy_events = [e for e in events if e.stage == "copy"]
    finished_copy_events = [e for e in copy_events if e.total is not None and e.done == e.total and e.total > 0]
    assert len(finished_copy_events) == 1
    assert finished_copy_events[0].message == "Copy completed"


def test_file_report_sorted_by_source_filename_r11(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    write_dicom(
        input_root / "z_image.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        input_root / "a_image.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
    )
    (input_root / ".hidden_file").write_bytes(b"some content")

    run(OrganizeOptions(input_root=input_root, output_root=output_root, include_hidden=False))
    with (output_root / "file_report.csv").open(encoding="utf-8-sig", newline="") as h:
        rows = list(csv.DictReader(h))

    source_names = [r["SourceFileName"] for r in rows]
    assert source_names == sorted(source_names)
    assert source_names[0] == ".hidden_file"


def test_list_only_mode(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    series_uid = generate_uid()
    for inst in (1, 2):
        write_dicom(
            input_root / f"img_{inst}.dcm",
            series_uid=series_uid,
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=inst,
            acquisition_date="20260515",
        )
    (input_root / "not_a_dicom.txt").write_text("hello", encoding="utf-8")

    parsed = parse_args([str(input_root), "--list-only"])
    opts = normalize_options(parsed)
    assert opts.list_only is True
    assert opts.output_root == (input_root / "organized_list").resolve()

    events: list[ProgressEvent] = []
    result = run(opts, progress=events.append)
    assert result.status == "completed"
    assert result.list_only is True

    out = opts.output_root
    entries = sorted(p.name for p in out.iterdir())
    assert entries == [
        "all_dicom_parameters.csv",
        "all_series_summary.csv",
        "file_report.csv",
        "organize_summary.json",
    ]
    assert not list(out.rglob("*.dcm"))

    with (out / "all_dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as h:
        params = list(csv.DictReader(h))
    assert len(params) == 2
    assert all(r["OrganizedFileName"] == "N/A" for r in params)
    assert all(r["SeriesFolder"].startswith("UnitTest_Synthetic/20260515/000001_") for r in params)
    assert {r["FileCount"] for r in params} == {"2"}

    with (out / "all_series_summary.csv").open(encoding="utf-8-sig", newline="") as h:
        summaries = list(csv.DictReader(h))
    assert len(summaries) == 1

    with (out / "file_report.csv").open(encoding="utf-8-sig", newline="") as h:
        report = list(csv.DictReader(h))
    statuses = [(r["Status"], r["Reason"]) for r in report]
    assert statuses.count(("listed", "N/A")) == 2
    assert ("skipped", "not_dicom") in statuses

    summary = json.loads((out / "organize_summary.json").read_text(encoding="utf-8"))
    assert summary["list_only"] is True
    assert summary["listed_files"] == 2
    assert summary["organized_files"] == 0

    stages: list[str] = []
    for e in events:
        if e.stage not in stages:
            stages.append(e.stage)
    assert stages == ["discover", "read", "plan", "write"]

    # Re-run does not accumulate rows
    run(opts)
    with (out / "all_dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as h:
        params_rerun = list(csv.DictReader(h))
    assert len(params_rerun) == 2

    # Dry-run writes nothing
    dry_out = tmp_path / "dry"
    dry_result = run(replace(opts, output_root=dry_out), dry_run=True)
    assert dry_result.status == "dry_run"
    assert not dry_out.exists()


def test_folder_columns_and_legacy_csv_derivation(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    series_uid = generate_uid()
    sop_uid = generate_uid()
    write_dicom(
        input_root / "img.dcm",
        series_uid=series_uid,
        sop_uid=sop_uid,
        series_number=1,
        instance_number=1,
        acquisition_date="20260515",
    )
    out = tmp_path / "out"
    run(OrganizeOptions(input_root=input_root, output_root=out))

    study_dir = out / "UnitTest_Synthetic" / "20260515"
    with (study_dir / "dicom_parameters.csv").open(encoding="utf-8-sig", newline="") as h:
        param_reader = csv.DictReader(h)
        param_cols = list(param_reader.fieldnames or [])
        param_rows = list(param_reader)
    assert param_cols[:4] == ["OrganizedFileName", "StudyFolder", "SeriesFolder", "SeriesUID"]
    assert param_rows[0]["StudyFolder"] == "UnitTest_Synthetic/20260515"
    assert param_rows[0]["OrganizedFileName"].startswith(param_rows[0]["SeriesFolder"] + "/")

    with (study_dir / "series_summary.csv").open(encoding="utf-8-sig", newline="") as h:
        summary_reader = csv.DictReader(h)
        summary_cols = list(summary_reader.fieldnames or [])
        summary_rows = list(summary_reader)
    assert summary_cols[:4] == ["StudyFolder", "SeriesFolder", "AcquisitionDate", "SeriesNumber"]
    assert summary_rows[0]["StudyFolder"] == "UnitTest_Synthetic/20260515"
    assert summary_rows[0]["SeriesFolder"] == param_rows[0]["SeriesFolder"]

    # Legacy CSV rows without StudyFolder/SeriesFolder derivation check
    legacy_row = {
        "OrganizedFileName": "UnitTest_Synthetic/20260515/000001_Test/000001.dcm",
        "SeriesUID": "1.2.3.4",
        "InstanceNumber": "1",
    }
    legacy_csv = tmp_path / "legacy.csv"
    dummy_file = out / legacy_row["OrganizedFileName"]
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.touch()

    with legacy_csv.open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=["OrganizedFileName", "SeriesUID", "InstanceNumber"])
        writer.writeheader()
        writer.writerow(legacy_row)

    from dicom_organizer.core import existing_metadata_rows
    recovered = existing_metadata_rows(legacy_csv, out, set())
    assert len(recovered) == 1
    assert recovered[0]["SeriesFolder"] == "UnitTest_Synthetic/20260515/000001_Test"
    assert recovered[0]["StudyFolder"] == "UnitTest_Synthetic/20260515"


def test_all_series_summary_generation_and_incremental(tmp_path: Path) -> None:
    input_a = tmp_path / "input_a"
    input_a.mkdir()
    series_a = generate_uid()
    for inst in (1, 2):
        write_dicom(
            input_a / f"img_a_{inst}.dcm",
            series_uid=series_a,
            sop_uid=generate_uid(),
            series_number=1,
            instance_number=inst,
            acquisition_date="20260515",
        )

    out = tmp_path / "out"
    run(OrganizeOptions(input_root=input_a, output_root=out))

    all_summary_path = out / "all_series_summary.csv"
    assert all_summary_path.exists()
    with all_summary_path.open(encoding="utf-8-sig", newline="") as h:
        reader = csv.DictReader(h)
        cols = list(reader.fieldnames or [])
        rows_a = list(reader)
    assert cols[:2] == ["StudyFolder", "SeriesFolder"]
    assert len(rows_a) == 1

    summary_json_path = out / "organize_summary.json"
    summary_data = json.loads(summary_json_path.read_text(encoding="utf-8"))
    assert "all_series_summary.csv" in summary_data["reports"]

    # Incremental run with input_b
    input_b = tmp_path / "input_b"
    input_b.mkdir()
    series_b = generate_uid()
    write_dicom(
        input_b / "img_b_1.dcm",
        series_uid=series_b,
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        acquisition_date="20260516",
    )
    run(OrganizeOptions(input_root=input_b, output_root=out, if_exists="skip"))

    with all_summary_path.open(encoding="utf-8-sig", newline="") as h:
        reader = csv.DictReader(h)
        rows_ab = list(reader)
    assert len(rows_ab) == 2
    folders = sorted({r["StudyFolder"] for r in rows_ab})
    assert folders == ["UnitTest_Synthetic/20260515", "UnitTest_Synthetic/20260516"]


def test_layout_presets_and_template_keys(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    study_uid_1 = generate_uid()
    study_uid_2 = generate_uid()

    write_dicom(
        input_root / "s1.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        study_uid=study_uid_1,
        patient_id="PID001",
        acquisition_date="20260515",
    )
    write_dicom(
        input_root / "s2.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        study_uid=study_uid_2,
        patient_id="PID001",
        acquisition_date="20260515",
    )

    from dicom_organizer.core import LAYOUTS, hash_text

    assert tuple(LAYOUTS) == ("device-date", "study", "patient-study")
    key1 = hash_text(study_uid_1, 8)
    key2 = hash_text(study_uid_2, 8)

    # 1. device-date
    out_device = tmp_path / "out_device"
    run(OrganizeOptions(input_root=input_root, output_root=out_device, layout="device-date"))
    device_dirs = sorted(p.parent.relative_to(out_device).as_posix() for p in out_device.rglob("dicom_parameters.csv"))
    assert device_dirs == ["UnitTest_Synthetic/20260515"]

    # 2. study
    out_study = tmp_path / "out_study"
    run(OrganizeOptions(input_root=input_root, output_root=out_study, layout="study"))
    study_dirs = sorted(p.parent.relative_to(out_study).as_posix() for p in out_study.rglob("dicom_parameters.csv"))
    assert study_dirs == sorted([f"20260515_{key1}", f"20260515_{key2}"])

    # 3. patient-study (keep)
    out_patient_keep = tmp_path / "out_patient_keep"
    run(OrganizeOptions(input_root=input_root, output_root=out_patient_keep, layout="patient-study", patient_mode="keep"))
    p_keep_dirs = sorted(p.parent.relative_to(out_patient_keep).as_posix() for p in out_patient_keep.rglob("dicom_parameters.csv"))
    assert p_keep_dirs == sorted([f"PID001/20260515_{key1}", f"PID001/20260515_{key2}"])

    # 4. patient-study (hash)
    pseudonym = "P-" + hashlib.sha256(b"|PID001").hexdigest()[:12]
    out_patient_hash = tmp_path / "out_patient_hash"
    run(OrganizeOptions(input_root=input_root, output_root=out_patient_hash, layout="patient-study", patient_mode="hash"))
    p_hash_dirs = sorted(p.parent.relative_to(out_patient_hash).as_posix() for p in out_patient_hash.rglob("dicom_parameters.csv"))
    assert p_hash_dirs == sorted([f"{pseudonym}/20260515_{key1}", f"{pseudonym}/20260515_{key2}"])
    all_paths_text = "\n".join(p.as_posix() for p in out_patient_hash.rglob("*"))
    assert "PID001" not in all_paths_text

    # 5. Template with study_key and patient_key
    out_tmpl = tmp_path / "out_tmpl"
    run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out_tmpl,
            layout="study",
            series_dir_template="{study_key}_{series_number}",
            file_template="{study_key}_{instance_number}.dcm",
        )
    )
    tmpl_files = list(out_tmpl.rglob("*.dcm"))
    assert len(tmpl_files) == 2
    assert any(key1 in f.name for f in tmpl_files)
    assert any(key2 in f.name for f in tmpl_files)


def test_privacy_drop_notices_and_tag_warnings(tmp_path: Path) -> None:
    from dicom_organizer import messages
    from dicom_organizer.core import patient_data_notices

    input_root = tmp_path / "input"
    input_root.mkdir()
    write_dicom(
        input_root / "img.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_name="Yamada^Taro",
        patient_id="PID999",
    )

    # 1. drop mode: all 4 patient columns are N/A
    out_drop = tmp_path / "out_drop"
    run(OrganizeOptions(input_root=input_root, output_root=out_drop, patient_mode="drop"))
    with (out_drop / "UnitTest_Synthetic" / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig", newline=""
    ) as h:
        drop_rows = list(csv.DictReader(h))
    for col in ("PatientName", "PatientID", "PatientNameHash", "PatientIDHash"):
        assert drop_rows[0][col] == "N/A"

    # hash mode check
    out_hash = tmp_path / "out_hash"
    run(OrganizeOptions(input_root=input_root, output_root=out_hash, patient_mode="hash"))
    with (out_hash / "UnitTest_Synthetic" / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig", newline=""
    ) as h:
        hash_rows = list(csv.DictReader(h))
    assert hash_rows[0]["PatientName"].startswith("sha256:")
    assert hash_rows[0]["PatientNameHash"] != "N/A"

    # 2. patient_data_notices return codes
    base_opts = OrganizeOptions(input_root=input_root, output_root=out_drop)
    assert patient_data_notices(base_opts) == [
        "csv_patient_fields_kept",
        "dicom_files_unchanged",
        "csv_other_identifiers",
    ]
    hash_opts = replace(
        base_opts,
        patient_mode="hash",
        list_only=True,
        dicom_tags=("EchoTime",),
        layout="patient-study",
    )
    assert patient_data_notices(hash_opts) == [
        "csv_patient_fields_hashed",
        "no_dicom_copies",
        "csv_other_identifiers",
        "custom_tags_written",
        "folder_names_contain_patient_key",
    ]

    # 3. messages.notice_text for all codes
    import re

    for code in messages.NOTICE_CODES:
        en = messages.notice_text(code, "en")
        ja = messages.notice_text(code, "ja")
        assert en.strip() and ja.strip() and en != ja
        assert re.search(r"[぀-ヿ一-鿿]", ja)

    # 4. Custom tag warnings
    out_warn = tmp_path / "out_warn"
    res_warn = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out_warn,
            patient_mode="hash",
            dicom_tags=("PatientBirthDate",),
        )
    )
    assert any("PatientBirthDate" in w for w in res_warn.warnings)

    out_nowarn = tmp_path / "out_nowarn"
    res_nowarn = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out_nowarn,
            patient_mode="keep",
            dicom_tags=("PatientBirthDate",),
        )
    )
    assert not any("PatientBirthDate" in w for w in res_nowarn.warnings)

    out_safe = tmp_path / "out_safe"
    res_safe = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out_safe,
            patient_mode="drop",
            dicom_tags=("EchoTime",),
        )
    )
    assert not any("EchoTime" in w for w in res_safe.warnings)


def test_patient_study_layout_non_ascii_patient_id(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    # Patient 1: 山田001 (SpecificCharacterSet="ISO_IR 192")
    write_dicom(
        input_root / "p1.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_id="山田001",
        specific_character_set="ISO_IR 192",
    )
    # Patient 2: 田中002 (SpecificCharacterSet="ISO_IR 192")
    write_dicom(
        input_root / "p2.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_id="田中002",
        specific_character_set="ISO_IR 192",
    )
    # Patient 3: 山田 (safe_name only would result in "NA")
    write_dicom(
        input_root / "p3.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_id="山田",
        specific_character_set="ISO_IR 192",
    )
    # Patient 4: 田中 (safe_name only would result in "NA")
    write_dicom(
        input_root / "p4.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_id="田中",
        specific_character_set="ISO_IR 192",
    )
    # Patient 5: ASCII ID PID001 (should remain "PID001" without hash suffix)
    write_dicom(
        input_root / "p5.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_id="PID001",
    )

    res = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=output_root,
            layout="patient-study",
            patient_mode="keep",
        )
    )
    assert res.status == "completed"

    patient_dirs = sorted([p.name for p in output_root.iterdir() if p.is_dir()])
    assert len(patient_dirs) == 5

    assert "PID001" in patient_dirs

    p1_expected = f"001-{hashlib.sha256('山田001'.encode()).hexdigest()[:8]}"
    p2_expected = f"002-{hashlib.sha256('田中002'.encode()).hexdigest()[:8]}"
    p3_expected = f"NA-{hashlib.sha256('山田'.encode()).hexdigest()[:8]}"
    p4_expected = f"NA-{hashlib.sha256('田中'.encode()).hexdigest()[:8]}"

    assert p1_expected in patient_dirs
    assert p2_expected in patient_dirs
    assert p3_expected in patient_dirs
    assert p4_expected in patient_dirs
    assert p3_expected != p4_expected


def test_list_only_ordering_matches_regular_organization(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()

    study1_uid = generate_uid()
    study2_uid = generate_uid()

    # Study 1 (20260101) with Series 1 & 2
    write_dicom(
        input_root / "s1_ser1.dcm",
        study_uid=study1_uid,
        acquisition_date="20260101",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        input_root / "s1_ser2.dcm",
        study_uid=study1_uid,
        acquisition_date="20260101",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
    )

    # Study 2 (20260202) with Series 1 & 2
    write_dicom(
        input_root / "s2_ser1.dcm",
        study_uid=study2_uid,
        acquisition_date="20260202",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    write_dicom(
        input_root / "s2_ser2.dcm",
        study_uid=study2_uid,
        acquisition_date="20260202",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
    )

    # 1. Regular organization
    out_regular = tmp_path / "out_regular"
    res_regular = run(OrganizeOptions(input_root=input_root, output_root=out_regular))
    assert res_regular.status == "completed"

    reg_summary_csv = out_regular / "all_series_summary.csv"
    with reg_summary_csv.open(encoding="utf-8-sig") as f:
        reg_summary_rows = list(csv.DictReader(f))

    reg_keys = [(r["StudyFolder"], r["SeriesNumber"], r["SeriesFolder"]) for r in reg_summary_rows]

    # 2. List-only mode
    out_list = tmp_path / "out_list"
    res_list = run(OrganizeOptions(input_root=input_root, output_root=out_list, list_only=True))
    assert res_list.status == "completed"

    list_summary_csv = out_list / "all_series_summary.csv"
    with list_summary_csv.open(encoding="utf-8-sig") as f:
        list_summary_rows = list(csv.DictReader(f))

    list_keys = [(r["StudyFolder"], r["SeriesNumber"], r["SeriesFolder"]) for r in list_summary_rows]

    assert list_keys == reg_keys

    # Verify all_dicom_parameters.csv ordering: (StudyFolder, SeriesNumber, SeriesFolder, InstanceNumber, SourceFileName)
    list_param_csv = out_list / "all_dicom_parameters.csv"
    with list_param_csv.open(encoding="utf-8-sig") as f:
        param_rows = list(csv.DictReader(f))

    param_keys = [
        (
            r["StudyFolder"],
            r["SeriesNumber"],
            r["SeriesFolder"],
            int(r["InstanceNumber"]) if r["InstanceNumber"].isdigit() else 0,
            r["SourceFileName"],
        )
        for r in param_rows
    ]
    assert param_keys == sorted(param_keys)


def test_enhanced_mr_multiframe_and_varying_attributes(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = EnhancedMRImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()
    ds = FileDataset(str(input_root / "enhanced.dcm"), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = EnhancedMRImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.Modality = "MR"
    ds.StudyDate = "20260515"
    ds.AcquisitionDate = "20260515"
    ds.SeriesNumber = 5
    ds.InstanceNumber = 1
    ds.SeriesDescription = "Enhanced ME"
    ds.ProtocolName = "Enhanced ME"
    ds.PatientName = "Enhanced^Patient"
    ds.PatientID = "PID001"
    ds.Manufacturer = "UnitTest"
    ds.ManufacturerModelName = "Synthetic"
    ds.Rows = 16
    ds.Columns = 16
    ds.NumberOfFrames = 3
    ds.ImageType = ["ORIGINAL", "PRIMARY", "M", "NONE"]

    shared_item = Dataset()
    timing = Dataset()
    timing.RepetitionTime = 2000.0
    timing.FlipAngle = 15.0
    timing.EchoTrainLength = 1
    shared_item.MRTimingAndRelatedParametersSequence = Sequence([timing])

    pixel_meas = Dataset()
    pixel_meas.PixelSpacing = [0.5, 0.5]
    pixel_meas.SliceThickness = 3.0
    shared_item.PixelMeasuresSequence = Sequence([pixel_meas])

    plane_orient = Dataset()
    plane_orient.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    shared_item.PlaneOrientationSequence = Sequence([plane_orient])

    fov_geom = Dataset()
    fov_geom.InPlanePhaseEncodingDirection = "ROW"
    shared_item.MRFOVGeometrySequence = Sequence([fov_geom])

    ds.SharedFunctionalGroupsSequence = Sequence([shared_item])

    frames = []
    for index, echo in enumerate((10.0, 20.0, 30.0)):
        frame_item = Dataset()
        echo_ds = Dataset()
        echo_ds.EffectiveEchoTime = echo
        frame_item.MREchoSequence = Sequence([echo_ds])
        pos_ds = Dataset()
        pos_ds.ImagePositionPatient = [0, 0, float(index)]
        frame_item.PlanePositionSequence = Sequence([pos_ds])
        frames.append(frame_item)
    ds.PerFrameFunctionalGroupsSequence = Sequence(frames)
    ds.save_as(input_root / "enhanced.dcm", enforce_file_format=True)

    run(OrganizeOptions(input_root=input_root, output_root=output_root))

    with (output_root / "UnitTest_Synthetic" / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    row = rows[0]
    assert row["TE_ms"] == "10.0|20.0|30.0"
    assert row["EchoCount"] == "3"
    assert row["EchoTimes_ms"] == "10.0|20.0|30.0"
    assert row["TR_ms"] == "2000.0"
    assert row["FlipAngle_deg"] == "15.0"
    assert row["NumberOfFrames"] == "3"
    assert row["FrameVaryingAttributes"] == "TE_ms"
    assert row["FOV_HxW_mm"] == "8x8"
    assert row["PhaseEncodingDirectionPatient"] == "R→L"

    with (output_root / "UnitTest_Synthetic" / "20260515" / "series_summary.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        summary_rows = list(csv.DictReader(f))
    assert summary_rows[0]["FrameVaryingAttributes"] == "TE_ms"


def test_classic_mr_frames_columns_na(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    write_dicom(
        input_root / "classic.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
    )
    run(OrganizeOptions(input_root=input_root, output_root=output_root))
    with (output_root / "UnitTest_Synthetic" / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["NumberOfFrames"] == "N/A"
    assert rows[0]["FrameVaryingAttributes"] == "N/A"


def test_config_file_loading_and_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert len(CONFIG_KEYS) == 16
    assert "output" in CONFIG_KEYS
    input_root = tmp_path / "input"
    input_root.mkdir()
    cfg_dir = tmp_path / "facility"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.toml"
    cfg_file.write_text(
        'output = "my_out"\npatient_mode = "hash"\nlayout = "study"\n'
        'dicom_tags = ["EchoTime"]\nchecksum = true\n',
        encoding="utf-8",
    )
    loaded = load_config(cfg_file)
    assert Path(loaded["output"]) == (cfg_dir / "my_out").resolve()
    assert loaded["patient_mode"] == "hash"
    assert loaded["checksum"] is True

    args = parse_args([str(input_root), "--config", str(cfg_file)])
    opts = normalize_options(args)
    assert opts.output_root == (cfg_dir / "my_out").resolve()
    assert opts.patient_mode == "hash"
    assert opts.layout == "study"
    assert opts.checksum is True
    assert opts.dicom_tags == ("EchoTime",)
    assert opts.config_file == str(cfg_file.resolve())

    args2 = parse_args([
        str(input_root), "--config", str(cfg_file),
        "--patient-mode", "drop", "-t", "FlipAngle",
    ])
    opts2 = normalize_options(args2)
    assert opts2.patient_mode == "drop"
    assert opts2.dicom_tags == ("EchoTime", "FlipAngle")

    monkeypatch.setenv("DICOM_ORGANIZER_CONFIG", str(cfg_file))
    args3 = parse_args([str(input_root)])
    opts3 = normalize_options(args3)
    assert opts3.patient_mode == "hash"


def test_config_file_validation_and_errors(tmp_path: Path) -> None:
    bad_unknown = tmp_path / "bad_unknown.toml"
    bad_unknown.write_text("invalid_key = 'val'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_key"):
        load_config(bad_unknown)

    bad_type = tmp_path / "bad_type.toml"
    bad_type.write_text("checksum = 'yes'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_config(bad_type)

    bad_choice = tmp_path / "bad_choice.toml"
    bad_choice.write_text("layout = 'nonexistent'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="layout"):
        load_config(bad_choice)

    bad_syntax = tmp_path / "bad_syntax.toml"
    bad_syntax.write_text("checksum = \n", encoding="utf-8")
    with pytest.raises(ValueError, match="bad_syntax.toml"):
        load_config(bad_syntax)

    values = {
        "output": str(tmp_path / "out"),
        "patient_mode": "drop",
        "dicom_tags": ["EchoTime", 'Col"Q"=0018,0081'],
        "checksum": True,
        "series_dir_template": "{series_number}_{series_folder_label}",
    }
    toml_str = config_to_toml(values)
    parsed = tomllib.loads(toml_str)
    assert parsed == values


def test_sample_dataset_determinism_and_expected(tmp_path: Path) -> None:
    ds1 = create_sample_dataset(tmp_path / "a")
    ds2 = create_sample_dataset(tmp_path / "b")

    uids_1 = {
        str(pydicom.dcmread(p, stop_before_pixels=True).SOPInstanceUID)
        for p in ds1.root.rglob("IM*")
    }
    uids_2 = {
        str(pydicom.dcmread(p, stop_before_pixels=True).SOPInstanceUID)
        for p in ds2.root.rglob("IM*")
    }
    assert uids_1 == uids_2
    assert len(uids_1) == ds1.expected["organized_files"]

    out = tmp_path / "out"
    res = run(OrganizeOptions(input_root=ds1.root, output_root=out))
    assert res.summary["organized_files"] == ds1.expected["organized_files"]
    assert res.summary["csv_target_files"] == ds1.expected["csv_target_files"]
    assert res.summary["series_count"] == ds1.expected["series_count"]


def test_self_test_and_report_file(tmp_path: Path) -> None:
    report_file = tmp_path / "self_test_report.txt"
    exit_code = run_self_test(report_path=report_file)
    assert exit_code == 0
    assert report_file.is_file()
    content = report_file.read_text(encoding="utf-8")
    assert "[PASS]" in content
    assert "self-test: 3/3 checks passed" in content


def test_diagnostics_lines_no_home_leak() -> None:
    lines = diagnostics_lines(config_file="/Users/example/fake/config.toml")
    assert isinstance(lines, list)
    assert len(lines) == 10
    home = str(Path.home())
    output_text = "\n".join(lines)
    assert home not in output_text


def test_normalize_vendor_name_word_boundary() -> None:
    assert normalize_vendor_name("GE MEDICAL SYSTEMS") == "GE"
    assert normalize_vendor_name("GE HealthCare") == "GE"
    assert normalize_vendor_name("General Electric Medical Systems") == "GE"
    assert normalize_vendor_name("Agfa-Gevaert") != "GE"
    assert normalize_vendor_name("Agfa-Gevaert") == "Agfa-Gevaert"
    assert normalize_vendor_name("SIEMENS") == "Siemens"
    assert normalize_vendor_name("Siemens Healthineers") == "Siemens"
    assert normalize_vendor_name("Philips Medical Systems") == "Philips"
    assert normalize_vendor_name("PHILIPS") == "Philips"
    assert normalize_vendor_name("Canon Medical Systems") == "Canon"
    assert normalize_vendor_name("TOSHIBA") == "Toshiba"
    assert normalize_vendor_name("Hitachi Medical") == "Hitachi"
    assert normalize_vendor_name("FUJIFILM Corporation") == "Fujifilm"
    assert normalize_vendor_name("Fuji Photo Film") == "Fujifilm"


def test_config_file_tilde_expansion(tmp_path: Path) -> None:
    cfg = tmp_path / "test_config.toml"
    cfg.write_text('output = "~/dicom_organizer_test_out"\n', encoding="utf-8")
    loaded = load_config(cfg)
    expected = str((Path.home() / "dicom_organizer_test_out").resolve())
    assert loaded["output"] == expected


def test_enhanced_mr_multi_orientation_phase_encoding(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = EnhancedMRImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()
    ds = FileDataset(str(input_root / "multi_orient.dcm"), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = EnhancedMRImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.Modality = "MR"
    ds.StudyDate = "20260520"
    ds.SeriesNumber = 12
    ds.InstanceNumber = 1
    ds.SeriesDescription = "Multi-orient localizer"
    ds.PatientName = "Orient^Test"
    ds.PatientID = "PID_ORIENT"
    ds.Manufacturer = "UnitTest"
    ds.Rows = 16
    ds.Columns = 16
    ds.NumberOfFrames = 3
    ds.ImageType = ["ORIGINAL", "PRIMARY", "M", "NONE"]

    shared_item = Dataset()
    timing = Dataset()
    timing.RepetitionTime = 100.0
    timing.FlipAngle = 20.0
    shared_item.MRTimingAndRelatedParametersSequence = Sequence([timing])
    pixel_meas = Dataset()
    pixel_meas.PixelSpacing = [1.0, 1.0]
    pixel_meas.SliceThickness = 5.0
    shared_item.PixelMeasuresSequence = Sequence([pixel_meas])
    fov_geom = Dataset()
    fov_geom.InPlanePhaseEncodingDirection = "COL"
    shared_item.MRFOVGeometrySequence = Sequence([fov_geom])
    ds.SharedFunctionalGroupsSequence = Sequence([shared_item])

    # 3 frames: axial (A->P), coronal (H->F), sagittal (H->F)
    orientations = [
        [1, 0, 0, 0, 1, 0],   # axial: COL=(0,1,0) -> A->P
        [1, 0, 0, 0, 0, -1],  # coronal: COL=(0,0,-1) -> H->F
        [0, 1, 0, 0, 0, -1],  # sagittal: COL=(0,0,-1) -> H->F
    ]
    frames = []
    for orient in orientations:
        f_item = Dataset()
        po = Dataset()
        po.ImageOrientationPatient = orient
        f_item.PlaneOrientationSequence = Sequence([po])
        frames.append(f_item)
    ds.PerFrameFunctionalGroupsSequence = Sequence(frames)
    ds.save_as(input_root / "multi_orient.dcm", enforce_file_format=True)

    run(OrganizeOptions(input_root=input_root, output_root=output_root))

    param_csv = next(output_root.rglob("dicom_parameters.csv"))
    with param_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["PhaseEncodingDirectionPatient"] == "A→P|H→F"
    assert "PhaseEncodingDirectionPatient" in row["FrameVaryingAttributes"]
    assert row["FrameVaryingAttributes"].endswith("PhaseEncodingDirectionPatient")

    summary_csv = next(output_root.rglob("series_summary.csv"))
    with summary_csv.open(encoding="utf-8-sig", newline="") as handle:
        s_rows = list(csv.DictReader(handle))
    assert len(s_rows) == 1
    assert s_rows[0]["PhaseEncodingDirectionPatient"] == "A→P|H→F"


def test_diagnostics_lines_mask_home_exact_or_sep() -> None:
    home = str(Path.home())
    sibling_home = home + "def" + os.sep + "config.toml"
    lines = diagnostics_lines(config_file=sibling_home)
    config_line = next(line for line in lines if line.startswith("config_file: "))
    assert sibling_home in config_line
    assert not config_line.startswith("config_file: ~def")

    exact_home = home
    lines_exact = diagnostics_lines(config_file=exact_home)
    config_line_exact = next(line for line in lines_exact if line.startswith("config_file: "))
    assert config_line_exact == "config_file: ~"

    child_home = home + os.sep + "my_config.toml"
    lines_child = diagnostics_lines(config_file=child_home)
    config_line_child = next(line for line in lines_child if line.startswith("config_file: "))
    assert config_line_child == "config_file: ~/my_config.toml"


def test_mixed_output_warning_on_older_schema_or_different_layout(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    write_dicom(
        input_root / "test.dcm",
        series_uid="1.2.3.4",
        sop_uid="1.2.3.4.1",
        series_number=1,
        instance_number=1,
    )
    out = tmp_path / "out"
    out.mkdir()

    # 1. Old version lacking output_schema_version
    (out / "organize_summary.json").write_text(
        json.dumps({"status": "completed"}), encoding="utf-8"
    )
    result_old = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out,
            dry_run=True,
            layout="device-date",
            if_exists="skip",
        )
    )
    assert any(
        "0.1" in w or "older" in w.lower() or "schema" in w.lower()
        for w in result_old.warnings
    )

    # 2. Different layout
    (out / "organize_summary.json").write_text(
        json.dumps({
            "status": "completed",
            "output_schema_version": 2,
            "layout": "study",
        }),
        encoding="utf-8",
    )
    result_diff = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out,
            dry_run=True,
            layout="device-date",
            if_exists="skip",
        )
    )
    assert any("layout" in w.lower() for w in result_diff.warnings)

    # 3. Same version and layout produces no warning
    (out / "organize_summary.json").write_text(
        json.dumps({
            "status": "completed",
            "output_schema_version": 2,
            "layout": "device-date",
        }),
        encoding="utf-8",
    )
    result_same = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=out,
            dry_run=True,
            layout="device-date",
            if_exists="skip",
        )
    )
    assert not [
        w for w in result_same.warnings if "layout" in w.lower() or "older" in w.lower()
    ]
    assert result_same.previous_run_status is None


def test_previous_run_status_completed_stays_none(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    write_dicom(
        input_root / "test.dcm",
        series_uid="1.2.3.4",
        sop_uid="1.2.3.4.1",
        series_number=1,
        instance_number=1,
    )
    first = run(OrganizeOptions(input_root=input_root, output_root=output_root))
    assert first.previous_run_status is None

    second = run(
        OrganizeOptions(
            input_root=input_root,
            output_root=output_root,
            if_exists="skip",
        )
    )
    assert second.previous_run_status is None
    assert not [
        w for w in second.warnings if "older" in w.lower() or "layout" in w.lower()
    ]

    summary = json.loads(
        (output_root / "organize_summary.json").read_text(encoding="utf-8")
    )
    assert summary["previous_run_status"] is None

