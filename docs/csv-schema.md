# CSV Schema

This document describes the CSV files written by `dicom-organizer`.

## Files And Row Scope

`dicom_parameters.csv` is written once per study directory (e.g., `<StudyFolder>/dicom_parameters.csv`). Each row represents
one supported image DICOM object selected by the active metadata profile.

`series_summary.csv` is also written once per study directory. Each row
summarizes one organized series folder after applying the same profile filter.

`all_series_summary.csv` is written directly under the output root directory (`organized/all_series_summary.csv`) in both regular organization and list-only mode. It concatenates all `series_summary.csv` files found in the output directory tree (both from current and prior runs). Rows are ordered by directory path, and columns are the ordered union of all encountered summary columns, filling missing values with `N/A`.

The organizer first prepares the rows written to `dicom_parameters.csv`, adds
series aggregates to those rows, and then creates `series_summary.csv` only from
that same in-memory data. It does not re-read DICOM headers for the summary.
Consequently, every `series_summary.csv` column is also present in
`dicom_parameters.csv`. `FileCount`, `EchoCount`, `EchoTimes_ms`,
`CoilElementCount`, and `CoilElements` are repeated on each corresponding
parameter row. If a shared column has multiple non-missing values in one series,
the summary preserves the distinct values in parameter-row order, separated by
`|`.

The following per-image columns remain only in `dicom_parameters.csv` (and `all_dicom_parameters.csv`), because a
single series-level value would be ambiguous: `OrganizedFileName`,
`SOPInstanceUID`, `InstanceNumber`, `SliceLocation_mm`, `SourceFileName`, and
`ImagePositionPatient`.

Supported image modalities are `MR`, `CT`, `US`, `XA`, and `PT`. Presentation
states, unsupported modalities, and vendor helper objects can still be organized
into folders, but they are excluded from the CSV tables. The run summary reports
both total organized files and CSV target files, including modality-level counts.

### List-Only Mode (`--list-only`)

When `--list-only` is specified, `dicom-organizer` scans, classifies, and plans organization without copying or creating any DICOM files.
The default output directory is `<input>/organized_list` when `-o/--output` is omitted (automatically excluded from future scans).
Instead of per-study folders, four files are generated directly in the output root:

1. `all_dicom_parameters.csv`: All image rows across all planned series.
2. `all_series_summary.csv`: Summary of all planned series.
3. `file_report.csv`: Traceability report where organized candidates have `Status` set to `listed` and `OrganizedFileName` set to `N/A`.
4. `organize_summary.json`: Run summary recording `list_only: true`, `listed_files` count, and `organized_files: 0`.

Re-running `--list-only` on an existing output directory overwrites and regenerates these four files from scratch.

## Common Columns

`dicom_parameters.csv` (and `all_dicom_parameters.csv`) begins with:
`OrganizedFileName`, `StudyFolder`, `SeriesFolder`, `SeriesUID`, ...

`series_summary.csv` (and `all_series_summary.csv`) begins with:
`StudyFolder`, `SeriesFolder`, `AcquisitionDate`, `SeriesNumber`, ...

### Folder Columns

- `StudyFolder`: Relative path from the output root to the study directory where per-study CSV files reside (e.g., `UnitTest_Synthetic/20260515` or `20260515_a1b2c3d4`). In list-only mode, records the planned study path.
- `SeriesFolder`: Relative path from the output root to the series directory (e.g., `UnitTest_Synthetic/20260515/000001_Protocol-1`). In list-only mode, records the planned series path. Series grouping uses `SeriesFolder` as the primary key.

### Patient Fields

Patient fields follow `--patient-mode`:

- `keep` (default): writes `PatientName` and `PatientID` verbatim as read from the DICOM header. `PatientNameHash` and `PatientIDHash` record 16-character SHA-256 digests.
- `hash`: writes `sha256:` digests to `PatientName` and `PatientID`. `PatientNameHash` and `PatientIDHash` also record 16-character SHA-256 digests.
- `drop`: strictly writes `N/A` to all four columns: `PatientName`, `PatientID`, `PatientNameHash`, and `PatientIDHash`.

Time fields (`AcquisitionTime`, `SeriesTime`, `StudyTime`) output raw DICOM TM values as-is (e.g., `190429.500000`) without formatting. Missing values are written as `N/A`.

`PatientPosition` is preserved as a common per-image reference field. It is not
used to transform coordinates: DICOM specifies this attribute for annotation
rather than as an exact mathematical relationship to the equipment.

## Organization Layouts (`--layout`)

The `--layout` option controls how study directories are partitioned under the output root:

| Layout | Study Folder Structure | Typical Use Case |
|---|---|---|
| `device-date` (default) | `<Device>/<StudyDate>` | Comparing acquisition parameters grouped by scanner and date. |
| `study` | `<StudyDate>_<StudyKey>` | Strict 1-folder-per-study workflows. |
| `patient-study` | `<PatientKey>/<StudyDate>_<StudyKey>` | Patient-centric hierarchies (Patient → Study → Series). |

### Identity by UID

- `StudyKey`: First 8 hex characters of the SHA-1 digest of `StudyInstanceUID`. Prevents collisions when multiple studies occur on the same date. In `device-date` layout, multiple studies on the same date/device share the same directory; verify study counts using the `StudyInstanceUID` column or `study_count` in `organize_summary.json`.
- `PatientKey`:
  - Under `keep`: `safe_name(PatientID)` or `safe_name(f"{PatientID}_{IssuerOfPatientID}")` if `IssuerOfPatientID` is present. If non-alphanumeric characters (such as Japanese or symbols) cause information loss via `safe_name()`, a suffix `"-" + sha256(raw_string).hexdigest()[:8]` is appended to guarantee distinct patient directories while keeping safe characters readable. Values unchanged by `safe_name()` (e.g. `PID001`, `PID001_HOSP-A`) are used as-is. Defaults to `unknown-patient` if missing.
  - Under `hash` or `drop`: `"P-" + sha256(f"{IssuerOfPatientID}|{PatientID}".encode()).hexdigest()[:12]`. Distinguishes patients across different institutions where `PatientID` alone may not be unique.

Templates for `--series-dir-template` and `--file-template` support the additional context variables `study_key`, `patient_key`, `device_folder`, and `study_date`.

## Privacy Boundaries And Retained Information

`dicom-organizer` is designed for organizing local files and extracting parameters; it is **not** a DICOM de-identification or anonymization tool. The following table summarizes what information is retained across `--patient-mode` settings:

| Information | `keep` | `hash` | `drop` |
|---|---|---|---|
| Organized DICOM files (copy / symlink / hardlink / move) | Fully retained (original headers untouched). *Note: not created in list-only mode.* | Fully retained (original headers untouched). *Note: not created in list-only mode.* | Fully retained (original headers untouched). *Note: not created in list-only mode.* |
| `PatientName`, `PatientID` | Verbatim from DICOM | Pseudonymized (`sha256:...`) | `N/A` |
| `PatientNameHash`, `PatientIDHash` | 16-char SHA-256 digest | 16-char SHA-256 digest | `N/A` |
| Study dates, times, UIDs, Device | Retained | Retained | Retained |
| `SourceFileName` (in `file_report.csv`, `dicom_parameters.csv`, `all_dicom_parameters.csv`) | Retained (may contain patient names if present in source paths) | Retained (may contain patient names if present in source paths) | Retained (may contain patient names if present in source paths) |
| Custom tags (`--dicom-tag`) | Verbatim | Verbatim (warning issued for direct identifiers) | Verbatim (warning issued for direct identifiers) |
| Destination folder names (`patient-study`) | Contains `PatientID` | Contains `P-...` hash key | Contains `P-...` hash key |

Privacy notices detailing retained data are recorded under `privacy_notices` in `organize_summary.json` and printed during CLI runs. If direct patient identifiers (e.g. `PatientBirthDate`, `AccessionNumber`) are requested via `--dicom-tag` under `hash` or `drop`, a warning is added to `organize_summary.json`.


## Patient-Relative Phase-Encoding Direction

MR rows include these standard/derived fields by default:

- `InPlanePhaseEncodingDirection`: the source DICOM value (`ROW`, `COL`, or the
  Enhanced MR spelling `COLUMN`).
- `PhaseEncodingDirectionPatient`: the corresponding positive image-index axis
  in biped patient coordinates, written as an arrow such as `R→L`, `L→R`,
  `A→P`, `P→A`, `F→H`, or `H→F`.

The derivation selects the first three `ImageOrientationPatient` direction
cosines for `ROW` and the last three for `COL`/`COLUMN`. DICOM patient axes
increase from right to left, anterior to posterior, and feet to head. For an
oblique axis, the largest absolute direction-cosine component determines the
reported cardinal direction. `series_summary.csv` uses the same prepared values;
if they differ within a series, distinct values are joined with `|`.

`PhaseEncodingDirectionPatient` is `N/A` when the phase axis or image
orientation is missing or invalid, the phase axis is `OTHER`, or
`AnatomicalOrientationType` is not `BIPED`. Classic top-level attributes and the
first Shared/Per-Frame Functional Group values used by Enhanced MR are
supported.

The arrow reports the direction in which the image row/column index increases.
`InPlanePhaseEncodingDirection` does not encode the acquired gradient polarity,
so this column must not be interpreted as a BIDS `i` versus `i-` (or equivalent
polarity) value. The mapping follows the DICOM definitions of
[the MR phase axis](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.13.5.3.html),
[Image Orientation (Patient)](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.16.2.html),
and [Patient Position](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.7.3.html).

## Parallel-Imaging Acceleration

MR rows include `ParallelReductionFactorInPlane`, sourced from DICOM
`Parallel Reduction Factor In-plane (0018,9069)`. It is the ratio of the
original measurement time to the reduced in-plane measurement time, so `2.0`
represents a twofold reduction factor. The organizer reads the Classic MR
top-level attribute and the first Shared/Per-Frame `MRModifierSequence` value
used by Enhanced MR. The standard value takes precedence. For Siemens DICOM
without it, the organizer reads the explicit CSA protocol setting
`sPat.lAccelFactPE` from a private binary header. The value is written to both
CSV files and is `N/A` when neither source exists; no factor is inferred from
acquisition matrix or sampling values. See the
[DICOM MR Modifier Macro](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.13.5.5.html).

## Scan Duration

Both `dicom_parameters.csv` and `series_summary.csv` include common columns for
scan duration and its source:

- `ScanDuration`: the total acquisition / scan duration formatted as `HH:MM:SS`
  (rounded to the nearest second, with hours having 2 or more digits). Values
  less than or equal to 0, non-numeric, or missing are written as `N/A`.
- `ScanDurationSource`: an identifier indicating the tag or element where the
  duration was found, or `N/A` if none was found.

The organizer checks for scan duration in the following priority order, using
the first valid source found:

1. Top-level standard DICOM attribute `(0018,9073)` `AcquisitionDuration` in
   seconds. `ScanDurationSource` is written as `0018,9073`.
2. GE private block with creator `GEMS_ACQU_01` element `0x5A` in microseconds,
   converted to seconds by dividing by `1e6`. `ScanDurationSource` is written
   as `0019,105A`.
3. For Siemens objects (where `Manufacturer` contains `siemens`, case-insensitive),
   scans private binary elements for the ASCCONV protocol and extracts
   `lTotalScanTimeSec` in seconds using regular expressions.
   `ScanDurationSource` is constructed from the actual matched element tag
   (for example, `0021,1019:lTotalScanTimeSec`).
4. If none of the above are present, both `ScanDuration` and `ScanDurationSource`
   are written as `N/A`.

## Profile Columns

Profile-specific columns are appended after the common columns.

- `mr`: TR/TE, bandwidth, echo train length, flip angle, averages, field
  strength, sequence fields, inversion time, echo numbers, acquisition matrix,
  phase encoding, parallel reduction factor, sampling, SAR, coil, MR acquisition
  type, and Siemens channel helper fields.
- `ct`: kVp, tube current, exposure time, convolution kernel, and reconstruction
  diameter.
- `us`: transducer, mechanical/thermal index, and color data flag.
- `xa`: kVp, tube current, exposure time, frame time, and source-detector/source-
  patient distances.
- `pt`: radiopharmaceutical, dose, half-life, and decay correction.

`--profile auto` writes the union of columns for supported modalities present in
the input. For example, an MR/CT mixed folder includes both MR columns such as
`TE_ms` and CT columns such as `KVP_kV`. A row that does not use a modality-
specific column writes `N/A` in that column.

`--profile generic` writes common columns only. A modality-specific profile such
as `--profile ct` writes only rows matching that profile and appends only that
profile's columns.

Repeatable `--dicom-tag` columns are appended to both CSV files after the profile
columns. Missing custom tags are written as `N/A`; multiple distinct values in a
series are joined with `|` in `series_summary.csv`.

## Summary JSON Counts

`organize_summary.json` includes these CSV-related counts:

- `organized_files`: all readable DICOM files that were organized (always `0` when `--list-only` is active).
- `listed_files`: readable DICOM files planned and listed when `--list-only` is active.
- `csv_target_files`: files included in `dicom_parameters.csv` (or `all_dicom_parameters.csv`) and `series_summary.csv` (or `all_series_summary.csv`).
- `csv_excluded_non_image_files`: organized files excluded from the CSV tables.
- `organized_files_by_modality`: organized DICOM counts grouped by `Modality`.
- `csv_target_files_by_modality`: CSV target counts grouped by `Modality`.
- `csv_excluded_files_by_modality`: CSV-excluded counts grouped by `Modality`.
- `study_count`: total count of distinct `StudyInstanceUID`s encountered.

These counts use the same profile filter as the CSV writer, so CLI output, GUI
logs, CSV files, and `organize_summary.json` describe the same selection.

## File Report (`file_report.csv`)

`file_report.csv` is written directly under the output root directory (`organized/file_report.csv` or `<output>/file_report.csv`) in UTF-8 with BOM (`utf-8-sig`). Each row represents one candidate file encountered during scanning (or an excluded hidden file), providing traceability between source files and organized outputs.

### Columns

1. `SourceFileName`: Relative path from the input root directory (POSIX format).
2. `Status`: Processing outcome status:
   - `organized`: File successfully organized in non-dry-run mode.
   - `listed`: File planned and listed in `--list-only` mode (`OrganizedFileName` is `N/A`).
   - `planned`: File planned for organization during a dry run.
   - `skipped`: File skipped without being organized.
   - `not_processed`: Planned file that was not placed due to cancellation, interruption, or failure.
3. `Reason`: Reason code explaining `skipped` or `not_processed` status (or `duplicate_conflict` for organized files with colliding SOPInstanceUIDs). `N/A` for normal organized or listed files.
4. `Detail`: Short explanation in English, or `N/A`. In dry-run mode with `--if-exists error`, notes if destination already exists in output folder.
5. `OrganizedFileName`: Relative path from the output root directory (POSIX format), or `N/A`.
6. `DuplicateOf`: Relative path of the first encountered source file sharing the same SOPInstanceUID (or first matching identical file for duplicate copies), or `N/A`.
7. `SOPInstanceUID`: SOP Instance UID from the DICOM header, or `N/A`.
8. `SeriesUID`: Series Instance UID from the DICOM header, or `N/A`.
9. `Modality`: Modality from the DICOM header, or `N/A`.
10. `SizeBytes`: File size in bytes, or `N/A`.
11. `SHA256`: SHA-256 hex digest when `--checksum` is enabled or computed during duplicate detection (recorded for both duplicates and the first-encountered matching file), otherwise `N/A`.

### Skip Reason Codes (`SKIP_REASONS`)

| Reason Code | Meaning |
|---|---|
| `not_dicom` | Not a DICOM file (excluded from organization). |
| `dicomdir` | DICOMDIR index file (media index; excluded from organization). |
| `missing_required_uid` | DICOM object lacking `SeriesInstanceUID` or `SOPInstanceUID`. |
| `read_error` | DICOM header/prefix detected but could not be parsed (suspected corruption). |
| `permission_denied` | Read permission denied by OS. |
| `io_error` | Other OS-level I/O read error. |
| `excluded_hidden` | Hidden file (name starting with `.`) excluded without `--include-hidden`. |
| `duplicate_identical` | Second or later instance of the same SOPInstanceUID with identical content (not copied). |
| `existing_output` | Destination file already exists and was preserved under `--if-exists skip`. |

For files that are organized despite a shared SOPInstanceUID (content differs), `Reason` is set to `duplicate_conflict`. For unplaced files upon termination, `Reason` is set to `cancelled`, `interrupted`, or `failed`.

## Summary JSON (`organize_summary.json`)

`organize_summary.json` contains run metadata and counts with schema version 2 (`output_schema_version: 2`). Note that dry-run mode does not write `organize_summary.json` to disk (it only returns an in-memory `OrganizeResult` with `status="dry_run"`):

- `status`: Lifecycle status of the run:
  - `completed`: Successfully organized all planned files.
  - `running`: Processing in progress.
  - `cancelled`: Cancelled gracefully via cancel event or API.
  - `interrupted`: Interrupted via keyboard signal (`SIGINT` / Ctrl+C).
  - `failed`: Failed due to an unhandled exception or integrity error.
- `error`: Error message if status is `failed`, otherwise `null`.
- `software`: Environment metadata including versions of `dicom-organizer`, Python, `pydicom`, and OS platform (`platform.platform()`).
- `options`: Normalized dictionary of all run options.
- `layout`: Name of the organization layout used (`device-date`, `study`, or `patient-study`).
- `planned_files`: Total files planned for organization.
- `organized_files`: Number of files successfully placed in the destination (`0` in `--list-only` mode).
- `listed_files`: Number of files planned and recorded when `--list-only` is active.
- `not_processed_files`: Number of planned files that were not placed due to interruption or failure.
- `study_count`: Count of distinct `StudyInstanceUID`s in the run.
- `group_folders`: Mapping of study folder relative paths to their organized/planned file counts.
- `device_dates`: Deprecated alias of `group_folders` retained for backward compatibility.
- `privacy_notices`: List of stable privacy notice codes applicable to the run options.
- `skipped_by_reason`: Mapping of reason codes to skipped file counts.
- `skipped_non_dicom`: Count of files with `not_dicom` reason only.
- `duplicate_conflicts`: Count of duplicate SOPInstanceUID files with conflicting content.
- `existing_output_conflicts`: Count of planned files whose destination already exists during dry-run with `--if-exists error`.
- `excluded_directories`: List of directories pruned during scan with their relative paths and reasons (`hidden`, `organized`, `output_root`).
- `space_check`: Result of disk space pre-check (`checked`, `required_bytes`, `free_bytes`).
- `previous_run_status`: Status of an unfinished previous run detected in the output root, or `null`.
- `warnings`: Warning messages, including guidance to resume incomplete runs, tag warnings, and dry-run existing file notices.
- `reports`: List of relative paths for all generated reports and summary files (e.g., `all_series_summary.csv`, `file_report.csv`).

### Resuming Incomplete Runs

If a run is cancelled, interrupted, or fails partway through, placed files and partial metadata tables are safely preserved. To resume and complete the remaining files, re-run with:

```bash
dicom-organizer <INPUT> -o <OUTPUT> --if-exists skip
```

### Understanding File Counts

- `organized_files`: Total files placed into the organized directory structure.
- `csv_target_files`: Subset of organized files that are supported images matching the active profile and listed in `dicom_parameters.csv`.
- `skipped_by_reason`: Files found in the input tree that were not organized, classified by specific skip reasons.

> [!NOTE]
> **Scope of Verification**: Counts and reports reflect only the files discovered in the specified input directory. `dicom-organizer` cannot verify whether the input dataset itself is complete (i.e. whether any slices were omitted before organization) without external acquisition logs.

## Enhanced and Multi-Frame Images

`dicom_parameters.csv` and `series_summary.csv` include dedicated columns for multi-frame metadata:

- `NumberOfFrames`: Number of frames in the DICOM object (`NumberOfFrames` attribute). `N/A` if absent.
- `FrameVaryingAttributes`: For objects with `PerFrameFunctionalGroupsSequence`, lists the attribute columns whose values vary across frames, joined by `|` in table order. If all frames have identical values, reports `none`. If `PerFrameFunctionalGroupsSequence` is not present, reports `N/A`.

### Difference Between "Reading Enhanced Values" and "Expressing Frame Variations"

Earlier versions of `dicom-organizer` only inspected the first element of `SharedFunctionalGroupsSequence` or `PerFrameFunctionalGroupsSequence`. However, in Enhanced MR acquisitions (such as multi-echo, dynamic scans, or multi-orientation localizers), critical parameters like Echo Time (`TE_ms`) or patient orientation differ across frames.

`dicom-organizer` represents frame-by-frame differences for the columns in the table above:
- When an attribute is found in `SharedFunctionalGroupsSequence`, it applies to all frames and is returned as a single value.
- When an attribute is in `PerFrameFunctionalGroupsSequence`, all frame items are inspected in frame order. If values differ across frames, distinct values are joined in frame order with `|` without duplicates (e.g. `10|20|30`).
- If an attribute varies across frames, its column name is recorded in `FrameVaryingAttributes`.
- If `ImageOrientationPatient` or `InPlanePhaseEncodingDirection` varies across frames, `PhaseEncodingDirectionPatient` is calculated for each frame, joined with `|` across distinct values, and appended to the end of `FrameVaryingAttributes`. Classic images and Enhanced images whose orientation does not vary retain a single value.

### Functional Group Mapping Table

The following columns prioritize classic top-level DICOM attributes; if absent or empty, values are retrieved from Functional Groups:

| CSV Column | Classic Attribute | Functional Group Sequence | Attribute |
|---|---|---|---|
| `TR_ms` | `RepetitionTime` | `MRTimingAndRelatedParametersSequence` | `RepetitionTime` |
| `FlipAngle_deg` | `FlipAngle` | `MRTimingAndRelatedParametersSequence` | `FlipAngle` |
| `EchoTrainLength` | `EchoTrainLength` | `MRTimingAndRelatedParametersSequence` | `EchoTrainLength` |
| `TE_ms` | `EchoTime` | `MREchoSequence` | `EffectiveEchoTime` |
| `InversionTime_ms` | `InversionTime` | `MRModifierSequence` | `InversionTimes` |
| `PixelBandwidth_Hz_per_px` | `PixelBandwidth` | `MRImagingModifierSequence` | `PixelBandwidth` |
| `NumberOfAverages` | `NumberOfAverages` | `MRAveragesSequence` | `NumberOfAverages` |
| `PixelSpacing` | `PixelSpacing` | `PixelMeasuresSequence` | `PixelSpacing` |
| `SliceThickness_mm` | `SliceThickness` | `PixelMeasuresSequence` | `SliceThickness` |
| `SpacingBetweenSlices_mm` | `SpacingBetweenSlices` | `PixelMeasuresSequence` | `SpacingBetweenSlices` |
| `ImageOrientationPatient` | `ImageOrientationPatient` | `PlaneOrientationSequence` | `ImageOrientationPatient` |
| `InPlanePhaseEncodingDirection` | `InPlanePhaseEncodingDirection` | `MRFOVGeometrySequence` | `InPlanePhaseEncodingDirection` |
| `ParallelReductionFactorInPlane` | `ParallelReductionFactorInPlane` | `MRModifierSequence` | `ParallelReductionFactorInPlane` |

### Limitations

- Attributes that only exist in a subset of frames are concatenated using only the frames where values are present (frames without values are ignored).
- In Enhanced CT, PET, XA, etc., generic columns in the table (such as `PixelSpacing`, `SliceThickness`, `SpacingBetweenSlices`, `ImageOrientationPatient`, `ImagePositionPatient`) are read from Functional Groups, but modality-specific parameters (such as `KVP` in CT) are read only from classic top-level attributes and may be reported as `N/A` in Enhanced non-MR modalities.
- `ImagePositionPatient` uses the first frame's value from `PlanePositionSequence` when the classic attribute is absent (slice positions naturally vary and are not included in `FrameVaryingAttributes`).
- `FOV_HxW_mm` is computed from the first resolved `PixelSpacing`.
- `EchoTimes_ms` and `EchoCount`: In series aggregation, `TE_ms` is split by `|` before counting unique values, correctly yielding `EchoCount=3` and `EchoTimes_ms=10|20|30` for multi-echo Enhanced MR.

## 日本語

この文書は `dicom-organizer` が出力するCSVファイルの仕様です。

## ファイルと行の単位

`dicom_parameters.csv` は検査ディレクトリ（例: `<StudyFolder>/dicom_parameters.csv`）ごとに1つ作られます。各行は、現在の
metadata profileで選択された対応画像DICOMオブジェクト1件を表します。

`series_summary.csv` も検査ディレクトリごとに1つ作られます。各行は、同じprofile
filterを適用した後の整理済みseries folder 1件を要約します。

`all_series_summary.csv` は、通常の整理（非 dry-run）および一覧のみモードの両方で、出力ルート直下（`organized/all_series_summary.csv`）に出力されます。出力ディレクトリ配下のすべての `series_summary.csv`（今回の実行と以前の実行の両方）をパス順に集約・連結したものです。列は出現順の和集合となり、欠損値は `N/A` で補完されます。

最初に `dicom_parameters.csv` へ書くrowを準備し、そのrowへseries集計値を追加した後、
同じmemory上のデータだけから `series_summary.csv` を作ります。summary用にDICOM
headerを読み直すことはありません。そのため、`series_summary.csv` の全列は
`dicom_parameters.csv` にも存在します。`FileCount`、`EchoCount`、
`EchoTimes_ms`、`CoilElementCount`、`CoilElements` は、対応するparameters各行にも
繰り返し出力します。共有列にseries内で複数の欠損でない値がある場合、summaryでは
parametersのrow順に重複を除き、`|` で連結して保持します。

画像固有でseriesの単一値にできない `OrganizedFileName`、`SOPInstanceUID`、
`InstanceNumber`、`SliceLocation_mm`、`SourceFileName`、`ImagePositionPatient` は
`dicom_parameters.csv`（および `all_dicom_parameters.csv`）だけに残します。

対応している画像モダリティは `MR`, `CT`, `US`, `XA`, `PT` です。presentation
state、非対応モダリティ、vendor helper object はフォルダ整理されることがありますが、
CSV表からは除外されます。実行summaryには、整理された総数とCSV対象数が
モダリティ別件数とともに出力されます。

### 一覧のみモード（`--list-only`）

`--list-only` を指定すると、DICOM ファイルをコピー・作成せず、メタデータ表とレポートのみを作成します。
`-o/--output` を省略した場合の既定出力先は `<input>/organized_list` です（以後の走査で自動的に除外されます）。
検査フォルダやシリーズフォルダは作成されず、出力ルート直下に次の4ファイルが出力されます：

1. `all_dicom_parameters.csv`: 全計画シリーズの全画像行。
2. `all_series_summary.csv`: 全計画シリーズの集約行。
3. `file_report.csv`: 候補ファイルの追跡レポート（配置予定ファイルの `Status` は `listed`、`OrganizedFileName` は `N/A`）。
4. `organize_summary.json`: `list_only: true`、`listed_files` 件数、および `organized_files: 0` を記録。

同じ出力先に再実行した場合、これら 4 ファイルが最初から作り直されます（追記ではなく上書き再生成）。

## 共通列

`dicom_parameters.csv`（および `all_dicom_parameters.csv`）は次の列順で始まります：
`OrganizedFileName`, `StudyFolder`, `SeriesFolder`, `SeriesUID`, ...

`series_summary.csv`（および `all_series_summary.csv`）は次の列順で始まります：
`StudyFolder`, `SeriesFolder`, `AcquisitionDate`, `SeriesNumber`, ...

### フォルダ列

- `StudyFolder`: 検査フォルダ（出力ルートからの相対パス、例: `UnitTest_Synthetic/20260515` や `20260515_a1b2c3d4`）。一覧のみモードでも計画上のパスが記録されます。
- `SeriesFolder`: シリーズフォルダ（出力ルートからの相対パス、例: `UnitTest_Synthetic/20260515/000001_Protocol-1`）。一覧のみモードでも計画上のパスが記録されます。シリーズ集計の第一キーとして使われます。

### 患者情報

患者情報は `--patient-mode` に従います：

- `keep`（既定）: DICOM ヘッダーの `PatientName` と `PatientID` をそのまま出力します。`PatientNameHash` と `PatientIDHash` に SHA-256（先頭 16 桁）を出力します。
- `hash`: `PatientName` と `PatientID` に `sha256:` ダイジェストを出力します。`PatientNameHash` と `PatientIDHash` にも SHA-256（先頭 16 桁）を出力します。
- `drop`: `PatientName`, `PatientID`, `PatientNameHash`, `PatientIDHash` の 4 列すべてに `N/A` を出力します（厳格化）。

時刻列（`AcquisitionTime`、`SeriesTime`、`StudyTime`）は DICOM の TM 値をそのまま出力します
（例: `190429.500000`）。整形は行いません。欠損値は `N/A` として出力されます。

`PatientPosition` は画像単位の参照用共通列として残します。ただしDICOMでは
装置との厳密な数学的関係ではなく注釈用の属性とされているため、座標変換には
使いません。

## 用途別レイアウト（`--layout`）

`--layout` オプションにより、出力ルート配下の検査フォルダの構成を変更できます：

| レイアウト | 検査フォルダ構造 | 主な想定用途 |
|---|---|---|
| `device-date`（既定） | `<Device>/<StudyDate>` | 装置・撮像日ごとのパラメータ確認・装置間比較 |
| `study` | `<StudyDate>_<StudyKey>` | 1 フォルダ = 1 検査として管理したい場合 |
| `patient-study` | `<PatientKey>/<StudyDate>_<StudyKey>` | 患者 → 検査 → シリーズの階層で管理したい場合 |

### UID による同一性

- `StudyKey`: `StudyInstanceUID` の SHA-1 ダイジェスト先頭 8 桁。同日に複数の検査が行われた場合でもフォルダの衝突を防ぎます。なお、`device-date` レイアウトでは同日・同装置の複数検査が同一フォルダに入るため、`StudyInstanceUID` 列や `organize_summary.json` の `study_count` で検査数を確認してください。
- `PatientKey`:
  - `keep` 時: `safe_name(PatientID)`（`IssuerOfPatientID` がある場合は `_` で連結）。もし英数字以外（日本語文字や記号など）が含まれて `safe_name()` により値が変化（情報脱落）した場合は、安全な文字の可読性を残しつつ末尾に `-` + `sha256(元の文字列).hexdigest()[:8]` を付加して患者フォルダの一意性を保証します。`safe_name()` で変化しない英数字等の値（例: `PID001`, `PID001_HOSP-A`）はそのまま使用されます。未設定時は `unknown-patient`。
  - `hash` または `drop` 時: `"P-" + sha256(f"{IssuerOfPatientID}|{PatientID}".encode()).hexdigest()[:12]`（仮名キー）。複数施設から収集されたデータで `PatientID` が重複するリスクを防ぐため、発行機関（`IssuerOfPatientID`）を含めてハッシュ化します。

`--series-dir-template` および `--file-template` では、追加のコンテキスト変数 `study_key`、`patient_key`、`device_folder`、`study_date` が利用可能です。

## 出力に残る情報と患者情報の境界

`dicom-organizer` はローカルファイルの整理とパラメータ抽出のためのツールであり、**DICOM の匿名化・脱特定化ツールではありません**。各 `--patient-mode` で出力に残る情報は次のとおりです：

| 項目 | `keep` | `hash` | `drop` |
|---|---|---|---|
| 整理後の DICOM ファイル（copy / symlink / hardlink / move） | 元ヘッダーのまま完全保持（匿名化されない。※一覧のみモードでは生成されません） | 元ヘッダーのまま完全保持（匿名化されない。※一覧のみモードでは生成されません） | 元ヘッダーのまま完全保持（匿名化されない。※一覧のみモードでは生成されません） |
| `PatientName`, `PatientID` | DICOM の値をそのまま出力 | SHA-256 ダイジェスト（仮名化） | `N/A` |
| `PatientNameHash`, `PatientIDHash` | SHA-256 ダイジェスト | SHA-256 ダイジェスト | `N/A` |
| 検査日時、UID、装置名 | 保持 | 保持 | 保持 |
| `SourceFileName` (`file_report.csv`, `dicom_parameters.csv`, `all_dicom_parameters.csv`) | 保持（元パスに患者名が含まれる場合は残る） | 保持（元パスに患者名が含まれる場合は残る） | 保持（元パスに患者名が含まれる場合は残る） |
| 追加タグ (`--dicom-tag`) | そのまま出力 | そのまま出力（直接識別子の場合は警告） | そのまま出力（直接識別子の場合は警告） |
| 出力先フォルダ名 (`patient-study`) | `PatientID` が含まれる | 仮名キー `P-...` が含まれる | 仮名キー `P-...` が含まれる |

実行時に適用された通知内容は `organize_summary.json` の `privacy_notices` に記録され、CLI 実行時にも案内されます。`hash` または `drop` 指定時に `--dicom-tag` で患者の直接識別属性（`PatientBirthDate`, `AccessionNumber` など）が指定された場合、警告メッセージが出力されます。


## 患者基準の位相エンコード方向

MR行では、次の標準列・導出列を既定で出力します。

- `InPlanePhaseEncodingDirection`: DICOM由来の値（`ROW`, `COL`、Enhanced MRの
  表記である `COLUMN`）。
- `PhaseEncodingDirectionPatient`: 対応する画像index正方向を二足歩行の患者座標で
  表した値。`R→L`, `L→R`, `A→P`, `P→A`, `F→H`, `H→F` のいずれかです。

`ROW` では `ImageOrientationPatient` の先頭3個、`COL` / `COLUMN` では後半3個の
方向余弦を使います。DICOM患者座標の正方向は rightからleft、anteriorから
posterior、feetからheadです。斜位では絶対値が最大の方向余弦成分を代表する
解剖学的方向として出力します。`series_summary.csv` でも同じ準備済みの値を使い、
series内で異なる場合は重複しない値を `|` で連結します。

位相軸または画像方向が欠損・不正、位相軸が `OTHER`、または
`AnatomicalOrientationType` が `BIPED` 以外の場合、
`PhaseEncodingDirectionPatient` は `N/A` です。classic DICOMのtop-level属性に加え、
Enhanced MRの最初のShared/Per-Frame Functional Groupも読み取ります。

矢印が表すのは画像のrow/column indexが増える方向です。
`InPlanePhaseEncodingDirection` には撮像時gradientの極性が含まれないため、BIDSの
`i` と `i-` の違い（または同等の極性情報）として解釈しないでください。変換は
[MRの位相軸](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.13.5.3.html)、
[Image Orientation (Patient)](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.16.2.html)、
[Patient Position](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.7.3.html)
のDICOM定義に従います。

## パラレルイメージング倍速数

MR行には、DICOMの `Parallel Reduction Factor In-plane (0018,9069)` から取得した
`ParallelReductionFactorInPlane` を出力します。これは元の測定時間と面内方向で
短縮した測定時間の比で、`2.0` は短縮係数が2倍であることを表します。classic MRの
top-level属性と、Enhanced MRで使われる最初のShared/Per-Frame
`MRModifierSequence` を読み取り、標準値を優先します。標準属性がないSiemens
DICOMでは、private binary header内のCSA protocol設定 `sPat.lAccelFactPE` を
fallbackとして読み取ります。両CSVへ同じ値を出力し、どちらのsourceもない場合は
`N/A` とします。acquisition matrixやsampling値から倍速数を推測しません。定義は
[DICOM MR Modifier Macro](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.13.5.5.html)
を参照してください。

## 撮像時間

`dicom_parameters.csv` と `series_summary.csv` の両方に、撮像時間とその取得元を示す共通列を出力します。

- `ScanDuration`: スキャン所要時間（撮像時間）を `HH:MM:SS` 形式で出力します。
  最も近い秒に四捨五入され、1時間を超える場合は時は2桁以上になります。0以下、
  数値化できない値、欠損値は `N/A` になります。
- `ScanDurationSource`: 撮像時間を取得したタグまたは要素を示す文字列です。
  取得元が存在しない場合は `N/A` になります。

取得ロジックは次の優先順序で最初に見つかったものを採用します。

1. トップレベルの標準タグ `(0018,9073)` `AcquisitionDuration`（秒）。
   `ScanDurationSource` は `0018,9073` となります。
2. private creator が `GEMS_ACQU_01` のブロックにある要素 `0x5A`（マイクロ秒）。
   値を `1e6` で割って秒に換算します。`ScanDurationSource` は `0019,105A` となります。
3. Siemens（`Manufacturer` に大文字小文字問わず `siemens` を含む場合）:
   private かつ bytes 値の要素を走査し、ASCCONV プロトコル内の `lTotalScanTimeSec` を
   正規表現で取り出して秒として使用します。`ScanDurationSource` は実際に見つかった要素のタグ
   （例: `0021,1019:lTotalScanTimeSec`）となります。
4. いずれも見つからない場合は、`ScanDuration` も `ScanDurationSource` も `N/A` となります。

## profile別列

profile別の列は共通列の後ろに追加されます。

- `mr`: TR/TE、bandwidth、echo train length、flip angle、加算回数、磁場強度、
  sequence系、inversion time、echo number、acquisition matrix、phase encoding、
  parallel reduction factor、sampling、SAR、coil、MR acquisition type、Siemens
  channel補助列。
- `ct`: kVp、tube current、exposure time、convolution kernel、reconstruction diameter。
- `us`: transducer、mechanical/thermal index、color data flag。
- `xa`: kVp、tube current、exposure time、frame time、source-detector/source-patient距離。
- `pt`: radiopharmaceutical、dose、half-life、decay correction。

`--profile auto` は、入力内に存在する対応モダリティの列をまとめて出力します。たとえば
MR/CT混在フォルダでは、`TE_ms` などのMR列と `KVP_kV` などのCT列が両方入ります。
その行に該当しないモダリティ専用列は `N/A` になります。

`--profile generic` は共通列だけを出力します。`--profile ct` のような単一モダリティ
profileでは、そのprofileに一致する行だけを出力し、そのprofileの列だけを追加します。

繰り返し指定できる `--dicom-tag` の列は両CSVのprofile列の後ろに追加されます。
存在しないcustom tagは `N/A` になり、series内に複数の異なる値がある場合は
`series_summary.csv` で `|` 連結されます。

## summary JSONの件数

`organize_summary.json` にはCSV関連の件数が含まれます。

- `organized_files`: 整理された読み取り可能なDICOMファイル数（`--list-only` 指定時は常に `0`）。
- `listed_files`: `--list-only` 指定時に計画・一覧化されたDICOMファイル数。
- `csv_target_files`: `dicom_parameters.csv`（または `all_dicom_parameters.csv`）と `series_summary.csv`（または `all_series_summary.csv`）の対象ファイル数。
- `csv_excluded_non_image_files`: 整理されたがCSV表から除外されたファイル数。
- `organized_files_by_modality`: `Modality` 別の整理済みDICOM件数。
- `csv_target_files_by_modality`: `Modality` 別のCSV対象件数。
- `csv_excluded_files_by_modality`: `Modality` 別のCSV除外件数。
- `study_count`: 走査で確認された異なる `StudyInstanceUID` の総数。

これらの件数はCSV writerと同じprofile filterで計算されるため、CLI出力、GUIログ、
CSVファイル、`organize_summary.json` は同じ選択範囲を表します。

## ファイル一覧レポート (`file_report.csv`)

`file_report.csv` は出力ルート直下（`organized/file_report.csv` または `<output>/file_report.csv`）に UTF-8 BOM 付き（`utf-8-sig`）で出力されます。走査で見つかったすべての候補ファイル（および除外された隠しファイル）が 1 行ずつ記録され、元ファイルと出力先の対応およびスキップ理由を完全に追跡できます。

### 列構成

1. `SourceFileName`: 入力ルートからの相対パス（POSIX 形式）。
2. `Status`: 処理ステータス:
   - `organized`: 実際に配置が完了したファイル。
   - `listed`: `--list-only` モードで計画・一覧化されたファイル（`OrganizedFileName` は `N/A`）。
   - `planned`: dry-run で配置予定のファイル。
   - `skipped`: 整理対象外としてスキップされたファイル。
   - `not_processed`: 中断や失敗により配置されなかった予定ファイル。
3. `Reason`: スキップ理由または未処理理由（理由コード）。通常配置されたファイルおよび listed ファイルは `N/A`、SOPInstanceUID 重複かつ内容相違の場合は `duplicate_conflict`。
4. `Detail`: 英語による補足説明（欠損時は `N/A`）。`--if-exists error` の dry-run では、出力先に既に存在する予定ファイルにその旨が記録されます。
5. `OrganizedFileName`: 出力ルートからの相対パス（POSIX 形式、未配置時は `N/A`）。
6. `DuplicateOf`: 同一 SOPInstanceUID を持つ 1 件目ファイルの入力相対パス（または同一内容の最初のファイルの相対パス、非重複時は `N/A`）。
7. `SOPInstanceUID`: DICOM ヘッダーの SOP Instance UID（欠損時は `N/A`）。
8. `SeriesUID`: DICOM ヘッダーの Series Instance UID（欠損時は `N/A`）。
9. `Modality`: DICOM ヘッダーのモダリティ（欠損時は `N/A`）。
10. `SizeBytes`: ファイルサイズ（バイト単位、欠損時は `N/A`）。
11. `SHA256`: `--checksum` 指定時、または重複比較時に計算された SHA-256 ハッシュ（重複行および比較元の 1 件目ファイル行の両方に記録。未計算時は `N/A`）。

### 未処理理由コード (`SKIP_REASONS`)

| 理由コード | 意味 |
|---|---|
| `not_dicom` | DICOM ではないファイル（整理対象外） |
| `dicomdir` | DICOMDIR（メディア索引ファイル。整理対象外） |
| `missing_required_uid` | DICOM だが `SeriesInstanceUID` または `SOPInstanceUID` がない（必須情報不足） |
| `read_error` | DICOM プレフィックス等の形跡があるが読めない（破損疑い） |
| `permission_denied` | OS の読み取り権限がない |
| `io_error` | その他の OS レベルの読み取りエラー |
| `excluded_hidden` | 隠しファイル（`.` で始まる）で `--include-hidden` なしのため除外 |
| `duplicate_identical` | 同じ SOPInstanceUID で内容も完全に同一な 2 件目以降のファイル（配置しない） |
| `existing_output` | 出力先に同名ファイルが既に存在し、`--if-exists skip` により残された |

SOPInstanceUID が同じで内容が異なるファイルは、重複衝突（`duplicate_conflict`）として配置されます。中断・停止時に未配置だった予定ファイルには、理由コードとして `cancelled` / `interrupted` / `failed` が記録されます。

## 実行サマリー (`organize_summary.json`)

`organize_summary.json` には、実行環境や結果の集計値がスキーマ版 2（`output_schema_version: 2`）として記録されます。なお、dry-run は `organize_summary.json` をディスクに書き出さず、`OrganizeResult.status` のみが `dry_run` となります:

- `status`: 実行の最終状態:
  - `completed`: すべての配置が正常に完了。
  - `running`: 実行中。
  - `cancelled`: キャンセル要求により安全に中断。
  - `interrupted`: Ctrl+C（`SIGINT`）により中断。
  - `failed`: 例外や整合性エラーにより失敗。
- `error`: `status` が `failed` の場合のエラーメッセージ（正常時は `null`）。
- `software`: `dicom-organizer` のバージョン、Python、`pydicom`、OS プラットフォーム情報（`platform.platform()`）。
- `options`: 実行時に適用された正規化済み全オプション。
- `layout`: 適用されたレイアウト名（`device-date`, `study`, `patient-study`）。
- `planned_files`: 配置予定ファイル総数。
- `organized_files`: **実際に配置が完了したファイル数**（`--list-only` 指定時は `0`）。
- `listed_files`: `--list-only` 指定時に計画・一覧化されたファイル数。
- `not_processed_files`: 中断・失敗により配置されなかったファイル数。
- `study_count`: 異なる `StudyInstanceUID` の総数。
- `group_folders`: 検査フォルダごとの配置（計画）ファイル数マップ。
- `device_dates`: `group_folders` の非推奨別名（後方互換性のため維持）。
- `privacy_notices`: 適用されたプライバシー通知コードのリスト。
- `skipped_by_reason`: 理由コード別のスキップ件数マップ。
- `skipped_non_dicom`: `not_dicom`（非 DICOM）のみの件数。
- `duplicate_conflicts`: 内容が異なる SOPInstanceUID 重複ファイルの件数。
- `existing_output_conflicts`: `--if-exists error` の dry-run で出力先に既に存在していた予定ファイル件数。
- `excluded_directories`: 走査で刈り込まれたディレクトリの一覧（相対パスと理由 `hidden` / `organized` / `output_root`）。
- `space_check`: 空き容量チェック結果（`checked`、`required_bytes`、`free_bytes`）。
- `previous_run_status`: 出力先に残されていた未完了実行のステータス（未検出時は `null`）。
- `warnings`: 未完了実行の検出、追加タグ警告、および既存出力先に対する `--if-exists error` の dry-run での警告・再開案内メッセージ。
- `reports`: 出力された全レポート・サマリーファイルの出力ルート相対パス一覧（`all_series_summary.csv`, `file_report.csv` など）。

### 中断・失敗した処理の再開方法

処理が途中で中断（Ctrl+C やキャンセル）または失敗した場合でも、配置済みのファイルと中間レポートは安全に保持されます。続きから処理を再開するには、`--if-exists skip` を指定して再実行してください:

```bash
dicom-organizer <INPUT> -o <OUTPUT> --if-exists skip
```

### 件数の違いについて

- `organized_files`: 出力先フォルダに実際に整理・配置されたファイル総数。
- `csv_target_files`: 整理されたファイルのうち、指定プロファイルに合致し `dicom_parameters.csv` に掲載された画像ファイル数。
- `skipped_by_reason`: 入力フォルダ内で発見されたが、整理されなかったファイルの理由別内訳。

> [!NOTE]
> **確認できる範囲の注意点**: 記録される結果は、指定された入力フォルダ内に現実に存在したファイルについてのものです。検査全体として本来あるべき画像がすべて揃っているか（撮像装置側からの転送漏れや欠落がないか）は、検査プロトコルの予定枚数や外部情報と照合しない限りツール単体では保証できません。

## Enhanced / マルチフレーム画像

`dicom_parameters.csv` および `series_summary.csv` には、マルチフレーム画像用の共通列が含まれます。

- `NumberOfFrames`: `NumberOfFrames` 属性の値。属性が存在しない場合は `N/A`。
- `FrameVaryingAttributes`: `PerFrameFunctionalGroupsSequence` を持つオブジェクトにおいて、フレーム間で値が異なる列名をマッピング表の順に `|` で連結したもの。変動がない場合は `none`。`PerFrameFunctionalGroupsSequence` を持たないオブジェクトは `N/A`。

### 「Enhanced の値を読める」と「フレームごとの違いを表現できる」の違い

以前の版の `dicom-organizer` は最初の要素だけを読んでいましたが、マルチエコー（ME）や異なる向きを含むローカライザー等の Enhanced MR 撮像では、フレームごとに TE や向きなどの撮像条件が異なります。

`dicom-organizer` は上の表の列について、フレームごとの違いを表現します：
- `SharedFunctionalGroupsSequence` にある値は全フレーム共通として 1 つの値を返します。
- `PerFrameFunctionalGroupsSequence` にある値は全フレームをフレーム順に走査します。フレーム間で値が異なる場合、異なる値をフレーム順に重複なく `|` で連結します（例: `10|20|30`）。
- フレーム間で値が変動した列名は `FrameVaryingAttributes` に記録され、どの撮像パラメータが変動しているかを一目で確認できます。
- Enhanced MR 画像で `ImageOrientationPatient` または `InPlanePhaseEncodingDirection` がフレーム間で変わる場合、フレームごとに患者座標の方向を求め、異なる値をフレーム順に `|` で連結し、`FrameVaryingAttributes` の末尾に `PhaseEncodingDirectionPatient` を追加します。classic 画像や、向きが変わらない Enhanced 画像では単一値となり、`FrameVaryingAttributes` には追加されません。

### Functional Group 取得元対応表

次の列は「classic の top-level 属性があればそれ、なければ Functional Group」から取得します（classic 優先）。

| CSV 列 | classic 属性 | Functional Group の sequence | 属性 |
|---|---|---|---|
| `TR_ms` | `RepetitionTime` | `MRTimingAndRelatedParametersSequence` | `RepetitionTime` |
| `FlipAngle_deg` | `FlipAngle` | `MRTimingAndRelatedParametersSequence` | `FlipAngle` |
| `EchoTrainLength` | `EchoTrainLength` | `MRTimingAndRelatedParametersSequence` | `EchoTrainLength` |
| `TE_ms` | `EchoTime` | `MREchoSequence` | `EffectiveEchoTime` |
| `InversionTime_ms` | `InversionTime` | `MRModifierSequence` | `InversionTimes` |
| `PixelBandwidth_Hz_per_px` | `PixelBandwidth` | `MRImagingModifierSequence` | `PixelBandwidth` |
| `NumberOfAverages` | `NumberOfAverages` | `MRAveragesSequence` | `NumberOfAverages` |
| `PixelSpacing` | `PixelSpacing` | `PixelMeasuresSequence` | `PixelSpacing` |
| `SliceThickness_mm` | `SliceThickness` | `PixelMeasuresSequence` | `SliceThickness` |
| `SpacingBetweenSlices_mm` | `SpacingBetweenSlices` | `PixelMeasuresSequence` | `SpacingBetweenSlices` |
| `ImageOrientationPatient` | `ImageOrientationPatient` | `PlaneOrientationSequence` | `ImageOrientationPatient` |
| `InPlanePhaseEncodingDirection` | `InPlanePhaseEncodingDirection` | `MRFOVGeometrySequence` | `InPlanePhaseEncodingDirection` |
| `ParallelReductionFactorInPlane` | `ParallelReductionFactorInPlane` | `MRModifierSequence` | `ParallelReductionFactorInPlane` |

### 制限事項

- 一部のフレームにしか値がない属性は、値のあるフレームだけから連結します（値のないフレームは無視します）。
- Enhanced CT / PET / XA などでは、表の汎用の列（`PixelSpacing`, `SliceThickness`, `SpacingBetweenSlices`, `ImageOrientationPatient`, `ImagePositionPatient`）は Functional Group から読みますが、CT の KVP などモダリティ固有のパラメータは classic の top-level 属性だけを読むため、Enhanced CT では `N/A` になり得ます。
- `ImagePositionPatient` は classic がなければ `PlanePositionSequence` の最初のフレームの値を使用します（スライス位置は通常フレームごとに異なるため、変動属性一覧には含めません）。
- `FOV_HxW_mm` は最初に得られる PixelSpacing を用いて計算します。
- `EchoTimes_ms` と `EchoCount` の集計では、`TE_ms` の値を `|` で分割してから異なる値を数えるため、Enhanced multi-echo で 1 行に `10|20|30` が入る場合でも `EchoCount=3` として正しく集計されます。
