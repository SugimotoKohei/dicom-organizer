"""Support matrix verification tests for DICOM transfer syntaxes, charsets, and objects.

These synthetic tests verify supported capabilities referenced in documentation:
- Compressed transfer syntaxes (JPEG Baseline, JPEG 2000 Lossless)
- Multi-byte character sets (UTF-8 ISO_IR 192, ISO 2022 IR 87)
- Non-image objects (Basic Text SR, RT Structure Set)
- Preamble-less DICOM files (force-read vs no-force-read)
- DICOMDIR media directory handling
- Enhanced MR functional groups
- Private tag parameter extraction fallbacks (Siemens ASCCONV, GE GEMS_ACQU_01)
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.encaps import encapsulate
from pydicom.fileset import FileSet
from pydicom.sequence import Sequence
from pydicom.uid import (
    EnhancedMRImageStorage,
    ExplicitVRLittleEndian,
    MRImageStorage,
    generate_uid,
)

import dicom_organizer.core as core
from test_dicom_organizer import write_dicom

JPEG_BASELINE_SYNTAX = "1.2.840.10008.1.2.4.50"
JPEG_2000_LOSSLESS_SYNTAX = "1.2.840.10008.1.2.4.90"
BASIC_TEXT_SR_STORAGE = "1.2.840.10008.5.1.4.1.1.88.11"
RT_STRUCTURE_SET_STORAGE = "1.2.840.10008.5.1.4.1.1.481.3"
DICOMDIR_STORAGE = "1.2.840.10008.1.3.10"


def _create_encapsulated_file(
    path: Path,
    transfer_syntax_uid: str,
    sop_uid: str,
    series_uid: str,
    tr: float,
    te: float,
) -> None:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = transfer_syntax_uid
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = generate_uid()
    ds.Modality = "MR"
    ds.PatientName = "COMP^SAMPLE"
    ds.PatientID = "PID_COMP"
    ds.StudyDate = "20260601"
    ds.SeriesDate = "20260601"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.SeriesDescription = f"Compressed {transfer_syntax_uid.split('.')[-1]}"
    ds.ProtocolName = "Compressed Proto"
    ds.Manufacturer = "Synthetic Vendor"
    ds.ManufacturerModelName = "Compress 3T"
    ds.RepetitionTime = tr
    ds.EchoTime = te
    ds.FlipAngle = 90.0
    ds.Rows = 16
    ds.Columns = 16
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"

    fake_compressed_frame = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 48 + b"\xff\xd9"
    ds.PixelData = encapsulate([fake_compressed_frame])
    ds.save_as(path, enforce_file_format=True)


def test_compressed_transfer_syntax_jpeg_baseline_and_lossless(tmp_path: Path) -> None:
    """1. Verify JPEG Baseline and JPEG 2000 Lossless encapsulated files are organized with byte-identical SHA-256."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"

    s_uid1 = generate_uid()
    f1 = in_dir / "jpeg_baseline.dcm"
    _create_encapsulated_file(
        f1,
        transfer_syntax_uid="1.2.840.10008.1.2.4.50",
        sop_uid=generate_uid(),
        series_uid=s_uid1,
        tr=2500.0,
        te=45.0,
    )

    s_uid2 = generate_uid()
    f2 = in_dir / "jpeg_2000.dcm"
    _create_encapsulated_file(
        f2,
        transfer_syntax_uid="1.2.840.10008.1.2.4.90",
        sop_uid=generate_uid(),
        series_uid=s_uid2,
        tr=3200.0,
        te=90.0,
    )

    sha1_in = hashlib.sha256(f1.read_bytes()).hexdigest()
    sha2_in = hashlib.sha256(f2.read_bytes()).hexdigest()

    res = core.run(core.OrganizeOptions(input_root=in_dir, output_root=out_dir))
    assert res.status == "completed"
    assert len(res.items) == 2

    # Verify byte-identical preservation via SHA-256 (P8)
    out_files = list(out_dir.rglob("*.dcm"))
    assert len(out_files) == 2
    out_shas = {hashlib.sha256(p.read_bytes()).hexdigest() for p in out_files}
    assert sha1_in in out_shas
    assert sha2_in in out_shas

    csv_path = out_dir / "all_series_summary.csv"
    assert csv_path.is_file()
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    tr_values = {float(r["TR_ms"]) for r in rows}
    te_values = {float(r["TE_ms"]) for r in rows}
    assert tr_values == {2500.0, 3200.0}
    assert te_values == {45.0, 90.0}


def test_charset_encoding_utf8_and_iso_2022_ir_87(tmp_path: Path) -> None:
    """2. Verify UTF-8 (ISO_IR 192) and ISO 2022 IR 87 Japanese strings in headers and safe_name() folder labels."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"

    # UTF-8: SpecificCharacterSet = "ISO_IR 192"
    f_utf8 = in_dir / "utf8.dcm"
    write_dicom(
        f_utf8,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        patient_name="山田^太郎",
        series_description="頭部 T2",
        protocol_name="頭部 T2",
        specific_character_set="ISO_IR 192",
    )

    # ISO 2022 IR 87: SpecificCharacterSet = ["", "ISO 2022 IR 87"]
    f_iso = in_dir / "iso.dcm"
    write_dicom(
        f_iso,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        patient_name="Yamada^Tarou=山田^太郎",
        series_description="Pelvis T1",
        protocol_name="Pelvis T1",
        specific_character_set=["", "ISO 2022 IR 87"],
    )

    res = core.run(
        core.OrganizeOptions(input_root=in_dir, output_root=out_dir, patient_mode="keep")
    )
    assert res.status == "completed"
    assert len(res.items) == 2

    csv_path = out_dir / "all_series_summary.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2

    utf8_row = next(r for r in rows if r["SeriesNumber"] == "000001")
    assert "山田^太郎" in utf8_row["PatientName"]
    assert "頭部 T2" in utf8_row["SeriesDescription"]

    # Verify folder name follows safe_name() exact rules and the directory exists (P8)
    expected_utf8_suffix = f"000001_{core.safe_name('頭部 T2')}"
    assert utf8_row["SeriesFolder"].endswith(expected_utf8_suffix)
    assert (out_dir / utf8_row["SeriesFolder"]).is_dir()

    iso_row = next(r for r in rows if r["SeriesNumber"] == "000002")
    assert "山田^太郎" in iso_row["PatientName"]
    assert iso_row["SeriesDescription"] == "Pelvis T1"
    expected_iso_suffix = f"000002_{core.safe_name('Pelvis T1')}"
    assert iso_row["SeriesFolder"].endswith(expected_iso_suffix)
    assert (out_dir / iso_row["SeriesFolder"]).is_dir()


def test_non_image_objects_sr_and_rtstruct(tmp_path: Path) -> None:
    """3. Verify Basic Text SR and RTSTRUCT are organized into folders and verified via file_report.csv."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"

    # 1. Normal MR image
    write_dicom(
        in_dir / "image.dcm",
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        modality="MR",
    )

    # 2. Basic Text SR
    sr_path = in_dir / "sr.dcm"
    write_dicom(
        sr_path,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=90,
        instance_number=1,
        modality="SR",
        sop_class_uid=BASIC_TEXT_SR_STORAGE,
    )

    # 3. RT Structure Set
    rt_path = in_dir / "rtstruct.dcm"
    write_dicom(
        rt_path,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=91,
        instance_number=1,
        modality="RTSTRUCT",
        sop_class_uid=RT_STRUCTURE_SET_STORAGE,
    )

    res = core.run(core.OrganizeOptions(input_root=in_dir, output_root=out_dir))
    assert res.status == "completed"
    assert len(res.items) == 3
    assert res.summary["csv_excluded_files"] == 2
    assert res.summary["csv_excluded_files_by_modality"]["SR"] == 1
    assert res.summary["csv_excluded_files_by_modality"]["RTSTRUCT"] == 1

    # Verify SR and RTSTRUCT via file_report.csv and confirm destination files exist (P8)
    file_report_path = out_dir / "file_report.csv"
    assert file_report_path.is_file()
    with file_report_path.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))

    sr_rec = next(r for r in records if "sr.dcm" in r["SourceFileName"])
    assert sr_rec["Status"] == "organized"
    assert (out_dir / sr_rec["OrganizedFileName"]).is_file()

    rt_rec = next(r for r in records if "rtstruct.dcm" in r["SourceFileName"])
    assert rt_rec["Status"] == "organized"
    assert (out_dir / rt_rec["OrganizedFileName"]).is_file()

    # CSV contains only the MR image series
    csv_path = out_dir / "all_series_summary.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["Modality"] == "MR"


def test_preamble_missing_force_read_and_no_force_read(tmp_path: Path) -> None:
    """4. Verify preamble-less DICOM files organize under default force-read and are skipped under --no-force-read."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    nopreamble_path = in_dir / "raw_stream.dcm"

    ds = Dataset()
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.Modality = "MR"
    ds.PatientName = "NOPREAMBLE^PATIENT"
    ds.PatientID = "PID_NO_PREAMBLE"
    ds.StudyDate = "20260601"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.SeriesDescription = "No Preamble MR"
    ds.Rows = 16
    ds.Columns = 16
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = b"\x00" * (16 * 16 * 2)

    from pydicom.filebase import DicomFile
    from pydicom.filewriter import write_dataset

    with DicomFile(str(nopreamble_path), "wb") as fp:
        fp.is_little_endian = True
        fp.is_implicit_VR = True
        write_dataset(fp, ds)

    # 1. Default force_read=True: organized successfully
    out_force = tmp_path / "out_force"
    res_force = core.run(
        core.OrganizeOptions(input_root=in_dir, output_root=out_force, force_read=True)
    )
    assert res_force.status == "completed"
    assert len(res_force.items) == 1

    # 2. force_read=False: recorded as not_dicom skip reason
    out_noforce = tmp_path / "out_noforce"
    res_noforce = core.run(
        core.OrganizeOptions(input_root=in_dir, output_root=out_noforce, force_read=False)
    )
    assert res_noforce.status == "completed"
    assert len(res_noforce.items) == 0
    assert res_noforce.summary["skipped_non_dicom"] == 1
    assert any(r.reason == "not_dicom" for r in res_noforce.file_records)


def test_dicomdir_handling(tmp_path: Path) -> None:
    """5. Verify DICOMDIR media files created via pydicom.fileset.FileSet are skipped as dicomdir."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    in_dir = tmp_path / "media_root"
    in_dir.mkdir()
    out_dir = tmp_path / "organized_media"

    study_uid = generate_uid()
    fs = FileSet()
    try:
        # Create 2 series x 2 images (4 images total) meeting FileSet requirements
        for s_idx in (1, 2):
            s_uid = generate_uid()
            for i_idx in (1, 2):
                p = staging_dir / f"s{s_idx}_i{i_idx}.dcm"
                write_dicom(
                    p,
                    series_uid=s_uid,
                    sop_uid=generate_uid(),
                    study_uid=study_uid,
                    series_number=s_idx,
                    instance_number=i_idx,
                    study_time="120000",
                    patient_name="FILESET^PATIENT",
                    patient_id="PID_FILESET",
                    modality="MR",
                    series_description=f"FileSet Series {s_idx}",
                )
                ds = pydicom.dcmread(p)
                ds.StudyID = "1"
                fs.add(ds)

        fs.write(in_dir)
    finally:
        # Clean up pydicom FileSet staging directory to prevent ResourceWarning.
        if hasattr(fs, "_stage") and "t" in fs._stage:
            fs._stage["t"].cleanup()

    # Verify real DICOMDIR file was generated
    assert (in_dir / "DICOMDIR").is_file()

    res = core.run(core.OrganizeOptions(input_root=in_dir, output_root=out_dir))
    assert res.status == "completed"
    assert len(res.items) == 4
    assert res.stats["skip_dicomdir"] == 1
    assert any(r.reason == "dicomdir" for r in res.file_records)


def test_enhanced_mr_functional_groups(tmp_path: Path) -> None:
    """6. Verify Enhanced MR attributes are extracted from Shared and Per-Frame Functional Groups."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"

    file_path = in_dir / "enhanced_mr.dcm"
    sop_uid = generate_uid()
    series_uid = generate_uid()

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = EnhancedMRImageStorage
    meta.MediaStorageSOPInstanceUID = sop_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(str(file_path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = EnhancedMRImageStorage
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = generate_uid()
    ds.Modality = "MR"
    ds.PatientName = "ENHANCED^SAMPLE"
    ds.PatientID = "PID_ENHANCED"
    ds.StudyDate = "20260601"
    ds.SeriesDate = "20260601"
    ds.SeriesNumber = 10
    ds.InstanceNumber = 1
    ds.SeriesDescription = "Enhanced T2 MultiFrame"
    ds.NumberOfFrames = 2
    ds.Rows = 16
    ds.Columns = 16
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = b"\x00" * (16 * 16 * 2 * 2)

    # Shared functional groups: TR and FlipAngle
    timing_item = Dataset()
    timing_item.RepetitionTime = 3800.0
    timing_item.FlipAngle = 120.0
    shared_item = Dataset()
    shared_item.MRTimingAndRelatedParametersSequence = Sequence([timing_item])
    ds.SharedFunctionalGroupsSequence = Sequence([shared_item])

    # Per-frame functional groups: differing TE per frame (multi-echo)
    frame1 = Dataset()
    echo1 = Dataset()
    echo1.EffectiveEchoTime = 30.0
    frame1.MREchoSequence = Sequence([echo1])

    frame2 = Dataset()
    echo2 = Dataset()
    echo2.EffectiveEchoTime = 90.0
    frame2.MREchoSequence = Sequence([echo2])

    ds.PerFrameFunctionalGroupsSequence = Sequence([frame1, frame2])
    ds.save_as(file_path, enforce_file_format=True)

    res = core.run(core.OrganizeOptions(input_root=in_dir, output_root=out_dir))
    assert res.status == "completed"

    csv_path = out_dir / "all_series_summary.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    row = rows[0]
    assert float(row["TR_ms"]) == 3800.0
    assert float(row["FlipAngle_deg"]) == 120.0
    assert "30" in row["TE_ms"] and "90" in row["TE_ms"]
    assert row["EchoCount"] == "2"


def test_private_tag_fallback_siemens_and_ge(tmp_path: Path) -> None:
    """7. Verify Siemens ASCCONV protocol and GE GEMS_ACQU_01 private tag fallbacks."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"

    # Siemens MR with ASCCONV: lAccelFactPE and lTotalScanTimeSec
    siemens_file = in_dir / "siemens.dcm"
    write_dicom(
        siemens_file,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=1,
        instance_number=1,
        manufacturer="Siemens Healthcare",
        siemens_private_parallel_reduction_factor=2.0,
        siemens_total_scan_time_sec=185.0,
    )

    # GE MR with GEMS_ACQU_01 duration
    ge_file = in_dir / "ge.dcm"
    write_dicom(
        ge_file,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
        series_number=2,
        instance_number=1,
        manufacturer="GE Medical Systems",
        ge_acquisition_duration_us=120_000_000.0,  # 120s = 00:02:00
    )

    res = core.run(core.OrganizeOptions(input_root=in_dir, output_root=out_dir))
    assert res.status == "completed"

    csv_path = out_dir / "all_series_summary.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2

    siemens_row = next(r for r in rows if "Siemens" in r["Manufacturer"])
    assert float(siemens_row["ParallelReductionFactorInPlane"]) == 2.0
    assert siemens_row["ScanDuration"] == "00:03:05"

    ge_row = next(r for r in rows if "GE" in r["Manufacturer"])
    assert ge_row["ScanDuration"] == "00:02:00"
