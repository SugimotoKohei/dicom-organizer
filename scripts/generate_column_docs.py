#!/usr/bin/env python3
"""Generate docs/csv-columns.md from COLUMN_SPECS in dicom_organizer.columns."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dicom_organizer.columns import COLUMN_SPECS  # noqa: E402


def escape_cell(text: str) -> str:
    """Escape pipe characters and line breaks for Markdown table cells."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown() -> str:
    """Build the complete Markdown content for docs/csv-columns.md."""
    lines: list[str] = [
        "# CSV Column Dictionary",
        "",
        (
            "This document provides a comprehensive dictionary of all CSV columns "
            "output by `dicom-organizer`, including their definitions, measurement units, "
            "data sources, missing (`N/A`) conditions, and applicable metadata profiles."
        ),
        "",
        (
            "For the schema architecture, file row scopes, and folder layout options, "
            "see [CSV Schema (csv-schema.md)](csv-schema.md)."
        ),
        "",
        "## Conventions",
        "",
        "- **Missing Values**: Represented as `N/A`.",
        "- **Multiple Values**: Distinct values within a series or across frames are joined with `|`.",
        (
            "- **DICOM Multi-Valued Attributes**: Standard backslash `\\` delimiter "
            "is preserved for multi-valued DICOM elements (VM > 1)."
        ),
        "- **Dates and Times**: Dates follow DICOM DA format (`YYYYMMDD`); times follow DICOM TM format as-is.",
        "- **Character Encoding**: CSV files are encoded in UTF-8 with BOM (`utf-8-sig`) for Excel compatibility.",
        (
            "- **Custom Tags**: Requested via `--dicom-tag` as `DICOM_<Keyword>` "
            "(or user-specified alias) with user-selected DICOM tag sources."
        ),
        "",
        "## Column Specifications (English)",
        "",
        "| Column | Description | Unit | Source | Missing (N/A) Condition | Profiles |",
        "|---|---|---|---|---|---|",
    ]

    for spec in COLUMN_SPECS:
        profiles_str = ", ".join(spec.profiles) if spec.profiles else "all"
        lines.append(
            f"| `{escape_cell(spec.name)}` | {escape_cell(spec.description_en)} | "
            f"{escape_cell(spec.unit)} | {escape_cell(spec.source)} | "
            f"{escape_cell(spec.missing)} | {escape_cell(profiles_str)} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 日本語 (Japanese)",
            "",
            (
                "この文書は `dicom-organizer` が出力するすべての CSV 列の意味、単位、"
                "取得元、N/A（欠損）になる条件、および対象プロファイルの完全な一覧です。"
            ),
            "",
            (
                "出力ファイル全体の構成やフォルダレイアウトについては "
                "[CSV スキーマ (csv-schema.md)](csv-schema.md) を参照してください。"
            ),
            "",
            "### 値の規則",
            "",
            "- **欠損値**: `N/A` で表記されます。",
            (
                "- **シリーズ・フレーム間の複数値**: シリーズ内またはフレーム間で値が複数存在する場合、"
                "重複を除いて `|` で連結されます。"
            ),
            "- **DICOM 多値属性**: DICOM の多値要素（VM > 1）は標準のバックスラッシュ `\\` で区切られます。",
            "- **日付・時刻**: 日付は DICOM DA 形式（`YYYYMMDD`）、時刻は DICOM TM 形式をそのまま出力します。",
            "- **文字コード**: Excel でそのまま開けるよう、UTF-8 BOM 付き（`utf-8-sig`）で出力されます。",
            (
                "- **追加タグ**: `--dicom-tag` で指定したタグは `DICOM_<Keyword>`"
                "（または指定名）として出力されます。"
            ),
            "",
            "### 列定義一覧",
            "",
            "| 列名 | 意味 | 単位 | 取得元 | N/A になる条件 | 対象プロファイル |",
            "|---|---|---|---|---|---|",
        ]
    )

    for spec in COLUMN_SPECS:
        profiles_ja = ", ".join(spec.profiles) if spec.profiles else "共通"
        lines.append(
            f"| `{escape_cell(spec.name)}` | {escape_cell(spec.description_ja)} | "
            f"{escape_cell(spec.unit)} | {escape_cell(spec.source)} | "
            f"{escape_cell(spec.missing)} | {escape_cell(profiles_ja)} |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify docs/csv-columns.md from column dictionary."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if docs/csv-columns.md matches generated content without writing.",
    )
    args = parser.parse_args()

    target_path = REPO_ROOT / "docs" / "csv-columns.md"
    content = build_markdown()

    if args.check:
        if not target_path.is_file():
            print(f"Error: {target_path} does not exist.", file=sys.stderr)
            return 1
        existing = target_path.read_text(encoding="utf-8")
        if existing != content:
            print(
                f"Error: {target_path} is out of date. "
                "Run `python scripts/generate_column_docs.py` to update it.",
                file=sys.stderr,
            )
            return 1
        print(f"{target_path} is up to date.")
        return 0

    target_path.write_text(content, encoding="utf-8")
    print(f"Successfully generated {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
