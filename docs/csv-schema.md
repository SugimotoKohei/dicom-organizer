# CSV Schema

This document describes the CSV files written by `dicom-organizer`.

## Files And Row Scope

`dicom_parameters.csv` is written once per acquisition date. Each row represents
one supported image DICOM object selected by the active metadata profile.

`series_summary.csv` is also written once per acquisition date. Each row
summarizes one organized series folder after applying the same profile filter.

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

## Profile Columns

Profile-specific columns are appended after the common columns.

- `mr`: TR/TE, bandwidth, echo train length, flip angle, averages, field
  strength, sequence fields, inversion time, echo numbers, acquisition matrix,
  phase encoding, sampling, SAR, coil, MR acquisition type, and Siemens channel
  helper fields.
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

Repeatable `--dicom-tag` columns are appended after the profile columns. Missing
custom tags are written as `N/A`.

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

## profile別列

profile別の列は共通列の後ろに追加されます。

- `mr`: TR/TE、bandwidth、echo train length、flip angle、加算回数、磁場強度、
  sequence系、inversion time、echo number、acquisition matrix、phase encoding、
  sampling、SAR、coil、MR acquisition type、Siemens channel補助列。
- `ct`: kVp、tube current、exposure time、convolution kernel、reconstruction diameter。
- `us`: transducer、mechanical/thermal index、color data flag。
- `xa`: kVp、tube current、exposure time、frame time、source-detector/source-patient距離。
- `pt`: radiopharmaceutical、dose、half-life、decay correction。

`--profile auto` は、入力内に存在する対応モダリティの列をまとめて出力します。たとえば
MR/CT混在フォルダでは、`TE_ms` などのMR列と `KVP_kV` などのCT列が両方入ります。
その行に該当しないモダリティ専用列は `N/A` になります。

`--profile generic` は共通列だけを出力します。`--profile ct` のような単一モダリティ
profileでは、そのprofileに一致する行だけを出力し、そのprofileの列だけを追加します。

繰り返し指定できる `--dicom-tag` の列はprofile列の後ろに追加されます。存在しない
custom tagは `N/A` になります。

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
