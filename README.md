# dicom-organizer

[![CI](https://github.com/SugimotoKohei/dicom-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/SugimotoKohei/dicom-organizer/actions/workflows/ci.yml)

A command-line tool that organizes DICOM files by acquisition date and series,
and writes CSV summaries of DICOM acquisition parameters.

DICOMファイルを日付・シリーズごとに整理し、撮像条件のCSVを作るコマンドです。

## English

### Installation

Install the command-line tool:

```bash
uv tool install dicom-organizer
```

From this repository:

```bash
git clone https://github.com/SugimotoKohei/dicom-organizer.git
cd dicom-organizer
uv tool install --editable . --force
```

### Usage

Run the organizer:

```bash
dicom-organizer /path/to/dicom-root
```

Check the installed version:

```bash
dicom-organizer --version
```

A dry run is optional, but useful when checking a new input folder or output
template before writing files:

```bash
dicom-organizer /path/to/dicom-root -n
```

`-i /path/to/dicom-root` and `--input /path/to/dicom-root` are still accepted
for compatibility, but the positional input path is preferred. By default, files are copied to
`<input>/organized/`. Source files are not removed.
By default, DICOM headers are read with `force=True` so exports with slightly
non-standard headers are still included. Add `--no-force-read` if you want to
require standard DICOM headers. Existing output files still raise an error by
default; add `--if-exists skip` when re-running into an existing output folder
and you want to leave existing files untouched.
The default metadata profile is `auto`, which writes a single
`dicom_parameters.csv` for supported image modalities (`MR`, `CT`, `US`, `XA`,
`PT`) and expands columns based on the modalities actually present. Use
`--profile generic` for common columns only, or `--profile mr|ct|us|xa|pt` to
focus the CSVs on one modality.

```bash
dicom-organizer /path/to/dicom-root -p generic
dicom-organizer /path/to/dicom-root -p ct
```

The default series folder name uses a normalized series label: usually `ProtocolName`,
but on vendors where `SeriesDescription` better matches the console-visible sequence
name (for example Philips, GE, and Canon/Toshiba-family systems), it prefers
`SeriesDescription`. If a Philips series contains multiple reconstruction types in the
same `SeriesInstanceUID`, the default folder name also appends a reconstruction label
derived from `ImageType`. When a Philips series label is only a number, the default
name also prefixes the descriptive anchor label from the same acquisition when one is
available.

Output:

```text
organized/<AcquisitionDate>/<SeriesNumber>_<SeriesFolderLabel>/000001.dcm
organized/<AcquisitionDate>/dicom_parameters.csv
organized/<AcquisitionDate>/series_summary.csv
organized/organize_summary.json
```

`dicom_parameters.csv` and `series_summary.csv` focus on supported image objects.
Presentation states and vendor-private helper objects may still be organized into
folders, but they are excluded from these parameter tables.

Run summaries report both the total organized DICOM files and the files included
in the CSV parameter tables:

```text
profile=auto
organized_files=12
csv_target_files=10
csv_excluded_non_image_files=2
organized_files_by_modality=CT=3,MR=7,PR=2
csv_target_files_by_modality=CT=3,MR=7
csv_excluded_files_by_modality=PR=2
```

During `--dry-run`, no files are written. The summary also lists the metadata
files that would be created.

### CSV Columns

`--profile auto` writes the union of columns for supported modalities present in
the input. `--profile generic` writes common columns only. Repeatable
`--dicom-tag` columns are appended to both CSV files after the profile columns.
`series_summary.csv` is generated only from the prepared `dicom_parameters.csv`
rows; it does not read or derive a separate set of DICOM values. Every summary
column is therefore also present in `dicom_parameters.csv`. Series aggregates
such as `FileCount`, `EchoCount`, and `EchoTimes_ms` are repeated on the
corresponding parameter rows. Per-image identifiers, filenames, instance
numbers, and image positions remain parameter-only because they cannot be
represented by one unambiguous series value. See
[CSV Schema](docs/csv-schema.md) for the full CSV row scope, modality-specific
columns, `N/A` handling, and summary counts.

MR outputs include `InPlanePhaseEncodingDirection` and the derived
`PhaseEncodingDirectionPatient` in both `dicom_parameters.csv` and
`series_summary.csv`. The derived value maps the DICOM `ROW`/`COL` image axis
through `ImageOrientationPatient` and writes the positive image-index direction
as a patient-relative arrow such as `R→L`, `A→P`, or `H→F`. `PatientPosition`
is also retained in both CSV files for reference, but is not used as a geometric
transform because DICOM defines it as an annotation. Missing or
unsupported source geometry produces `N/A`.

The MR column `ParallelReductionFactorInPlane` reports the standard DICOM
in-plane parallel-imaging acceleration factor in both CSV files. For example,
`2.0` means a twofold measurement-time reduction factor. Classic top-level and
Enhanced MR functional-group values are supported. For Siemens DICOM without
the standard attribute, the explicit CSA protocol value `sPat.lAccelFactPE` is
used as a fallback. If neither value exists, the result is `N/A`.

### Common Options

Avoid writing patient identifiers to CSV:

```bash
dicom-organizer /path/to/dicom-root --patient-mode hash
dicom-organizer /path/to/dicom-root --patient-mode drop
```

Add extra DICOM tags to the CSV:

```bash
dicom-organizer /path/to/dicom-root -t EchoTime -t TransmitCoilName
```

Common short options are also available: `-i/--input`, `-o/--output`,
`-p/--profile`, `-n/--dry-run`, `-f/--force-read`, `-l/--limit`,
`-t/--dicom-tag`, and `-v/--verbose`.

Use the optional GUI:

```bash
uv tool install 'dicom-organizer[gui]'
dicom-organizer-gui
```

On macOS, create a lightweight `.app` launcher for the installed GUI:

```bash
dicom-organizer-gui-app
open ~/Applications/dicom-organizer.app
```

The launcher uses the Python environment where `dicom-organizer[gui]` is
installed, so keep that tool installation in place. Re-run
`dicom-organizer-gui-app --force` after upgrading if you want to refresh the
launcher metadata.

Try it without real DICOM data:

```bash
uv run python examples/synthetic_quickstart.py
```

Note: the default `--patient-mode keep` writes `PatientName` and `PatientID` to CSV files. Use `hash` or `drop`, and inspect generated CSV files before sharing outputs.

## 日本語

### インストール

コマンドラインツールをインストールします。

```bash
uv tool install dicom-organizer
```

このリポジトリから使う場合:

```bash
git clone https://github.com/SugimotoKohei/dicom-organizer.git
cd dicom-organizer
uv tool install --editable . --force
```

### 使い方

整理を実行します。

```bash
dicom-organizer /path/to/dicom-root
```

インストール済みバージョンを確認します。

```bash
dicom-organizer --version
```

dry-runは必須ではありませんが、新しい入力フォルダや出力テンプレートを使う前に、
書き込みなしで確認したい場合に便利です。

```bash
dicom-organizer /path/to/dicom-root -n
```

互換性のため `-i /path/to/dicom-root` と `--input /path/to/dicom-root` も
引き続き使えますが、通常は位置引数の入力パスを推奨します。
既定では `<input>/organized/` にコピーされます。元ファイルは消えません。
既定では `force=True` でDICOMヘッダーを読み、少し非標準なexport由来のDICOMも
対象にします。標準的なDICOMヘッダーだけを許可したい場合は `--no-force-read` を
付けます。出力先に既存ファイルがある場合は、引き続き既定でエラーにします。
既存の出力フォルダへ再実行し、既存ファイルをそのまま残したい場合は
`--if-exists skip` を付けます。
既定の metadata profile は `auto` で、対応している画像モダリティ（`MR`, `CT`,
`US`, `XA`, `PT`）を 1 つの `dicom_parameters.csv` にまとめ、実際に含まれる
モダリティに応じて列を広げます。共通列だけ欲しい場合は `--profile generic`、
単一モダリティに絞りたい場合は `--profile mr|ct|us|xa|pt` を使います。

```bash
dicom-organizer /path/to/dicom-root -p generic
dicom-organizer /path/to/dicom-root -p ct
```

シリーズフォルダ名の既定値は正規化した series label で、通常は `ProtocolName`、
ただし Philips や GE、Canon/Toshiba 系のように `SeriesDescription` のほうが
コンソール上の系列名に近い装置では `SeriesDescription` を優先します。さらに、
Philips で同じ `SeriesInstanceUID` に複数の再構成が含まれる場合は、`ImageType`
由来の再構成ラベルもフォルダ名に付きます。また、Philips でラベルが数字だけの
系列は、同一 acquisition 内の説明的な系列名を前置して分かりやすくします。

出力:

```text
organized/<AcquisitionDate>/<SeriesNumber>_<SeriesFolderLabel>/000001.dcm
organized/<AcquisitionDate>/dicom_parameters.csv
organized/<AcquisitionDate>/series_summary.csv
organized/organize_summary.json
```

`dicom_parameters.csv` と `series_summary.csv` は対応している画像オブジェクトを
対象にしています。プレゼンテーションステートやベンダー独自の補助オブジェクトも
フォルダ整理はされますが、パラメータ表からは除外されます。

実行サマリには、整理されたDICOMファイル総数と、CSVパラメータ表の対象になった
ファイル数が分かれて表示されます。

```text
profile=auto
organized_files=12
csv_target_files=10
csv_excluded_non_image_files=2
organized_files_by_modality=CT=3,MR=7,PR=2
csv_target_files_by_modality=CT=3,MR=7
csv_excluded_files_by_modality=PR=2
```

`--dry-run` ではファイルは書き込まれません。サマリには、作成予定のメタデータ
ファイルも表示されます。

### CSV列

`--profile auto` は入力内に存在する対応モダリティの列をまとめて出力します。
`--profile generic` は共通列だけを出力します。繰り返し指定できる `--dicom-tag`
列は両CSVのprofile列の後ろに追加されます。`series_summary.csv` は、準備済みの
`dicom_parameters.csv` 用rowだけから生成し、DICOM値を別経路で読み直したり
導出したりしません。そのため、summaryの全列は `dicom_parameters.csv` にも
存在します。`FileCount`、`EchoCount`、`EchoTimes_ms` などのseries集計値は、
対応するparameters各行にも繰り返し出力します。画像固有の識別子、ファイル名、
instance number、画像位置は、seriesの単一値にできないためparametersだけに残します。
CSVの行単位、モダリティ別列、`N/A` の扱い、summary件数の詳細は
[CSV Schema](docs/csv-schema.md) を参照してください。

MR出力では、`InPlanePhaseEncodingDirection` と、そこから導出した
`PhaseEncodingDirectionPatient` を `dicom_parameters.csv` と
`series_summary.csv` の両方に出力します。導出列はDICOMの `ROW` / `COL` 軸を
`ImageOrientationPatient` で患者座標へ写像し、画像indexが増える向きを `R→L`、
`A→P`、`H→F` などの矢印で表します。参照用の `PatientPosition` も両CSVに
残しますが、DICOM上は注釈情報なので幾何変換には
使いません。必要なgeometryが欠損または非対応の場合は `N/A` になります。

MR列の `ParallelReductionFactorInPlane` には、標準DICOMの面内パラレル
イメージング倍速数を両CSVへ出力します。たとえば `2.0` は測定時間の短縮係数が
2倍であることを表します。classic DICOMのtop-level属性とEnhanced MRの
functional groupに対応します。標準属性がないSiemens DICOMでは、CSA protocolの
明示値 `sPat.lAccelFactPE` をfallbackとして使います。どちらもない場合は `N/A` です。

### よく使うオプション

患者情報をCSVに残したくない場合:

```bash
dicom-organizer /path/to/dicom-root --patient-mode hash
dicom-organizer /path/to/dicom-root --patient-mode drop
```

任意のDICOMタグをCSVに追加する場合:

```bash
dicom-organizer /path/to/dicom-root -t EchoTime -t TransmitCoilName
```

よく使う短縮形として、`-i/--input`, `-o/--output`, `-p/--profile`,
`-n/--dry-run`, `-f/--force-read`, `-l/--limit`, `-t/--dicom-tag`,
`-v/--verbose` が使えます。

GUIを使う場合:

```bash
uv tool install 'dicom-organizer[gui]'
dicom-organizer-gui
```

macOSでは、インストール済みGUI用の軽量 `.app` launcherを作成できます。

```bash
dicom-organizer-gui-app
open ~/Applications/dicom-organizer.app
```

このlauncherは `dicom-organizer[gui]` をインストールしたPython環境を使います。
そのため、作成後もuv toolのインストール環境は残してください。アップグレード後に
launcherのメタデータを更新したい場合は `dicom-organizer-gui-app --force` を再実行します。

実DICOMなしで試す場合:

```bash
uv run python examples/synthetic_quickstart.py
```

注意: 既定の `--patient-mode keep` では `PatientName` と `PatientID` がCSVに残ります。共有前は `hash` または `drop` を使い、出力CSVを確認してください。

## Development

```bash
uv sync --locked
uv run python -m pytest
uv run ruff check
uv build
```

MIT License. See [LICENSE](LICENSE).
