#!/usr/bin/env python3
"""Render GUI screenshots and demo GIF for documentation.

Uses PySide6 in offscreen mode to capture light-themed, sanitized screenshots
of the start page, task setup, listing results, and dry-run preview results.
Outputs PNGs and demo-ja.gif to docs/images/, along with before-after.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtGui import QColor, QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import dicom_organizer.core as core  # noqa: E402
from dicom_organizer import gui  # noqa: E402
from dicom_organizer.sample_data import create_sample_dataset  # noqa: E402

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 860


def apply_light_theme(app: QApplication) -> None:
    """Configure a clean, high-contrast light theme with standard macOS/system fonts."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(248, 249, 250))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(25, 30, 36))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(243, 244, 246))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(25, 30, 36))
    palette.setColor(QPalette.ColorRole.Text, QColor(25, 30, 36))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 242, 245))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(25, 30, 36))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(10, 102, 194))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    font = app.font()
    font.setPointSize(13)
    app.setFont(font)


def render_window_to_png(window: gui.MainWindow, output_path: Path) -> None:
    """Ensure layout is updated and save window rendering to PNG."""
    app = QApplication.instance()
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.show()
    for _ in range(5):
        app.processEvents()

    pixmap = window.grab()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(output_path), "PNG")
    print(f"Rendered: {output_path} ({pixmap.width()}x{pixmap.height()})")


def _format_tree(root_dir: Path, max_files_per_dir: int = 3) -> str:
    lines = [f"{root_dir.name}/"]

    def _walk(directory: Path, prefix: str) -> None:
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        dirs = [e for e in entries if e.is_dir()]
        files = [e for e in entries if e.is_file()]

        items: list[tuple[Path, bool, bool]] = []
        for d in dirs:
            items.append((d, True, False))

        if len(files) > max_files_per_dir:
            for f in files[:max_files_per_dir]:
                items.append((f, False, False))
            items.append((directory / "...", False, True))
        else:
            for f in files:
                items.append((f, False, False))

        count = len(items)
        for idx, (item, is_dir, is_ell) in enumerate(items):
            is_last = idx == count - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            if is_ell:
                lines.append(f"{prefix}{connector}...")
            elif is_dir:
                lines.append(f"{prefix}{connector}{item.name}/")
                _walk(item, child_prefix)
            else:
                lines.append(f"{prefix}{connector}{item.name}")

    _walk(root_dir, "")
    return "\n".join(lines)


def write_before_after_markdown(output_path: Path) -> None:
    """Dynamically generate deterministic sample input and output trees and summary excerpt."""
    with tempfile.TemporaryDirectory(prefix="dicom_ba_gen_") as tmp_str:
        tmp = Path(tmp_str)
        sample_root = tmp / "sample_dataset"
        create_sample_dataset(sample_root)

        organized_root = tmp / "organized"
        core.run(core.OrganizeOptions(input_root=sample_root, output_root=organized_root))

        input_tree = _format_tree(sample_root, max_files_per_dir=3)
        output_tree = _format_tree(organized_root, max_files_per_dir=3)

        summary_json_path = organized_root / "organize_summary.json"
        summary_data = json.loads(summary_json_path.read_text(encoding="utf-8"))
        candidate_count = summary_data.get("candidate_files", 0)
        organized_count = summary_data.get("organized_files", 0)

        file_report_path = organized_root / "file_report.csv"
        unprocessed_by_reason: dict[str, list[tuple[str, str]]] = {}
        with file_report_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("Status") != "organized":
                    reason = row.get("Reason", "unprocessed")
                    src = row.get("SourceFileName", "")
                    dup = row.get("DuplicateOf", "N/A")
                    unprocessed_by_reason.setdefault(reason, []).append((src, dup))

        unprocessed_lines = []
        for reason in sorted(unprocessed_by_reason):
            items = unprocessed_by_reason[reason]
            desc_items = []
            for src, dup in sorted(items):
                if dup and dup != "N/A":
                    desc_items.append(f"`{src}` (duplicate of `{dup}`)")
                else:
                    desc_items.append(f"`{src}`")
            files_str = ", ".join(desc_items)
            unprocessed_lines.append(
                f"  - `{reason}`: {len(items)} file(s) ({files_str})"
            )

        all_summary_path = organized_root / "all_series_summary.csv"
        table_rows = []
        with all_summary_path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                table_rows.append((
                    r.get("StudyFolder", "N/A"),
                    r.get("SeriesFolder", "N/A"),
                    r.get("SeriesDescription", "N/A"),
                    r.get("Modality", "N/A"),
                    r.get("TR_ms", "N/A"),
                    r.get("TE_ms", "N/A"),
                    r.get("FlipAngle_deg", "N/A"),
                    r.get("ScanDuration", "N/A"),
                ))

        table_rows.sort(key=lambda r: (r[0], r[1]))

    unprocessed_block = "\n".join(unprocessed_lines)

    table_lines = [
        "| StudyFolder | SeriesFolder | SeriesDescription | Modality | TR_ms | TE_ms | FlipAngle_deg | ScanDuration |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in table_rows:
        table_lines.append(
            f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]} | {row[7]} |"
        )
    table_block = "\n".join(table_lines)

    content = f"""# Sample DICOM Organization Example (Before & After) / 整理前後の実例

## 1. Input Structure / 整理前の入力ツリー

The raw input directory contains DICOM slices exported across nested media folders (`EXPORT/DISK1/...`), identical copies in `BACKUP/` (`BACKUP/IM00001`), and non-DICOM documentation files (`README.TXT`):
整理前の入力フォルダには、入れ子になった媒体フォルダ（`EXPORT/DISK1/...`）の DICOM 画像、`BACKUP/` にある同一画像のコピー（`BACKUP/IM00001`）、および DICOM 以外の説明ファイル（`README.TXT`）が含まれています:

```text
{input_tree}
```

## 2. Organized Output Structure / 整理後の出力ツリー

When organized using the default layout (`device-date`), DICOM files are sorted into stable series directories with standardized metadata summaries:

```text
{output_tree}
```

## 3. File Processing Summary / 入力ファイル処理状況の内訳

- Candidate Files / 検出ファイル総数: {candidate_count}
- Successfully Organized / 整理完了ファイル数: {organized_count}
- Unprocessed Files by Reason / 未処理の理由ごとの内訳:
{unprocessed_block}

本体は、フォルダ名・ファイル名を並び順にたどって最初に見つけたファイルを整理し、同じ SOPInstanceUID で内容も同じ後のファイルを `duplicate_identical` として記録します。どのファイルの重複かは `file_report.csv` の `DuplicateOf` 列に出ます。
When scanning files in alphabetical order, the first instance found is organized, while subsequent files with identical content and SOPInstanceUID are skipped and recorded as `duplicate_identical`. The `DuplicateOf` column in `file_report.csv` shows which file was duplicated.

## 4. Extracted Imaging Parameters / 抽出された撮像条件の抜粋 (`all_series_summary.csv`)

`all_series_summary.csv` aggregates modality parameters across all studies:

{table_block}
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"Saved before-after example to: {output_path}")


def create_demo_gif(png_paths: list[Path], gif_path: Path) -> None:
    """Create demo animated GIF using magick, ffmpeg, or Pillow."""
    magick = shutil.which("magick")
    if magick:
        cmd = [
            magick,
            "-delay",
            "180",
            "-loop",
            "0",
            "-resize",
            "960x645",
            *[str(p) for p in png_paths],
            str(gif_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and gif_path.is_file():
            print(f"Generated GIF using ImageMagick: {gif_path}")
            return

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg and len(png_paths) >= 2:
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp = Path(tmp_d)
            for idx, p in enumerate(png_paths):
                shutil.copyfile(p, tmp / f"frame_{idx:02d}.png")
            filter_str = (
                "fps=0.5,scale=960:645:flags=lanczos,split[s0][s1];"
                "[s0]palettegen[p];[s1][p]paletteuse"
            )
            cmd = [
                ffmpeg,
                "-y",
                "-framerate",
                "0.5",
                "-i",
                str(tmp / "frame_%02d.png"),
                "-vf",
                filter_str,
                str(gif_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and gif_path.is_file():
                print(f"Generated GIF using ffmpeg: {gif_path}")
                return

    try:
        from PIL import Image

        images = [Image.open(p) for p in png_paths]
        resized = [img.resize((960, 645), Image.Resampling.LANCZOS) for img in images]
        resized[0].save(
            str(gif_path),
            save_all=True,
            append_images=resized[1:],
            duration=1800,
            loop=0,
            optimize=True,
        )
        print(f"Generated GIF using Pillow: {gif_path}")
        return
    except Exception:
        pass

    print(
        "Notice: Neither ImageMagick (magick), ffmpeg, nor Pillow is available. "
        "Skipping demo-ja.gif generation.",
        file=sys.stderr,
    )


def run_gui_and_wait(
    window: gui.MainWindow,
    input_path: Path,
    output_path: Path,
    display_input: str,
    display_output: str,
    expected_status: str | None = None,
) -> None:
    """Run process through actual worker execution and sanitize paths for screenshots."""
    if expected_status is None:
        expected_status = "dry_run" if window.current_task == "preview" else "completed"
    app = QApplication.instance()
    window.input_edit.setText(str(input_path))
    window.output_edit.setText(str(output_path))
    window._output_manually_edited = True
    window._on_run_clicked()
    deadline = time.time() + 60
    while window.is_running and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    for _ in range(10):
        app.processEvents()

    if window.is_running:
        raise TimeoutError("GUI execution did not finish within 60 seconds")

    last_result = getattr(window, "last_result", None)
    actual_status = getattr(last_result, "status", None) if last_result else None
    if actual_status != expected_status:
        raise RuntimeError(
            f"GUI execution finished with unexpected status: got {actual_status!r}, expected {expected_status!r}"
        )

    # Sanitize input and output paths so temporary directory paths don't appear in screenshots
    window.input_edit.setText(display_input)
    window.output_edit.setText(display_output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render screenshots and demo GIF for documentation.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "images",
        help="Directory to save generated PNG and GIF files.",
    )
    parser.add_argument(
        "--gif",
        action="store_true",
        default=False,
        help="Generate demo-ja.gif from screenshots.",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv[:1])
    apply_light_theme(app)

    with tempfile.TemporaryDirectory(prefix="dicom_ss_") as tmp_dir:
        tmp = Path(tmp_dir)
        settings_ini = tmp / "settings.ini"

        # Create sample dataset
        dataset = create_sample_dataset(tmp / "sample")

        # 1. start-ja.png
        settings = QSettings(str(settings_ini), QSettings.Format.IniFormat)
        window_ja = gui.MainWindow(settings=settings, language="ja")
        window_ja.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        window_ja.stack.setCurrentIndex(0)
        render_window_to_png(window_ja, output_dir / "start-ja.png")

        # 2. start-en.png
        window_en = gui.MainWindow(settings=settings, language="en")
        window_en.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        window_en.stack.setCurrentIndex(0)
        render_window_to_png(window_en, output_dir / "start-en.png")

        # 3. work-list-ja.png
        window_ja.select_task("list")
        window_ja.input_edit.setText("~/sample_dicom")
        window_ja.output_edit.setText("~/sample_dicom/organized_list")
        window_ja._update_privacy_panel()
        window_ja.scroll_area.verticalScrollBar().setValue(0)
        render_window_to_png(window_ja, output_dir / "work-list-ja.png")

        # 4. result-list-ja.png
        window_ja.select_task("list")
        run_gui_and_wait(
            window_ja,
            dataset.root,
            tmp / "list_ja_out",
            "~/sample_dicom",
            "~/sample_dicom/organized_list",
            expected_status="completed",
        )
        render_window_to_png(window_ja, output_dir / "result-list-ja.png")

        # 5. result-list-en.png
        window_en.select_task("list")
        run_gui_and_wait(
            window_en,
            dataset.root,
            tmp / "list_en_out",
            "~/sample_dicom",
            "~/sample_dicom/organized_list",
            expected_status="completed",
        )
        render_window_to_png(window_en, output_dir / "result-list-en.png")

        # 6. result-preview-ja.png
        window_ja.select_task("preview")
        run_gui_and_wait(
            window_ja,
            dataset.root,
            tmp / "preview_ja_out",
            "~/sample_dicom",
            "~/sample_dicom/organized",
            expected_status="dry_run",
        )
        render_window_to_png(window_ja, output_dir / "result-preview-ja.png")

        window_ja.close()
        window_en.close()

    # 7. before-after.md
    write_before_after_markdown(output_dir / "before-after.md")

    # 8. demo-ja.gif
    if args.gif:
        gif_frames = [
            output_dir / "start-ja.png",
            output_dir / "work-list-ja.png",
            output_dir / "result-list-ja.png",
            output_dir / "result-preview-ja.png",
        ]
        create_demo_gif(gif_frames, output_dir / "demo-ja.gif")

    print("\nAll documentation screenshots and examples rendered successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
