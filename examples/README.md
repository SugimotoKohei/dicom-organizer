# Examples and Tool Integrations / サンプルと連携スクリプト

This directory provides runnable examples and workflow integration scripts demonstrating how `dicom-organizer` connects to downstream neuroimaging, research, and analysis workflows.

Both integration scripts (`compare_protocols.py` and `dcm2niix_batch.py`) are implemented using only the Python standard library, requiring Python 3.11 or higher. They can be executed independently without installing the `dicom-organizer` package (note: standalone desktop app users must have Python 3.11+ installed to run these scripts).

このディレクトリには、`dicom-organizer` を下流の研究・画像解析ワークフローと連携させるための実行可能な実例スクリプトが収録されています。
連携スクリプト（`compare_protocols.py` および `dcm2niix_batch.py`）は Python 標準ライブラリのみで書かれており、Python 3.11 以上があれば `dicom-organizer` 本体をインストールしていなくても単独で実行可能です（単体アプリの利用者がスクリプトを実行する場合は、環境に Python 3.11 以上が必要です）。

---

## English

### 1. `synthetic_quickstart.py`
Generates a deterministic synthetic DICOM dataset in a temporary folder and runs `dicom-organizer` against it. It verifies end-to-end organization and parameter extraction without requiring real patient or scanner data.

**Usage:**
```bash
python examples/synthetic_quickstart.py
```

### 2. `compare_protocols.py`
Reads `all_series_summary.csv` produced by `dicom-organizer` and compiles a side-by-side protocol comparison table (`protocol_comparison.csv`) across scanners (Manufacturer + Model) and studies.

- Groups series by `SeriesDescription` by default. When comparing acquisitions across different scanners or facilities, grouping with `--by ProtocolName` is recommended.
- Identifies any imaging parameters (TR, TE, flip angle, bandwidth, matrix, etc.) that vary within the same protocol group in the `DifferingColumns` column.
- Validates grouping and comparison columns against the CSV header; unknown column names are reported with error code 2.
- Saves output with a UTF-8 BOM (`utf-8-sig`) for immediate inspection in spreadsheet software such as Microsoft Excel.
- Implemented with the Python standard library (requires Python 3.11+).

**Usage:**
```bash
# Compare using summary CSV
python examples/compare_protocols.py path/to/organized/all_series_summary.csv

# Compare directly specifying organized output folder and custom output path across scanners
python examples/compare_protocols.py path/to/organized -o comparison.csv --by ProtocolName
```

### 3. `dcm2niix_batch.py`
Selects relevant imaging series (e.g. MRI T1/T2 series) from `all_series_summary.csv` using regular expressions, and prepares or executes `dcm2niix` conversion commands into a dedicated NIfTI folder (`<output>_nifti/`).

- By default, it outputs dry-run shell commands starting with `dcm2niix` without executing them (quoted for POSIX or Windows `cmd.exe`).
- Pass `--run` to execute conversion commands if `dcm2niix` is installed in your `PATH`. If any series conversion fails, execution continues for remaining series and exits with a non-zero status displaying all failed series.
- Warns to stderr if a series listed in the CSV does not exist on disk.
- Rejects output directories inside the organized folder to preserve DICOM tree purity.
- Rejects `--list-only` output directories with a clear explanation since DICOM image files were not materialized.
- Implemented with the Python standard library (requires Python 3.11+).

**Usage:**
```bash
# Preview conversion commands for T2 series
python examples/dcm2niix_batch.py path/to/organized --match T2

# Execute dcm2niix conversion for all MR series
python examples/dcm2niix_batch.py path/to/organized --modality MR --run
```

---

## 日本語 (Japanese)

### 1. `synthetic_quickstart.py`
実患者データや実機データを使わず、一時フォルダに合成 DICOM データセットを自動生成して `dicom-organizer` を実行するクイックスタート例です。安全に初期動作や CSV 出力を確認できます。

**実行方法:**
```bash
python examples/synthetic_quickstart.py
```

### 2. `compare_protocols.py`
`dicom-organizer` が出力した `all_series_summary.csv` を読み込み、装置（Manufacturer + ManufacturerModelName）および検査間で撮像条件（TR、TE、FlipAngle、マトリクスなど）を横断比較する表（`protocol_comparison.csv`）を出力します。

- 既定では `--by SeriesDescription` でシリーズをまとめます。装置や施設をまたいで同じプロトコルを比較したいときは `--by ProtocolName` の指定が向いています。
- まとまりの中で値が一致しない項目名を `DifferingColumns` 列に `|` 区切りで抽出します（例: `TE_ms|FlipAngle_deg`）。
- `--by` や `--columns` に存在しない列名が指定された場合は、利用可能な列名一覧を表示して終了コード 2 で安全に停止します。
- 出力 CSV は UTF-8 BOM 付き（`utf-8-sig`）のため、Excel でそのまま文字化けなく開けます。
- Python 標準ライブラリのみで動作します（Python 3.11 以上が必要）。

**実行方法:**
```bash
# 整理済みフォルダ内の all_series_summary.csv を比較
python examples/compare_protocols.py path/to/organized/all_series_summary.csv

# 出力先を指定してプロトコル名単位で装置間を横断比較
python examples/compare_protocols.py path/to/organized -o comparison.csv --by ProtocolName
```

### 3. `dcm2niix_batch.py`
`all_series_summary.csv` の情報に基づいて、NIfTI 変換に必要なシリーズ（例: T2 強調画像など）を正規表現で絞り込み、`dcm2niix` 変換コマンドを組み立てる連携スクリプトです。

- 既定では実行せず、組み立てた `dcm2niix` コマンドを 1 行 1 コマンドで標準出力に表示します（Windows 環境では `cmd.exe` に適した引用形式を使用）。
- `--run` オプションを指定した場合のみ、環境内の `dcm2niix` コマンドを呼び出して変換を実行します。一部の変換が失敗した場合でも残りのシリーズの変換を継続し、最後に失敗件数と対象シリーズ名を表示して終了コード 1 で終了します。
- CSV に記載されているがフォルダが存在しないシリーズがある場合は、標準エラー出力に警告を表示してスキップします。
- `--nifti-dir` に整理済みフォルダ内部のパスが指定された場合はエラーで停止します。
- 一覧作成のみモード（`--list-only`）で作成されたフォルダが渡された場合は、DICOM ファイルが配置されていない旨を分かりやすく案内して終了します。
- Python 標準ライブラリのみで動作します（Python 3.11 以上が必要）。

**実行方法:**
```bash
# T2 シリーズのみを抽出して dcm2niix コマンドを表示
python examples/dcm2niix_batch.py path/to/organized --match T2

# MR シリーズを実際に NIfTI に一括変換
python examples/dcm2niix_batch.py path/to/organized --modality MR --run
```
