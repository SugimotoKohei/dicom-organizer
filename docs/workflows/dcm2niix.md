# Downstream NIfTI Conversion with dcm2niix / dcm2niix による NIfTI 変換連携

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

[dcm2niix](https://github.com/rordenlab/dcm2niix) is the standard neuroimaging research tool for converting DICOM datasets into NIfTI format. However, running batch conversions over raw archives can convert unwanted localizer scans or corrupted series. This guide explains how to pre-filter series using `dicom-organizer`.

### 1. Organizing and Inspecting Series

Run `dicom-organizer` to structure the folder and generate parameter summaries:
```bash
dicom-organizer /path/to/raw-dicom -p mr
```

Inspect `all_series_summary.csv` or `series_summary.csv` to review series descriptions, slice counts, TR/TE values, and modalities. This allows you to identify exactly which series folders correspond to your target functional or structural scans.

### 2. Basic dcm2niix Usage

According to official `dcm2niix` documentation:
- Basic conversion command:
  ```bash
  dcm2niix /path/to/dicom/folder
  ```
- Common command from official documentation:
  ```bash
  dcm2niix -z y -f %p_%t_%s -o /path/to/output /path/to/dicom/folder
  ```
  - `-o`: Specifies the output directory.
  - `-f`: Output file naming template (`%p` for protocol name, `%t` for acquisition time, `%s` for series number).
  - `-z y`: Enables gzip compression (`.nii.gz`).
- For additional conversion flags and advanced parameters, refer to `dcm2niix -h`.

### 3. Automated Batch Conversion Helper (`examples/dcm2niix_batch.py`)

To automate the selection of series directly from organized CSV summaries, use the helper script bundled in this repository:

```bash
# Preview planned dcm2niix commands (dry run)
python examples/dcm2niix_batch.py organized --nifti-dir /path/to/nifti-out

# Execute conversion for series matching description
python examples/dcm2niix_batch.py organized --nifti-dir /path/to/nifti-out --match "T1|T2" --run
```

---

<a id="japanese"></a>
## 日本語

[dcm2niix](https://github.com/rordenlab/dcm2niix) は、脳機能画像や医用画像解析において DICOM を NIfTI 形式へ変換するためのデファクトスタンダードツールです。しかし、未整理のまま一括変換を実行すると、位置決め画像（localizer）や不要な系列まで変換されてしまいます。本ガイドでは、`dicom-organizer` を用いた前処理と連携手順を説明します。

### 1. シリーズの整理と事前確認

`dicom-organizer` を実行してシリーズごとに整理し、サマリ表を作成します:
```bash
dicom-organizer /path/to/raw-dicom -p mr
```

生成された `all_series_summary.csv` を確認し、系列名、スライス数、TR/TE 等から解析対象とすべきシリーズフォルダを特定します。

### 2. dcm2niix の基本的な実行方法

`dcm2niix` の公式ドキュメントに記載されている標準的なコマンドです:
- 基本的な変換コマンド:
  ```bash
  dcm2niix /path/to/dicom/folder
  ```
- 公式ドキュメント記載の圧縮・命名オプション例:
  ```bash
  dcm2niix -z y -f %p_%t_%s -o /path/to/output /path/to/dicom/folder
  ```
  - `-o`: 出力先フォルダの指定。
  - `-f`: ファイル名テンプレート（`%p` プロトコル名、`%t` 撮像時刻、`%s` シリーズ番号）。
  - `-z y`: gzip 圧縮を有効化（`.nii.gz`）。
- その他のオプションについては `dcm2niix -h` を参照してください。

### 3. 一括変換支援スクリプト (`examples/dcm2niix_batch.py`)

リポジトリ同梱の支援スクリプトを用いると、整理済みフォルダ内の `all_series_summary.csv` を読み込んで対象シリーズを絞り込み、`dcm2niix` を一括実行できます:

```bash
# 実行予定コマンドの事前確認（dry-run）
python examples/dcm2niix_batch.py organized --nifti-dir /path/to/nifti-out

# 系列名に T1 または T2 を含むシリーズのみを実際に変換
python examples/dcm2niix_batch.py organized --nifti-dir /path/to/nifti-out --match "T1|T2" --run
```
