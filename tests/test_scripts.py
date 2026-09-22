"""Tests for scripts and examples introduced in WP6a.

Tests verify:
- python -m dicom_organizer module entry execution
- benchmark.py runs with small file count (--files 200) and records verified_files
- render_screenshots.py generates documentation PNG images and before-after text
- compare_protocols.py detects differing TE_ms, supports --by ProtocolName, and rejects unknown columns
- dcm2niix_batch.py generates correct conversion commands, warns on missing series, rejects nested nifti-dir and list-only
"""

from __future__ import annotations

import csv
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import dicom_organizer.core as core
from dicom_organizer.sample_data import create_sample_dataset

REPO = Path(__file__).resolve().parents[1]


def test_module_entry_execution() -> None:
    """Verify python -m dicom_organizer and python -m dicom_organizer.cli print version."""
    version = core.package_version()
    cmd1 = [sys.executable, "-m", "dicom_organizer", "--version"]
    proc1 = subprocess.run(cmd1, capture_output=True, text=True)
    assert proc1.returncode == 0
    assert version in (proc1.stdout + proc1.stderr)

    cmd2 = [sys.executable, "-m", "dicom_organizer.cli", "--version"]
    proc2 = subprocess.run(cmd2, capture_output=True, text=True)
    assert proc2.returncode == 0
    assert version in (proc2.stdout + proc2.stderr)


def test_benchmark_smoke(tmp_path: Path) -> None:
    """Verify benchmark.py executes end-to-end with --files 200 and checks verified_files."""
    json_path = tmp_path / "bench.json"
    md_path = tmp_path / "bench.md"
    cmd = [
        sys.executable,
        str(REPO / "scripts" / "benchmark.py"),
        "--files",
        "200",
        "--matrix",
        "64",
        "--repeat",
        "2",
        "--workdir",
        str(tmp_path / "work"),
        "--output-json",
        str(json_path),
        "--output-markdown",
        str(md_path),
    ]
    sub_env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    proc = subprocess.run(cmd, capture_output=True, text=True, env=sub_env)
    assert proc.returncode == 0, f"Benchmark failed:\n{proc.stderr}"
    assert json_path.is_file()
    assert md_path.is_file()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "machine_info" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["files"] == 200
    modes = data["results"][0]["modes"]
    for m in ("dry", "list", "copy", "checksum"):
        assert m in modes
        assert modes[m]["verified_files"] == 200

    md_text = md_path.read_text(encoding="utf-8")
    assert "|" in md_text
    assert "200" in md_text
    assert "64" in md_text


def test_render_screenshots_smoke(tmp_path: Path) -> None:
    """Verify render_screenshots.py creates required PNG images and before-after text."""
    pytest.importorskip("PySide6.QtWidgets")
    img_dir = tmp_path / "images"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(REPO / "src"))
    cmd = [
        sys.executable,
        str(REPO / "scripts" / "render_screenshots.py"),
        "--output-dir",
        str(img_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"render_screenshots failed:\n{proc.stderr}"

    for name in (
        "start-ja.png",
        "start-en.png",
        "work-list-ja.png",
        "result-list-ja.png",
        "result-list-en.png",
        "result-preview-ja.png",
    ):
        p = img_dir / name
        assert p.is_file()
        assert p.stat().st_size > 0

    before_after = img_dir / "before-after.md"
    assert before_after.is_file()
    text = before_after.read_text(encoding="utf-8")
    for token in ("EXPORT", "DISK1", "IM00001", "all_series_summary", "TE_ms"):
        assert token in text


def test_compare_protocols_functionality(tmp_path: Path) -> None:
    """Verify compare_protocols.py detects differing TE_ms, rejects unknown columns, and groups by protocol."""
    dataset = create_sample_dataset(tmp_path / "raw")
    organized = tmp_path / "organized"
    core.run(core.OrganizeOptions(input_root=dataset.root, output_root=organized))

    script = str(REPO / "examples" / "compare_protocols.py")
    sub_env = dict(os.environ, PYTHONPATH=str(REPO / "src"))

    # 1. Unknown grouping column --by
    bad_by = subprocess.run(
        [sys.executable, script, str(organized), "-o", str(tmp_path / "bad_by.csv"), "--by", "NoSuchColumn"],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert bad_by.returncode == 2
    assert "SeriesDescription" in bad_by.stderr
    assert not (tmp_path / "bad_by.csv").exists()

    # 2. Unknown comparison column --columns
    bad_cols = subprocess.run(
        [sys.executable, script, str(organized), "-o", str(tmp_path / "bad_cols.csv"), "--columns", "TR_ms,Bogus"],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert bad_cols.returncode == 2
    assert "Bogus" in bad_cols.stderr
    assert not (tmp_path / "bad_cols.csv").exists()

    # 3. Successful run with default grouping
    out_csv = tmp_path / "compare.csv"
    good = subprocess.run(
        [sys.executable, script, str(organized / "all_series_summary.csv"), "-o", str(out_csv)],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert good.returncode == 0
    with out_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert "DifferingColumns" in rows[0]
    differing = [r for r in rows if "TE_ms" in r["DifferingColumns"].split("|")]
    assert differing

    # 4. Group by ProtocolName across scanners
    proto_csv = tmp_path / "proto_compare.csv"
    proto_run = subprocess.run(
        [sys.executable, script, str(organized), "-o", str(proto_csv), "--by", "ProtocolName"],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert proto_run.returncode == 0
    with proto_csv.open(encoding="utf-8-sig", newline="") as f:
        proto_rows = [r for r in csv.DictReader(f) if r["ProtocolName"] == "T2"]
    devices = {r["Device"] for r in proto_rows}
    assert len(proto_rows) == 3
    assert len(devices) == 2
    assert all("TE_ms" in r["DifferingColumns"].split("|") for r in proto_rows)


def test_dcm2niix_batch_filtering_and_checks(tmp_path: Path) -> None:
    """Verify dcm2niix_batch.py generates commands with exact non-duplicated paths and rejects invalid options."""
    dataset = create_sample_dataset(tmp_path / "raw")
    organized = tmp_path / "organized"
    core.run(core.OrganizeOptions(input_root=dataset.root, output_root=organized))

    script = str(REPO / "examples" / "dcm2niix_batch.py")
    sub_env = dict(os.environ, PYTHONPATH=str(REPO / "src"))

    # 1. Successful command generation with --match T2 and exact path check
    proc = subprocess.run(
        [sys.executable, script, str(organized), "--match", "T2"],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert proc.returncode == 0, f"dcm2niix_batch failed:\n{proc.stderr}"
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("dcm2niix")]
    assert len(lines) == 3

    nifti_dir = organized.parent / f"{organized.name}_nifti"
    rel_path = "Example-Medical_Demo-MR-3T/20260601/000002_T2"
    expected_cmd = [
        "dcm2niix",
        "-z",
        "y",
        "-f",
        "%p_%t_%s",
        "-o",
        str(nifti_dir / rel_path),
        str(organized / rel_path),
    ]
    parsed_commands = [shlex.split(ln) for ln in lines]
    assert expected_cmd in parsed_commands
    for cmd in parsed_commands:
        target = cmd[cmd.index("-o") + 1]
        assert target.count("20260") == 1

    # 2. Reject --nifti-dir inside organized folder
    nested_run = subprocess.run(
        [sys.executable, script, str(organized), "--nifti-dir", str(organized / "nifti")],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert nested_run.returncode != 0

    # 3. Reject list-only output
    list_dir = tmp_path / "list_dir"
    core.run(core.OrganizeOptions(input_root=dataset.root, output_root=list_dir, list_only=True))
    proc_list = subprocess.run(
        [sys.executable, script, str(list_dir)],
        capture_output=True,
        text=True,
        env=sub_env,
    )
    assert proc_list.returncode != 0
    assert "list-only" in (proc_list.stderr + proc_list.stdout).lower()
