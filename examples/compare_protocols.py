#!/usr/bin/env python3
"""Compare DICOM imaging protocols across devices and studies.

Reads all_series_summary.csv from dicom-organizer output, groups series by
SeriesDescription (or another tag), and produces a side-by-side comparison CSV
highlighting parameters that differ between acquisitions or scanners.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_COLUMNS = (
    "TR_ms",
    "TE_ms",
    "FlipAngle_deg",
    "PixelBandwidth_Hz_per_px",
    "SliceThickness_mm",
    "FOV_HxW_mm",
    "Matrix_RowsxCols",
    "ScanDuration",
    "ParallelReductionFactorInPlane",
)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare imaging parameters across scanners and studies from dicom-organizer summary CSV."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to all_series_summary.csv or an organized output directory.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to output CSV (default: protocol_comparison.csv in input directory).",
    )
    parser.add_argument(
        "--by",
        default="SeriesDescription",
        help="Column to group series by (default: SeriesDescription).",
    )
    parser.add_argument(
        "--columns",
        default=",".join(DEFAULT_COLUMNS),
        help="Comma-separated column names to compare across series.",
    )
    return parser.parse_args(argv)


def resolve_csv_path(input_path: Path) -> Path:
    if input_path.is_dir():
        candidate = input_path / "all_series_summary.csv"
        if not candidate.is_file():
            raise FileNotFoundError(
                f"Could not find 'all_series_summary.csv' in directory: {input_path}"
            )
        return candidate
    if input_path.is_file():
        return input_path
    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    try:
        csv_path = resolve_csv_path(args.input)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    columns_to_compare = [c.strip() for c in args.columns.split(",") if c.strip()]
    by_column = args.by

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        all_rows = list(reader)

    # Validate column names against available CSV headers (P7)
    if by_column not in fieldnames:
        print(
            f"Error: Grouping column '{by_column}' not found in CSV headers. "
            f"Available columns: {', '.join(fieldnames)}",
            file=sys.stderr,
        )
        return 2

    unknown_columns = [c for c in columns_to_compare if c not in fieldnames]
    if unknown_columns:
        print(
            f"Error: Comparison column(s) not found in CSV headers: {', '.join(unknown_columns)}. "
            f"Available columns: {', '.join(fieldnames)}",
            file=sys.stderr,
        )
        return 2

    output_path = (
        args.output
        if args.output is not None
        else csv_path.parent / "protocol_comparison.csv"
    )

    if not all_rows:
        print(f"Warning: No rows found in {csv_path}", file=sys.stderr)
        return 0

    # Group series by the specified column
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in all_rows:
        key = row.get(by_column, "N/A")
        grouped[key].append(row)

    output_rows: list[dict[str, str]] = []
    base_headers = [
        by_column,
        "Device",
        "Manufacturer",
        "ManufacturerModelName",
        "StudyFolder",
        "SeriesFolder",
        "SeriesNumber",
    ]

    for group_key, group_rows in grouped.items():
        # Identify which comparison columns have differing values within this group
        differing: list[str] = []
        for col in columns_to_compare:
            vals = {r.get(col, "N/A") for r in group_rows}
            if len(vals) > 1:
                differing.append(col)
        diff_str = "|".join(differing)

        for r in group_rows:
            mfg = r.get("Manufacturer", "").strip()
            model = r.get("ManufacturerModelName", "").strip()
            device = f"{mfg} {model}".strip() or "UnknownDevice"

            out_row: dict[str, str] = {
                by_column: group_key,
                "Device": device,
                "Manufacturer": mfg,
                "ManufacturerModelName": model,
                "StudyFolder": r.get("StudyFolder", "N/A"),
                "SeriesFolder": r.get("SeriesFolder", "N/A"),
                "SeriesNumber": r.get("SeriesNumber", "N/A"),
                "DifferingColumns": diff_str,
            }
            for col in columns_to_compare:
                out_row[col] = r.get(col, "N/A")
            output_rows.append(out_row)

    # Sort output rows: group_key ascending, Device ascending, StudyFolder ascending
    output_rows.sort(
        key=lambda r: (
            r[by_column],
            r["Device"],
            r["StudyFolder"],
            r["SeriesNumber"],
        )
    )

    out_fieldnames = base_headers + columns_to_compare + ["DifferingColumns"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Protocol comparison written to: {output_path} ({len(output_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
