#!/usr/bin/env python3
"""Batch convert organized DICOM series to NIfTI using dcm2niix.

Filters series from all_series_summary.csv (by modality and regular expression)
and generates or executes dcm2niix commands placing NIfTI files adjacent to the
organized DICOM tree.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter organized DICOM series and convert them to NIfTI with dcm2niix."
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Organized DICOM output directory containing all_series_summary.csv.",
    )
    parser.add_argument(
        "--modality",
        default="MR",
        help="Filter by Modality (default: MR). Set empty to disable modality filter.",
    )
    parser.add_argument(
        "--match",
        default=None,
        help="Regular expression to include matching SeriesDescription or ProtocolName.",
    )
    parser.add_argument(
        "--exclude",
        default=None,
        help="Regular expression to exclude matching SeriesDescription or ProtocolName.",
    )
    parser.add_argument(
        "--nifti-dir",
        type=Path,
        default=None,
        help="Destination directory for NIfTI files (default: <output_dir>_nifti adjacent to output_dir).",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the dcm2niix commands directly instead of only printing them.",
    )
    return parser.parse_args(argv)


def check_list_only(output_dir: Path, summary_json_path: Path, rows: list[dict[str, str]]) -> bool:
    """Check if the output was generated with --list-only."""
    if summary_json_path.is_file():
        try:
            data = json.loads(summary_json_path.read_text(encoding="utf-8"))
            if data.get("list_only") is True or data.get("options", {}).get("list_only") is True:
                return True
        except Exception:
            pass

    # Check if series folders actually exist
    existing_series_count = 0
    total_checked = 0
    for r in rows:
        series_folder = r.get("SeriesFolder", "")
        if not series_folder:
            continue
        total_checked += 1
        if (output_dir / series_folder).is_dir():
            existing_series_count += 1

    if total_checked > 0 and existing_series_count == 0:
        return True
    return False


def format_command(cmd_args: list[str]) -> str:
    """Format command string appropriately for the operating system."""
    if os.name == "nt":
        return subprocess.list2cmdline(cmd_args)
    return " ".join(shlex.quote(a) for a in cmd_args)


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    output_dir = args.output_dir.resolve()

    if not output_dir.is_dir():
        print(f"Error: Output directory not found: {output_dir}", file=sys.stderr)
        return 1

    csv_path = output_dir / "all_series_summary.csv"
    if not csv_path.is_file():
        print(f"Error: 'all_series_summary.csv' not found in: {output_dir}", file=sys.stderr)
        return 1

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    summary_json = output_dir / "organize_summary.json"
    if check_list_only(output_dir, summary_json, rows):
        print(
            f"Error: Directory '{output_dir}' was generated with --list-only. "
            "No materialized DICOM series folders exist for NIfTI conversion.",
            file=sys.stderr,
        )
        return 2

    nifti_dir = (
        args.nifti_dir.resolve()
        if args.nifti_dir is not None
        else output_dir.parent / f"{output_dir.name}_nifti"
    )

    # Validate that nifti_dir is not inside output_dir (P6)
    if nifti_dir == output_dir:
        print(
            f"Error: NIfTI directory '{nifti_dir}' cannot be the organized directory '{output_dir}'.",
            file=sys.stderr,
        )
        return 1
    try:
        nifti_dir.relative_to(output_dir)
        print(
            f"Error: NIfTI directory '{nifti_dir}' cannot be inside organized directory '{output_dir}'.",
            file=sys.stderr,
        )
        return 1
    except ValueError:
        pass

    try:
        match_re = re.compile(args.match, re.IGNORECASE) if args.match else None
    except re.error as exc:
        print(f"Error: Invalid regular expression for --match: {exc}", file=sys.stderr)
        return 2

    try:
        exclude_re = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None
    except re.error as exc:
        print(f"Error: Invalid regular expression for --exclude: {exc}", file=sys.stderr)
        return 2

    modality_target = args.modality.strip().upper() if args.modality else None

    commands: list[tuple[list[str], Path, Path, str]] = []

    for r in rows:
        # Modality filter
        if modality_target and r.get("Modality", "").strip().upper() != modality_target:
            continue

        desc = r.get("SeriesDescription", "")
        proto = r.get("ProtocolName", "")
        text_to_match = f"{desc} {proto}".strip()

        # Regex filters
        if match_re and not match_re.search(text_to_match):
            continue
        if exclude_re and exclude_re.search(text_to_match):
            continue

        series_folder = r.get("SeriesFolder", "")
        if not series_folder:
            continue

        series_path = output_dir / series_folder
        if not series_path.is_dir():
            print(f"Warning: Series folder not found: {series_folder}", file=sys.stderr)
            continue

        series_nifti_dir = nifti_dir / series_folder
        cmd_args = [
            "dcm2niix",
            "-z",
            "y",
            "-f",
            "%p_%t_%s",
            "-o",
            str(series_nifti_dir),
            str(series_path),
        ]
        commands.append((cmd_args, series_nifti_dir, series_path, series_folder))

    if not commands:
        print("No matching series found for dcm2niix conversion.", file=sys.stderr)
        return 0

    if args.run:
        dcm2niix_bin = shutil.which("dcm2niix")
        if not dcm2niix_bin:
            print(
                "Error: 'dcm2niix' executable was not found in PATH. "
                "Please install dcm2niix to use --run.",
                file=sys.stderr,
            )
            return 1

        failed_series: list[str] = []
        total_commands = len(commands)
        for idx, (cmd_args, target_dir, source_dir, rel_folder) in enumerate(commands, 1):
            print(f"[{idx}/{total_commands}] {rel_folder}")
            target_dir.mkdir(parents=True, exist_ok=True)
            exec_args = [dcm2niix_bin] + cmd_args[1:]
            try:
                res = subprocess.run(exec_args)
                if res.returncode != 0:
                    failed_series.append(rel_folder)
            except OSError as exc:
                print(f"Error running dcm2niix for {rel_folder}: {exc}", file=sys.stderr)
                failed_series.append(rel_folder)

        if failed_series:
            print(
                f"Error: {len(failed_series)} series failed to convert: {', '.join(failed_series)}",
                file=sys.stderr,
            )
            return 1
    else:
        for cmd_args, _, _, _ in commands:
            print(format_command(cmd_args))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
