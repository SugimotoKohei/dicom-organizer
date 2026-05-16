#!/usr/bin/env python3
"""Organize DICOM files into stable series directories.

The default output layout intentionally matches the older local organizer:

    organized/<AcquisitionDate>/<SeriesNumber>_<sha1(SeriesInstanceUID)[:12]>/
        000001.dcm
        ...
    organized/<AcquisitionDate>/
        mri_parameters.csv
        series_summary.csv
    organized/organize_summary.json

The script reads DICOM headers only, keeps source files untouched by default,
and writes metadata tables that are useful for later phantom/MRI analysis.
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
from pydicom.multival import MultiValue


BASE_METADATA_COLUMNS = [
    "OrganizedFileName",
    "SeriesUID",
    "SOPInstanceUID",
    "SeriesNumber",
    "SeriesDescription",
    "InstanceNumber",
    "AcquisitionDate",
    "AcquisitionTime",
    "PatientName",
    "Modality",
    "TR(ms)",
    "TE(ms)",
    "FOV(HxW_mm)",
    "Matrix(RowsxCols)",
    "PixelBandwidth(Hz/px)",
    "EchoTrainLength",
    "FlipAngle(deg)",
    "SliceThickness(mm)",
    "SpacingBetweenSlices(mm)",
    "SliceLocation(mm)",
    "NumberOfAverages",
    "MagneticFieldStrength(T)",
    "ScanningSequence",
    "SequenceVariant",
    "PhaseEncodingDirection",
    "Manufacturer",
    "ManufacturerModelName",
    "ReceiveCoilName",
]

EXTRA_METADATA_COLUMNS = [
    "SourceFileName",
    "ProtocolName",
    "ImageType",
    "MRAcquisitionType",
    "Rows",
    "Columns",
    "PixelSpacing",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "FrameOfReferenceUID",
    "StudyInstanceUID",
    "StudyDate",
    "StudyTime",
    "SeriesDate",
    "SeriesTime",
    "PatientID",
    "PatientIDHash",
    "PatientNameHash",
    "SOPClassUID",
    "SiemensChannelMixing",
    "SiemensCoilElement",
    "SiemensIceDims",
    "SiemensIceDimChannel",
    "SiemensIceDimEcho",
    "IsNormalized",
]

METADATA_COLUMNS = BASE_METADATA_COLUMNS + EXTRA_METADATA_COLUMNS

SUMMARY_COLUMNS = [
    "AcquisitionDate",
    "SeriesNumber",
    "SeriesUID",
    "SeriesUIDHash",
    "SeriesDescription",
    "ProtocolName",
    "FileCount",
    "EchoCount",
    "EchoTimes(ms)",
    "CoilElementCount",
    "CoilElements",
    "Rows",
    "Columns",
    "Matrix(RowsxCols)",
    "FOV(HxW_mm)",
    "ImageType",
    "MRAcquisitionType",
    "TR(ms)",
    "EchoTrainLength",
    "NumberOfAverages",
    "Manufacturer",
    "ManufacturerModelName",
    "ReceiveCoilName",
]

DEFAULT_SERIES_DIR_TEMPLATE = "{series_number}_{series_uid_hash}"
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
    patient_mode: str = "keep"
    verbose: bool = False


@dataclass(frozen=True)
class OrganizeResult:
    items: list[OrganizedItem]
    stats: Counter[str]
    output_root: Path
    started_at: str
    ended_at: str
    dry_run: bool

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
            "series_number, series_description, protocol_name, series_uid_hash."
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
        "--patient-mode",
        choices=PATIENT_MODES,
        default="keep",
        help="How to write PatientName in metadata CSV. Default keeps the old behavior.",
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
            patient_mode=str(getattr(args, "patient_mode", "keep")),
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


def file_context(
    ds: pydicom.dataset.Dataset,
    item_index: int,
    patient_mode: str,
    input_root: Path,
    source: Path,
) -> dict[str, str]:
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

    return {
        "acquisition_date": ds_value(
            ds, "AcquisitionDate", default=ds_value(ds, "StudyDate", default="unknown_date")
        ),
        "series_number": series_number(ds),
        "series_description": safe_name(ds_value(ds, "SeriesDescription")),
        "protocol_name": safe_name(ds_value(ds, "ProtocolName")),
        "series_uid_hash": series_uid_hash,
        "sop_uid_hash": sop_uid_hash,
        "instance_number": str(inst),
        "instance_number_6": f"{inst:06d}",
        "echo_time_ms": safe_name(float_text(getattr(ds, "EchoTime", "NA"))),
        "siemens_coil_element": safe_name(tag_value(ds, 0x0021, 0x114F)),
        "row": {
            "SeriesUID": series_uid,
            "SOPInstanceUID": sop_uid,
            "SeriesNumber": series_number(ds),
            "SeriesDescription": ds_value(ds, "SeriesDescription"),
            "InstanceNumber": str(inst),
            "AcquisitionDate": ds_value(
                ds,
                "AcquisitionDate",
                default=ds_value(ds, "StudyDate", default="unknown_date"),
            ),
            "AcquisitionTime": ds_value(ds, "AcquisitionTime"),
            "PatientName": patient_name,
            "Modality": ds_value(ds, "Modality"),
            "TR(ms)": ds_value(ds, "RepetitionTime"),
            "TE(ms)": ds_value(ds, "EchoTime"),
            "FOV(HxW_mm)": fov_text(ds),
            "Matrix(RowsxCols)": matrix_text(ds),
            "PixelBandwidth(Hz/px)": ds_value(ds, "PixelBandwidth"),
            "EchoTrainLength": ds_value(ds, "EchoTrainLength"),
            "FlipAngle(deg)": ds_value(ds, "FlipAngle"),
            "SliceThickness(mm)": ds_value(ds, "SliceThickness"),
            "SpacingBetweenSlices(mm)": ds_value(ds, "SpacingBetweenSlices"),
            "SliceLocation(mm)": ds_value(ds, "SliceLocation"),
            "NumberOfAverages": ds_value(ds, "NumberOfAverages"),
            "MagneticFieldStrength(T)": ds_value(ds, "MagneticFieldStrength"),
            "ScanningSequence": ds_value(ds, "ScanningSequence"),
            "SequenceVariant": ds_value(ds, "SequenceVariant"),
            "PhaseEncodingDirection": ds_value(ds, "InPlanePhaseEncodingDirection"),
            "Manufacturer": ds_value(ds, "Manufacturer"),
            "ManufacturerModelName": ds_value(ds, "ManufacturerModelName"),
            "ReceiveCoilName": ds_value(ds, "ReceiveCoilName"),
            "SourceFileName": source.relative_to(input_root).as_posix(),
            "ProtocolName": ds_value(ds, "ProtocolName"),
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
        },
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
    if not options.include_organized and any(part == "organized" for part in rel_parts):
        return True
    return False


def iter_candidate_files(input_root: Path, output_root: Path, options: OrganizeOptions):
    for path in sorted(input_root.rglob("*")):
        if not path.is_file():
            continue
        if should_skip(path, input_root, output_root, options):
            continue
        yield path


def read_dicom_header(path: Path, force: bool) -> pydicom.dataset.Dataset | None:
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=force)
    except Exception:
        return None
    if not hasattr(ds, "SeriesInstanceUID") or not hasattr(ds, "SOPInstanceUID"):
        return None
    return ds


def format_template(template: str, context: dict[str, str], label: str) -> str:
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

    for source in iter_candidate_files(input_root, output_root, options):
        stats["candidate_files"] += 1
        ds = read_dicom_header(source, force=options.force_read)
        if ds is None:
            stats["skipped_non_dicom"] += 1
            if options.verbose:
                print(f"[skip] non-DICOM: {source}", file=sys.stderr)
            continue

        item_index = stats["dicom_files"] + 1
        context = file_context(ds, item_index, options.patient_mode, input_root, source)
        acquisition_date = context["acquisition_date"]
        series_dir = safe_name(format_template(options.series_dir_template, context, "series-dir"))
        filename = safe_name(format_template(options.file_template, context, "file"))
        destination = output_root / acquisition_date / series_dir / filename
        resolved = resolve_collision(destination, seen_destinations, options.if_exists)
        if resolved is None:
            stats["skipped_existing"] += 1
            continue

        seen_destinations.add(resolved)
        row = dict(context["row"])
        row["OrganizedFileName"] = resolved.relative_to(output_root).as_posix()
        items.append(OrganizedItem(source=source, destination=resolved, row=row))
        stats["dicom_files"] += 1

        if options.limit and stats["dicom_files"] >= options.limit:
            break

    return items, stats


def write_metadata_tables(output_root: Path, items: list[OrganizedItem]) -> None:
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
        write_csv(date_dir / "mri_parameters.csv", METADATA_COLUMNS, rows)
        write_csv(date_dir / "series_summary.csv", SUMMARY_COLUMNS, build_series_summary(rows))


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_series_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["SeriesUID"]].append(row)

    summaries = []
    for series_uid, series_rows in sorted(
        grouped.items(), key=lambda item: (item[1][0]["SeriesNumber"], item[0])
    ):
        first = series_rows[0]
        echo_times = sorted(
            {r["TE(ms)"] for r in series_rows if r["TE(ms)"] != "N/A"},
            key=natural_key,
        )
        coil_elements = sorted(
            {r["SiemensCoilElement"] for r in series_rows if r["SiemensCoilElement"] != "N/A"},
            key=natural_key,
        )
        summaries.append(
            {
                "AcquisitionDate": first["AcquisitionDate"],
                "SeriesNumber": first["SeriesNumber"],
                "SeriesUID": series_uid,
                "SeriesUIDHash": hash_text(series_uid),
                "SeriesDescription": first["SeriesDescription"],
                "ProtocolName": first["ProtocolName"],
                "FileCount": str(len(series_rows)),
                "EchoCount": str(len(echo_times)),
                "EchoTimes(ms)": "|".join(echo_times) if echo_times else "N/A",
                "CoilElementCount": str(len(coil_elements)),
                "CoilElements": "|".join(coil_elements) if coil_elements else "N/A",
                "Rows": first["Rows"],
                "Columns": first["Columns"],
                "Matrix(RowsxCols)": first["Matrix(RowsxCols)"],
                "FOV(HxW_mm)": first["FOV(HxW_mm)"],
                "ImageType": first["ImageType"],
                "MRAcquisitionType": first["MRAcquisitionType"],
                "TR(ms)": first["TR(ms)"],
                "EchoTrainLength": first["EchoTrainLength"],
                "NumberOfAverages": first["NumberOfAverages"],
                "Manufacturer": first["Manufacturer"],
                "ManufacturerModelName": first["ManufacturerModelName"],
                "ReceiveCoilName": first["ReceiveCoilName"],
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
    by_series = Counter(item.row["SeriesUID"] for item in items)
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
        "patient_mode": options.patient_mode,
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
    by_series = Counter(item.row["SeriesUID"] for item in items)
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

    if not options.dry_run:
        for item in items:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            materialize(
                item.source,
                item.destination,
                action=options.action,
                overwrite=options.if_exists == "overwrite",
            )
        write_metadata_tables(options.output_root, items)
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
