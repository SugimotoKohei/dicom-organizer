"""Create synthetic DICOM files and run organize-dicoms.

This example intentionally avoids real patient or scanner data.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid


def write_synthetic_dicom(path: Path, *, series_uid: str, series_number: int, instance: int) -> None:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.Modality = "MR"
    ds.AcquisitionDate = "20260516"
    ds.StudyDate = "20260516"
    ds.SeriesDate = "20260516"
    ds.SeriesNumber = series_number
    ds.InstanceNumber = instance
    ds.SeriesDescription = f"Synthetic Series {series_number}"
    ds.ProtocolName = f"Synthetic Protocol {series_number}"
    ds.PatientName = "Synthetic^Patient"
    ds.PatientID = "SYNTHETIC001"
    ds.RepetitionTime = 1000
    ds.EchoTime = 10 + series_number
    ds.Rows = 16
    ds.Columns = 16
    ds.PixelSpacing = [1.5, 1.5]
    ds.ImageType = ["ORIGINAL", "PRIMARY"]
    ds.Manufacturer = "Synthetic"
    ds.ManufacturerModelName = "Synthetic"
    ds.save_as(path, enforce_file_format=True)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="organize-dicoms-example-") as tmp:
        root = Path(tmp)
        input_root = root / "input"
        input_root.mkdir()

        for series_number in (1, 2):
            series_uid = generate_uid()
            for instance in (1, 2):
                write_synthetic_dicom(
                    input_root / f"series{series_number}_image{instance}.dcm",
                    series_uid=series_uid,
                    series_number=series_number,
                    instance=instance,
                )

        command = [
            "organize-dicoms",
            "--input",
            str(input_root),
            "--patient-mode",
            "drop",
        ]
        subprocess.run(command, check=True)

        output_root = input_root / "organized"
        print(f"Synthetic DICOM input: {input_root}")
        print(f"Organized output: {output_root}")
        print((output_root / "organize_summary.json").read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
