# CSV Schema

This document describes the CSV files written by `dicom-organizer`.

## Files And Row Scope

`dicom_parameters.csv` is written once per acquisition date. Each row represents
one supported image DICOM object selected by the active metadata profile.

`series_summary.csv` is also written once per acquisition date. Each row
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
filename, image type, and spatial orientation. Missing values are written as
`N/A`.

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

## 日本語

この文書は `dicom-organizer` が出力するCSVファイルの仕様です。

## ファイルと行の単位

`dicom_parameters.csv` は acquisition date ごとに1つ作られます。各行は、現在の
metadata profileで選択された対応画像DICOMオブジェクト1件を表します。

`series_summary.csv` も acquisition date ごとに1つ作られます。各行は、同じprofile
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
欠損値は `N/A` として出力されます。

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
