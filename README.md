# organize-dicoms

[![CI](https://github.com/SugimotoKohei/organize-dicoms/actions/workflows/ci.yml/badge.svg)](https://github.com/SugimotoKohei/organize-dicoms/actions/workflows/ci.yml)

DICOMファイルを日付・シリーズごとに整理し、撮像条件のCSVを作るコマンドです。

## 日本語

### インストール

PyPI公開後:

```bash
uv tool install organize-dicoms
```

このリポジトリから使う場合:

```bash
git clone https://github.com/SugimotoKohei/organize-dicoms.git
cd organize-dicoms
uv tool install --editable . --force
```

### 使い方

まずdry-runで確認します。

```bash
organize-dicoms --input /path/to/dicom-root --dry-run --force-read --if-exists skip
```

問題なければ実行します。

```bash
organize-dicoms --input /path/to/dicom-root --force-read --if-exists skip
```

既定では `<input>/organized/` にコピーされます。元ファイルは消えません。

出力:

```text
organized/<AcquisitionDate>/<SeriesNumber>_<ProtocolName>/000001.dcm
organized/<AcquisitionDate>/mri_parameters.csv
organized/<AcquisitionDate>/series_summary.csv
organized/organize_summary.json
```

### よく使うオプション

患者情報をCSVに残したくない場合:

```bash
organize-dicoms --input /path/to/dicom-root --patient-mode hash
organize-dicoms --input /path/to/dicom-root --patient-mode drop
```

任意のDICOMタグをCSVに追加する場合:

```bash
organize-dicoms --input /path/to/dicom-root --dicom-tag EchoTime --dicom-tag InPlanePhaseEncodingDirection
```

GUIを使う場合:

```bash
uv tool install 'organize-dicoms[gui]'
organize-dicoms-gui
```

実DICOMなしで試す場合:

```bash
uv run python examples/synthetic_quickstart.py
```

注意: 既定の `--patient-mode keep` では `PatientName` と `PatientID` がCSVに残ります。共有前は `hash` または `drop` を使い、出力CSVを確認してください。

## English

### Installation

After the first PyPI release:

```bash
uv tool install organize-dicoms
```

From this repository:

```bash
git clone https://github.com/SugimotoKohei/organize-dicoms.git
cd organize-dicoms
uv tool install --editable . --force
```

### Usage

Run a dry run first.

```bash
organize-dicoms --input /path/to/dicom-root --dry-run --force-read --if-exists skip
```

Then run the organizer.

```bash
organize-dicoms --input /path/to/dicom-root --force-read --if-exists skip
```

By default, files are copied to `<input>/organized/`. Source files are not removed.

Output:

```text
organized/<AcquisitionDate>/<SeriesNumber>_<ProtocolName>/000001.dcm
organized/<AcquisitionDate>/mri_parameters.csv
organized/<AcquisitionDate>/series_summary.csv
organized/organize_summary.json
```

### Common Options

Avoid writing patient identifiers to CSV:

```bash
organize-dicoms --input /path/to/dicom-root --patient-mode hash
organize-dicoms --input /path/to/dicom-root --patient-mode drop
```

Add extra DICOM tags to the CSV:

```bash
organize-dicoms --input /path/to/dicom-root --dicom-tag EchoTime --dicom-tag InPlanePhaseEncodingDirection
```

Use the optional GUI:

```bash
uv tool install 'organize-dicoms[gui]'
organize-dicoms-gui
```

Try it without real DICOM data:

```bash
uv run python examples/synthetic_quickstart.py
```

Note: the default `--patient-mode keep` writes `PatientName` and `PatientID` to CSV files. Use `hash` or `drop`, and inspect generated CSV files before sharing outputs.

## Development

```bash
uv sync --locked
uv run pytest
uv run ruff check
uv build
```

MIT License. See [LICENSE](LICENSE).
