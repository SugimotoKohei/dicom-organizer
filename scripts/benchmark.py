#!/usr/bin/env python3
"""Benchmark dicom-organizer execution time and memory consumption across modes.

Measures dry-run, list-only, copy, and copy+checksum modes with varying file counts
using synthetic MR DICOM datasets. Measures per-process RSS via os.wait4.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pydicom  # noqa: E402
from pydicom.dataset import FileDataset, FileMetaDataset  # noqa: E402
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid  # noqa: E402


def get_cpu_brand() -> str:
    """Retrieve the human-readable CPU model/brand string."""
    if sys.platform == "darwin":
        try:
            brand = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            if brand:
                return brand
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        brand = line.split(":", 1)[1].strip()
                        if brand:
                            return brand
        except Exception:
            pass
    return platform.processor() or platform.machine() or "unknown"


def get_filesystem_type(workdir: Path) -> str:
    """Retrieve filesystem type (e.g. apfs, ext4) for the directory."""
    resolved = workdir.resolve()
    if sys.platform == "darwin":
        try:
            mount_proc = subprocess.run(["mount"], capture_output=True, text=True, check=False)
            if mount_proc.returncode == 0:
                best_mount = ""
                best_fstype = "unknown"
                for line in mount_proc.stdout.splitlines():
                    # Format: /dev/disk3s1s1 on / (apfs, sealed, local, read-only, journaled)
                    parts = line.split(" on ")
                    if len(parts) == 2:
                        m_point, _, f_info = parts[1].partition(" (")
                        fstype = f_info.split(",")[0].strip("() ")
                        try:
                            m_path = Path(m_point).resolve()
                            if resolved == m_path or m_path in resolved.parents:
                                if len(str(m_path)) > len(best_mount):
                                    best_mount = str(m_path)
                                    best_fstype = fstype
                        except Exception:
                            pass
                return best_fstype
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/mounts", encoding="utf-8") as f:
                best_mount = ""
                best_fstype = "unknown"
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        m_point, fstype = parts[1], parts[2]
                        try:
                            m_path = Path(m_point).resolve()
                            if resolved == m_path or m_path in resolved.parents:
                                if len(str(m_path)) > len(best_mount):
                                    best_mount = str(m_path)
                                    best_fstype = fstype
                        except Exception:
                            pass
                return best_fstype
        except Exception:
            pass
    return "unknown"


def get_machine_info(workdir: Path | None = None) -> dict[str, Any]:
    try:
        from dicom_organizer.core import package_version

        pkg_ver = package_version()
    except Exception:
        pkg_ver = "unknown"

    info: dict[str, Any] = {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "cpu": get_cpu_brand(),
        "logical_cores": os.cpu_count(),
        "python_version": platform.python_version(),
        "pydicom_version": getattr(pydicom, "__version__", "unknown"),
        "dicom_organizer_version": pkg_ver,
        "filesystem": get_filesystem_type(workdir) if workdir is not None else "unknown",
    }

    # Memory detection
    mem_str = "N/A"
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            mem_bytes = int(out)
            mem_str = f"{mem_bytes / (1024**3):.1f} GB"
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        mem_str = f"{kb / (1024**2):.1f} GB"
                        break
        except Exception:
            pass
    info["memory"] = mem_str

    return info


def make_pixel_data(matrix: int = 256) -> bytes:
    """Generate deterministic synthetic 16-bit pixel data of size matrix x matrix."""
    needed = matrix * matrix * 2
    tile = bytes((i % 256) for i in range(512))
    return (tile * (needed // len(tile) + 1))[:needed]


def create_benchmark_dataset(target_dir: Path, file_count: int, matrix: int = 256) -> None:
    """Create a synthetic dataset with file_count instances (100 instances per series)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    pixel_data = make_pixel_data(matrix)
    series_per_study = 5
    images_per_series = 100

    study_uid = generate_uid()
    series_count = math.ceil(file_count / images_per_series)
    created = 0

    for s_idx in range(1, series_count + 1):
        if (s_idx - 1) % series_per_study == 0 and s_idx > 1:
            study_uid = generate_uid()
        series_uid = generate_uid()
        series_dir = target_dir / f"series_{s_idx:04d}"
        series_dir.mkdir(parents=True, exist_ok=True)

        for img_idx in range(1, images_per_series + 1):
            if created >= file_count:
                break
            sop_uid = generate_uid()
            file_path = series_dir / f"img_{img_idx:04d}.dcm"

            meta = FileMetaDataset()
            meta.MediaStorageSOPClassUID = MRImageStorage
            meta.MediaStorageSOPInstanceUID = sop_uid
            meta.TransferSyntaxUID = ExplicitVRLittleEndian
            meta.ImplementationClassUID = generate_uid()

            ds = FileDataset(str(file_path), {}, file_meta=meta, preamble=b"\0" * 128)
            ds.SOPClassUID = MRImageStorage
            ds.SOPInstanceUID = sop_uid
            ds.StudyInstanceUID = study_uid
            ds.SeriesInstanceUID = series_uid
            ds.Modality = "MR"
            ds.PatientName = f"BENCH^P{((s_idx - 1) // series_per_study) + 1:03d}"
            ds.PatientID = f"BENCH_{((s_idx - 1) // series_per_study) + 1:03d}"
            ds.StudyDate = "20260615"
            ds.AcquisitionDate = "20260615"
            ds.SeriesDate = "20260615"
            ds.SeriesNumber = s_idx
            ds.InstanceNumber = img_idx
            ds.SeriesDescription = f"Bench T2 Series {s_idx}"
            ds.ProtocolName = "Bench T2"
            ds.Manufacturer = "Benchmark Imaging"
            ds.ManufacturerModelName = "Bench 3T"
            ds.Rows = matrix
            ds.Columns = matrix
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 0
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.RepetitionTime = 3000.0
            ds.EchoTime = 80.0
            ds.FlipAngle = 90.0
            ds.PixelData = pixel_data

            ds.save_as(file_path, enforce_file_format=True)
            created += 1

        if created >= file_count:
            break


def run_mode_process_once(
    mode_name: str,
    input_dir: Path,
    output_dir: Path,
    expected_files: int,
) -> tuple[float, float | None, int]:
    """Run dicom-organizer in an isolated subprocess and return (elapsed, max_rss_mb, verified_files)."""
    cmd = [
        sys.executable,
        "-m",
        "dicom_organizer",
        str(input_dir),
        "-o",
        str(output_dir),
        "--no-progress",
    ]
    if mode_name == "dry":
        cmd.append("--dry-run")
    elif mode_name == "list":
        cmd.append("--list-only")
    elif mode_name == "copy":
        cmd.extend(["--action", "copy"])
    elif mode_name == "checksum":
        cmd.extend(["--action", "copy", "--checksum"])
    else:
        raise ValueError(f"Unknown benchmark mode: {mode_name}")

    sub_env = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "src"))

    with tempfile.NamedTemporaryFile(mode="w+t", delete=False) as out_tmp, \
         tempfile.NamedTemporaryFile(mode="w+t", delete=False) as err_tmp:
        out_name = out_tmp.name
        err_name = err_tmp.name

    try:
        with open(out_name, "w", encoding="utf-8") as out_fp, \
             open(err_name, "w", encoding="utf-8") as err_fp:
            t0 = time.perf_counter()
            proc = subprocess.Popen(cmd, stdout=out_fp, stderr=err_fp, env=sub_env)
            if os.name != "nt":
                pid, status, rusage = os.wait4(proc.pid, 0)
                t1 = time.perf_counter()
                returncode = os.waitstatus_to_exitcode(status)
                proc.returncode = returncode
                raw_rss = rusage.ru_maxrss
                if sys.platform == "darwin":
                    rss_mb = round(raw_rss / (1024 * 1024), 2)
                else:
                    rss_mb = round((raw_rss * 1024) / (1024 * 1024), 2)
            else:
                proc.wait()
                t1 = time.perf_counter()
                returncode = proc.returncode
                rss_mb = None

        with open(out_name, "r", encoding="utf-8", errors="replace") as out_fp:
            stdout_text = out_fp.read()
        with open(err_name, "r", encoding="utf-8", errors="replace") as err_fp:
            stderr_text = err_fp.read()
    finally:
        try:
            os.remove(out_name)
        except OSError:
            pass
        try:
            os.remove(err_name)
        except OSError:
            pass

    if returncode != 0:
        raise RuntimeError(
            f"Benchmark subprocess failed for mode '{mode_name}' with code {returncode}:\n"
            f"STDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}"
        )

    elapsed = t1 - t0

    # Verification according to P1
    verified_files = 0
    if mode_name == "dry":
        if output_dir.exists():
            raise RuntimeError(f"Verification failed: Output directory {output_dir} exists in dry-run mode.")
        import re

        m = re.search(r"organized_files=(\d+)", stdout_text)
        if not m or int(m.group(1)) != expected_files:
            found = m.group(1) if m else "None"
            raise RuntimeError(
                f"Verification failed: dry-run stdout organized_files={found}, expected {expected_files}."
            )
        verified_files = expected_files

    elif mode_name == "list":
        summary_json = output_dir / "organize_summary.json"
        if not summary_json.is_file():
            raise RuntimeError(f"Verification failed: {summary_json} missing in list-only mode.")
        data = json.loads(summary_json.read_text(encoding="utf-8"))
        if data.get("status") != "completed":
            raise RuntimeError(f"Verification failed: status={data.get('status')} in list-only mode.")
        if data.get("csv_target_files") != expected_files:
            raise RuntimeError(
                f"Verification failed: csv_target_files={data.get('csv_target_files')}, expected {expected_files}."
            )
        dcm_files = list(output_dir.rglob("*.dcm"))
        if len(dcm_files) > 0:
            raise RuntimeError(f"Verification failed: list-only output contains {len(dcm_files)} .dcm files.")
        verified_files = expected_files

    elif mode_name in ("copy", "checksum"):
        summary_json = output_dir / "organize_summary.json"
        if not summary_json.is_file():
            raise RuntimeError(f"Verification failed: {summary_json} missing in {mode_name} mode.")
        data = json.loads(summary_json.read_text(encoding="utf-8"))
        if data.get("status") != "completed":
            raise RuntimeError(f"Verification failed: status={data.get('status')} in {mode_name} mode.")
        if data.get("organized_files") != expected_files:
            raise RuntimeError(
                f"Verification failed: organized_files={data.get('organized_files')}, expected {expected_files}."
            )
        dcm_files = list(output_dir.rglob("*.dcm"))
        if len(dcm_files) != expected_files:
            raise RuntimeError(
                f"Verification failed: output directory contains {len(dcm_files)} .dcm files, expected {expected_files}."
            )
        verified_files = len(dcm_files)

    return elapsed, rss_mb, verified_files


def mask_home(text: str) -> str:
    """Mask user home directory with ~, requiring path separator or exact match."""
    home = str(Path.home())
    if text == home:
        return "~"
    return text.replace(home + os.sep, "~" + os.sep)


def build_markdown_report(
    machine_info: dict[str, Any],
    results: list[dict[str, Any]],
    cmd_str: str,
) -> str:
    lines = [
        "# dicom-organizer Performance Benchmark Report",
        "",
        "## Machine Information",
        f"- **OS**: {machine_info.get('os')}",
        f"- **CPU**: {machine_info.get('cpu')}",
        f"- **Logical Cores**: {machine_info.get('logical_cores')}",
        f"- **Memory**: {machine_info.get('memory')}",
        f"- **Filesystem**: {machine_info.get('filesystem')}",
        f"- **Python**: {machine_info.get('python_version')}",
        f"- **pydicom**: {machine_info.get('pydicom_version')}",
        f"- **dicom-organizer**: {machine_info.get('dicom_organizer_version')}",
        "",
        "## Measurement Notes & Environment",
        f"- **Command line**: `{cmd_str}`",
        "- **Dataset Structure**: 100 images per series (synthetic MR datasets).",
        "- **OS File Cache**: Test datasets are measured directly after synthetic generation, so input files are held in the operating system page cache (warm cache). First-time cold reads, slow external USB drives, or network-mounted storage will exhibit lower throughput.",
        "- **Storage Volume**: Input and output directories are located on the same filesystem volume.",
        "- **Process Isolation**: Each mode and trial is executed in a dedicated subprocess. Memory RSS is recorded per-process via `wait4`.",
        "",
        "## Benchmark Results (Median values over repetitions)",
        "",
        "| File Count | Series | Matrix | Total (MB) | Avg File (KiB) | Mode | Median (s) | Min / Max (s) | Throughput (files/s) | Speed (MB/s) | Max RSS (MB) | Verified Files |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    mode_display = {
        "dry": "Dry-run (preview)",
        "list": "List-only",
        "copy": "Copy",
        "checksum": "Copy + Checksum",
    }

    for bench in results:
        count = bench["files"]
        series_cnt = bench.get("series", bench.get("series_count", math.ceil(count / 100)))
        mat = bench.get("matrix", 256)
        total_mb = f"{bench.get('total_size_mb', 0.0):.2f}"
        avg_kib = f"{bench.get('avg_file_kib', 0.0):.1f}"
        modes = bench["modes"]
        for mode_key in ("dry", "list", "copy", "checksum"):
            if mode_key not in modes:
                continue
            m = modes[mode_key]
            disp = mode_display.get(mode_key, mode_key)
            med_s = f"{m['median_seconds']:.2f}"
            min_max = f"{m.get('min_seconds', 0.0):.2f} / {m.get('max_seconds', 0.0):.2f}"
            fps = f"{m['throughput_files_per_sec']:.1f}"
            mb_s = f"{m['throughput_mb_per_sec']:.1f} MB/s" if "throughput_mb_per_sec" in m else "N/A"
            rss = f"{m['max_rss_mb']:.1f}" if m.get("max_rss_mb") is not None else "N/A"
            v_files = str(m.get("verified_files", "N/A"))
            lines.append(
                f"| {count} | {series_cnt} | {mat} | {total_mb} | {avg_kib} | {disp} | {med_s} | {min_max} | {fps} | {mb_s} | {rss} | {v_files} |"
            )

    lines.append("")
    report_text = "\n".join(lines)
    return mask_home(report_text)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark dicom-organizer throughput and memory across modes."
    )
    parser.add_argument(
        "--files",
        nargs="+",
        type=int,
        default=[1000, 5000, 20000],
        help="Number of DICOM files to test per run (default: 1000 5000 20000).",
    )
    parser.add_argument(
        "--matrix",
        type=int,
        default=256,
        help="Matrix dimension for synthetic images (default: 256 for 256x256 16-bit).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="Number of repetitions per mode to calculate median (default: 3).",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        default=False,
        help="Preserve benchmark output folders after measuring (default: delete).",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="Working directory for dataset generation (default: temporary directory).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Path to save benchmark results as JSON.",
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        default=None,
        help="Path to save benchmark report as Markdown.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    file_counts = sorted(set(args.files))

    workdir_context = None
    if args.workdir is not None:
        base_workdir = args.workdir.resolve()
        base_workdir.mkdir(parents=True, exist_ok=True)
    else:
        workdir_context = tempfile.TemporaryDirectory(prefix="dicom_bench_")
        base_workdir = Path(workdir_context.name)

    machine_info = get_machine_info(base_workdir)
    results: list[dict[str, Any]] = []
    raw_args = sys.argv[1:] if argv is None else argv
    cmd_str = mask_home(f"python scripts/benchmark.py {' '.join(raw_args)}")

    try:
        for count in file_counts:
            print(f"\n--- Benchmarking {count} synthetic DICOM files (matrix={args.matrix}) ---")

            # Check free disk space before generating data (P3)
            # Estimated file size: header ~2KB + pixel data
            bytes_per_file = 2048 + (args.matrix * args.matrix * 2)
            dataset_bytes_est = count * bytes_per_file
            required_space = int(dataset_bytes_est * 2.5)

            usage = shutil.disk_usage(base_workdir)
            if usage.free < required_space:
                raise RuntimeError(
                    f"Insufficient free disk space in '{base_workdir}': "
                    f"{usage.free / (1024**2):.1f} MB available, but "
                    f"{required_space / (1024**2):.1f} MB required (2.5x dataset size)."
                )

            dataset_dir = base_workdir / f"dataset_{count}_m{args.matrix}"
            needs_gen = True
            if dataset_dir.is_dir():
                existing_dcms = list(dataset_dir.rglob("*.dcm"))
                if len(existing_dcms) == count:
                    needs_gen = False
                else:
                    shutil.rmtree(dataset_dir)

            if needs_gen:
                print(f"Generating synthetic dataset ({count} files, matrix={args.matrix})...")
                create_benchmark_dataset(dataset_dir, count, matrix=args.matrix)

            # Compute actual dataset byte size
            actual_dataset_bytes = sum(f.stat().st_size for f in dataset_dir.rglob("*.dcm"))
            total_size_mb = round(actual_dataset_bytes / (1024 * 1024), 2)
            avg_file_kib = round((actual_dataset_bytes / count) / 1024, 2) if count > 0 else 0.0

            count_modes: dict[str, dict[str, Any]] = {}
            for mode in ("dry", "list", "copy", "checksum"):
                trial_times: list[float] = []
                trial_rss: list[float] = []
                verified_files = 0

                print(f"Running mode '{mode}' ({args.repeat} repetitions)...")
                for rep in range(1, args.repeat + 1):
                    out_dir = base_workdir / f"out_{count}_{mode}"
                    if out_dir.exists():
                        shutil.rmtree(out_dir)

                    elapsed, rss_mb, v_count = run_mode_process_once(
                        mode, dataset_dir, out_dir, count
                    )
                    trial_times.append(elapsed)
                    if rss_mb is not None:
                        trial_rss.append(rss_mb)
                    verified_files = v_count

                    # Clean up output directory after each repetition unless --keep-output (P3)
                    if not args.keep_output and out_dir.exists():
                        shutil.rmtree(out_dir)

                med_time = statistics.median(trial_times)
                min_time = min(trial_times)
                max_time = max(trial_times)
                max_rss = max(trial_rss) if trial_rss else None
                throughput_fps = count / med_time if med_time > 0 else 0.0

                mode_result: dict[str, Any] = {
                    "time_seconds": round(med_time, 4),
                    "median_seconds": round(med_time, 4),
                    "min_seconds": round(min_time, 4),
                    "max_seconds": round(max_time, 4),
                    "throughput_files_per_sec": round(throughput_fps, 2),
                    "max_rss_mb": max_rss,
                    "verified_files": verified_files,
                }
                if mode in ("copy", "checksum"):
                    mode_result["throughput_mb_per_sec"] = round(
                        total_size_mb / med_time if med_time > 0 else 0.0, 2
                    )

                count_modes[mode] = mode_result
                print(
                    f"  -> {mode}: median {med_time:.2f}s ({throughput_fps:.1f} files/s), "
                    f"max RSS: {max_rss if max_rss is not None else 'N/A'} MB, "
                    f"verified: {verified_files} files"
                )

            results.append({
                "files": count,
                "series": math.ceil(count / 100),
                "series_count": math.ceil(count / 100),
                "matrix": args.matrix,
                "total_size_mb": total_size_mb,
                "avg_file_kib": avg_file_kib,
                "repeat": args.repeat,
                "modes": count_modes,
            })

        data_to_export = {
            "machine_info": machine_info,
            "command_line": cmd_str,
            "results": results,
        }

        if args.output_json:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(json.dumps(data_to_export, indent=2), encoding="utf-8")
            print(f"\nJSON results written to: {args.output_json}")

        markdown_report = build_markdown_report(machine_info, results, cmd_str)
        if args.output_markdown:
            args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.output_markdown.write_text(markdown_report, encoding="utf-8")
            print(f"Markdown report written to: {args.output_markdown}")
        else:
            print("\n" + markdown_report)

    finally:
        if workdir_context is not None:
            workdir_context.cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
