# Migration and Upgrade Guide (0.1.x to 0.2.0) / アップグレードと移行ガイド

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This guide details the differences, breaking changes, and upgrade/downgrade instructions when migrating from version 0.1.x (latest: 0.1.3) to 0.2.0 of `dicom-organizer`.
All facts in this guide are empirically verified against 0.1.3 code and outputs.

### 1. Key Changes and Breaking Modifications

#### 1. Default Folder Hierarchy (Breaking Change)
- **0.1.3**: `<output>/<AcquisitionDate>/<SeriesNumber>_<Label>/` (no device directory, date was based on `AcquisitionDate` falling back to `StudyDate`).
- **0.2.0**: `<output>/<Device>/<StudyDate>/<SeriesNumber>_<Label>/` (default `--layout device-date`, device folder derived from `Manufacturer` and `ManufacturerModelName`, date based on `StudyDate` falling back to `AcquisitionDate`).
- **Additional Layouts**: Added `--layout study` and `--layout patient-study`.
- **Do NOT reuse an existing 0.1.x output folder**: Organizing into a folder created by 0.1.x with 0.2.0 (even with `--if-exists skip`) will copy files again under the new directory layout, causing duplicate files and doubling rows in series summaries. Always specify a **new output folder** for 0.2.0.

#### 2. Identical Duplicate Handling (Behavior Change)
- **0.1.3**: Copied identical duplicate files with the same SOPInstanceUID and identical content into multiple files.
- **0.2.0**: Places only the first discovered file and skips identical duplicates, recording them as `duplicate_identical` in `file_report.csv` with their original source in `DuplicateOf`. As a result, row counts in `dicom_parameters.csv` and `FileCount` in `series_summary.csv` may be lower than in 0.1.3.

#### 3. `--force-read` Default (Behavior Change)
- **0.1.3**: Default was off (pydicom `force=True` only when `--force-read` was passed).
- **0.2.0**: Default is on. Files missing the 128-byte preamble and `DICM` prefix are parsed as DICOM by default if valid UIDs are present. Use `--no-force-read` for strict 0.1.3-style reading.

#### 4. Strict Privacy Mode Semantics (`--patient-mode drop`) (Breaking Change)
- **0.1.3**: `PatientName` and `PatientID` were `N/A`, but `PatientNameHash` and `PatientIDHash` retained SHA-256 hashes.
- **0.2.0**: All 4 columns are set to `N/A`. If you need hashes, use `--patient-mode hash`.

#### 5. Granular Skip Reason Classification (`skipped_non_dicom`) (Breaking Change)
- **0.1.3**: All unreadable candidate files were lumped into `skipped_non_dicom`.
- **0.2.0**: `skipped_non_dicom` counts only genuinely non-DICOM files (reason code `not_dicom`). All skip reasons are categorized into 9 distinct codes (`core.SKIP_REASONS`): `not_dicom`, `dicomdir`, `missing_required_uid`, `read_error`, `permission_denied`, `io_error`, `excluded_hidden`, `duplicate_identical`, and `existing_output`.

#### 6. CSV Column Changes
- **`series_summary.csv`**: **`SeriesUIDHash` column was removed** (Breaking Change). Identify series via `SeriesUID` or `SeriesFolder`.
- **`CoilElementCount`**: Missing value representation changed from `0` in 0.1.3 to `N/A` in 0.2.0.
- **`dicom_parameters.csv`**: 15 columns added (no columns deleted).

#### 7. New Output Files in 0.2.0
- **`all_series_summary.csv`**: Root-level cross-study series summary.
- **`file_report.csv`**: Comprehensive per-file tracking (11 columns).
- **`all_dicom_parameters.csv`**: Parameter table produced in list-only mode (`--list-only`).

#### 8. `organize_summary.json`
- No keys were removed. Added 22 new keys including `output_schema_version` (integer 2), `skipped_by_reason`, `planned_files`, `not_processed_files`, `duplicate_conflicts`, `previous_run_status`, `privacy_notices`, `warnings`, `layout`, and `checksum`.

#### 9. Command Line Additions
- Positional argument support: `dicom-organizer /path/to/input` (`--input` remains supported).
- New options (no options removed): `--list-only`, `--layout`, `--checksum`, `--no-space-check`, `--no-progress`, `--config`, `--print-config`, `--self-test`, `--self-test-report`, `--diagnostics`, `--print-schema`, `--no-force-read`, and short flags (`-i`, `-o`, `-n`, `-f`, `-l`, `-p`, `-t`, `-v`). Can also be invoked with `python -m dicom_organizer`.

### 2. How to Upgrade or Downgrade

#### Standalone Desktop App
- **Upgrade**: Download the `0.2.0` `.zip` from GitHub Releases, extract it, and place it in your applications folder.
- **Downgrade to 0.1.x**: Standalone desktop app packages were **not available** in 0.1.x (standalone apps are introduced starting with 0.2.0). To use 0.1.x, install the Python package.

#### Python Package (`uv tool` / `pip`)
- **Upgrade to 0.2.0**:
  ```bash
  uv tool upgrade dicom-organizer
  # Or with GUI extra:
  uv tool install --force 'dicom-organizer[gui]>=0.2.0'
  ```
- **Downgrade to 0.1.3**:
  ```bash
  uv tool install --force 'dicom-organizer==0.1.3'
  # Or with GUI extra:
  uv tool install --force 'dicom-organizer[gui]==0.1.3'
  # With pip:
  pip install 'dicom-organizer==0.1.3'
  ```

---

<a id="japanese"></a>
## 日本語

本文書は、`dicom-organizer` のバージョン 0.1.x（最新: 0.1.3）から 0.2.0 への移行に伴う変更点、影響、および更新・復帰手順を解説します。
本文書に記載された事実は、0.1.3 の実コードおよび実行結果に基づいています。

### 1. 0.2.0 における主な変更点と破壊的変更

#### 1. 既定のフォルダ構成（破壊的変更）
- **0.1.3**: `<出力>/<AcquisitionDate>/<シリーズ番号>_<ラベル>/`（装置フォルダなし、日付は `AcquisitionDate` 優先）。
- **0.2.0**: `<出力>/<装置>/<StudyDate>/<シリーズ番号>_<ラベル>/`（既定の `--layout device-date`。装置フォルダは `Manufacturer` と `ManufacturerModelName` から生成、日付は `StudyDate` 優先）。
- **新レイアウトの追加**: `--layout study` および `--layout patient-study` を追加。
- **旧版の出力フォルダに追記しないこと**: 0.1.x で作成した出力フォルダに 0.2.0 で整理（`--if-exists skip` を指定しても）を実行すると、新構成で再度ファイルがコピーされ、一覧 CSV に新旧両方のシリーズが重複して掲載されます。必ず**新しい空の出力フォルダ**を指定してください。0.1.x のフォルダはそのまま残しておけます。

#### 2. 同一内容の重複ファイル（動作の変更）
- **0.1.3**: 同じ SOPInstanceUID で内容が同一のファイルもすべてコピーしていました。
- **0.2.0**: 最初に見つかった 1 つのみを整理し、残りはコピーせず `file_report.csv` に `duplicate_identical`（`DuplicateOf` 列に元のファイル）として記録します。そのため、`dicom_parameters.csv` の行数や `series_summary.csv` の `FileCount` が減少する場合があります。

#### 3. `--force-read` の既定（動作の変更）
- **0.1.3**: 既定はオフ（`--force-read` を指定したときのみ pydicom の `force=True` で読み込み）。
- **0.2.0**: 既定でオン。先頭 128 バイトや `DICM` マジックナンバーがないファイルも必要な UID があれば既定で整理されます。0.1.3 と同様の厳密な読み込みに戻すには `--no-force-read` を指定します。

#### 4. プライバシー設定 `drop` の厳格化（破壊的変更）
- **0.1.3**: `PatientName` / `PatientID` は `N/A` ですが、`PatientIDHash` / `PatientNameHash` にハッシュ値が残っていました。
- **0.2.0**: 4 列すべてが `N/A` となります。ハッシュ値が必要な場合は `--patient-mode hash` を使用してください。

#### 5. スキップ理由の細分化と `skipped_non_dicom`（破壊的変更）
- **0.1.3**: 読み込めなかった候補ファイル全般を `skipped_non_dicom` に集計していました。
- **0.2.0**: 非 DICOM ファイル（理由コード `not_dicom`）のみをカウントします。スキップ理由は次の 9 種のコード（`core.SKIP_REASONS`）で詳細に分類され、`organize_summary.json` の `skipped_by_reason` および `file_report.csv` の `Reason` 列に出力されます: `not_dicom`, `dicomdir`, `missing_required_uid`, `read_error`, `permission_denied`, `io_error`, `excluded_hidden`, `duplicate_identical`, `existing_output`。

#### 6. CSV の列の変更（破壊的変更）
- **`series_summary.csv`**: **`SeriesUIDHash` 列が削除されました**（破壊的変更）。シリーズの識別には `SeriesUID` または `SeriesFolder` を使用してください。
- **`CoilElementCount`**: 値が取れないときの表記が `0` から `N/A` に変更されました。
- **`dicom_parameters.csv`**: 15 列が追加されました（削除列はありません）。

#### 7. 新しい出力ファイル
- **`all_series_summary.csv`**: 全検査のシリーズ一覧（出力ルート直下）。
- **`file_report.csv`**: 全候補ファイルの処理結果・理由・SHA-256 レポート（11 列）。
- **`all_dicom_parameters.csv`**: 一覧のみモード（`--list-only`）専用の撮像条件表。

#### 8. `organize_summary.json`
- 0.1.3 のキーはすべて維持され（削除なし）、整数の `output_schema_version`（値: 2）、`skipped_by_reason`、`planned_files`、`not_processed_files`、`duplicate_conflicts`、`previous_run_status`、`privacy_notices`、`warnings`、`layout`、`checksum` など 22 個のキーが追加されました。

#### 9. コマンドラインの機能拡張
- 入力フォルダを位置引数として指定可能になりました（`dicom-organizer /path/to/input`。従来の `--input` も使用可能）。
- 新規オプション（削除されたオプションはありません）: `--list-only`, `--layout`, `--checksum`, `--no-space-check`, `--no-progress`, `--config`, `--print-config`, `--self-test`, `--self-test-report`, `--diagnostics`, `--print-schema`, `--no-force-read`、および短縮オプション（`-i`, `-o`, `-n`, `-f`, `-l`, `-p`, `-t`, `-v`）。`python -m dicom_organizer` での起動も可能になりました。

### 2. 更新方法と旧版への戻し方

#### 単体アプリ版
- **更新**: GitHub Releases から 0.2.0 の zip をダウンロードして展開し、既存のアプリを置き換えてください。
- **旧版への復帰**: 0.1.x には単体アプリ（Python 不要の版）は存在しません（単体アプリは 0.2.0 からの提供です）。0.1.x に戻す場合は下記の Python パッケージ版を使用してください。なお、0.2.0 以降の版どうしであれば以前のリリースの zip で置き換え可能です。

#### Python パッケージ版 (`uv tool` / `pip`)
- **0.2.0 への更新**:
  ```bash
  uv tool upgrade dicom-organizer
  # または GUI 版:
  uv tool install --force 'dicom-organizer[gui]>=0.2.0'
  ```
- **0.1.3 への復帰**:
  ```bash
  uv tool install --force 'dicom-organizer==0.1.3'
  # または GUI 版:
  uv tool install --force 'dicom-organizer[gui]==0.1.3'
  # pip の場合:
  pip install 'dicom-organizer==0.1.3'
  ```
- **注意**: 0.2.0 で作成した出力フォルダは、0.1.x で上書き・追記しないでください（フォルダ構成が異なるためファイルが二重にコピーされます）。必ず新しい出力フォルダを使用してください。
