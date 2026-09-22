# CSV Schema

This document describes the CSV files written by `dicom-organizer`.

## Files And Row Scope

`dicom_parameters.csv` is written once per study directory (`organized/<Device>/<StudyDate>/`). Each row represents
one supported image DICOM object selected by the active metadata profile.

`series_summary.csv` is also written once per study directory. Each row
summarizes one organized series folder after applying the same profile filter.

The organizer first prepares the rows written to `dicom_parameters.csv`, adds
series aggregates to those rows, and then creates `series_summary.csv` only from
that same in-memory data. It does not re-read DICOM headers for the summary.
Consequently, every `series_summary.csv` column is also present in
`dicom_parameters.csv`. `FileCount`, `EchoCount`, `EchoTimes_ms`,
`CoilElementCount`, and `CoilElements` are repeated on each corresponding
parameter row. If a shared column has multiple non-missing values in one series,
the summary preserves the distinct values in parameter-row order, separated by
`|`.

The following per-image columns remain only in `dicom_parameters.csv`, because a
single series-level value would be ambiguous: `OrganizedFileName`,
`SOPInstanceUID`, `InstanceNumber`, `SliceLocation_mm`, `SourceFileName`, and
`ImagePositionPatient`.

Supported image modalities are `MR`, `CT`, `US`, `XA`, and `PT`. Presentation
states, unsupported modalities, and vendor helper objects can still be organized
into folders, but they are excluded from the CSV tables. The run summary reports
both total organized files and CSV target files, including modality-level counts.

## Common Columns

`dicom_parameters.csv` starts with common columns for identifiers, series labels,
dates and times, patient fields, geometry, manufacturer information, source
filename, image type, and spatial orientation. Time fields (`AcquisitionTime`,
`SeriesTime`, `StudyTime`) output raw DICOM TM values as-is (for example,
`190429.500000`) without formatting. Missing values are written as `N/A`.

Patient fields follow `--patient-mode`:

- `keep`: writes `PatientName` and `PatientID` as read from the DICOM header.
- `hash`: writes `sha256:` digests to `PatientName` and `PatientID`.
- `drop`: writes `N/A` to `PatientName` and `PatientID`.

`PatientNameHash` and `PatientIDHash` are written for checking in all modes when
source values are available.

`PatientPosition` is preserved as a common per-image reference field. It is not
used to transform coordinates: DICOM specifies this attribute for annotation
rather than as an exact mathematical relationship to the equipment.

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

- `organized_files`: all readable DICOM files that were organized.
- `csv_target_files`: files included in `dicom_parameters.csv` and
  `series_summary.csv`.
- `csv_excluded_non_image_files`: organized files excluded from the CSV tables.
- `organized_files_by_modality`: organized DICOM counts grouped by `Modality`.
- `csv_target_files_by_modality`: CSV target counts grouped by `Modality`.
- `csv_excluded_files_by_modality`: CSV-excluded counts grouped by `Modality`.

These counts use the same profile filter as the CSV writer, so CLI output, GUI
logs, CSV files, and `organize_summary.json` describe the same selection.

## File Report (`file_report.csv`)

`file_report.csv` is written directly under the output root directory (`organized/file_report.csv`) in UTF-8 with BOM (`utf-8-sig`). Each row represents one candidate file encountered during scanning (or an excluded hidden file), providing traceability between source files and organized outputs.

### Columns

1. `SourceFileName`: Relative path from the input root directory (POSIX format).
2. `Status`: Processing outcome status:
   - `organized`: File successfully organized in non-dry-run mode.
   - `planned`: File planned for organization during a dry run.
   - `skipped`: File skipped without being organized.
   - `not_processed`: Planned file that was not placed due to cancellation, interruption, or failure.
3. `Reason`: Reason code explaining `skipped` or `not_processed` status (or `duplicate_conflict` for organized files with colliding SOPInstanceUIDs). `N/A` for normal organized files.
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
- `planned_files`: Total files planned for organization.
- `organized_files`: Number of files successfully placed in the destination.
- `not_processed_files`: Number of planned files that were not placed due to interruption or failure.
- `skipped_by_reason`: Mapping of reason codes to skipped file counts.
- `skipped_non_dicom`: Count of files with `not_dicom` reason only.
- `duplicate_conflicts`: Count of duplicate SOPInstanceUID files with conflicting content.
- `existing_output_conflicts`: Count of planned files whose destination already exists during dry-run with `--if-exists error`.
- `excluded_directories`: List of directories pruned during scan with their relative paths and reasons (`hidden`, `organized`, `output_root`).
- `space_check`: Result of disk space pre-check (`checked`, `required_bytes`, `free_bytes`).
- `previous_run_status`: Status of an unfinished previous run detected in the output root, or `null`.
- `warnings`: Warning messages, including guidance to resume incomplete runs and warnings when `--if-exists error` dry-run encounters existing files.
- `reports`: List of relative paths for all generated reports and summary files.

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

## 日本語

この文書は `dicom-organizer` が出力するCSVファイルの仕様です。

## ファイルと行の単位

`dicom_parameters.csv` は検査ディレクトリ（`organized/<Device>/<StudyDate>/`）ごとに1つ作られます。各行は、現在の
metadata profileで選択された対応画像DICOMオブジェクト1件を表します。

`series_summary.csv` も検査ディレクトリごとに1つ作られます。各行は、同じprofile
filterを適用した後の整理済みseries folder 1件を要約します。

最初に `dicom_parameters.csv` へ書くrowを準備し、そのrowへseries集計値を追加した後、
同じmemory上のデータだけから `series_summary.csv` を作ります。summary用にDICOM
headerを読み直すことはありません。そのため、`series_summary.csv` の全列は
`dicom_parameters.csv` にも存在します。`FileCount`、`EchoCount`、
`EchoTimes_ms`、`CoilElementCount`、`CoilElements` は、対応するparameters各行にも
繰り返し出力します。共有列にseries内で複数の欠損でない値がある場合、summaryでは
parametersのrow順に重複を除き、`|` で連結して保持します。

画像固有でseriesの単一値にできない `OrganizedFileName`、`SOPInstanceUID`、
`InstanceNumber`、`SliceLocation_mm`、`SourceFileName`、`ImagePositionPatient` は
`dicom_parameters.csv` だけに残します。

対応している画像モダリティは `MR`, `CT`, `US`, `XA`, `PT` です。presentation
state、非対応モダリティ、vendor helper object はフォルダ整理されることがありますが、
CSV表からは除外されます。実行summaryには、整理された総数とCSV対象数が
モダリティ別件数とともに出力されます。

## 共通列

`dicom_parameters.csv` は、識別子、series label、日付・時刻、患者情報、幾何情報、
メーカー情報、元ファイル名、image type、空間位置・方向の共通列から始まります。
時刻列（`AcquisitionTime`、`SeriesTime`、`StudyTime`）は DICOM の TM 値をそのまま出力します
（例: `190429.500000`）。整形は行いません。欠損値は `N/A` として出力されます。

患者情報は `--patient-mode` に従います。

- `keep`: DICOM headerから読んだ `PatientName` と `PatientID` をそのまま書きます。
- `hash`: `PatientName` と `PatientID` に `sha256:` digestを書きます。
- `drop`: `PatientName` と `PatientID` に `N/A` を書きます。

元の値がある場合、確認用の `PatientNameHash` と `PatientIDHash` はどのmodeでも
出力されます。

`PatientPosition` は画像単位の参照用共通列として残します。ただしDICOMでは
装置との厳密な数学的関係ではなく注釈用の属性とされているため、座標変換には
使いません。

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

- `organized_files`: 整理された読み取り可能なDICOMファイル数。
- `csv_target_files`: `dicom_parameters.csv` と `series_summary.csv` の対象ファイル数。
- `csv_excluded_non_image_files`: 整理されたがCSV表から除外されたファイル数。
- `organized_files_by_modality`: `Modality` 別の整理済みDICOM件数。
- `csv_target_files_by_modality`: `Modality` 別のCSV対象件数。
- `csv_excluded_files_by_modality`: `Modality` 別のCSV除外件数。

これらの件数はCSV writerと同じprofile filterで計算されるため、CLI出力、GUIログ、
CSVファイル、`organize_summary.json` は同じ選択範囲を表します。

## ファイル一覧レポート (`file_report.csv`)

`file_report.csv` は出力ルート直下（`organized/file_report.csv`）に UTF-8 BOM 付き（`utf-8-sig`）で出力されます。走査で見つかったすべての候補ファイル（および除外された隠しファイル）が 1 行ずつ記録され、元ファイルと出力先の対応およびスキップ理由を完全に追跡できます。

### 列構成

1. `SourceFileName`: 入力ルートからの相対パス（POSIX 形式）。
2. `Status`: 処理ステータス:
   - `organized`: 実際に配置が完了したファイル。
   - `planned`: dry-run で配置予定のファイル。
   - `skipped`: 整理対象外としてスキップされたファイル。
   - `not_processed`: 中断や失敗により配置されなかった予定ファイル。
3. `Reason`: スキップ理由または未処理理由（理由コード）。通常配置されたファイルは `N/A`、SOPInstanceUID 重複かつ内容相違の場合は `duplicate_conflict`。
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
- `planned_files`: 配置予定ファイル総数。
- `organized_files`: **実際に配置が完了したファイル数**。
- `not_processed_files`: 中断・失敗により配置されなかったファイル数。
- `skipped_by_reason`: 理由コード別のスキップ件数マップ。
- `skipped_non_dicom`: `not_dicom`（非 DICOM）のみの件数。
- `duplicate_conflicts`: 内容が異なる SOPInstanceUID 重複ファイルの件数。
- `existing_output_conflicts`: `--if-exists error` の dry-run で出力先に既に存在していた予定ファイル件数。
- `excluded_directories`: 走査で刈り込まれたディレクトリの一覧（相対パスと理由 `hidden` / `organized` / `output_root`）。
- `space_check`: 空き容量チェック結果（`checked`、`required_bytes`、`free_bytes`）。
- `previous_run_status`: 出力先に残されていた未完了実行のステータス（未検出時は `null`）。
- `warnings`: 未完了実行の検出、および既存出力先に対する `--if-exists error` の dry-run での警告・再開案内メッセージ。
- `reports`: 出力された全レポート・サマリーファイルの出力ルート相対パス一覧。

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
