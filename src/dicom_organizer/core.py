#!/usr/bin/env python3
"""Organize DICOM files into stable series directories.

The default output layout organizes files by device, study date, and series:

    organized/<Device>/<StudyDate>/<SeriesNumber>_<SeriesFolderLabel>/
        000001.dcm
        ...
    organized/<Device>/<StudyDate>/
        dicom_parameters.csv
        series_summary.csv
    organized/organize_summary.json

The script reads DICOM headers only, keeps source files untouched by default,
and writes metadata tables that are useful for later modality-specific analysis.
"""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import shutil
import sys
import threading
import uuid
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Callable

import pydicom
from pydicom.datadict import keyword_for_tag, tag_for_keyword
from pydicom.multival import MultiValue
from pydicom.tag import Tag
from pydicom.uid import (
    CTImageStorage,
    EnhancedCTImageStorage,
    EnhancedMRImageStorage,
    EnhancedPETImageStorage,
    EnhancedUSVolumeStorage,
    EnhancedXAImageStorage,
    MRImageStorage,
    PositronEmissionTomographyImageStorage,
    UltrasoundImageStorage,
    XRayAngiographicImageStorage,
)

__version__ = "0.2.0"
OUTPUT_SCHEMA_VERSION = 2

SKIP_REASONS = (
    "not_dicom",
    "dicomdir",
    "missing_required_uid",
    "read_error",
    "permission_denied",
    "io_error",
    "excluded_hidden",
    "duplicate_identical",
    "existing_output",
)

FILE_REPORT_COLUMNS = [
    "SourceFileName",
    "Status",
    "Reason",
    "Detail",
    "OrganizedFileName",
    "DuplicateOf",
    "SOPInstanceUID",
    "SeriesUID",
    "Modality",
    "SizeBytes",
    "SHA256",
]


class InsufficientSpaceError(OSError):
    """Raised when destination has insufficient disk space."""


class IntegrityError(RuntimeError):
    """Raised when file integrity check fails after organization."""


@dataclass(frozen=True)
class HeaderReadResult:
    dataset: pydicom.dataset.Dataset | None
    reason: str
    detail: str


@dataclass
class FileRecord:
    source: Path
    status: str
    reason: str = "N/A"
    detail: str = "N/A"
    destination: Path | None = None
    duplicate_of: Path | None = None
    sop_instance_uid: str = "N/A"
    series_uid: str = "N/A"
    modality: str = "N/A"
    size_bytes: int | None = None
    sha256: str = "N/A"


@dataclass
class _SopTracker:
    first_source: Path
    first_record: FileRecord
    hashes: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class ProgressEvent:
    stage: str
    done: int
    total: int | None
    message: str = ""


def package_version() -> str:
    try:
        return importlib.metadata.version("dicom-organizer")
    except importlib.metadata.PackageNotFoundError:
        return __version__


def merge_columns(*groups: list[str] | tuple[str, ...]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for column in group:
            if column in seen:
                continue
            seen.add(column)
            merged.append(column)
    return merged


COMMON_METADATA_COLUMNS = [
    "OrganizedFileName",
    "StudyFolder",
    "SeriesFolder",
    "SeriesUID",
    "SOPInstanceUID",
    "SeriesNumber",
    "SeriesDescription",
    "ProtocolName",
    "FileCount",
    "InstanceNumber",
    "AcquisitionDate",
    "AcquisitionTime",
    "StudyDate",
    "StudyTime",
    "SeriesDate",
    "SeriesTime",
    "PatientName",
    "PatientID",
    "PatientIDHash",
    "PatientNameHash",
    "Modality",
    "SOPClassUID",
    "FOV_HxW_mm",
    "Matrix_RowsxCols",
    "SliceThickness_mm",
    "SpacingBetweenSlices_mm",
    "SliceLocation_mm",
    "Manufacturer",
    "ManufacturerModelName",
    "SourceFileName",
    "ImageType",
    "Rows",
    "Columns",
    "PixelSpacing",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "PatientPosition",
    "FrameOfReferenceUID",
    "StudyInstanceUID",
    "IsNormalized",
    "ScanDuration",
    "ScanDurationSource",
]

MR_METADATA_COLUMNS = [
    "TR_ms",
    "TE_ms",
    "EchoCount",
    "EchoTimes_ms",
    "PixelBandwidth_Hz_per_px",
    "EchoTrainLength",
    "FlipAngle_deg",
    "NumberOfAverages",
    "MagneticFieldStrength_T",
    "ScanningSequence",
    "SequenceVariant",
    "SequenceName",
    "InversionTime_ms",
    "EchoNumbers",
    "AcquisitionMatrix",
    "NumberOfPhaseEncodingSteps",
    "PercentSampling",
    "PercentPhaseFOV",
    "ParallelReductionFactorInPlane",
    "SAR",
    "InPlanePhaseEncodingDirection",
    "PhaseEncodingDirectionPatient",
    "ReceiveCoilName",
    "MRAcquisitionType",
    "SiemensChannelMixing",
    "SiemensCoilElement",
    "CoilElementCount",
    "CoilElements",
    "SiemensIceDims",
    "SiemensIceDimChannel",
    "SiemensIceDimEcho",
]

CT_METADATA_COLUMNS = [
    "KVP_kV",
    "XRayTubeCurrent_mA",
    "ExposureTime_ms",
    "ConvolutionKernel",
    "ReconstructionDiameter_mm",
]

US_METADATA_COLUMNS = [
    "TransducerData",
    "TransducerType",
    "MechanicalIndex",
    "ThermalIndex",
    "UltrasoundColorDataPresent",
]

XA_METADATA_COLUMNS = [
    "KVP_kV",
    "XRayTubeCurrent_mA",
    "ExposureTime_ms",
    "FrameTime_ms",
    "DistanceSourceToDetector_mm",
    "DistanceSourceToPatient_mm",
]

PT_METADATA_COLUMNS = [
    "Radiopharmaceutical",
    "RadionuclideTotalDose_Bq",
    "RadionuclideHalfLife_s",
    "DecayCorrection",
]

PER_INSTANCE_METADATA_COLUMNS = {
    "OrganizedFileName",
    "SOPInstanceUID",
    "InstanceNumber",
    "SliceLocation_mm",
    "SourceFileName",
    "ImagePositionPatient",
}

COMMON_SUMMARY_COLUMNS = merge_columns(
    [
        "StudyFolder",
        "SeriesFolder",
        "AcquisitionDate",
        "SeriesNumber",
        "SeriesUID",
        "Modality",
        "SeriesDescription",
        "ProtocolName",
        "FileCount",
        "Rows",
        "Columns",
        "Matrix_RowsxCols",
        "FOV_HxW_mm",
        "ImageType",
        "Manufacturer",
        "ManufacturerModelName",
    ],
    [
        column
        for column in COMMON_METADATA_COLUMNS
        if column not in PER_INSTANCE_METADATA_COLUMNS
    ],
)

# Modality-specific summary values use the same columns as dicom_parameters.csv.
MR_SUMMARY_COLUMNS = merge_columns(
    [
        "EchoCount",
        "EchoTimes_ms",
        "CoilElementCount",
        "CoilElements",
        "MRAcquisitionType",
        "TR_ms",
        "InversionTime_ms",
        "EchoNumbers",
        "EchoTrainLength",
        "NumberOfAverages",
        "AcquisitionMatrix",
        "NumberOfPhaseEncodingSteps",
        "PercentSampling",
        "PercentPhaseFOV",
        "SAR",
        "InPlanePhaseEncodingDirection",
        "PhaseEncodingDirectionPatient",
        "ReceiveCoilName",
    ],
    MR_METADATA_COLUMNS,
)
CT_SUMMARY_COLUMNS = list(CT_METADATA_COLUMNS)
US_SUMMARY_COLUMNS = list(US_METADATA_COLUMNS)
XA_SUMMARY_COLUMNS = list(XA_METADATA_COLUMNS)
PT_SUMMARY_COLUMNS = list(PT_METADATA_COLUMNS)

PROFILE_NAMES = ("auto", "generic", "mr", "ct", "us", "xa", "pt")

DEFAULT_SERIES_DIR_TEMPLATE = "{series_number}_{series_folder_label}"
DEFAULT_FILE_TEMPLATE = "{instance_number_6}.dcm"

ACTIONS = ("copy", "symlink", "hardlink", "move")
IF_EXISTS_MODES = ("error", "skip", "overwrite", "rename")
PATIENT_MODES = ("keep", "hash", "drop")
LAYOUTS = ("device-date", "study", "patient-study")

SIEMENS_PARALLEL_REDUCTION_FACTOR_PATTERN = re.compile(
    rb"(?:^|[\x00\r\n ])sPat\.lAccelFactPE\s*=\s*([0-9]+(?:\.[0-9]+)?)"
)
SIEMENS_TOTAL_SCAN_TIME_PATTERN = re.compile(
    rb"(?:^|[\x00\r\n ])lTotalScanTimeSec\s*=\s*([0-9]+(?:\.[0-9]+)?)"
)


@dataclass(frozen=True)
class OrganizedItem:
    source: Path
    destination: Path
    row: dict[str, str]


@dataclass(frozen=True)
class OrganizeOptions:
    input_root: Path
    output_root: Path
    action: str = "copy"
    confirm_move: bool = False
    if_exists: str = "error"
    dry_run: bool = False
    force_read: bool = True
    include_hidden: bool = False
    include_organized: bool = False
    limit: int = 0
    series_dir_template: str = DEFAULT_SERIES_DIR_TEMPLATE
    file_template: str = DEFAULT_FILE_TEMPLATE
    profile: str = "auto"
    patient_mode: str = "keep"
    dicom_tags: tuple[str, ...] = ()
    verbose: bool = False
    checksum: bool = False
    space_check: bool = True
    list_only: bool = False
    layout: str = "device-date"


@dataclass(frozen=True)
class DicomTagSpec:
    column: str
    tag: Tag


@dataclass(frozen=True)
class ModalityProfile:
    name: str
    modalities: tuple[str, ...]
    sop_classes: tuple[str, ...]
    metadata_columns: tuple[str, ...]
    summary_columns: tuple[str, ...]


MODALITY_PROFILES = {
    "mr": ModalityProfile(
        name="mr",
        modalities=("MR",),
        sop_classes=(str(MRImageStorage), str(EnhancedMRImageStorage)),
        metadata_columns=tuple(MR_METADATA_COLUMNS),
        summary_columns=tuple(MR_SUMMARY_COLUMNS),
    ),
    "ct": ModalityProfile(
        name="ct",
        modalities=("CT",),
        sop_classes=(str(CTImageStorage), str(EnhancedCTImageStorage)),
        metadata_columns=tuple(CT_METADATA_COLUMNS),
        summary_columns=tuple(CT_SUMMARY_COLUMNS),
    ),
    "us": ModalityProfile(
        name="us",
        modalities=("US",),
        sop_classes=(str(UltrasoundImageStorage), str(EnhancedUSVolumeStorage)),
        metadata_columns=tuple(US_METADATA_COLUMNS),
        summary_columns=tuple(US_SUMMARY_COLUMNS),
    ),
    "xa": ModalityProfile(
        name="xa",
        modalities=("XA",),
        sop_classes=(str(XRayAngiographicImageStorage), str(EnhancedXAImageStorage)),
        metadata_columns=tuple(XA_METADATA_COLUMNS),
        summary_columns=tuple(XA_SUMMARY_COLUMNS),
    ),
    "pt": ModalityProfile(
        name="pt",
        modalities=("PT",),
        sop_classes=(
            str(PositronEmissionTomographyImageStorage),
            str(EnhancedPETImageStorage),
        ),
        metadata_columns=tuple(PT_METADATA_COLUMNS),
        summary_columns=tuple(PT_SUMMARY_COLUMNS),
    ),
}

ALL_METADATA_COLUMNS = merge_columns(
    COMMON_METADATA_COLUMNS,
    *(profile.metadata_columns for profile in MODALITY_PROFILES.values()),
)


@dataclass(frozen=True)
class OrganizeResult:
    items: list[OrganizedItem]
    stats: Counter[str]
    output_root: Path
    started_at: str
    ended_at: str
    dry_run: bool
    profile: str
    status: str = "completed"
    file_records: list[FileRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    previous_run_status: str | None = None
    list_only: bool = False
    privacy_notices: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        return summarize_items(
            self.items,
            self.stats,
            self.output_root,
            self.profile,
            status=self.status,
            list_only=self.list_only,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize DICOM files by device, StudyDate, and SeriesInstanceUID."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {package_version()}",
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        metavar="INPUT",
        help="Input directory containing DICOM files.",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input",
        type=Path,
        help="Input directory containing DICOM files. Kept for compatibility; positional INPUT is preferred.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory. Defaults to <input>/organized.",
    )
    parser.add_argument(
        "--action",
        choices=ACTIONS,
        default="copy",
        help="How to materialize files in the organized tree. Default: copy.",
    )
    parser.add_argument(
        "--confirm-move",
        action="store_true",
        help="Required when --action move is used.",
    )
    parser.add_argument(
        "--if-exists",
        choices=IF_EXISTS_MODES,
        default="error",
        help="Behavior when the target file already exists. Default: error.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Do not copy DICOM files; write parameter tables and reports only.",
    )
    parser.add_argument(
        "--layout",
        choices=LAYOUTS,
        default="device-date",
        help="Organization layout preset: device-date, study, or patient-study. Default: device-date.",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Scan and summarize without writing output files.",
    )
    parser.add_argument(
        "-f",
        "--force-read",
        dest="force_read",
        action="store_true",
        default=True,
        help="Read DICOM headers with pydicom force=True. Default: enabled.",
    )
    parser.add_argument(
        "--no-force-read",
        dest="force_read",
        action="store_false",
        help="Disable pydicom force=True and require standard DICOM headers.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Also scan hidden files and directories.",
    )
    parser.add_argument(
        "--include-organized",
        action="store_true",
        help="Do not skip directories named organized.",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=0,
        help="Limit the number of readable DICOM files processed; useful for smoke tests.",
    )
    parser.add_argument(
        "--series-dir-template",
        default=DEFAULT_SERIES_DIR_TEMPLATE,
        help=(
            "Series directory name template. Available keys: acquisition_date, "
            "series_number, series_description, protocol_name, series_label, "
            "reconstruction_label, series_folder_label, series_uid_hash."
        ),
    )
    parser.add_argument(
        "--file-template",
        default=DEFAULT_FILE_TEMPLATE,
        help=(
            "Output filename template. Available keys include instance_number, "
            "instance_number_6, sop_uid_hash, echo_time_ms, siemens_coil_element."
        ),
    )
    parser.add_argument(
        "-p",
        "--profile",
        choices=PROFILE_NAMES,
        default="auto",
        help=(
            "Metadata profile for dicom_parameters.csv and series_summary.csv. "
            "Use auto for mixed supported modalities, generic for common columns only, "
            "or a modality-specific profile such as mr/ct/us/xa/pt."
        ),
    )
    parser.add_argument(
        "--patient-mode",
        choices=PATIENT_MODES,
        default="keep",
        help="How to write PatientName in metadata CSV. Default keeps the old behavior.",
    )
    parser.add_argument(
        "-t",
        "--dicom-tag",
        "--tag",
        action="append",
        dest="dicom_tags",
        default=[],
        metavar="TAG",
        help=(
            "Also write this DICOM tag to both metadata CSV files. Repeatable. "
            "Accepts keywords such as EchoTime, numeric tags such as 0018,0081 "
            "or 0x00180081, and optional ColumnName=TAG."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print skipped files and per-series output while running.",
    )
    parser.add_argument(
        "--checksum",
        action="store_true",
        default=False,
        help="Verify SHA-256 checksum during file materialization.",
    )
    parser.add_argument(
        "--no-space-check",
        dest="space_check",
        action="store_false",
        default=True,
        help="Disable free disk space pre-check.",
    )
    parser.add_argument(
        "--no-progress",
        dest="progress",
        action="store_false",
        default=True,
        help="Disable console progress display.",
    )
    args = parser.parse_args(argv)
    if args.input is None and args.input_path is None:
        parser.error("the following arguments are required: INPUT (or --input)")
    if args.input is not None and args.input_path is not None:
        parser.error("specify the input directory either as INPUT or --input, not both")
    args.input = args.input if args.input is not None else args.input_path
    return args


def resolved_root(value: Path | str) -> Path:
    return Path(value).expanduser().resolve()


def normalize_options(
    args: argparse.Namespace | OrganizeOptions,
    *,
    dry_run: bool | None = None,
    validate: bool = False,
) -> OrganizeOptions:
    if isinstance(args, OrganizeOptions):
        overrides: dict[str, Any] = {
            "input_root": resolved_root(args.input_root),
            "output_root": resolved_root(args.output_root),
        }
        if dry_run is not None:
            overrides["dry_run"] = dry_run
        options = replace(args, **overrides)
    else:
        input_root = resolved_root(args.input)
        is_list_only = bool(getattr(args, "list_only", False))
        output_value = getattr(args, "output", None)
        if is_list_only and not output_value:
            output_root = input_root / "organized_list"
        else:
            output_root = (
                resolved_root(output_value)
                if output_value
                else input_root / "organized"
            )
        options = OrganizeOptions(
            input_root=input_root,
            output_root=output_root,
            action=str(getattr(args, "action", "copy")),
            confirm_move=bool(getattr(args, "confirm_move", False)),
            if_exists=str(getattr(args, "if_exists", "error")),
            dry_run=bool(getattr(args, "dry_run", False) if dry_run is None else dry_run),
            force_read=bool(getattr(args, "force_read", True)),
            include_hidden=bool(getattr(args, "include_hidden", False)),
            include_organized=bool(getattr(args, "include_organized", False)),
            limit=int(getattr(args, "limit", 0) or 0),
            series_dir_template=str(
                getattr(args, "series_dir_template", DEFAULT_SERIES_DIR_TEMPLATE)
                or DEFAULT_SERIES_DIR_TEMPLATE
            ),
            file_template=str(
                getattr(args, "file_template", DEFAULT_FILE_TEMPLATE) or DEFAULT_FILE_TEMPLATE
            ),
            profile=str(getattr(args, "profile", "auto")),
            patient_mode=str(getattr(args, "patient_mode", "keep")),
            dicom_tags=tuple(str(tag) for tag in getattr(args, "dicom_tags", ()) or ()),
            verbose=bool(getattr(args, "verbose", False)),
            checksum=bool(getattr(args, "checksum", False)),
            space_check=bool(getattr(args, "space_check", True)),
            list_only=is_list_only,
            layout=str(getattr(args, "layout", "device-date") or "device-date"),
        )

    if validate:
        validate_options(options)
    return options


def validate_options(options: OrganizeOptions) -> None:
    if options.action not in ACTIONS:
        raise ValueError(f"Unsupported --action value: {options.action}")
    if options.if_exists not in IF_EXISTS_MODES:
        raise ValueError(f"Unsupported --if-exists value: {options.if_exists}")
    if options.layout not in LAYOUTS:
        raise ValueError(f"Unsupported --layout value: {options.layout}")
    if options.profile not in PROFILE_NAMES:
        raise ValueError(f"Unsupported --profile value: {options.profile}")
    if options.patient_mode not in PATIENT_MODES:
        raise ValueError(f"Unsupported --patient-mode value: {options.patient_mode}")
    if options.limit < 0:
        raise ValueError("--limit must be greater than or equal to 0")
    if not options.input_root.exists() or not options.input_root.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {options.input_root}")
    if options.output_root == options.input_root:
        raise ValueError(
            f"Output directory must be different from input directory: {options.input_root}"
        )
    if options.action == "move" and not options.confirm_move:
        raise ValueError("--action move requires --confirm-move")
    parse_dicom_tag_specs(options.dicom_tags)


def parse_dicom_tag_specs(values: tuple[str, ...]) -> list[DicomTagSpec]:
    specs: list[DicomTagSpec] = []
    seen_columns: set[str] = set(ALL_METADATA_COLUMNS)
    for value in values:
        column, tag = parse_dicom_tag_spec(value)
        column = unique_column_name(column, seen_columns)
        seen_columns.add(column)
        specs.append(DicomTagSpec(column=column, tag=tag))
    return specs


def parse_dicom_tag_spec(value: str) -> tuple[str, Tag]:
    raw = value.strip()
    if not raw:
        raise ValueError("--dicom-tag must not be empty")

    column_override = ""
    tag_text = raw
    if "=" in raw:
        column_override, tag_text = (part.strip() for part in raw.split("=", 1))
        if not column_override:
            raise ValueError(f"Column name is empty in --dicom-tag: {value}")
        if not tag_text:
            raise ValueError(f"Tag is empty in --dicom-tag: {value}")

    tag = parse_dicom_tag(tag_text)
    keyword = keyword_for_tag(tag) or tag_text
    column = safe_column_name(column_override or f"DICOM_{keyword}")
    if not column:
        raise ValueError(f"Column name could not be derived from --dicom-tag: {value}")
    return column, tag


def parse_dicom_tag(value: str) -> Tag:
    cleaned = value.strip()
    keyword_tag = tag_for_keyword(cleaned)
    if keyword_tag is not None:
        return Tag(keyword_tag)

    hex_text = cleaned
    if hex_text.startswith("(") and hex_text.endswith(")"):
        hex_text = hex_text[1:-1]
    hex_text = hex_text.replace(",", "").replace(" ", "").replace("_", "")
    if hex_text.lower().startswith("0x"):
        hex_text = hex_text[2:]
    if len(hex_text) != 8 or not re.fullmatch(r"[0-9A-Fa-f]{8}", hex_text):
        raise ValueError(
            f"Unsupported DICOM tag format: {value}. "
            "Use a DICOM keyword, 0018,0081, (0018,0081), or 0x00180081."
        )
    return Tag(int(hex_text, 16))


def safe_column_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def unique_column_name(column: str, seen: set[str]) -> str:
    if column not in seen:
        return column
    index = 2
    while True:
        candidate = f"{column}_{index}"
        if candidate not in seen:
            return candidate
        index += 1


def text_value(value: Any, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, bytes):
        return value.decode(errors="replace").strip() or default
    if isinstance(value, (list, tuple, MultiValue)):
        return "\\".join(text_value(v, default="") for v in value)
    return str(value)


def ds_value(ds: pydicom.dataset.Dataset, name: str, default: str = "N/A") -> str:
    return text_value(getattr(ds, name, None), default=default)


def tag_value(
    ds: pydicom.dataset.Dataset,
    group: int,
    element: int,
    default: str = "N/A",
) -> str:
    tag = (group, element)
    if tag not in ds:
        return default
    return text_value(ds[tag].value, default=default)


def dicom_tag_value(ds: pydicom.dataset.Dataset, tag: Tag, default: str = "N/A") -> str:
    if tag not in ds:
        return default
    return text_value(ds[tag].value, default=default)


def philips_private_sequence_item(ds: pydicom.dataset.Dataset) -> pydicom.dataset.Dataset | None:
    elem = ds.get((0x2005, 0x140F))
    if elem is None or elem.VR != "SQ" or not elem.value:
        return None
    item = elem.value[0]
    return item if isinstance(item, pydicom.dataset.Dataset) else None


def sequence_name_text(ds: pydicom.dataset.Dataset) -> str:
    value = ds_value(ds, "SequenceName")
    if value != "N/A":
        return value
    private_item = philips_private_sequence_item(ds)
    if private_item is None:
        return "N/A"
    return ds_value(private_item, "PulseSequenceName")


def radiopharmaceutical_info_item(ds: pydicom.dataset.Dataset) -> pydicom.dataset.Dataset | None:
    sequence = getattr(ds, "RadiopharmaceuticalInformationSequence", None)
    if not sequence:
        return None
    item = sequence[0]
    return item if isinstance(item, pydicom.dataset.Dataset) else None


def radiopharmaceutical_text(ds: pydicom.dataset.Dataset) -> str:
    item = radiopharmaceutical_info_item(ds)
    if item is None:
        return "N/A"
    return ds_value(item, "Radiopharmaceutical")


def radionuclide_total_dose_text(ds: pydicom.dataset.Dataset) -> str:
    item = radiopharmaceutical_info_item(ds)
    if item is None:
        return "N/A"
    return ds_value(item, "RadionuclideTotalDose")


def radionuclide_half_life_text(ds: pydicom.dataset.Dataset) -> str:
    item = radiopharmaceutical_info_item(ds)
    if item is None:
        return "N/A"
    return ds_value(item, "RadionuclideHalfLife")


def private_text_fields(raw: str, mode: str) -> tuple[str, str]:
    if not raw:
        return "N/A", "N/A"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    if mode == "keep":
        return raw, digest
    if mode == "hash":
        return f"sha256:{digest}", digest
    if mode == "drop":
        return "N/A", "N/A"
    return "N/A", digest


def patient_name_fields(ds: pydicom.dataset.Dataset, mode: str) -> tuple[str, str]:
    return private_text_fields(ds_value(ds, "PatientName", default=""), mode)


def hash_text(text: str, length: int = 12) -> str:
    if not text or text == "N/A":
        text = "missing"
    return hashlib.sha1(text.encode()).hexdigest()[:length]


def safe_name(value: str, fallback: str = "NA") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "-", value.strip())
    cleaned = cleaned.strip("-_.")
    return cleaned or fallback


def compute_study_key(study_uid: str) -> str:
    return hash_text(study_uid, 8)


def compute_patient_key(patient_id: str, issuer: str, patient_mode: str) -> str:
    if not patient_id or patient_id == "N/A":
        return "unknown-patient"
    if patient_mode == "keep":
        if issuer and issuer != "N/A":
            raw_key = f"{patient_id}_{issuer}"
        else:
            raw_key = patient_id
        sanitized = safe_name(raw_key)
        if sanitized != raw_key:
            digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:8]
            return f"{sanitized}-{digest}"
        return sanitized
    issuer_part = issuer if (issuer and issuer != "N/A") else ""
    raw = f"{issuer_part}|{patient_id}"
    return "P-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def compute_study_folder(
    layout: str,
    device_folder: str,
    study_date: str,
    study_key: str,
    patient_key: str,
) -> str:
    if layout == "device-date":
        return f"{device_folder}/{study_date}"
    if layout == "study":
        return f"{study_date}_{study_key}"
    if layout == "patient-study":
        return f"{patient_key}/{study_date}_{study_key}"
    raise ValueError(f"Unsupported layout: {layout}")


DIRECT_IDENTIFIER_TAGS = {
    "PatientName",
    "PatientID",
    "IssuerOfPatientID",
    "OtherPatientIDs",
    "OtherPatientIDsSequence",
    "OtherPatientNames",
    "PatientBirthName",
    "PatientBirthDate",
    "PatientBirthTime",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "PatientMotherBirthName",
    "MedicalRecordLocator",
    "AccessionNumber",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "OperatorsName",
    "InstitutionName",
    "InstitutionAddress",
}


def patient_data_notices(options: OrganizeOptions) -> list[str]:
    """Return stable notice codes describing what patient information remains."""
    notices: list[str] = []
    if options.patient_mode == "keep":
        notices.append("csv_patient_fields_kept")
    elif options.patient_mode == "hash":
        notices.append("csv_patient_fields_hashed")
    elif options.patient_mode == "drop":
        notices.append("csv_patient_fields_dropped")

    if options.list_only:
        notices.append("no_dicom_copies")
    else:
        notices.append("dicom_files_unchanged")

    notices.append("csv_other_identifiers")

    if options.dicom_tags:
        notices.append("custom_tags_written")

    if options.layout == "patient-study":
        if options.patient_mode == "keep":
            notices.append("folder_names_contain_patient_id")
        else:
            notices.append("folder_names_contain_patient_key")

    return notices


def safe_date(value: str, fallback: str = "unknown_date") -> str:
    """Return a YYYYMMDD folder-safe date, or the fallback when it is not a valid date."""
    text = str(value).strip()
    digits = re.sub(r"\D", "", text)
    if len(digits) != 8:
        return fallback
    try:
        datetime.strptime(digits, "%Y%m%d")
    except ValueError:
        return fallback
    return digits


def ensure_within_output_root(output_root: Path, path: Path) -> Path:
    """Return path unchanged after verifying that it stays inside output_root."""
    root = output_root.resolve()
    candidate = path if path.is_absolute() else output_root / path
    if not candidate.resolve().is_relative_to(root):
        raise ValueError(f"Output path escapes the output root: {candidate}")
    return candidate


def normalize_vendor_name(manufacturer: str) -> str:
    cleaned = manufacturer.strip()
    if not cleaned or cleaned == "N/A":
        return ""
    m = cleaned.casefold()
    if "ge" in m:
        return "GE"
    if "siemens" in m:
        return "Siemens"
    if "philips" in m:
        return "Philips"
    if "canon" in m:
        return "Canon"
    if "toshiba" in m:
        return "Toshiba"
    if "hitachi" in m:
        return "Hitachi"
    if "fujifilm" in m or "fuji" in m:
        return "Fujifilm"
    return safe_name(cleaned, fallback="UnknownVendor")


def device_folder_name(manufacturer: str, model_name: str) -> str:
    vendor = normalize_vendor_name(manufacturer)
    cleaned_model = model_name.strip() if model_name and model_name != "N/A" else ""
    model = safe_name(cleaned_model, fallback="") if cleaned_model else ""
    if vendor and model:
        return f"{vendor}_{model}"
    if model:
        return model
    if vendor:
        return vendor
    return "UnknownDevice"


def series_number(ds: pydicom.dataset.Dataset) -> str:
    raw = ds_value(ds, "SeriesNumber", default="0")
    try:
        return f"{int(float(raw)):06d}"
    except ValueError:
        return safe_name(raw, fallback="000000")


def preferred_series_label(ds: pydicom.dataset.Dataset) -> str:
    manufacturer = ds_value(ds, "Manufacturer", default="").casefold()
    series_description = ds_value(ds, "SeriesDescription")
    protocol_name = ds_value(ds, "ProtocolName")
    if (
        any(
            vendor in manufacturer
            for vendor in (
                "philips",
                "ge medical systems",
                "ge healthcare",
                "canon",
                "toshiba",
            )
        )
        and series_description != "N/A"
    ):
        return series_description
    if protocol_name != "N/A":
        return protocol_name
    return series_description


def image_type_parts(ds: pydicom.dataset.Dataset) -> tuple[str, ...]:
    raw = getattr(ds, "ImageType", None)
    if raw is None or raw == "":
        return ()
    if isinstance(raw, (list, tuple, MultiValue)):
        return tuple(str(part).strip() for part in raw if str(part).strip())
    return tuple(part.strip() for part in str(raw).split("\\") if part.strip())


def reconstruction_label(image_type: tuple[str, ...]) -> str:
    if not image_type:
        return ""
    major = image_type[2] if len(image_type) >= 3 else image_type[-1]
    minor = image_type[4] if len(image_type) >= 5 else ""
    major_safe = safe_name(major)
    if not minor:
        return major_safe
    minor_safe = safe_name(minor)
    if (
        major_safe == minor_safe
        or major_safe.endswith(f"_{minor_safe}")
        or major_safe.endswith(f"-{minor_safe}")
    ):
        return major_safe
    return safe_name(f"{major} {minor}")


def is_numeric_series_label(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))


def should_split_philips_series(contexts: list[dict[str, Any]]) -> bool:
    reconstruction_keys = {
        tuple(context["philips_image_type"])
        for context in contexts
        if context["philips_image_type"]
    }
    return len(reconstruction_keys) > 1


def dominant_philips_reconstruction(contexts: list[dict[str, Any]]) -> tuple[str, ...]:
    counter = Counter(
        tuple(context["philips_image_type"])
        for context in contexts
        if context["philips_image_type"]
    )
    if not counter:
        return ()
    return counter.most_common(1)[0][0]


def resolved_series_assignments(
    pending: list[tuple[Path, dict[str, Any], str, tuple[Any, ...]]],
) -> list[tuple[tuple[Any, ...], dict[str, str]]]:
    assignments: list[tuple[tuple[Any, ...], dict[str, str]]] = [
        ((), {}) for _ in pending
    ]
    indices_by_series: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    anchor_labels: dict[tuple[str, str, str, tuple[str, ...]], str] = {}

    anchor_candidates: dict[tuple[str, str, str, tuple[str, ...]], set[str]] = defaultdict(set)
    for _source, context, _filename, _base_series_key in pending:
        if not context["is_philips_mr"]:
            continue
        study_instance_uid = context.get("study_instance_uid", "")
        if not study_instance_uid or study_instance_uid == "N/A":
            continue
        acquisition_number = context["acquisition_number"]
        if not acquisition_number or acquisition_number == "N/A":
            continue
        if is_numeric_series_label(context["raw_series_label"]):
            continue
        key = (
            study_instance_uid,
            context["study_date"],
            acquisition_number,
            tuple(context["philips_image_type"]),
        )
        anchor_candidates[key].add(context["series_label"])

    for key, candidates in anchor_candidates.items():
        if len(candidates) == 1:
            anchor_labels[key] = next(iter(candidates))

    for index, (_source, _context, _filename, base_series_key) in enumerate(pending):
        indices_by_series[base_series_key].append(index)

    for base_series_key, indices in indices_by_series.items():
        contexts = [pending[index][1] for index in indices]
        is_philips_series = any(bool(context["is_philips_mr"]) for context in contexts)
        split_series = is_philips_series and should_split_philips_series(contexts)
        dominant_reconstruction = dominant_philips_reconstruction(contexts)

        for index in indices:
            context = pending[index][1]
            effective_reconstruction: tuple[str, ...] = ()
            reconstruction_name = ""
            series_label = context["series_label"]
            if context["is_philips_mr"] and is_numeric_series_label(context["raw_series_label"]):
                study_instance_uid = context.get("study_instance_uid", "")
                if study_instance_uid and study_instance_uid != "N/A":
                    anchor_key = (
                        study_instance_uid,
                        context["study_date"],
                        context["acquisition_number"],
                        tuple(context["philips_image_type"]),
                    )
                    anchor_label = anchor_labels.get(anchor_key)
                    if anchor_label:
                        series_label = safe_name(f"{anchor_label}_{series_label}")
            if split_series:
                effective_reconstruction = tuple(context["philips_image_type"]) or dominant_reconstruction
                reconstruction_name = reconstruction_label(effective_reconstruction)
            series_folder_label = series_label
            if reconstruction_name:
                series_folder_label = f"{series_folder_label}_{reconstruction_name}"
            assignments[index] = (
                (*base_series_key, effective_reconstruction),
                {
                    "series_label": series_label,
                    "reconstruction_label": reconstruction_name,
                    "series_folder_label": series_folder_label,
                },
            )

    return assignments


def is_organized_dir_name(part: str) -> bool:
    return (
        part == "organized"
        or part.startswith("organized.")
        or part.startswith("organized_")
        or part.startswith("organized-")
    )


def instance_number(ds: pydicom.dataset.Dataset, fallback: int) -> int:
    raw = getattr(ds, "InstanceNumber", None)
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return fallback


def float_text(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return text_value(value)


def pixel_spacing(ds: pydicom.dataset.Dataset) -> str:
    return text_value(getattr(ds, "PixelSpacing", None), default="N/A")


def functional_group_value(
    ds: pydicom.dataset.Dataset,
    sequence_name: str,
    attribute_name: str,
) -> Any | None:
    """Return the first shared/per-frame functional-group attribute value."""
    for functional_groups_name in (
        "SharedFunctionalGroupsSequence",
        "PerFrameFunctionalGroupsSequence",
    ):
        functional_groups = getattr(ds, functional_groups_name, None)
        if not functional_groups:
            continue
        nested_sequence = getattr(functional_groups[0], sequence_name, None)
        if not nested_sequence:
            continue
        value = getattr(nested_sequence[0], attribute_name, None)
        if value is not None and value != "":
            return value
    return None


def image_orientation_patient_value(ds: pydicom.dataset.Dataset) -> Any | None:
    value = getattr(ds, "ImageOrientationPatient", None)
    if value is not None and value != "":
        return value
    return functional_group_value(
        ds,
        "PlaneOrientationSequence",
        "ImageOrientationPatient",
    )


def in_plane_phase_encoding_direction_value(ds: pydicom.dataset.Dataset) -> Any | None:
    value = getattr(ds, "InPlanePhaseEncodingDirection", None)
    if value is not None and value != "":
        return value
    return functional_group_value(
        ds,
        "MRFOVGeometrySequence",
        "InPlanePhaseEncodingDirection",
    )


def parallel_reduction_factor_in_plane_value(ds: pydicom.dataset.Dataset) -> Any | None:
    value = getattr(ds, "ParallelReductionFactorInPlane", None)
    if value is not None and value != "":
        return value
    value = functional_group_value(
        ds,
        "MRModifierSequence",
        "ParallelReductionFactorInPlane",
    )
    if value is not None and value != "":
        return value
    if "siemens" not in ds_value(ds, "Manufacturer", default="").casefold():
        return None

    for element in ds:
        if not element.tag.is_private or not isinstance(element.value, bytes):
            continue
        match = SIEMENS_PARALLEL_REDUCTION_FACTOR_PATTERN.search(element.value)
        if match is None:
            continue
        try:
            factor = float(match.group(1))
        except ValueError:
            continue
        if factor > 0:
            return factor
    return None


def format_duration(value: Any) -> str:
    """Format duration in seconds as HH:MM:SS rounded to the nearest second."""
    if value is None or value == "":
        return "N/A"
    try:
        sec_float = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not math.isfinite(sec_float) or sec_float <= 0:
        return "N/A"
    total_seconds = int(
        Decimal(str(sec_float)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    if total_seconds <= 0:
        return "N/A"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def scan_duration_fields(ds: pydicom.dataset.Dataset) -> tuple[str, str]:
    """Extract scan duration and source tag as (ScanDuration, ScanDurationSource)."""
    if (0x0018, 0x9073) in ds:
        elem = ds[0x0018, 0x9073]
        if elem.value is not None and elem.value != "":
            duration = format_duration(elem.value)
            if duration != "N/A":
                return duration, "0018,9073"

    try:
        block = ds.private_block(0x0019, "GEMS_ACQU_01")
        if 0x5A in block:
            elem_val = block[0x5A].value
            if elem_val is not None and elem_val != "":
                try:
                    sec = float(elem_val) / 1e6
                    duration = format_duration(sec)
                    if duration != "N/A":
                        return duration, "0019,105A"
                except (TypeError, ValueError):
                    pass
    except KeyError:
        pass

    if "siemens" in ds_value(ds, "Manufacturer", default="").casefold():
        for element in ds:
            if not element.tag.is_private or not isinstance(element.value, bytes):
                continue
            match = SIEMENS_TOTAL_SCAN_TIME_PATTERN.search(element.value)
            if match is None:
                continue
            try:
                sec = float(match.group(1).decode("ascii"))
            except (ValueError, UnicodeDecodeError):
                continue
            duration = format_duration(sec)
            if duration != "N/A":
                tag_str = f"{element.tag.group:04X},{element.tag.elem:04X}"
                return duration, f"{tag_str}:lTotalScanTimeSec"

    return "N/A", "N/A"


def direction_cosines(value: Any) -> tuple[float, ...] | None:
    if value is None or value == "":
        return None
    values = value.split("\\") if isinstance(value, str) else value
    try:
        cosines = tuple(float(component) for component in values)
    except (TypeError, ValueError):
        return None
    if len(cosines) != 6 or not all(math.isfinite(component) for component in cosines):
        return None
    return cosines


def phase_encoding_direction_patient(ds: pydicom.dataset.Dataset) -> str:
    """Map the positive phase-encoding image axis to a biped patient direction."""
    anatomical_orientation_type = ds_value(
        ds,
        "AnatomicalOrientationType",
        default="BIPED",
    ).upper()
    if anatomical_orientation_type not in {"BIPED", "N/A"}:
        return "N/A"

    phase_axis = text_value(
        in_plane_phase_encoding_direction_value(ds),
        default="",
    ).upper()
    cosines = direction_cosines(image_orientation_patient_value(ds))
    if cosines is None:
        return "N/A"
    if phase_axis == "ROW":
        vector = cosines[:3]
    elif phase_axis in {"COL", "COLUMN"}:
        vector = cosines[3:]
    else:
        return "N/A"

    dominant_axis = max(range(3), key=lambda index: abs(vector[index]))
    component = vector[dominant_axis]
    if abs(component) < 1e-6:
        return "N/A"

    negative_to_positive = (
        ("R", "L"),
        ("A", "P"),
        ("F", "H"),
    )
    start, end = negative_to_positive[dominant_axis]
    if component < 0:
        start, end = end, start
    return f"{start}\N{RIGHTWARDS ARROW}{end}"


def fov_text(ds: pydicom.dataset.Dataset) -> str:
    try:
        spacing = getattr(ds, "PixelSpacing")
        rows = int(getattr(ds, "Rows"))
        cols = int(getattr(ds, "Columns"))
        return f"{float(spacing[0]) * rows:g}x{float(spacing[1]) * cols:g}"
    except (AttributeError, TypeError, ValueError, IndexError):
        return "N/A"


def matrix_text(ds: pydicom.dataset.Dataset) -> str:
    rows = ds_value(ds, "Rows")
    cols = ds_value(ds, "Columns")
    if rows == "N/A" or cols == "N/A":
        return "N/A"
    return f"{rows}x{cols}"


def parse_siemens_ice_dims(value: str) -> tuple[str, str]:
    if not value or value == "N/A":
        return "N/A", "N/A"
    parts = value.split("_")
    channel = parts[0] if len(parts) >= 1 and parts[0] else "N/A"
    echo = parts[1] if len(parts) >= 2 and parts[1] else "N/A"
    return channel, echo


def is_normalized(image_type: str) -> str:
    parts = {part.upper() for part in image_type.split("\\") if part}
    return "true" if "NORM" in parts else "false"


def row_profile_name(row: dict[str, str]) -> str | None:
    for name, profile in MODALITY_PROFILES.items():
        if row.get("Modality") in profile.modalities and row.get("SOPClassUID") in profile.sop_classes:
            return name
    return None


def metadata_rows(rows: list[dict[str, str]], profile_name: str) -> list[dict[str, str]]:
    if profile_name == "generic" or profile_name == "auto":
        return [row for row in rows if row_profile_name(row) is not None]
    return [row for row in rows if row_profile_name(row) == profile_name]


def row_modality(row: dict[str, str]) -> str:
    modality = row.get("Modality", "N/A").strip()
    return modality or "N/A"


def modality_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    return dict(sorted(Counter(row_modality(row) for row in rows).items()))


def present_modality_profiles(rows: list[dict[str, str]]) -> list[ModalityProfile]:
    present_names = {
        name for name in (row_profile_name(row) for row in rows) if name in MODALITY_PROFILES
    }
    return [MODALITY_PROFILES[name] for name in PROFILE_NAMES if name in present_names]


def metadata_columns_for_profile(
    profile_name: str,
    rows: list[dict[str, str]],
    extra_metadata_columns: list[str] | None = None,
) -> list[str]:
    if profile_name == "generic":
        columns = list(COMMON_METADATA_COLUMNS)
    elif profile_name == "auto":
        columns = merge_columns(
            COMMON_METADATA_COLUMNS,
            *(profile.metadata_columns for profile in present_modality_profiles(rows)),
        )
    else:
        columns = merge_columns(
            COMMON_METADATA_COLUMNS,
            MODALITY_PROFILES[profile_name].metadata_columns,
        )
    return merge_columns(columns, extra_metadata_columns or [])


def summary_columns_for_profile(
    profile_name: str,
    rows: list[dict[str, str]],
    extra_metadata_columns: list[str] | None = None,
) -> list[str]:
    if profile_name == "generic":
        columns = list(COMMON_SUMMARY_COLUMNS)
    elif profile_name == "auto":
        columns = merge_columns(
            COMMON_SUMMARY_COLUMNS,
            *(profile.summary_columns for profile in present_modality_profiles(rows)),
        )
    else:
        columns = merge_columns(
            COMMON_SUMMARY_COLUMNS,
            MODALITY_PROFILES[profile_name].summary_columns,
        )
    return merge_columns(columns, extra_metadata_columns or [])


def file_context(
    ds: pydicom.dataset.Dataset,
    item_index: int,
    patient_mode: str,
    input_root: Path,
    source: Path,
    dicom_tag_specs: list[DicomTagSpec],
) -> dict[str, Any]:
    series_uid = ds_value(ds, "SeriesInstanceUID")
    sop_uid = ds_value(ds, "SOPInstanceUID")
    series_uid_hash = hash_text(series_uid)
    sop_uid_hash = hash_text(sop_uid)
    inst = instance_number(ds, item_index)
    image_type = ds_value(ds, "ImageType")
    patient_name, patient_hash = patient_name_fields(ds, patient_mode)
    patient_id, patient_id_hash = private_text_fields(
        ds_value(ds, "PatientID", default=""),
        patient_mode,
    )
    siemens_ice_dims = tag_value(ds, 0x0021, 0x118E)
    siemens_dim_channel, siemens_dim_echo = parse_siemens_ice_dims(siemens_ice_dims)
    series_description = ds_value(ds, "SeriesDescription")
    protocol_name = ds_value(ds, "ProtocolName")
    philips_image_type = image_type_parts(ds)
    manufacturer = ds_value(ds, "Manufacturer")
    sequence_name = sequence_name_text(ds)
    modality = ds_value(ds, "Modality")
    image_orientation_patient = image_orientation_patient_value(ds)
    in_plane_phase_encoding_direction = in_plane_phase_encoding_direction_value(ds)
    scan_duration, scan_duration_source = scan_duration_fields(ds)

    row = {
        "SeriesUID": series_uid,
        "SOPInstanceUID": sop_uid,
        "SeriesNumber": series_number(ds),
        "SeriesDescription": series_description,
        "FileCount": "N/A",
        "InstanceNumber": str(inst),
        "AcquisitionDate": ds_value(
            ds,
            "AcquisitionDate",
            default=ds_value(ds, "StudyDate", default="unknown_date"),
        ),
        "AcquisitionTime": ds_value(ds, "AcquisitionTime"),
        "PatientName": patient_name,
        "Modality": ds_value(ds, "Modality"),
        "TR_ms": ds_value(ds, "RepetitionTime"),
        "TE_ms": ds_value(ds, "EchoTime"),
        "EchoCount": "N/A",
        "EchoTimes_ms": "N/A",
        "FOV_HxW_mm": fov_text(ds),
        "Matrix_RowsxCols": matrix_text(ds),
        "PixelBandwidth_Hz_per_px": ds_value(ds, "PixelBandwidth"),
        "EchoTrainLength": ds_value(ds, "EchoTrainLength"),
        "FlipAngle_deg": ds_value(ds, "FlipAngle"),
        "SliceThickness_mm": ds_value(ds, "SliceThickness"),
        "SpacingBetweenSlices_mm": ds_value(ds, "SpacingBetweenSlices"),
        "SliceLocation_mm": ds_value(ds, "SliceLocation"),
        "NumberOfAverages": ds_value(ds, "NumberOfAverages"),
        "MagneticFieldStrength_T": ds_value(ds, "MagneticFieldStrength"),
        "ScanningSequence": ds_value(ds, "ScanningSequence"),
        "SequenceVariant": ds_value(ds, "SequenceVariant"),
        "SequenceName": sequence_name,
        "InversionTime_ms": ds_value(ds, "InversionTime"),
        "EchoNumbers": ds_value(ds, "EchoNumbers"),
        "AcquisitionMatrix": ds_value(ds, "AcquisitionMatrix"),
        "NumberOfPhaseEncodingSteps": ds_value(ds, "NumberOfPhaseEncodingSteps"),
        "PercentSampling": ds_value(ds, "PercentSampling"),
        "PercentPhaseFOV": ds_value(ds, "PercentPhaseFieldOfView"),
        "ParallelReductionFactorInPlane": text_value(
            parallel_reduction_factor_in_plane_value(ds)
        ),
        "SAR": ds_value(ds, "SAR"),
        "ScanDuration": scan_duration,
        "ScanDurationSource": scan_duration_source,
        "InPlanePhaseEncodingDirection": text_value(in_plane_phase_encoding_direction),
        "PhaseEncodingDirectionPatient": phase_encoding_direction_patient(ds),
        "Manufacturer": manufacturer,
        "ManufacturerModelName": ds_value(ds, "ManufacturerModelName"),
        "ReceiveCoilName": ds_value(ds, "ReceiveCoilName"),
        "SourceFileName": source.relative_to(input_root).as_posix(),
        "ProtocolName": protocol_name,
        "ImageType": image_type,
        "MRAcquisitionType": ds_value(ds, "MRAcquisitionType"),
        "Rows": ds_value(ds, "Rows"),
        "Columns": ds_value(ds, "Columns"),
        "PixelSpacing": pixel_spacing(ds),
        "ImagePositionPatient": ds_value(ds, "ImagePositionPatient"),
        "ImageOrientationPatient": text_value(image_orientation_patient),
        "PatientPosition": ds_value(ds, "PatientPosition"),
        "FrameOfReferenceUID": ds_value(ds, "FrameOfReferenceUID"),
        "StudyInstanceUID": ds_value(ds, "StudyInstanceUID"),
        "StudyDate": ds_value(ds, "StudyDate"),
        "StudyTime": ds_value(ds, "StudyTime"),
        "SeriesDate": ds_value(ds, "SeriesDate"),
        "SeriesTime": ds_value(ds, "SeriesTime"),
        "PatientID": patient_id,
        "PatientIDHash": patient_id_hash,
        "PatientNameHash": patient_hash,
        "SOPClassUID": ds_value(ds, "SOPClassUID"),
        "SiemensChannelMixing": tag_value(ds, 0x0021, 0x1176),
        "SiemensCoilElement": tag_value(ds, 0x0021, 0x114F),
        "CoilElementCount": "N/A",
        "CoilElements": "N/A",
        "SiemensIceDims": siemens_ice_dims,
        "SiemensIceDimChannel": siemens_dim_channel,
        "SiemensIceDimEcho": siemens_dim_echo,
        "IsNormalized": is_normalized(image_type),
        "KVP_kV": ds_value(ds, "KVP"),
        "XRayTubeCurrent_mA": ds_value(ds, "XRayTubeCurrent"),
        "ExposureTime_ms": ds_value(ds, "ExposureTime"),
        "ConvolutionKernel": ds_value(ds, "ConvolutionKernel"),
        "ReconstructionDiameter_mm": ds_value(ds, "ReconstructionDiameter"),
        "TransducerData": ds_value(ds, "TransducerData"),
        "TransducerType": ds_value(ds, "TransducerType"),
        "MechanicalIndex": ds_value(ds, "MechanicalIndex"),
        "ThermalIndex": ds_value(ds, "ThermalIndex"),
        "UltrasoundColorDataPresent": ds_value(ds, "UltrasoundColorDataPresent"),
        "FrameTime_ms": ds_value(ds, "FrameTime"),
        "DistanceSourceToDetector_mm": ds_value(ds, "DistanceSourceToDetector"),
        "DistanceSourceToPatient_mm": ds_value(ds, "DistanceSourceToPatient"),
        "Radiopharmaceutical": radiopharmaceutical_text(ds),
        "RadionuclideTotalDose_Bq": radionuclide_total_dose_text(ds),
        "RadionuclideHalfLife_s": radionuclide_half_life_text(ds),
        "DecayCorrection": ds_value(ds, "DecayCorrection"),
    }
    for spec in dicom_tag_specs:
        row[spec.column] = dicom_tag_value(ds, spec.tag)

    study_instance_uid = ds_value(ds, "StudyInstanceUID", default="")
    study_date = safe_date(
        ds_value(
            ds, "StudyDate", default=ds_value(ds, "AcquisitionDate", default="unknown_date")
        )
    )
    device_folder = device_folder_name(manufacturer, ds_value(ds, "ManufacturerModelName"))
    patient_id_raw = ds_value(ds, "PatientID", default="")
    issuer = ds_value(ds, "IssuerOfPatientID", default="")
    study_key = compute_study_key(study_instance_uid)
    patient_key = compute_patient_key(patient_id_raw, issuer, patient_mode)

    return {
        "study_instance_uid": study_instance_uid,
        "study_date": study_date,
        "study_key": study_key,
        "patient_key": patient_key,
        "device_folder": device_folder,
        "acquisition_date": safe_date(
            ds_value(
                ds, "AcquisitionDate", default=ds_value(ds, "StudyDate", default="unknown_date")
            )
        ),
        "acquisition_number": ds_value(ds, "AcquisitionNumber", default=""),
        "series_uid": series_uid,
        "series_number": series_number(ds),
        "series_description": safe_name(series_description),
        "protocol_name": safe_name(protocol_name),
        "series_label": safe_name(preferred_series_label(ds)),
        "raw_series_label": preferred_series_label(ds),
        "reconstruction_label": "",
        "series_folder_label": safe_name(preferred_series_label(ds)),
        "series_uid_hash": series_uid_hash,
        "sop_uid_hash": sop_uid_hash,
        "instance_number": str(inst),
        "instance_number_6": f"{inst:06d}",
        "echo_time_ms": safe_name(float_text(getattr(ds, "EchoTime", "NA"))),
        "siemens_coil_element": safe_name(tag_value(ds, 0x0021, 0x114F)),
        "is_philips": "philips" in manufacturer.casefold(),
        "is_philips_mr": "philips" in manufacturer.casefold() and modality == "MR",
        "modality": modality,
        "philips_image_type": philips_image_type,
        "row": row,
    }


def should_skip(path: Path, input_root: Path, output_root: Path, options: OrganizeOptions) -> bool:
    try:
        path.relative_to(output_root)
        return True
    except ValueError:
        pass

    rel_parts = path.relative_to(input_root).parts
    if not options.include_hidden and any(part.startswith(".") for part in rel_parts):
        return True
    if not options.include_organized and any(is_organized_dir_name(part) for part in rel_parts):
        return True
    return False


def classify_prune_dir(
    dir_path: Path,
    input_root: Path,
    output_root: Path,
    options: OrganizeOptions,
) -> str | None:
    try:
        dir_path.relative_to(output_root)
        return "output_root"
    except ValueError:
        pass
    resolved_dir = dir_path.resolve()
    resolved_out = output_root.resolve()
    if resolved_dir == resolved_out or (
        resolved_out.exists() and resolved_dir.is_relative_to(resolved_out)
    ):
        return "output_root"

    rel_parts = dir_path.relative_to(input_root).parts
    if not options.include_hidden and any(part.startswith(".") for part in rel_parts):
        return "hidden"
    if not options.include_organized and any(is_organized_dir_name(part) for part in rel_parts):
        return "organized"
    return None


def should_prune_dir(
    path: Path,
    input_root: Path,
    output_root: Path,
    options: OrganizeOptions,
) -> bool:
    return classify_prune_dir(path, input_root, output_root, options) is not None


def scan_candidates(
    input_root: Path,
    output_root: Path,
    options: OrganizeOptions,
    cancel_event: threading.Event | None = None,
) -> tuple[list[Path], list[Path], list[dict[str, str]]]:
    """Scan input_root for DICOM candidate files, hidden files, and excluded directories."""
    candidates: list[Path] = []
    hidden_files: list[Path] = []
    excluded_dirs: list[dict[str, str]] = []
    resolved_out = output_root.resolve()

    for root, dirnames, filenames in os.walk(input_root):
        if cancel_event is not None and cancel_event.is_set():
            break
        root_path = Path(root)
        kept_dirnames = []
        for dirname in sorted(dirnames):
            dir_path = root_path / dirname
            prune_reason = classify_prune_dir(dir_path, input_root, output_root, options)
            if prune_reason is not None:
                excluded_dirs.append({
                    "path": dir_path.relative_to(input_root).as_posix(),
                    "reason": prune_reason,
                })
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            if cancel_event is not None and cancel_event.is_set():
                break
            path = root_path / filename

            # Check if within output_root
            is_out = False
            try:
                path.relative_to(output_root)
                is_out = True
            except ValueError:
                if path.is_symlink():
                    resolved_f = path.resolve()
                    if resolved_out.exists() and resolved_f.is_relative_to(resolved_out):
                        is_out = True
            if is_out:
                continue

            rel_parts = path.relative_to(input_root).parts
            if not options.include_organized and any(is_organized_dir_name(p) for p in rel_parts):
                continue

            if not options.include_hidden and any(part.startswith(".") for part in rel_parts):
                if filename.startswith("."):
                    hidden_files.append(path)
                continue

            candidates.append(path)

    return candidates, hidden_files, excluded_dirs


def iter_candidate_files(input_root: Path, output_root: Path, options: OrganizeOptions):
    candidates, _hidden, _dirs = scan_candidates(input_root, output_root, options)
    yield from candidates


def classify_dicom_file(path: Path, force: bool) -> HeaderReadResult:
    # 1. Read first 132 bytes to check DICM prefix
    has_dicm = False
    try:
        with path.open("rb") as f:
            header = f.read(132)
            has_dicm = len(header) >= 132 and header[128:132] == b"DICM"
    except PermissionError as exc:
        return HeaderReadResult(None, "permission_denied", str(exc))
    except OSError as exc:
        return HeaderReadResult(None, "io_error", str(exc))

    # 2. Read with pydicom
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=force)
    except PermissionError as exc:
        return HeaderReadResult(None, "permission_denied", str(exc))
    except OSError as exc:
        return HeaderReadResult(None, "io_error", str(exc))
    except pydicom.errors.InvalidDicomError as exc:
        reason = "read_error" if has_dicm else "not_dicom"
        return HeaderReadResult(None, reason, str(exc))
    except Exception as exc:
        reason = "read_error" if has_dicm else "not_dicom"
        return HeaderReadResult(None, reason, str(exc))

    # 3. Check for DICOMDIR
    file_meta = getattr(ds, "file_meta", None)
    sop_class = getattr(file_meta, "MediaStorageSOPClassUID", None) if file_meta else None
    if (
        str(sop_class) == "1.2.840.10008.1.3.10"
        or str(getattr(ds, "SOPClassUID", None)) == "1.2.840.10008.1.3.10"
    ):
        return HeaderReadResult(None, "dicomdir", "DICOMDIR media storage directory")

    # 4. Check for SeriesInstanceUID and SOPInstanceUID
    has_series = hasattr(ds, "SeriesInstanceUID") and str(ds.SeriesInstanceUID).strip() != ""
    has_sop = hasattr(ds, "SOPInstanceUID") and str(ds.SOPInstanceUID).strip() != ""
    if has_series and has_sop:
        return HeaderReadResult(ds, "N/A", "N/A")

    # 5. Check if has_dicm but no transfer syntax or empty dataset
    has_ts = file_meta is not None and getattr(file_meta, "TransferSyntaxUID", None) is not None
    if has_dicm and (not has_ts or len(ds) == 0):
        return HeaderReadResult(
            None, "read_error", "DICM prefix found but no data elements could be read"
        )

    # 6. Check if has_dicm or SOPClassUID / Modality / StudyInstanceUID
    has_marker = any(
        hasattr(ds, attr) and str(getattr(ds, attr)).strip() != ""
        for attr in ("SOPClassUID", "Modality", "StudyInstanceUID")
    )
    if has_dicm or has_marker:
        missing = []
        if not has_series:
            missing.append("SeriesInstanceUID")
        if not has_sop:
            missing.append("SOPInstanceUID")
        return HeaderReadResult(None, "missing_required_uid", f"missing {' and '.join(missing)}")

    # 7. Otherwise not_dicom
    return HeaderReadResult(None, "not_dicom", "not a DICOM file")


def read_dicom_header(path: Path, force: bool) -> pydicom.dataset.Dataset | None:
    return classify_dicom_file(path, force).dataset


def format_template(template: str, context: dict[str, Any], label: str) -> str:
    try:
        return template.format(**context)
    except KeyError as exc:
        key = exc.args[0]
        raise ValueError(f"Unknown key in {label} template: {key}") from exc


def resolve_collision(
    path: Path,
    seen: set[Path],
    if_exists: str,
    *,
    dry_run: bool = False,
) -> Path | None:
    if path in seen:
        return suffixed_path(path, seen)
    if not path.exists():
        return path
    if if_exists == "error":
        if dry_run:
            return path
        raise FileExistsError(
            f"Target exists: {path}. "
            "Re-run with --if-exists skip to continue into an existing output folder."
        )
    if if_exists == "skip":
        return None
    if if_exists == "overwrite":
        return path
    if if_exists == "rename":
        return suffixed_path(path, seen)
    raise ValueError(f"Unsupported --if-exists value: {if_exists}")


def suffixed_path(path: Path, seen: set[Path]) -> Path:
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        if candidate not in seen and not candidate.exists():
            return candidate
        index += 1


def assign_series_dirs(
    base_dir_by_series: dict[Any, Path],
    series_order: list[Any],
) -> dict[Any, Path]:
    reserved = set(base_dir_by_series.values())  # Do not steal original names of other series
    counts = Counter(base_dir_by_series[key] for key in series_order)
    used: set[Path] = set()
    assigned: dict[Any, Path] = {}
    for series_key in series_order:
        base_dir = base_dir_by_series[series_key]
        if counts[base_dir] == 1 and base_dir not in used:
            assigned[series_key] = base_dir
            used.add(base_dir)
            continue
        index = 1
        while True:
            candidate = base_dir.with_name(f"{base_dir.name}_{index:02d}")
            if candidate not in used and candidate not in reserved:
                break
            index += 1
        assigned[series_key] = candidate
        used.add(candidate)
    return assigned


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def materialize(
    source: Path,
    destination: Path,
    action: str,
    overwrite: bool,
    *,
    checksum: bool = False,
) -> str:
    """Materialize source at destination using specified action.

    Returns the source SHA-256 hex digest when checksum is True, otherwise "N/A".
    """
    if action not in ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    if not overwrite and (destination.exists() or destination.is_symlink()):
        raise FileExistsError(
            f"Target exists: {destination}. "
            "Re-run with --if-exists skip to continue into an existing output folder."
        )

    src_size = source.stat().st_size
    src_sha = compute_sha256(source) if checksum else "N/A"

    if action == "move":
        try:
            os.replace(source, destination)  # Atomic on same filesystem
            if destination.stat().st_size != src_size:
                raise IntegrityError(f"File size mismatch after move: {destination}")
            return src_sha
        except OSError as exc:
            if exc.errno != errno.EXDEV:
                raise

    temp_path = destination.with_name(f".{destination.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        if action in ("copy", "move"):
            shutil.copy2(source, temp_path)
            if temp_path.stat().st_size != src_size:
                raise IntegrityError(
                    f"Size mismatch during copy: {temp_path.stat().st_size} != {src_size}"
                )
            if checksum:
                dst_sha = compute_sha256(temp_path)
                if dst_sha != src_sha:
                    raise IntegrityError(
                        f"SHA-256 mismatch during copy: {dst_sha} != {src_sha}"
                    )
        elif action == "symlink":
            temp_path.symlink_to(source)
            if temp_path.resolve() != source.resolve():
                raise IntegrityError(
                    f"Symlink does not resolve to source: {temp_path} -> {source}"
                )
        elif action == "hardlink":
            os.link(source, temp_path)
            if not os.path.samefile(source, temp_path):
                raise IntegrityError(
                    f"Hardlink is not the same file: {temp_path} and {source}"
                )

        os.replace(temp_path, destination)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    if action == "move":
        source.unlink()

    return src_sha


def write_file_report(
    output_root: Path,
    input_root: Path,
    records: list[FileRecord],
) -> Path:
    path = ensure_within_output_root(output_root, output_root / "file_report.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for record in records:
        try:
            source_rel = record.source.relative_to(input_root).as_posix()
        except ValueError:
            source_rel = str(record.source)

        dup_rel = "N/A"
        if record.duplicate_of is not None:
            try:
                dup_rel = record.duplicate_of.relative_to(input_root).as_posix()
            except ValueError:
                dup_rel = str(record.duplicate_of)

        dest_rel = "N/A"
        if record.destination is not None:
            try:
                dest_rel = record.destination.relative_to(output_root).as_posix()
            except ValueError:
                dest_rel = str(record.destination)

        size_str = str(record.size_bytes) if record.size_bytes is not None else "N/A"

        rows.append({
            "SourceFileName": source_rel,
            "Status": record.status,
            "Reason": record.reason,
            "Detail": record.detail,
            "OrganizedFileName": dest_rel,
            "DuplicateOf": dup_rel,
            "SOPInstanceUID": record.sop_instance_uid,
            "SeriesUID": record.series_uid,
            "Modality": record.modality,
            "SizeBytes": size_str,
            "SHA256": record.sha256,
        })
    rows.sort(key=lambda r: r["SourceFileName"])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILE_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def collect_reports(output_root: Path, items: list[OrganizedItem]) -> list[str]:
    reports: list[str] = ["file_report.csv"]
    if (output_root / "all_series_summary.csv").exists():
        reports.append("all_series_summary.csv")
    group_dirs = sorted({item.destination.parent.parent for item in items}, key=lambda p: str(p))
    for group_dir in group_dirs:
        try:
            rel_group = group_dir.relative_to(output_root).as_posix()
            reports.append(f"{rel_group}/dicom_parameters.csv")
            reports.append(f"{rel_group}/series_summary.csv")
        except ValueError:
            pass
    reports.append("organize_summary.json")
    return reports


def check_previous_run(output_root: Path) -> tuple[str | None, list[str]]:
    summary_path = output_root / "organize_summary.json"
    if not summary_path.exists():
        return None, []
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        prev_status = data.get("status")
        if prev_status in ("running", "cancelled", "interrupted", "failed"):
            warning = (
                f"Previous run was not completed (status={prev_status}). "
                "Re-run with --if-exists skip to continue into an existing output folder."
            )
            return prev_status, [warning]
    except Exception:
        pass
    return None, []


def find_existing_ancestor(path: Path) -> Path:
    cur = path.resolve()
    while not cur.exists():
        cur = cur.parent
    return cur


def check_free_space(
    items: list[OrganizedItem],
    output_root: Path,
    input_root: Path,
    action: str,
    space_check: bool,
) -> dict[str, Any]:
    if not space_check or not items:
        return {"checked": False, "required_bytes": None, "free_bytes": None}

    ancestor = find_existing_ancestor(output_root)
    needs_check = False
    if action == "copy":
        needs_check = True
    elif action == "move":
        try:
            in_dev = os.stat(input_root).st_dev
            out_dev = os.stat(ancestor).st_dev
            needs_check = in_dev != out_dev
        except OSError:
            needs_check = True

    if not needs_check:
        return {"checked": False, "required_bytes": None, "free_bytes": None}

    total_bytes = 0
    for item in items:
        try:
            total_bytes += item.source.stat().st_size
        except OSError:
            pass

    margin = max(64 * 1024 * 1024, total_bytes // 50)
    required = total_bytes + margin
    usage = shutil.disk_usage(ancestor)
    free = usage.free

    if free < required:
        def _fmt(b: int) -> str:
            val = float(b)
            for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
                if val < 1024 or unit == "TiB":
                    return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
                val /= 1024
            return f"{b} B"

        raise InsufficientSpaceError(
            f"Insufficient free space on destination: required {_fmt(required)} ({required} bytes), "
            f"available {_fmt(free)} ({free} bytes)"
        )

    return {"checked": True, "required_bytes": required, "free_bytes": free}


def plan_organization(
    options: OrganizeOptions,
    progress: Callable[[ProgressEvent], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[
    list[OrganizedItem],
    list[FileRecord],
    Counter[str],
    list[dict[str, str]],
    bool,
    bool,
]:
    input_root = options.input_root
    output_root = options.output_root
    stats: Counter[str] = Counter()
    for r in SKIP_REASONS:
        stats[f"skip_{r}"] = 0
    stats["existing_output_conflicts"] = 0

    if progress:
        progress(
            ProgressEvent(
                stage="discover",
                done=0,
                total=None,
                message="Scanning input directory...",
            )
        )

    candidates, hidden_files, excluded_dirs = scan_candidates(
        input_root, output_root, options, cancel_event
    )

    if cancel_event is not None and cancel_event.is_set():
        if progress:
            progress(
                ProgressEvent(
                    stage="discover",
                    done=len(candidates),
                    total=len(candidates),
                    message="Cancelled during discover",
                )
            )
        return [], [], stats, excluded_dirs, False, True

    if progress:
        progress(
            ProgressEvent(
                stage="discover",
                done=len(candidates),
                total=len(candidates),
                message=f"Found {len(candidates)} candidate files",
            )
        )

    # Stage: read
    total_candidates = len(candidates)
    if progress:
        progress(
            ProgressEvent(
                stage="read",
                done=0,
                total=total_candidates,
                message="Reading headers...",
            )
        )

    dicom_tag_specs = parse_dicom_tag_specs(options.dicom_tags)
    pending_sources: list[tuple[Path, dict[str, Any], str, tuple[Any, ...], FileRecord]] = []
    seen_sop_trackers: dict[str, _SopTracker] = {}
    file_records: list[FileRecord] = []
    limit_reached = False
    read_count = 0

    for i, source in enumerate(candidates, 1):
        read_count = i
        if cancel_event is not None and cancel_event.is_set():
            if progress:
                progress(
                    ProgressEvent(
                        stage="read",
                        done=i - 1,
                        total=total_candidates,
                        message="Cancelled during read",
                    )
                )
            return [], file_records, stats, excluded_dirs, False, True

        stats["candidate_files"] += 1
        try:
            size_bytes = source.stat().st_size
        except OSError:
            size_bytes = None

        read_result = classify_dicom_file(source, force=options.force_read)
        if read_result.reason != "N/A":
            stats[f"skip_{read_result.reason}"] += 1
            if read_result.reason == "not_dicom":
                stats["skipped_non_dicom"] += 1
            if options.verbose:
                print(
                    f"[skip] {read_result.reason}: {source} ({read_result.detail})",
                    file=sys.stderr,
                )
            file_records.append(
                FileRecord(
                    source=source,
                    status="skipped",
                    reason=read_result.reason,
                    detail=read_result.detail,
                    size_bytes=size_bytes,
                )
            )
            if progress:
                progress(ProgressEvent(stage="read", done=i, total=total_candidates))
            continue

        ds = read_result.dataset
        assert ds is not None
        sop_uid = ds_value(ds, "SOPInstanceUID")
        series_uid = ds_value(ds, "SeriesInstanceUID")
        modality = ds_value(ds, "Modality")

        # Duplicate SOPInstanceUID check
        is_identical_dup = False
        is_conflict_dup = False
        duplicate_of: Path | None = None
        curr_sha: str | None = None

        if sop_uid in seen_sop_trackers:
            tracker = seen_sop_trackers[sop_uid]
            if not tracker.hashes:
                first_sha = compute_sha256(tracker.first_source)
                tracker.first_record.sha256 = first_sha
                tracker.hashes[first_sha] = tracker.first_source
            curr_sha = compute_sha256(source)
            if curr_sha in tracker.hashes:
                is_identical_dup = True
                duplicate_of = tracker.hashes[curr_sha]
            else:
                is_conflict_dup = True
                tracker.hashes[curr_sha] = source
                duplicate_of = tracker.first_source
        if is_identical_dup:
            stats["skip_duplicate_identical"] += 1
            file_records.append(
                FileRecord(
                    source=source,
                    status="skipped",
                    reason="duplicate_identical",
                    detail="identical SOPInstanceUID and content",
                    duplicate_of=duplicate_of,
                    sop_instance_uid=sop_uid,
                    series_uid=series_uid,
                    modality=modality,
                    size_bytes=size_bytes,
                    sha256=curr_sha if curr_sha is not None else "N/A",
                )
            )
            if progress:
                progress(ProgressEvent(stage="read", done=i, total=total_candidates))
            continue

        item_index = stats["dicom_files"] + 1
        context = file_context(
            ds,
            item_index,
            options.patient_mode,
            input_root,
            source,
            dicom_tag_specs,
        )
        study_date = context["study_date"]
        device_folder = context["device_folder"]
        study_folder = compute_study_folder(
            options.layout,
            device_folder,
            study_date,
            context["study_key"],
            context["patient_key"],
        )

        filename = safe_name(format_template(options.file_template, context, "file"))

        rec = FileRecord(
            source=source,
            status="planned" if options.dry_run else ("listed" if options.list_only else "organized"),
            reason="duplicate_conflict" if is_conflict_dup else "N/A",
            detail="duplicate SOPInstanceUID with different content"
            if is_conflict_dup
            else "N/A",
            duplicate_of=duplicate_of,
            sop_instance_uid=sop_uid,
            series_uid=series_uid,
            modality=modality,
            size_bytes=size_bytes,
            sha256=curr_sha if curr_sha is not None else "N/A",
        )
        if sop_uid not in seen_sop_trackers:
            seen_sop_trackers[sop_uid] = _SopTracker(first_source=source, first_record=rec)
        if is_conflict_dup:
            stats["duplicate_conflicts"] += 1

        pending_sources.append(
            (
                source,
                context,
                filename,
                (study_folder, context["series_uid"]),
                rec,
                study_folder,
            )
        )
        file_records.append(rec)
        stats["dicom_files"] += 1

        if progress:
            progress(ProgressEvent(stage="read", done=i, total=total_candidates))

        if options.limit and stats["dicom_files"] >= options.limit:
            limit_reached = True
            break

    # Add hidden files to file_records
    for hidden in hidden_files:
        try:
            h_size = hidden.stat().st_size
        except OSError:
            h_size = None
        stats["skip_excluded_hidden"] += 1
        file_records.append(
            FileRecord(
                source=hidden,
                status="skipped",
                reason="excluded_hidden",
                detail="hidden file excluded by default",
                size_bytes=h_size,
            )
        )

    if progress:
        if limit_reached:
            progress(
                ProgressEvent(
                    stage="read",
                    done=read_count,
                    total=read_count,
                    message=f"Limit of {options.limit} files reached",
                )
            )
        else:
            progress(
                ProgressEvent(
                    stage="read",
                    done=total_candidates,
                    total=total_candidates,
                    message="Read completed",
                )
            )

    # Stage: plan
    if progress:
        progress(
            ProgressEvent(
                stage="plan",
                done=0,
                total=len(pending_sources),
                message="Planning destinations...",
            )
        )

    if cancel_event is not None and cancel_event.is_set():
        if progress:
            progress(
                ProgressEvent(
                    stage="plan",
                    done=0,
                    total=len(pending_sources),
                    message="Cancelled before planning",
                )
            )
        return [], file_records, stats, excluded_dirs, limit_reached, True

    pending_assignments = resolved_series_assignments(
        [(s, c, f, k) for s, c, f, k, _r, _sf in pending_sources]
    )
    pending: list[tuple[Path, dict[str, Any], str, tuple[Any, ...], FileRecord, str]] = []
    series_order: list[tuple[Any, ...]] = []
    base_dir_by_series: dict[tuple[Any, ...], Path] = {}
    for (
        source,
        context,
        filename,
        _base_series_key,
        rec,
        study_folder,
    ), (series_key, series_context) in zip(pending_sources, pending_assignments):
        series_template_context = dict(context)
        series_template_context.update(series_context)
        series_dir_name = safe_name(
            format_template(options.series_dir_template, series_template_context, "series-dir")
        )
        base_dir = ensure_within_output_root(
            output_root,
            output_root / study_folder / series_dir_name,
        )
        if series_key not in base_dir_by_series:
            base_dir_by_series[series_key] = base_dir
            series_order.append(series_key)
        pending.append((source, context, filename, series_key, rec, study_folder))

    series_dirs = assign_series_dirs(base_dir_by_series, series_order)
    seen_destinations: set[Path] = set()
    items: list[OrganizedItem] = []

    for source, context, filename, series_key, rec, study_folder in pending:
        destination = series_dirs[series_key] / filename
        series_folder_rel = series_dirs[series_key].relative_to(output_root).as_posix()
        study_folder_rel = Path(study_folder).as_posix()

        if options.list_only:
            if destination in seen_destinations:
                resolved = suffixed_path(destination, seen_destinations)
            else:
                resolved = destination
            seen_destinations.add(resolved)
            rec.destination = None
            rec.status = "planned" if options.dry_run else "listed"
            row = dict(context["row"])
            row["OrganizedFileName"] = "N/A"
            row["StudyFolder"] = study_folder_rel
            row["SeriesFolder"] = series_folder_rel
            items.append(OrganizedItem(source=source, destination=resolved, row=row))
            continue

        resolved = resolve_collision(
            destination,
            seen_destinations,
            options.if_exists,
            dry_run=options.dry_run,
        )
        if resolved is None:
            stats["skipped_existing"] += 1
            stats["skip_existing_output"] += 1
            rec.status = "skipped"
            rec.reason = "existing_output"
            rec.detail = "destination already exists and if_exists is skip"
            rec.destination = destination
            continue

        resolved = ensure_within_output_root(output_root, resolved)
        seen_destinations.add(resolved)
        rec.destination = resolved
        row = dict(context["row"])
        row["OrganizedFileName"] = resolved.relative_to(output_root).as_posix()
        row["StudyFolder"] = study_folder_rel
        row["SeriesFolder"] = series_folder_rel
        items.append(OrganizedItem(source=source, destination=resolved, row=row))

        if options.dry_run and options.if_exists == "error":
            if resolved.exists() or resolved.is_symlink():
                stats["existing_output_conflicts"] += 1
                rec.detail = "destination already exists in output folder"

    if progress:
        progress(
            ProgressEvent(
                stage="plan",
                done=len(items),
                total=len(items),
                message=f"Planned {len(items)} files",
            )
        )

    return items, file_records, stats, excluded_dirs, limit_reached, False


def build_items(
    args: argparse.Namespace | OrganizeOptions,
) -> tuple[list[OrganizedItem], Counter[str]]:
    options = normalize_options(args)
    items, _records, stats, _excluded, _limit, _cancelled = plan_organization(options)
    return items, stats


def existing_metadata_rows(
    csv_path: Path, output_root: Path, replaced_names: set[str]
) -> list[dict[str, str]]:
    if not csv_path.exists():
        return []
    rows: list[dict[str, str]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            name = (raw.get("OrganizedFileName") or "").strip()
            if not name or name in replaced_names:
                continue                      # Will be replaced by current rows
            target = output_root / name
            if not (target.exists() or target.is_symlink()):
                continue                      # Drop rows whose target no longer exists
            row = {key: (value or "N/A") for key, value in raw.items() if key}
            if row.get("SeriesFolder", "N/A") == "N/A" and name:
                parts = name.split("/")
                if len(parts) >= 2:
                    row["SeriesFolder"] = "/".join(parts[:-1])
                if len(parts) >= 3 and row.get("StudyFolder", "N/A") == "N/A":
                    row["StudyFolder"] = "/".join(parts[:-2])
            rows.append(row)
    return rows


def write_metadata_tables(
    output_root: Path,
    items: list[OrganizedItem],
    profile_name: str,
    extra_metadata_columns: list[str] | None = None,
) -> None:
    by_dir: dict[Path, list[OrganizedItem]] = defaultdict(list)
    for item in items:
        by_dir[item.destination.parent.parent].append(item)

    for group_dir, group_items in sorted(by_dir.items(), key=lambda x: str(x[0])):
        ensure_within_output_root(output_root, group_dir)
        group_dir.mkdir(parents=True, exist_ok=True)
        replaced_names = {item.row["OrganizedFileName"] for item in group_items}
        existing_rows = existing_metadata_rows(
            group_dir / "dicom_parameters.csv", output_root, replaced_names
        )
        combined_rows = [item.row for item in group_items] + existing_rows
        rows = sorted(
            combined_rows,
            key=lambda row: (
                str(row.get("SeriesNumber", "")),
                int(row["InstanceNumber"])
                if str(row.get("InstanceNumber", "")).isdigit()
                else 0,
                str(row.get("OrganizedFileName", "")),
            ),
        )
        profile_rows = add_series_aggregates(metadata_rows(rows, profile_name))
        write_csv(
            group_dir / "dicom_parameters.csv",
            metadata_columns_for_profile(profile_name, profile_rows, extra_metadata_columns),
            profile_rows,
        )
        write_csv(
            group_dir / "series_summary.csv",
            summary_columns_for_profile(
                profile_name,
                profile_rows,
                extra_metadata_columns,
            ),
            build_series_summary(
                profile_rows,
                profile_name,
                extra_metadata_columns,
            ),
        )
    write_all_series_summary(output_root)


def write_all_series_summary(output_root: Path) -> Path | None:
    summary_files = sorted(
        [
            p
            for p in output_root.rglob("series_summary.csv")
            if p.is_file() and p.name == "series_summary.csv"
        ],
        key=lambda p: p.as_posix(),
    )
    if not summary_files:
        return None

    all_rows: list[dict[str, str]] = []
    seen_columns: list[str] = ["StudyFolder", "SeriesFolder"]
    known_cols_set = set(seen_columns)

    for summary_path in summary_files:
        study_folder_default = summary_path.parent.relative_to(output_root).as_posix()
        with summary_path.open(encoding="utf-8-sig", newline="") as h:
            reader = csv.DictReader(h)
            for col in reader.fieldnames or []:
                if col not in known_cols_set:
                    seen_columns.append(col)
                    known_cols_set.add(col)
            for raw_row in reader:
                row = dict(raw_row)
                if not row.get("StudyFolder") or row["StudyFolder"] == "N/A":
                    row["StudyFolder"] = study_folder_default
                if not row.get("SeriesFolder") or row["SeriesFolder"] == "N/A":
                    org_file = row.get("OrganizedFileName", "")
                    if org_file and org_file != "N/A":
                        row["SeriesFolder"] = "/".join(org_file.split("/")[:-1])
                    else:
                        row["SeriesFolder"] = study_folder_default
                all_rows.append(row)

    out_path = output_root / "all_series_summary.csv"
    write_csv(out_path, seen_columns, all_rows)
    return out_path


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", restval="N/A")
        writer.writeheader()
        writer.writerows(rows)


def series_value(series_rows: list[dict[str, str]], column: str) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for row in series_rows:
        value = row.get(column, "N/A")
        if not value or value == "N/A" or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return "|".join(values) if values else "N/A"


def series_group_key(row: dict[str, str]) -> str:
    folder = row.get("SeriesFolder", "")
    if folder and folder != "N/A":
        return folder
    return row.get("OrganizedFileName", "").rsplit("/", 1)[0]


def add_series_aggregates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Repeat series aggregates on parameter rows so both CSVs share one source."""
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[series_group_key(row)].append(row)

    aggregates: dict[str, dict[str, str]] = {}
    for series_key, series_rows in grouped.items():
        echo_times = sorted(
            {
                row.get("TE_ms", "N/A")
                for row in series_rows
                if row.get("TE_ms", "N/A") != "N/A"
            },
            key=natural_key,
        )
        coil_elements = sorted(
            {
                row.get("SiemensCoilElement", "N/A")
                for row in series_rows
                if row.get("SiemensCoilElement", "N/A") != "N/A"
            },
            key=natural_key,
        )
        is_mr = any(row_profile_name(row) == "mr" for row in series_rows)
        aggregates[series_key] = {
            "FileCount": str(len(series_rows)),
            "EchoCount": str(len(echo_times)) if is_mr else "N/A",
            "EchoTimes_ms": "|".join(echo_times) if echo_times else "N/A",
            "CoilElementCount": str(len(coil_elements)) if is_mr else "N/A",
            "CoilElements": "|".join(coil_elements) if coil_elements else "N/A",
        }

    enriched_rows: list[dict[str, str]] = []
    for row in rows:
        enriched_row = dict(row)
        enriched_row.update(aggregates[series_group_key(row)])
        enriched_rows.append(enriched_row)
    return enriched_rows


def build_series_summary(
    rows: list[dict[str, str]],
    profile_name: str = "auto",
    extra_metadata_columns: list[str] | None = None,
) -> list[dict[str, str]]:
    rows = add_series_aggregates(metadata_rows(rows, profile_name))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[series_group_key(row)].append(row)

    columns = summary_columns_for_profile(profile_name, rows, extra_metadata_columns)
    summaries: list[dict[str, str]] = []
    for _series_dir, series_rows in sorted(
        grouped.items(),
        key=lambda item: (
            str(item[1][0].get("StudyFolder", "")),
            str(item[1][0].get("SeriesNumber", "")),
            item[0],
        ),
    ):
        summaries.append({column: series_value(series_rows, column) for column in columns})
    return summaries


def natural_key(value: str) -> tuple[int, float | str]:
    try:
        return (0, float(value))
    except ValueError:
        return (1, value)


def write_run_summary(
    output_root: Path,
    items: list[OrganizedItem],
    stats: Counter[str],
    options: OrganizeOptions,
    started_at: str,
    ended_at: str,
    *,
    status: str = "completed",
    error: str | None = None,
    planned_files: int | None = None,
    not_processed_files: int = 0,
    excluded_directories: list[dict[str, str]] | None = None,
    limit_reached: bool = False,
    space_check_info: dict[str, Any] | None = None,
    previous_run_status: str | None = None,
    warnings_list: list[str] | None = None,
    reports: list[str] | None = None,
) -> None:
    by_series = Counter(
        item.row.get(
            "SeriesFolder",
            item.destination.parent.relative_to(output_root).as_posix()
            if item.destination is not None
            else "N/A",
        )
        for item in items
    )
    by_date = Counter(item.row["AcquisitionDate"] for item in items)
    group_folders = Counter(
        item.row.get(
            "StudyFolder",
            item.destination.parent.parent.relative_to(output_root).as_posix()
            if item.destination is not None
            else "N/A",
        )
        for item in items
    )
    study_count = len(
        {
            item.row.get("StudyInstanceUID")
            for item in items
            if item.row.get("StudyInstanceUID") and item.row.get("StudyInstanceUID") != "N/A"
        }
    )
    summary_counts = summarize_items(
        items,
        stats,
        output_root,
        options.profile,
        status=status,
        list_only=options.list_only,
    )

    skipped_by_reason: dict[str, int] = {}
    for reason in SKIP_REASONS:
        count = stats.get(f"skip_{reason}", 0)
        if count > 0:
            skipped_by_reason[reason] = count

    summary = {
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "software": {
            "name": "dicom-organizer",
            "version": package_version(),
            "python": sys.version.split()[0],
            "pydicom": pydicom.__version__,
            "platform": platform.platform(),
        },
        "options": {
            "action": options.action,
            "if_exists": options.if_exists,
            "dry_run": options.dry_run,
            "force_read": options.force_read,
            "include_hidden": options.include_hidden,
            "include_organized": options.include_organized,
            "limit": options.limit,
            "series_dir_template": options.series_dir_template,
            "file_template": options.file_template,
            "profile": options.profile,
            "patient_mode": options.patient_mode,
            "dicom_tags": list(options.dicom_tags),
            "checksum": options.checksum,
            "space_check": options.space_check,
            "list_only": options.list_only,
            "layout": options.layout,
        },
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "error": error,
        "checksum": options.checksum,
        "input_root": str(options.input_root),
        "output_root": str(output_root),
        "action": options.action,
        "if_exists": options.if_exists,
        "force_read": options.force_read,
        "profile": options.profile,
        "patient_mode": options.patient_mode,
        "dicom_tags": list(options.dicom_tags),
        "candidate_files": stats["candidate_files"],
        "planned_files": planned_files if planned_files is not None else len(items),
        "organized_files": 0 if options.list_only else len(items),
        "not_processed_files": not_processed_files,
        "csv_target_files": summary_counts["csv_target_files"],
        "csv_excluded_files": summary_counts["csv_excluded_files"],
        "csv_excluded_non_image_files": summary_counts["csv_excluded_non_image_files"],
        "organized_files_by_modality": summary_counts["organized_files_by_modality"],
        "csv_target_files_by_modality": summary_counts["csv_target_files_by_modality"],
        "csv_excluded_files_by_modality": summary_counts["csv_excluded_files_by_modality"],
        "skipped_by_reason": skipped_by_reason,
        "skipped_non_dicom": skipped_by_reason.get("not_dicom", 0),
        "skipped_existing": stats["skipped_existing"],
        "duplicate_conflicts": stats.get("duplicate_conflicts", 0),
        "existing_output_conflicts": stats.get("existing_output_conflicts", 0),
        "excluded_directories": excluded_directories or [],
        "limit_reached": limit_reached,
        "space_check": space_check_info
        or {"checked": False, "required_bytes": None, "free_bytes": None},
        "previous_run_status": previous_run_status,
        "warnings": warnings_list or [],
        "privacy_notices": patient_data_notices(options),
        "reports": reports or [],
        "layout": options.layout,
        "group_folders": dict(sorted(group_folders.items())),
        "study_count": study_count,
        "device_dates": dict(sorted(group_folders.items())),
        "acquisition_dates": dict(sorted(by_date.items())),
        "series_count": len(by_series),
    }
    if options.list_only:
        summary["list_only"] = True
        summary["listed_files"] = len(items)

    path = ensure_within_output_root(output_root, output_root / "organize_summary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def summarize_items(
    items: list[OrganizedItem],
    stats: Counter[str],
    output_root: Path,
    profile_name: str = "auto",
    status: str = "completed",
    list_only: bool = False,
) -> dict[str, Any]:
    by_date = Counter(item.row["AcquisitionDate"] for item in items)
    group_folders = Counter(
        item.row.get(
            "StudyFolder",
            item.destination.parent.parent.relative_to(output_root).as_posix()
            if item.destination is not None
            else "N/A",
        )
        for item in items
    )
    by_series = Counter(
        item.row.get(
            "SeriesFolder",
            item.destination.parent.relative_to(output_root).as_posix()
            if item.destination is not None
            else "N/A",
        )
        for item in items
    )
    study_count = len(
        {
            item.row.get("StudyInstanceUID")
            for item in items
            if item.row.get("StudyInstanceUID") and item.row.get("StudyInstanceUID") != "N/A"
        }
    )
    rows = [item.row for item in items]
    csv_target_rows = metadata_rows(rows, profile_name)
    csv_target_row_ids = {id(row) for row in csv_target_rows}
    csv_excluded_rows = [row for row in rows if id(row) not in csv_target_row_ids]
    csv_target_files = len(csv_target_rows)
    csv_excluded_files = len(items) - csv_target_files

    skipped_by_reason: dict[str, int] = {}
    for reason in SKIP_REASONS:
        count = stats.get(f"skip_{reason}", 0)
        if count > 0:
            skipped_by_reason[reason] = count

    res: dict[str, Any] = {
        "candidate_files": stats["candidate_files"],
        "organized_files": 0 if list_only else len(items),
        "csv_target_files": csv_target_files,
        "csv_excluded_files": csv_excluded_files,
        "csv_excluded_non_image_files": csv_excluded_files,
        "organized_files_by_modality": modality_counts(rows),
        "csv_target_files_by_modality": modality_counts(csv_target_rows),
        "csv_excluded_files_by_modality": modality_counts(csv_excluded_rows),
        "series_count": len(by_series),
        "skipped_non_dicom": skipped_by_reason.get("not_dicom", 0),
        "skipped_existing": stats["skipped_existing"],
        "skipped_by_reason": skipped_by_reason,
        "duplicate_conflicts": stats.get("duplicate_conflicts", 0),
        "existing_output_conflicts": stats.get("existing_output_conflicts", 0),
        "status": status,
        "group_folders": dict(sorted(group_folders.items())),
        "study_count": study_count,
        "device_dates": dict(sorted(group_folders.items())),
        "acquisition_dates": dict(sorted(by_date.items())),
        "output_root": str(output_root),
        "profile": profile_name,
    }
    if list_only:
        res["list_only"] = True
        res["listed_files"] = len(items)
    return res


def planned_metadata_outputs(output_root: Path, items: list[OrganizedItem]) -> list[str]:
    outputs: list[str] = []
    group_dirs = sorted({item.destination.parent.parent for item in items}, key=lambda p: str(p))
    for group_dir in group_dirs:
        outputs.append((group_dir / "dicom_parameters.csv").as_posix())
        outputs.append((group_dir / "series_summary.csv").as_posix())
    outputs.append((output_root / "organize_summary.json").as_posix())
    return outputs


def format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "(none)"
    return ",".join(f"{key}={value}" for key, value in counts.items())


def print_summary(
    items: list[OrganizedItem],
    stats: Counter[str],
    output_root: Path,
    profile_name: str = "auto",
    *,
    dry_run: bool = False,
    status: str = "completed",
) -> None:
    summary = summarize_items(items, stats, output_root, profile_name, status=status)
    print(f"status={summary['status']}")
    print(f"profile={summary['profile']}")
    print(f"candidate_files={summary['candidate_files']}")
    print(f"organized_files={summary['organized_files']}")
    print(f"csv_target_files={summary['csv_target_files']}")
    print(f"csv_excluded_non_image_files={summary['csv_excluded_non_image_files']}")
    print(
        "organized_files_by_modality="
        f"{format_counts(summary['organized_files_by_modality'])}"
    )
    print(
        "csv_target_files_by_modality="
        f"{format_counts(summary['csv_target_files_by_modality'])}"
    )
    print(
        "csv_excluded_files_by_modality="
        f"{format_counts(summary['csv_excluded_files_by_modality'])}"
    )
    print(f"series_count={summary['series_count']}")
    print(f"skipped_non_dicom={summary['skipped_non_dicom']}")
    print(f"skipped_existing={summary['skipped_existing']}")
    print(f"skipped_by_reason={format_counts(summary.get('skipped_by_reason', {}))}")
    print(f"duplicate_conflicts={summary.get('duplicate_conflicts', 0)}")
    for device_date, count in summary.get("device_dates", {}).items():
        print(f"{device_date}: files={count}")
    print(f"output_root={output_root}")
    if dry_run and items:
        print("planned_metadata_outputs:")
        for output in planned_metadata_outputs(output_root, items):
            print(f"  {output}")


def make_cli_progress() -> Callable[[ProgressEvent], None]:
    import time

    last_update = 0.0
    last_stage: str | None = None

    def _progress(event: ProgressEvent) -> None:
        nonlocal last_update, last_stage
        now = time.monotonic()
        if event.stage != last_stage:
            if last_stage is not None:
                sys.stderr.write("\n")
            last_stage = event.stage
            last_update = 0.0

        is_terminal = (event.total is not None and event.done == event.total) or event.done == 0
        if not is_terminal and (now - last_update < 0.1):
            return
        last_update = now

        if event.total is not None:
            msg = f"[{event.stage}] {event.done}/{event.total}"
        else:
            msg = f"[{event.stage}] {event.done}"
        sys.stderr.write(f"\r{msg}")
        sys.stderr.flush()
        if (
            event.total is not None
            and event.done == event.total
            and event.stage in ("copy", "write")
        ):
            sys.stderr.write("\n")
            sys.stderr.flush()

    return _progress


def run(
    args: argparse.Namespace | OrganizeOptions,
    *,
    dry_run: bool | None = None,
    progress: Callable[[ProgressEvent], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> OrganizeResult:
    options = normalize_options(args, dry_run=dry_run, validate=True)
    started_at = datetime.now(timezone.utc).isoformat()

    # Check previous run
    previous_run_status, prev_warnings = check_previous_run(options.output_root)
    warnings_list = list(prev_warnings)
    notices = patient_data_notices(options)

    if options.patient_mode != "keep" and options.dicom_tags:
        for tag_str in options.dicom_tags:
            raw_tag = tag_str.split("=", 1)[-1].strip() if "=" in tag_str else tag_str.strip()
            try:
                parsed_tag = parse_dicom_tag(raw_tag)
                kw = keyword_for_tag(parsed_tag) or raw_tag
            except Exception:
                kw = raw_tag
            if kw in DIRECT_IDENTIFIER_TAGS or raw_tag in DIRECT_IDENTIFIER_TAGS:
                warnings_list.append(
                    f"Custom DICOM tag '{tag_str}' ({kw}) may contain direct patient identifiers "
                    f"and will be written verbatim to metadata CSV files regardless of --patient-mode {options.patient_mode}."
                )

    items, file_records, stats, excluded_dirs, limit_reached, cancelled = plan_organization(
        options, progress=progress, cancel_event=cancel_event
    )

    if cancelled:
        ended_at = datetime.now(timezone.utc).isoformat()
        return OrganizeResult(
            items=[],
            stats=stats,
            output_root=options.output_root,
            started_at=started_at,
            ended_at=ended_at,
            dry_run=options.dry_run,
            profile=options.profile,
            status="cancelled",
            file_records=file_records,
            warnings=warnings_list,
            previous_run_status=previous_run_status,
            list_only=options.list_only,
            privacy_notices=notices,
        )

    if options.dry_run:
        if stats.get("existing_output_conflicts", 0) > 0:
            n = stats["existing_output_conflicts"]
            warnings_list.append(
                f"{n} planned file(s) already exist at destination; real execution with --if-exists error "
                "will abort on the first existing file. Re-run with --if-exists skip to continue into an "
                "existing output folder, or use overwrite/rename."
            )
        ended_at = datetime.now(timezone.utc).isoformat()
        return OrganizeResult(
            items=items,
            stats=stats,
            output_root=options.output_root,
            started_at=started_at,
            ended_at=ended_at,
            dry_run=True,
            profile=options.profile,
            status="dry_run",
            file_records=file_records,
            warnings=warnings_list,
            previous_run_status=previous_run_status,
            list_only=options.list_only,
            privacy_notices=notices,
        )

    if options.list_only:
        if progress:
            progress(ProgressEvent(stage="write", done=0, total=None, message="Writing reports..."))

        options.output_root.mkdir(parents=True, exist_ok=True)
        extra_cols = [spec.column for spec in parse_dicom_tag_specs(options.dicom_tags)]
        all_rows = sorted(
            [item.row for item in items],
            key=lambda row: (
                str(row.get("StudyFolder", "")),
                str(row.get("SeriesNumber", "")),
                str(row.get("SeriesFolder", "")),
                int(row["InstanceNumber"])
                if str(row.get("InstanceNumber", "")).isdigit()
                else 0,
                str(row.get("SourceFileName", "")),
            ),
        )
        profile_rows = add_series_aggregates(metadata_rows(all_rows, options.profile))
        write_csv(
            options.output_root / "all_dicom_parameters.csv",
            metadata_columns_for_profile(options.profile, profile_rows, extra_cols),
            profile_rows,
        )
        write_csv(
            options.output_root / "all_series_summary.csv",
            summary_columns_for_profile(options.profile, profile_rows, extra_cols),
            build_series_summary(profile_rows, options.profile, extra_cols),
        )
        write_file_report(options.output_root, options.input_root, file_records)
        reports_list = [
            "all_dicom_parameters.csv",
            "all_series_summary.csv",
            "file_report.csv",
            "organize_summary.json",
        ]
        ended_at = datetime.now(timezone.utc).isoformat()
        write_run_summary(
            options.output_root,
            items,
            stats,
            options,
            started_at,
            ended_at,
            status="completed",
            error=None,
            planned_files=len(items),
            not_processed_files=0,
            excluded_directories=excluded_dirs,
            limit_reached=limit_reached,
            space_check_info=None,
            previous_run_status=previous_run_status,
            warnings_list=warnings_list,
            reports=reports_list,
        )
        if progress:
            progress(
                ProgressEvent(
                    stage="write",
                    done=1,
                    total=1,
                    message="Reports written successfully",
                )
            )
        return OrganizeResult(
            items=items,
            stats=stats,
            output_root=options.output_root,
            started_at=started_at,
            ended_at=ended_at,
            dry_run=False,
            profile=options.profile,
            status="completed",
            file_records=file_records,
            warnings=warnings_list,
            previous_run_status=previous_run_status,
            list_only=True,
            privacy_notices=notices,
        )

    space_check_info = check_free_space(
        items,
        options.output_root,
        options.input_root,
        options.action,
        options.space_check,
    )

    planned_files = len(items)
    records_by_dest = {rec.destination: rec for rec in file_records if rec.destination is not None}

    # Write initial "running" summary
    write_run_summary(
        options.output_root,
        [],
        stats,
        options,
        started_at,
        "",
        status="running",
        planned_files=planned_files,
        not_processed_files=planned_files,
        excluded_directories=excluded_dirs,
        limit_reached=limit_reached,
        space_check_info=space_check_info,
        previous_run_status=previous_run_status,
        warnings_list=warnings_list,
    )

    total_items = len(items)
    if progress:
        progress(ProgressEvent(stage="copy", done=0, total=total_items, message="Placing files..."))

    placed_items: list[OrganizedItem] = []
    run_status = "completed"
    records_placed: set[Path] = set()

    def _mark_remaining(reason: str):
        for item in items[len(placed_items):]:
            rec = records_by_dest.get(item.destination)
            if rec is not None and rec.source not in records_placed:
                rec.status = "not_processed"
                rec.reason = reason
                rec.detail = f"processing was {reason} before this file could be placed"

    def _write_partial(st: str, err: str | None = None):
        try:
            write_metadata_tables(
                options.output_root,
                placed_items,
                options.profile,
                extra_metadata_columns=[
                    spec.column for spec in parse_dicom_tag_specs(options.dicom_tags)
                ],
            )
            write_file_report(options.output_root, options.input_root, file_records)
            reports_list = collect_reports(options.output_root, placed_items)
            write_run_summary(
                options.output_root,
                placed_items,
                stats,
                options,
                started_at,
                datetime.now(timezone.utc).isoformat(),
                status=st,
                error=err,
                planned_files=planned_files,
                not_processed_files=planned_files - len(placed_items),
                excluded_directories=excluded_dirs,
                limit_reached=limit_reached,
                space_check_info=space_check_info,
                previous_run_status=previous_run_status,
                warnings_list=warnings_list,
                reports=reports_list,
            )
        except Exception:
            pass

    try:
        for idx, item in enumerate(items, 1):
            if cancel_event is not None and cancel_event.is_set():
                run_status = "cancelled"
                _mark_remaining("cancelled")
                _write_partial("cancelled")
                if progress:
                    progress(
                        ProgressEvent(
                            stage="copy",
                            done=len(placed_items),
                            total=total_items,
                            message="Cancelled during copy",
                        )
                    )
                break

            item.destination.parent.mkdir(parents=True, exist_ok=True)
            sha256 = materialize(
                item.source,
                item.destination,
                action=options.action,
                overwrite=(options.if_exists == "overwrite"),
                checksum=options.checksum,
            )
            rec = records_by_dest.get(item.destination)
            if rec is not None:
                if sha256 != "N/A":
                    rec.sha256 = sha256
                records_placed.add(rec.source)

            placed_items.append(item)
            if progress and idx < total_items:
                progress(ProgressEvent(stage="copy", done=idx, total=total_items))

    except KeyboardInterrupt:
        _mark_remaining("interrupted")
        _write_partial("interrupted")
        raise
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        _mark_remaining("failed")
        _write_partial("failed", error_msg)
        raise

    if run_status != "cancelled" and progress:
        progress(
            ProgressEvent(
                stage="copy",
                done=len(placed_items),
                total=total_items,
                message="Copy completed",
            )
        )

    ended_at = datetime.now(timezone.utc).isoformat()

    if run_status == "cancelled":
        return OrganizeResult(
            items=placed_items,
            stats=stats,
            output_root=options.output_root,
            started_at=started_at,
            ended_at=ended_at,
            dry_run=False,
            profile=options.profile,
            status="cancelled",
            file_records=file_records,
            warnings=warnings_list,
            previous_run_status=previous_run_status,
            privacy_notices=notices,
        )

    if progress:
        progress(ProgressEvent(stage="write", done=0, total=None, message="Writing reports..."))

    write_metadata_tables(
        options.output_root,
        placed_items,
        options.profile,
        extra_metadata_columns=[
            spec.column for spec in parse_dicom_tag_specs(options.dicom_tags)
        ],
    )
    write_file_report(options.output_root, options.input_root, file_records)
    reports_list = collect_reports(options.output_root, placed_items)
    write_run_summary(
        options.output_root,
        placed_items,
        stats,
        options,
        started_at,
        ended_at,
        status="completed",
        error=None,
        planned_files=planned_files,
        not_processed_files=0,
        excluded_directories=excluded_dirs,
        limit_reached=limit_reached,
        space_check_info=space_check_info,
        previous_run_status=previous_run_status,
        warnings_list=warnings_list,
        reports=reports_list,
    )

    if progress:
        progress(
            ProgressEvent(
                stage="write",
                done=1,
                total=1,
                message="Reports written successfully",
            )
        )

    return OrganizeResult(
        items=placed_items,
        stats=stats,
        output_root=options.output_root,
        started_at=started_at,
        ended_at=ended_at,
        dry_run=False,
        profile=options.profile,
        status="completed",
        file_records=file_records,
        warnings=warnings_list,
        previous_run_status=previous_run_status,
        privacy_notices=notices,
    )


def main() -> int:
    args = parse_args()
    progress_callback = None
    if getattr(args, "progress", True) and sys.stderr.isatty():
        progress_callback = make_cli_progress()

    try:
        result = run(args, progress=progress_callback)
    except KeyboardInterrupt:
        print(
            "Organization interrupted by user. If file placement had started, placed files and partial reports have been saved. "
            "Re-run with --if-exists skip to continue into an existing output folder.",
            file=sys.stderr,
        )
        return 130
    except InsufficientSpaceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except IntegrityError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Failed while scanning: {exc}", file=sys.stderr)
        return 1

    from dicom_organizer.messages import notice_text

    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if result.dry_run:
        for code in result.privacy_notices:
            print(notice_text(code, "en"), file=sys.stderr)
    elif not result.list_only and result.items:
        print(notice_text("dicom_files_unchanged", "en"), file=sys.stderr)

    if result.status == "cancelled":
        print("Organization was cancelled.", file=sys.stderr)
        return 1

    if not result.items:
        print("No DICOM files were organized.", file=sys.stderr)
        print_summary(
            result.items,
            result.stats,
            result.output_root,
            result.profile,
            dry_run=result.dry_run,
            status=result.status,
        )
        if result.stats["skipped_existing"] > 0:
            return 0
        return 1

    print_summary(
        result.items,
        result.stats,
        result.output_root,
        result.profile,
        dry_run=result.dry_run,
        status=result.status,
    )
    if result.dry_run:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
