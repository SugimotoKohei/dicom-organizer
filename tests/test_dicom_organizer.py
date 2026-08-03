from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    CTImageStorage,
    ExplicitVRLittleEndian,
    MRImageStorage,
    PositronEmissionTomographyImageStorage,
    UltrasoundImageStorage,
    XRayAngiographicImageStorage,
    generate_uid,
)

from dicom_organizer.core import (
    DEFAULT_FILE_TEMPLATE,
    DEFAULT_SERIES_DIR_TEMPLATE,
    build_items,
    parallel_reduction_factor_in_plane_value,
    parse_args,
    phase_encoding_direction_patient,
    print_summary,
    run,
)


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
    ds.SOPClassUID = sop_class_uid
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.Modality = modality
    ds.AcquisitionDate = acquisition_date
    ds.StudyDate = acquisition_date
    ds.SeriesDate = acquisition_date
    ds.SeriesNumber = series_number
    ds.InstanceNumber = instance_number
    if acquisition_number is not None:
        ds.AcquisitionNumber = acquisition_number
    ds.SeriesDescription = series_description or f"Series {series_number}"
    ds.ProtocolName = protocol_name or f"Protocol {series_number}"
    ds.PatientName = patient_name
    ds.PatientID = "PID001"
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
    if siemens_private_parallel_reduction_factor is not None:
        protocol = (
            "### ASCCONV BEGIN ###\n"
            f"sPat.lAccelFactPE = {siemens_private_parallel_reduction_factor:g}\n"
            "### ASCCONV END ###\n"
        ).encode()
        ds.add_new((0x0021, 0x1019), "OB", protocol)
    ds.save_as(path, enforce_file_format=True)


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
    date_dir = output_root / "20260515"
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

    date_dir = output_root / "20260515"
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
        assert row["SeriesUIDHash"] == summary_row["SeriesUIDHash"]
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

    date_dir = output_root / "20260515"
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

    date_dir = output_root / "20260515"
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

    date_dir = output_root / "20260515"
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        metadata_rows = list(csv.DictReader(handle))
    assert len(metadata_rows) == 1
    assert metadata_rows[0]["SOPClassUID"] == str(MRImageStorage)

    with (output_root / "20260515" / "series_summary.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
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

    with (output_root / "20260515" / "series_summary.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
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

    with (output_root / "20260515" / "series_summary.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["Modality"] == "CT"
    assert rows[0]["SOPClassUID"] == str(CTImageStorage)

    with (output_root / "20260515" / "series_summary.csv").open(
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

    with (output_root / "20260515" / "dicom_parameters.csv").open(
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
        "20260515/000003_T2-TSE-axial-fast/"
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

    with (output_root / "20260515" / "series_summary.csv").open(
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
    with (keep_output / "20260515" / "dicom_parameters.csv").open(
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
    with (hash_output / "20260515" / "dicom_parameters.csv").open(
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
    with (drop_output / "20260515" / "dicom_parameters.csv").open(
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
                "InPlanePhaseEncodingDirection",
                "PrivateMissing=0021,9999",
            ),
        )
    )

    with (output_root / "20260515" / "dicom_parameters.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))

    assert row["DICOM_EchoTime"] == "10.0"
    assert row["DICOM_RepetitionTime"] == "1000.0"
    assert row["CustomPhase"] == "ROW"
    assert row["DICOM_InPlanePhaseEncodingDirection"] == "ROW"
    assert row["PrivateMissing"] == "N/A"

    with (output_root / "20260515" / "series_summary.csv").open(
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
    assert args.dicom_tag == ["EchoTime"]
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
