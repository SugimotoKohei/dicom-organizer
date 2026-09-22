"""Deterministic synthetic DICOM sample dataset generator.

Creates synthetic datasets with mixed files in messy directory layouts
to demonstrate organization without using real patient or device data.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import (
    CTImageStorage,
    ExplicitVRLittleEndian,
    MRImageStorage,
    generate_uid,
)

# Standard Grayscale Softcopy Presentation State Storage SOP Class UID
PR_SOP_CLASS_UID = "1.2.840.10008.5.1.4.1.1.11.1"


@dataclass(frozen=True)
class SampleDataset:
    root: Path
    expected: dict[str, int]


def _make_pixel_data() -> bytes:
    """Create simple 16x16 uint16 MONOCHROME2 gradient pixel data."""
    buffer = bytearray(16 * 16 * 2)
    for y in range(16):
        for x in range(16):
            val = (x * 16 + y) * 16
            offset = (y * 16 + x) * 2
            buffer[offset] = val & 0xFF
            buffer[offset + 1] = (val >> 8) & 0xFF
    return bytes(buffer)


def create_sample_dataset(target_dir: Path) -> SampleDataset:
    """Create a deterministic sample DICOM dataset in target_dir."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    export_disk = target_dir / "EXPORT" / "DISK1"
    export_disk.mkdir(parents=True, exist_ok=True)
    backup_dir = target_dir / "BACKUP"
    backup_dir.mkdir(parents=True, exist_ok=True)

    def det_uid(*keys: str | int) -> str:
        srcs = ["dicom-organizer", "sample-v1", *[str(k) for k in keys]]
        return generate_uid(entropy_srcs=srcs)

    studies_def = [
        {
            "study_key": "study_mr_3t_1",
            "study_idx": 1,
            "patient_name": "SAMPLE^ALPHA",
            "patient_id": "SAMPLE_001",
            "study_date": "20260601",
            "manufacturer": "Example Medical",
            "model": "Demo MR 3T",
            "modality": "MR",
            "series": [
                {
                    "name": "T1",
                    "num": 1,
                    "tr": 500.0,
                    "te": 10.0,
                    "ti": None,
                    "fa": 70.0,
                    "dur": 120,
                    "phase_dir": "ROW",
                    "parallel": 1.0,
                },
                {
                    "name": "T2",
                    "num": 2,
                    "tr": 4000.0,
                    "te": 80.0,
                    "ti": None,
                    "fa": 90.0,
                    "dur": 180,
                    "phase_dir": "COL",
                    "parallel": 2.0,
                },
                {
                    "name": "FLAIR",
                    "num": 3,
                    "tr": 9000.0,
                    "te": 120.0,
                    "ti": 2500.0,
                    "fa": 150.0,
                    "dur": 240,
                    "phase_dir": "ROW",
                    "parallel": 1.0,
                },
            ],
            "slices": 3,
        },
        {
            "study_key": "study_mr_3t_2",
            "study_idx": 2,
            "patient_name": "SAMPLE^BETA",
            "patient_id": "SAMPLE_002",
            "study_date": "20260602",
            "manufacturer": "Example Medical",
            "model": "Demo MR 3T",
            "modality": "MR",
            "series": [
                {
                    "name": "T1",
                    "num": 1,
                    "tr": 500.0,
                    "te": 10.0,
                    "ti": None,
                    "fa": 70.0,
                    "dur": 120,
                    "phase_dir": "ROW",
                    "parallel": 1.0,
                },
                {
                    "name": "T2",
                    "num": 2,
                    "tr": 4000.0,
                    "te": 100.0,  # Differentiated from Study 1
                    "ti": None,
                    "fa": 90.0,
                    "dur": 180,
                    "phase_dir": "COL",
                    "parallel": 2.0,
                },
                {
                    "name": "FLAIR",
                    "num": 3,
                    "tr": 9000.0,
                    "te": 120.0,
                    "ti": 2500.0,
                    "fa": 150.0,
                    "dur": 240,
                    "phase_dir": "ROW",
                    "parallel": 1.0,
                },
            ],
            "slices": 3,
        },
        {
            "study_key": "study_mr_15t_1",
            "study_idx": 3,
            "patient_name": "SAMPLE^GAMMA",
            "patient_id": "SAMPLE_003",
            "study_date": "20260603",
            "manufacturer": "Example Medical",
            "model": "Demo MR 1.5T",
            "modality": "MR",
            "series": [
                {
                    "name": "T1",
                    "num": 1,
                    "tr": 450.0,
                    "te": 12.0,
                    "ti": None,
                    "fa": 70.0,
                    "dur": 100,
                    "phase_dir": "ROW",
                    "parallel": 1.0,
                },
                {
                    "name": "T2",
                    "num": 2,
                    "tr": 3500.0,
                    "te": 90.0,
                    "ti": None,
                    "fa": 90.0,
                    "dur": 160,
                    "phase_dir": "COL",
                    "parallel": 2.0,
                },
                {
                    "name": "FLAIR",
                    "num": 3,
                    "tr": 8000.0,
                    "te": 110.0,
                    "ti": 2200.0,
                    "fa": 140.0,
                    "dur": 210,
                    "phase_dir": "ROW",
                    "parallel": 1.0,
                },
            ],
            "slices": 3,
        },
        {
            "study_key": "study_ct_1",
            "study_idx": 4,
            "patient_name": "SAMPLE^DELTA",
            "patient_id": "SAMPLE_004",
            "study_date": "20260604",
            "manufacturer": "Example Medical",
            "model": "Demo CT",
            "modality": "CT",
            "series": [
                {
                    "name": "Axial CT",
                    "num": 1,
                    "kvp": 120.0,
                    "ma": 200.0,
                    "exp": 500.0,
                    "thick": 5.0,
                    "spacing": [0.8, 0.8],
                },
            ],
            "slices": 3,
        },
    ]

    pixel_data = _make_pixel_data()
    file_counter = 1
    image_file_count = 0
    series_ids: set[str] = set()
    image_series_ids: set[str] = set()

    for st in studies_def:
        study_folder = export_disk / f"{st['study_idx']:04d}"
        study_folder.mkdir(parents=True, exist_ok=True)
        study_uid = det_uid(st["study_key"])

        # Interleave instances across series within this study
        instances_to_write = []
        num_slices = st["slices"]
        for slice_idx in range(1, num_slices + 1):
            for s_info in st["series"]:
                series_uid = det_uid(st["study_key"], s_info["num"])
                sop_uid = det_uid(st["study_key"], s_info["num"], slice_idx)
                instances_to_write.append((s_info, slice_idx, series_uid, sop_uid))

        for s_info, slice_idx, series_uid, sop_uid in instances_to_write:
            file_name = f"IM{file_counter:05d}"
            file_path = study_folder / file_name
            file_counter += 1

            meta = FileMetaDataset()
            if st["modality"] == "MR":
                sop_class = MRImageStorage
            else:
                sop_class = CTImageStorage
            meta.MediaStorageSOPClassUID = sop_class
            meta.MediaStorageSOPInstanceUID = sop_uid
            meta.TransferSyntaxUID = ExplicitVRLittleEndian
            meta.ImplementationClassUID = det_uid("impl")

            ds = FileDataset(str(file_path), {}, file_meta=meta, preamble=b"\0" * 128)
            ds.SOPClassUID = sop_class
            ds.SOPInstanceUID = sop_uid
            ds.StudyInstanceUID = study_uid
            ds.SeriesInstanceUID = series_uid
            ds.FrameOfReferenceUID = det_uid(st["study_key"], "frame")
            ds.Modality = st["modality"]
            ds.PatientName = st["patient_name"]
            ds.PatientID = st["patient_id"]
            ds.StudyDate = st["study_date"]
            ds.AcquisitionDate = st["study_date"]
            ds.SeriesDate = st["study_date"]
            ds.SeriesNumber = s_info["num"]
            ds.InstanceNumber = slice_idx
            ds.SeriesDescription = f"{st['model']} {s_info['name']}"
            ds.ProtocolName = s_info["name"]
            ds.Manufacturer = st["manufacturer"]
            ds.ManufacturerModelName = st["model"]
            ds.Rows = 16
            ds.Columns = 16
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 0
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.PixelData = pixel_data

            if st["modality"] == "MR":
                ds.RepetitionTime = s_info["tr"]
                ds.EchoTime = s_info["te"]
                if s_info.get("ti") is not None:
                    ds.InversionTime = s_info["ti"]
                ds.FlipAngle = s_info["fa"]
                ds.SliceThickness = 3.0
                ds.PixelSpacing = [1.0, 1.0]
                ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
                ds.ImagePositionPatient = [0, 0, float((slice_idx - 1) * 3)]
                ds.InPlanePhaseEncodingDirection = s_info["phase_dir"]
                ds.ParallelReductionFactorInPlane = s_info["parallel"]
                ds.AcquisitionDuration = float(s_info["dur"])
            else:
                ds.KVP = s_info["kvp"]
                ds.XRayTubeCurrent = s_info["ma"]
                ds.ExposureTime = s_info["exp"]
                ds.SliceThickness = s_info["thick"]
                ds.PixelSpacing = s_info["spacing"]
                ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
                ds.ImagePositionPatient = [0, 0, float((slice_idx - 1) * 5)]

            ds.save_as(file_path, enforce_file_format=True)
            image_file_count += 1
            series_ids.add(series_uid)
            image_series_ids.add(series_uid)

    # Add 1 non-image presentation state object into study 1 folder
    study_1_folder = export_disk / "0001"
    pr_sop_uid = det_uid("study_mr_3t_1", "pr", 1)
    pr_series_uid = det_uid("study_mr_3t_1", "pr_series")
    pr_file_path = study_1_folder / f"IM{file_counter:05d}"
    file_counter += 1

    pr_meta = FileMetaDataset()
    pr_meta.MediaStorageSOPClassUID = PR_SOP_CLASS_UID
    pr_meta.MediaStorageSOPInstanceUID = pr_sop_uid
    pr_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    pr_meta.ImplementationClassUID = det_uid("impl")

    pr_ds = FileDataset(str(pr_file_path), {}, file_meta=pr_meta, preamble=b"\0" * 128)
    pr_ds.SOPClassUID = PR_SOP_CLASS_UID
    pr_ds.SOPInstanceUID = pr_sop_uid
    pr_ds.StudyInstanceUID = det_uid("study_mr_3t_1")
    pr_ds.SeriesInstanceUID = pr_series_uid
    pr_ds.Modality = "PR"
    pr_ds.PatientName = "SAMPLE^ALPHA"
    pr_ds.PatientID = "SAMPLE_001"
    pr_ds.StudyDate = "20260601"
    pr_ds.AcquisitionDate = "20260601"
    pr_ds.SeriesDate = "20260601"
    pr_ds.SeriesNumber = 99
    pr_ds.InstanceNumber = 1
    pr_ds.SeriesDescription = "Presentation State"
    pr_ds.ProtocolName = "PR"
    pr_ds.Manufacturer = "Example Medical"
    pr_ds.ManufacturerModelName = "Demo MR 3T"
    pr_ds.save_as(pr_file_path, enforce_file_format=True)
    series_ids.add(pr_series_uid)

    # Add non-DICOM README.TXT
    readme_path = target_dir / "EXPORT" / "README.TXT"
    readme_path.write_text("Export disk created by Example Medical imaging system.\n", encoding="utf-8")

    # Add duplicate file in BACKUP
    first_image = sorted(export_disk.rglob("IM*"))[0]
    shutil.copyfile(first_image, backup_dir / first_image.name)

    total_organized_files = image_file_count + 1  # images + PR
    expected = {
        "organized_files": total_organized_files,
        "csv_target_files": image_file_count,
        "series_count": len(series_ids),
        "image_series_count": len(image_series_ids),
        "study_count": len(studies_def),
        "not_dicom": 1,
        "duplicate_identical": 1,
        "candidate_files": total_organized_files + 1 + 1,  # organized + non_dicom + duplicate
    }

    return SampleDataset(root=target_dir, expected=expected)
