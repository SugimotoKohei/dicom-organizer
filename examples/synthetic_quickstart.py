"""Create synthetic DICOM files and run dicom-organizer.

This example intentionally avoids real patient or scanner data by using
the built-in deterministic sample dataset generator.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from dicom_organizer.sample_data import create_sample_dataset


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="dicom-organizer-example-") as tmp:
        root = Path(tmp)
        dataset = create_sample_dataset(root / "sample_data")

        command = [
            "dicom-organizer",
            str(dataset.root),
            "--patient-mode",
            "drop",
        ]
        subprocess.run(command, check=True)

        output_root = dataset.root / "organized"
        print(f"Synthetic DICOM input: {dataset.root}")
        print(f"Organized output: {output_root}")
        print((output_root / "organize_summary.json").read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
