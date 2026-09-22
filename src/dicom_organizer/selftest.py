"""Self-diagnostic testing using synthetic sample data."""

from __future__ import annotations

import csv
import re
import sys
import tempfile
from pathlib import Path

from dicom_organizer.core import OrganizeOptions, run
from dicom_organizer.sample_data import create_sample_dataset


def run_self_test(report_path: Path | str | None = None) -> int:
    """Run self-test checks using a temporary sample dataset and report results."""
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn):
        try:
            msg = fn()
            results.append((name, True, msg or ""))
        except Exception as exc:
            results.append((name, False, str(exc)))

    with tempfile.TemporaryDirectory(prefix="dicom-organizer-selftest-") as tmp:
        tmp_root = Path(tmp)
        sample = create_sample_dataset(tmp_root / "sample")

        # 1. Normal organization
        def check_normal():
            out_dir = tmp_root / "out_normal"
            res = run(
                OrganizeOptions(
                    input_root=sample.root,
                    output_root=out_dir,
                    checksum=True,
                    patient_mode="hash",
                )
            )
            summary = res.summary
            if summary["status"] != "completed":
                raise AssertionError(f"status is {summary['status']}, expected completed")
            if summary["organized_files"] != sample.expected["organized_files"]:
                raise AssertionError(
                    f"organized_files is {summary['organized_files']}, expected {sample.expected['organized_files']}"
                )
            if summary["csv_target_files"] != sample.expected["csv_target_files"]:
                raise AssertionError(
                    f"csv_target_files is {summary['csv_target_files']}, expected {sample.expected['csv_target_files']}"
                )
            if summary["series_count"] != sample.expected["series_count"]:
                raise AssertionError(
                    f"series_count is {summary['series_count']}, expected {sample.expected['series_count']}"
                )
            skipped = summary.get("skipped_by_reason", {})
            if skipped.get("not_dicom") != sample.expected["not_dicom"]:
                raise AssertionError(f"not_dicom is {skipped.get('not_dicom')}")
            if skipped.get("duplicate_identical") != sample.expected["duplicate_identical"]:
                raise AssertionError(f"duplicate_identical is {skipped.get('duplicate_identical')}")

            # file_report.csv
            file_report_path = out_dir / "file_report.csv"
            if not file_report_path.is_file():
                raise AssertionError("file_report.csv missing")
            with file_report_path.open(encoding="utf-8-sig", newline="") as f:
                report_rows = list(csv.DictReader(f))
            if len(report_rows) != sample.expected["candidate_files"]:
                raise AssertionError(
                    f"file_report rows={len(report_rows)}, expected {sample.expected['candidate_files']}"
                )

            # SHA-256 check
            organized_rows = [r for r in report_rows if r["Status"] == "organized"]
            for r in organized_rows:
                sha = r.get("SHA256", "")
                if not re.fullmatch(r"[0-9a-f]{64}", sha):
                    raise AssertionError(f"invalid sha256: {sha}")

            # all_series_summary.csv
            series_summary_path = out_dir / "all_series_summary.csv"
            if not series_summary_path.is_file():
                raise AssertionError("all_series_summary.csv missing")
            with series_summary_path.open(encoding="utf-8-sig", newline="") as f:
                series_rows = list(csv.DictReader(f))
            if len(series_rows) != sample.expected["image_series_count"]:
                raise AssertionError(
                    f"all_series_summary rows={len(series_rows)}, expected {sample.expected['image_series_count']}"
                )
            return "normal organize ok"

        # 2. List-only mode
        def check_list_only():
            out_dir = tmp_root / "out_list"
            run(
                OrganizeOptions(
                    input_root=sample.root,
                    output_root=out_dir,
                    list_only=True,
                )
            )
            dcm_files = list(out_dir.rglob("*.dcm"))
            if dcm_files:
                raise AssertionError(f"list_only wrote {len(dcm_files)} DICOM files")
            series_summary_path = out_dir / "all_series_summary.csv"
            if not series_summary_path.is_file():
                raise AssertionError("all_series_summary.csv missing in list_only")
            with series_summary_path.open(encoding="utf-8-sig", newline="") as f:
                series_rows = list(csv.DictReader(f))
            if len(series_rows) != sample.expected["image_series_count"]:
                raise AssertionError(
                    f"list_only all_series_summary rows={len(series_rows)}, expected {sample.expected['image_series_count']}"
                )
            return "list-only ok"

        # 3. Dry-run
        def check_dry_run():
            out_dir = tmp_root / "out_dry"
            run(
                OrganizeOptions(
                    input_root=sample.root,
                    output_root=out_dir,
                    dry_run=True,
                ),
                dry_run=True,
            )
            if out_dir.exists() and list(out_dir.iterdir()):
                raise AssertionError("dry_run created output files")
            return "dry-run ok"

        check("1. standard organization and reports", check_normal)
        check("2. list-only mode metadata tables", check_list_only)
        check("3. dry-run leaves disk untouched", check_dry_run)

    output_lines: list[str] = []
    for name, ok, msg in results:
        tag = "[PASS]" if ok else "[FAIL]"
        line = f"{tag} {name} - {msg}" if msg else f"{tag} {name}"
        output_lines.append(line)

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    summary_line = f"self-test: {passed}/{total} checks passed"
    output_lines.append(summary_line)

    output_text = "\n".join(output_lines) + "\n"
    sys.stdout.write(output_text)

    if report_path is not None:
        rep_p = Path(report_path)
        rep_p.parent.mkdir(parents=True, exist_ok=True)
        rep_p.write_text(output_text, encoding="utf-8")

    return 0 if passed == total else 1
