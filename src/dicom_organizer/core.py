#!/usr/bin/env python3
"""Organize DICOM files into stable series directories.

The default output layout intentionally matches the older local organizer:

    organized/<AcquisitionDate>/<SeriesNumber>_<SeriesFolderLabel>/
        000001.dcm
        ...
    organized/<AcquisitionDate>/
        dicom_parameters.csv
        series_summary.csv
    organized/organize_summary.json

The script reads DICOM headers only, keeps source files untouched by default,
and writes metadata tables that are useful for later modality-specific analysis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    "SeriesUID",
    "SOPInstanceUID",
    "SeriesNumber",
    "SeriesDescription",
    "ProtocolName",
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
    "FrameOfReferenceUID",
    "StudyInstanceUID",
    "IsNormalized",
]

MR_METADATA_COLUMNS = [
    "TR_ms",
    "TE_ms",
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
    "SAR",
    "ReceiveCoilName",
    "MRAcquisitionType",
    "SiemensChannelMixing",
    "SiemensCoilElement",
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

COMMON_SUMMARY_COLUMNS = [
    "AcquisitionDate",
    "SeriesNumber",
    "SeriesUID",
    "SeriesUIDHash",
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
]

MR_SUMMARY_COLUMNS = [
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
    "ReceiveCoilName",
]

CT_SUMMARY_COLUMNS = [
    "KVP_kV",
    "XRayTubeCurrent_mA",
    "ExposureTime_ms",
    "ConvolutionKernel",
    "ReconstructionDiameter_mm",
]

US_SUMMARY_COLUMNS = [
    "TransducerData",
    "TransducerType",
    "MechanicalIndex",
    "ThermalIndex",
    "UltrasoundColorDataPresent",
]

XA_SUMMARY_COLUMNS = [
    "KVP_kV",
    "XRayTubeCurrent_mA",
    "ExposureTime_ms",
    "FrameTime_ms",
    "DistanceSourceToDetector_mm",
    "DistanceSourceToPatient_mm",
]

PT_SUMMARY_COLUMNS = [
    "Radiopharmaceutical",
    "RadionuclideTotalDose_Bq",
    "RadionuclideHalfLife_s",
    "DecayCorrection",
]

PROFILE_NAMES = ("auto", "generic", "mr", "ct", "us", "xa", "pt")

DEFAULT_SERIES_DIR_TEMPLATE = "{series_number}_{series_folder_label}"
DEFAULT_FILE_TEMPLATE = "{instance_number_6}.dcm"

ACTIONS = ("copy", "symlink", "hardlink", "move")
IF_EXISTS_MODES = ("error", "skip", "overwrite", "rename")
PATIENT_MODES = ("keep", "hash", "drop")


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
    force_read: bool = False
    include_hidden: bool = False
    include_organized: bool = False
    limit: int = 0
    series_dir_template: str = DEFAULT_SERIES_DIR_TEMPLATE
    file_template: str = DEFAULT_FILE_TEMPLATE
    profile: str = "auto"
    patient_mode: str = "keep"
    dicom_tags: tuple[str, ...] = ()
    verbose: bool = False


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

    @property
    def summary(self) -> dict[str, Any]:
        return summarize_items(self.items, self.stats, self.output_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize DICOM files by AcquisitionDate and SeriesInstanceUID."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input directory containing DICOM files.",
    )
    parser.add_argument(
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
        "--dry-run",
        action="store_true",
        help="Scan and summarize without writing output files.",
    )
    parser.add_argument(
        "--force-read",
        action="store_true",
        help="Pass force=True to pydicom.dcmread for non-standard files.",
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
        "--dicom-tag",
        "--tag",
        action="append",
        default=[],
        metavar="TAG",
        help=(
            "Also write this DICOM tag to dicom_parameters.csv. Repeatable. "
            "Accepts keywords such as EchoTime, numeric tags such as 0018,0081 "
            "or 0x00180081, and optional ColumnName=TAG."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print skipped files and per-series output while running.",
    )
    return parser.parse_args()


def normalize_options(
    args: argparse.Namespace | OrganizeOptions,
    *,
    dry_run: bool | None = None,
    validate: bool = False,
) -> OrganizeOptions:
    if isinstance(args, OrganizeOptions):
        options = replace(args, dry_run=dry_run) if dry_run is not None else args
    else:
        input_root = Path(args.input).expanduser().resolve()
        output_value = getattr(args, "output", None)
        output_root = (
            Path(output_value).expanduser().resolve()
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
            force_read=bool(getattr(args, "force_read", False)),
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
        )

    if validate:
        validate_options(options)
    return options


def validate_options(options: OrganizeOptions) -> None:
    if options.action not in ACTIONS:
        raise ValueError(f"Unsupported --action value: {options.action}")
    if options.if_exists not in IF_EXISTS_MODES:
        raise ValueError(f"Unsupported --if-exists value: {options.if_exists}")
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
    pending: list[tuple[Path, dict[str, Any], str, tuple[str, str]]],
) -> list[tuple[tuple[str, str, tuple[str, ...]], dict[str, str]]]:
    assignments: list[tuple[tuple[str, str, tuple[str, ...]], dict[str, str]]] = [
        (("", "", ()), {}) for _ in pending
    ]
    indices_by_series: dict[tuple[str, str], list[int]] = defaultdict(list)
    anchor_labels: dict[tuple[str, str, tuple[str, ...]], str] = {}

    anchor_candidates: dict[tuple[str, str, tuple[str, ...]], set[str]] = defaultdict(set)
    for _source, context, _filename, _base_series_key in pending:
        if not context["is_philips_mr"]:
            continue
        acquisition_number = context["acquisition_number"]
        if not acquisition_number or acquisition_number == "N/A":
            continue
        if is_numeric_series_label(context["raw_series_label"]):
            continue
        key = (
            context["acquisition_date"],
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
                anchor_key = (
                    context["acquisition_date"],
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
                (base_series_key[0], base_series_key[1], effective_reconstruction),
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


def summary_columns_for_profile(profile_name: str, rows: list[dict[str, str]]) -> list[str]:
    if profile_name == "generic":
        return list(COMMON_SUMMARY_COLUMNS)
    if profile_name == "auto":
        return merge_columns(
            COMMON_SUMMARY_COLUMNS,
            *(profile.summary_columns for profile in present_modality_profiles(rows)),
        )
    return merge_columns(COMMON_SUMMARY_COLUMNS, MODALITY_PROFILES[profile_name].summary_columns)


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

    row = {
        "SeriesUID": series_uid,
        "SOPInstanceUID": sop_uid,
        "SeriesNumber": series_number(ds),
        "SeriesDescription": series_description,
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
        "SAR": ds_value(ds, "SAR"),
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
        "ImageOrientationPatient": ds_value(ds, "ImageOrientationPatient"),
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

    return {
        "acquisition_date": ds_value(
            ds, "AcquisitionDate", default=ds_value(ds, "StudyDate", default="unknown_date")
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


def iter_candidate_files(input_root: Path, output_root: Path, options: OrganizeOptions):
    for root, dirnames, filenames in os.walk(input_root):
        root_path = Path(root)
        kept_dirnames = []
        for dirname in sorted(dirnames):
            dir_path = root_path / dirname
            if should_prune_dir(dir_path, input_root, output_root, options):
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            path = root_path / filename
            if should_skip(path, input_root, output_root, options):
                continue
            yield path


def should_prune_dir(
    path: Path,
    input_root: Path,
    output_root: Path,
    options: OrganizeOptions,
) -> bool:
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


def read_dicom_header(path: Path, force: bool) -> pydicom.dataset.Dataset | None:
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=force)
    except Exception:
        return None
    if not hasattr(ds, "SeriesInstanceUID") or not hasattr(ds, "SOPInstanceUID"):
        return None
    return ds


def format_template(template: str, context: dict[str, Any], label: str) -> str:
    try:
        return template.format(**context)
    except KeyError as exc:
        key = exc.args[0]
        raise ValueError(f"Unknown key in {label} template: {key}") from exc


def resolve_collision(path: Path, seen: set[Path], if_exists: str) -> Path | None:
    if path in seen:
        return suffixed_path(path, seen)
    if not path.exists():
        return path
    if if_exists == "error":
        raise FileExistsError(f"Target exists: {path}")
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


def resolve_series_dir(
    base_dir: Path,
    series_key: tuple[str, str],
    assigned_dirs: dict[tuple[str, str], Path],
    used_dirs: set[Path],
) -> Path:
    if series_key in assigned_dirs:
        return assigned_dirs[series_key]

    candidate = unique_series_dir(base_dir, used_dirs)
    assigned_dirs[series_key] = candidate
    used_dirs.add(candidate)
    return candidate


def unique_series_dir(base_dir: Path, used_dirs: set[Path]) -> Path:
    if base_dir not in used_dirs:
        return base_dir

    index = 2
    while True:
        candidate = base_dir.with_name(f"{base_dir.name}_{index:02d}")
        if candidate not in used_dirs:
            return candidate
        index += 1


def assign_series_dirs(
    base_dir_by_series: dict[tuple[str, str, tuple[str, ...]], Path],
    series_order: list[tuple[str, str, tuple[str, ...]]],
) -> dict[tuple[str, str, tuple[str, ...]], Path]:
    series_by_base_dir: dict[Path, list[tuple[str, str, tuple[str, ...]]]] = defaultdict(list)
    for series_key in series_order:
        series_by_base_dir[base_dir_by_series[series_key]].append(series_key)

    assigned: dict[tuple[str, str, tuple[str, ...]], Path] = {}
    for base_dir, series_keys in series_by_base_dir.items():
        if len(series_keys) == 1:
            assigned[series_keys[0]] = base_dir
            continue
        for index, series_key in enumerate(series_keys, start=1):
            assigned[series_key] = base_dir.with_name(f"{base_dir.name}_{index:02d}")
    return assigned


def materialize(source: Path, destination: Path, action: str, overwrite: bool) -> None:
    if overwrite and destination.exists():
        destination.unlink()
    if action == "copy":
        shutil.copy2(source, destination)
    elif action == "symlink":
        destination.symlink_to(source)
    elif action == "hardlink":
        os.link(source, destination)
    elif action == "move":
        shutil.move(source, destination)
    else:
        raise ValueError(f"Unsupported action: {action}")


def build_items(args: argparse.Namespace | OrganizeOptions) -> tuple[list[OrganizedItem], Counter[str]]:
    options = normalize_options(args)
    input_root = options.input_root
    output_root = options.output_root
    stats: Counter[str] = Counter()
    seen_destinations: set[Path] = set()
    items: list[OrganizedItem] = []
    dicom_tag_specs = parse_dicom_tag_specs(options.dicom_tags)
    pending_sources: list[tuple[Path, dict[str, Any], str, tuple[str, str]]] = []

    for source in iter_candidate_files(input_root, output_root, options):
        stats["candidate_files"] += 1
        ds = read_dicom_header(source, force=options.force_read)
        if ds is None:
            stats["skipped_non_dicom"] += 1
            if options.verbose:
                print(f"[skip] non-DICOM: {source}", file=sys.stderr)
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
        acquisition_date = context["acquisition_date"]
        filename = safe_name(format_template(options.file_template, context, "file"))
        pending_sources.append((source, context, filename, (acquisition_date, context["series_uid"])))
        stats["dicom_files"] += 1

        if options.limit and stats["dicom_files"] >= options.limit:
            break

    pending_assignments = resolved_series_assignments(pending_sources)
    pending: list[tuple[Path, dict[str, Any], str, tuple[str, str, tuple[str, ...]]]] = []
    series_order: list[tuple[str, str, tuple[str, ...]]] = []
    base_dir_by_series: dict[tuple[str, str, tuple[str, ...]], Path] = {}
    for (
        source,
        context,
        filename,
        _base_series_key,
    ), (series_key, series_context) in zip(pending_sources, pending_assignments):
        series_template_context = dict(context)
        series_template_context.update(series_context)
        series_dir_name = safe_name(
            format_template(options.series_dir_template, series_template_context, "series-dir")
        )
        base_dir = output_root / context["acquisition_date"] / series_dir_name
        if series_key not in base_dir_by_series:
            base_dir_by_series[series_key] = base_dir
            series_order.append(series_key)
        pending.append((source, context, filename, series_key))

    series_dirs = assign_series_dirs(base_dir_by_series, series_order)

    for source, context, filename, series_key in pending:
        destination = series_dirs[series_key] / filename
        resolved = resolve_collision(destination, seen_destinations, options.if_exists)
        if resolved is None:
            stats["skipped_existing"] += 1
            continue

        seen_destinations.add(resolved)
        row = dict(context["row"])
        row["OrganizedFileName"] = resolved.relative_to(output_root).as_posix()
        items.append(OrganizedItem(source=source, destination=resolved, row=row))

    return items, stats


def write_metadata_tables(
    output_root: Path,
    items: list[OrganizedItem],
    profile_name: str,
    extra_metadata_columns: list[str] | None = None,
) -> None:
    by_date: dict[str, list[OrganizedItem]] = defaultdict(list)
    for item in items:
        by_date[item.row["AcquisitionDate"]].append(item)

    for acquisition_date, date_items in sorted(by_date.items()):
        date_dir = output_root / acquisition_date
        rows = sorted(
            (item.row for item in date_items),
            key=lambda row: (
                row["SeriesNumber"],
                int(row["InstanceNumber"]) if row["InstanceNumber"].isdigit() else 0,
                row["OrganizedFileName"],
            ),
        )
        profile_rows = metadata_rows(rows, profile_name)
        write_csv(
            date_dir / "dicom_parameters.csv",
            metadata_columns_for_profile(profile_name, profile_rows, extra_metadata_columns),
            profile_rows,
        )
        write_csv(
            date_dir / "series_summary.csv",
            summary_columns_for_profile(profile_name, profile_rows),
            build_series_summary(profile_rows, profile_name),
        )


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def series_value(series_rows: list[dict[str, str]], column: str) -> str:
    for row in series_rows:
        value = row.get(column, "N/A")
        if value != "N/A":
            return value
    return "N/A"


def build_series_summary(
    rows: list[dict[str, str]],
    profile_name: str = "auto",
) -> list[dict[str, str]]:
    rows = metadata_rows(rows, profile_name)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["OrganizedFileName"].rsplit("/", 1)[0]].append(row)

    summaries = []
    for _series_dir, series_rows in sorted(
        grouped.items(), key=lambda item: (item[1][0]["SeriesNumber"], item[0])
    ):
        echo_times = sorted(
            {r["TE_ms"] for r in series_rows if r["TE_ms"] != "N/A"},
            key=natural_key,
        )
        coil_elements = sorted(
            {r["SiemensCoilElement"] for r in series_rows if r["SiemensCoilElement"] != "N/A"},
            key=natural_key,
        )
        summaries.append(
            {
                "AcquisitionDate": series_value(series_rows, "AcquisitionDate"),
                "SeriesNumber": series_value(series_rows, "SeriesNumber"),
                "SeriesUID": series_value(series_rows, "SeriesUID"),
                "SeriesUIDHash": hash_text(series_value(series_rows, "SeriesUID")),
                "Modality": series_value(series_rows, "Modality"),
                "SeriesDescription": series_value(series_rows, "SeriesDescription"),
                "ProtocolName": series_value(series_rows, "ProtocolName"),
                "FileCount": str(len(series_rows)),
                "EchoCount": str(len(echo_times)),
                "EchoTimes_ms": "|".join(echo_times) if echo_times else "N/A",
                "CoilElementCount": str(len(coil_elements)),
                "CoilElements": "|".join(coil_elements) if coil_elements else "N/A",
                "Rows": series_value(series_rows, "Rows"),
                "Columns": series_value(series_rows, "Columns"),
                "Matrix_RowsxCols": series_value(series_rows, "Matrix_RowsxCols"),
                "FOV_HxW_mm": series_value(series_rows, "FOV_HxW_mm"),
                "ImageType": series_value(series_rows, "ImageType"),
                "MRAcquisitionType": series_value(series_rows, "MRAcquisitionType"),
                "TR_ms": series_value(series_rows, "TR_ms"),
                "InversionTime_ms": series_value(series_rows, "InversionTime_ms"),
                "EchoNumbers": series_value(series_rows, "EchoNumbers"),
                "EchoTrainLength": series_value(series_rows, "EchoTrainLength"),
                "NumberOfAverages": series_value(series_rows, "NumberOfAverages"),
                "AcquisitionMatrix": series_value(series_rows, "AcquisitionMatrix"),
                "NumberOfPhaseEncodingSteps": series_value(series_rows, "NumberOfPhaseEncodingSteps"),
                "PercentSampling": series_value(series_rows, "PercentSampling"),
                "PercentPhaseFOV": series_value(series_rows, "PercentPhaseFOV"),
                "SAR": series_value(series_rows, "SAR"),
                "Manufacturer": series_value(series_rows, "Manufacturer"),
                "ManufacturerModelName": series_value(series_rows, "ManufacturerModelName"),
                "ReceiveCoilName": series_value(series_rows, "ReceiveCoilName"),
                "KVP_kV": series_value(series_rows, "KVP_kV"),
                "XRayTubeCurrent_mA": series_value(series_rows, "XRayTubeCurrent_mA"),
                "ExposureTime_ms": series_value(series_rows, "ExposureTime_ms"),
                "ConvolutionKernel": series_value(series_rows, "ConvolutionKernel"),
                "ReconstructionDiameter_mm": series_value(series_rows, "ReconstructionDiameter_mm"),
                "TransducerData": series_value(series_rows, "TransducerData"),
                "TransducerType": series_value(series_rows, "TransducerType"),
                "MechanicalIndex": series_value(series_rows, "MechanicalIndex"),
                "ThermalIndex": series_value(series_rows, "ThermalIndex"),
                "UltrasoundColorDataPresent": series_value(series_rows, "UltrasoundColorDataPresent"),
                "FrameTime_ms": series_value(series_rows, "FrameTime_ms"),
                "DistanceSourceToDetector_mm": series_value(series_rows, "DistanceSourceToDetector_mm"),
                "DistanceSourceToPatient_mm": series_value(series_rows, "DistanceSourceToPatient_mm"),
                "Radiopharmaceutical": series_value(series_rows, "Radiopharmaceutical"),
                "RadionuclideTotalDose_Bq": series_value(series_rows, "RadionuclideTotalDose_Bq"),
                "RadionuclideHalfLife_s": series_value(series_rows, "RadionuclideHalfLife_s"),
                "DecayCorrection": series_value(series_rows, "DecayCorrection"),
            }
        )
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
) -> None:
    by_series = Counter(item.destination.parent.relative_to(output_root).as_posix() for item in items)
    by_date = Counter(item.row["AcquisitionDate"] for item in items)
    summary = {
        "started_at": started_at,
        "ended_at": ended_at,
        "status": "dry_run" if options.dry_run else "completed",
        "input_root": str(options.input_root),
        "output_root": str(output_root),
        "action": options.action,
        "if_exists": options.if_exists,
        "force_read": options.force_read,
        "profile": options.profile,
        "patient_mode": options.patient_mode,
        "dicom_tags": list(options.dicom_tags),
        "candidate_files": stats["candidate_files"],
        "organized_files": len(items),
        "skipped_non_dicom": stats["skipped_non_dicom"],
        "skipped_existing": stats["skipped_existing"],
        "acquisition_dates": dict(sorted(by_date.items())),
        "series_count": len(by_series),
    }
    path = output_root / "organize_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def summarize_items(
    items: list[OrganizedItem],
    stats: Counter[str],
    output_root: Path,
) -> dict[str, Any]:
    by_date = Counter(item.row["AcquisitionDate"] for item in items)
    by_series = Counter(item.destination.parent.relative_to(output_root).as_posix() for item in items)
    return {
        "candidate_files": stats["candidate_files"],
        "organized_files": len(items),
        "series_count": len(by_series),
        "skipped_non_dicom": stats["skipped_non_dicom"],
        "skipped_existing": stats["skipped_existing"],
        "acquisition_dates": dict(sorted(by_date.items())),
        "output_root": str(output_root),
    }


def print_summary(items: list[OrganizedItem], stats: Counter[str], output_root: Path) -> None:
    summary = summarize_items(items, stats, output_root)
    print(f"candidate_files={summary['candidate_files']}")
    print(f"organized_files={summary['organized_files']}")
    print(f"series_count={summary['series_count']}")
    print(f"skipped_non_dicom={summary['skipped_non_dicom']}")
    print(f"skipped_existing={summary['skipped_existing']}")
    for acquisition_date, count in summary["acquisition_dates"].items():
        print(f"{acquisition_date}: files={count}")
    print(f"output_root={output_root}")


def run(args: argparse.Namespace | OrganizeOptions, *, dry_run: bool | None = None) -> OrganizeResult:
    options = normalize_options(args, dry_run=dry_run, validate=True)
    started_at = datetime.now(timezone.utc).isoformat()

    items, stats = build_items(options)
    dicom_tag_specs = parse_dicom_tag_specs(options.dicom_tags)

    if not options.dry_run:
        for item in items:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            materialize(
                item.source,
                item.destination,
                action=options.action,
                overwrite=options.if_exists == "overwrite",
            )
        write_metadata_tables(
            options.output_root,
            items,
            options.profile,
            extra_metadata_columns=[spec.column for spec in dicom_tag_specs],
        )
        ended_at = datetime.now(timezone.utc).isoformat()
        write_run_summary(options.output_root, items, stats, options, started_at, ended_at)
    else:
        ended_at = datetime.now(timezone.utc).isoformat()

    return OrganizeResult(
        items=items,
        stats=stats,
        output_root=options.output_root,
        started_at=started_at,
        ended_at=ended_at,
        dry_run=options.dry_run,
        profile=options.profile,
    )


def main() -> int:
    args = parse_args()

    try:
        result = run(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Failed while scanning: {exc}", file=sys.stderr)
        return 1

    if not result.items:
        print("No DICOM files were organized.", file=sys.stderr)
        print_summary(result.items, result.stats, result.output_root)
        if result.stats["skipped_existing"] > 0:
            return 0
        return 1

    print_summary(result.items, result.stats, result.output_root)
    if result.dry_run:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
