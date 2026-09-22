# Routine Workflows and Repeat Ingestion / 継続運用と定期的な取り込み

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

In active clinical research environments, DICOM data is received continuously in batches. This guide explains how to establish consistent, repeatable intake routines using configuration files, incremental resumption, and GUI preferences.

### 1. Standardizing Intake via Facility Configuration Files

To guarantee consistent output hierarchies, modality profiles, and privacy controls across all staff members, deploy a facility-wide TOML configuration file:

```bash
dicom-organizer /path/to/inbox --config /path/to/facility-config.toml
```

Or configure the environment variable across user shell profiles:
```bash
export DICOM_ORGANIZER_CONFIG=/path/to/facility-config.toml
```

### 2. Incrementally Appending New Studies (`--if-exists skip`)

When new clinical studies arrive, you can append them into an existing organized archive without erroring on previously sorted scans:

```bash
dicom-organizer /path/to/inbox -o /path/to/archive --if-exists skip
```

- When `--if-exists skip` encounters a file at the destination with the same name, it simply skips placing that file without checking or verifying its contents.
- Only newly discovered DICOM slices are copied.
- Metadata tables (`all_series_summary.csv`, `dicom_parameters.csv`) are rebuilt across the entire combined dataset (including previously organized series).

### 3. Comparing Against Historical Catalogs

When performing periodic audits, compare current series summaries with prior archives using spreadsheet filters or diff tools:
- Sort `all_series_summary.csv` by `StudyDate` or `PatientID` to identify newly added examinations.
- Review `file_report.csv` to ensure no unexpected duplicate or skipped files were introduced in the latest intake batch.

### 4. GUI Persistent Preferences

When using the desktop GUI:
- The GUI remembers user preferences across restarts: language, font size, last selected workflow task, patient mode, layout, action (excluding move for safety), profile, series and file template strings, force_read, include_hidden, include_organized, checksum, space_check, advanced settings toggle state, window position and size, and the last browsed directory.
- For safety, target input and output paths are never saved (only the last browsed folder location is retained for dialog initial positions), nor does it save `--if-exists` or `--action move`.
- Use the menu **File → Load configuration file...** (File -> Load configuration file...) to load and apply your team's TOML configuration.

---

<a id="japanese"></a>
## 日本語

画像研究や臨床試験の現場では、検査データが定期的に追加されます。本ガイドでは、施設設定ファイル、差分追加オプション、GUI の設定保持機能を活用して、日々のデータ受け入れ作業を標準化する手順を解説します。

### 1. 施設共通設定ファイルによる手順の統一

チームや部署内でのフォルダ構造、プロファイル、プライバシー設定のばらつきを防ぐため、TOML 設定ファイルを共有します:

```bash
dicom-organizer /path/to/inbox --config /path/to/facility-config.toml
```

または環境変数 `DICOM_ORGANIZER_CONFIG` を設定しておくことで、オプションの指定漏れを防ぐことができます。

### 2. 新しい検査データの差分追加 (`--if-exists skip`)

既存の整理済みアーカイブフォルダに対して、新しい検査データを追記保存できます:

```bash
dicom-organizer /path/to/inbox -o /path/to/archive --if-exists skip
```

- `--if-exists skip` は、出力先に同名のファイルが既に存在する場合、そのファイルをそのままスキップして上書きを回避します（ファイル内容の検証は行いません）。
- 新規に見つかったスライスのみが追加配置されます。
- `all_series_summary.csv` などのメタデータ表は、過去に整理されたシリーズも含めて出力フォルダ全体から再構築されます。

### 3. 過去の一覧との比較

定期的な棚卸し作業では、更新された `all_series_summary.csv` を過去のバックアップ表と比較することで、新規追加された検査やプロトコルの変更点を容易に追跡できます。また、`file_report.csv` でスキップされたファイルの理由を確認できます。

### 4. デスクトップ GUI の設定記憶機能

GUI アプリ版では、次回起動時の利便性のため以下の設定が記憶されます:
- 記憶される設定: 言語、文字サイズ、直前に選んだ目的（一覧・整理・確認）、患者情報モード、レイアウト、動作（安全のため move は保存されません）、プロファイル、シリーズ・ファイル名テンプレート、force_read、隠しファイル、整理済みフォルダを含む、チェックサム、空き容量確認、詳細設定の開閉状態、ウィンドウの位置と大きさ、最後に参照したフォルダ。
- 安全のため、**入力先や書き出し先のパス自体は保存されません**（ファイル選択ダイアログの初期位置として「最後に参照したフォルダ」のみ保持されます）。また、`--if-exists` の選択値も保存されません。
- 「ファイル」メニュー → 「設定ファイルを読み込む…」から、チーム共通の TOML 設定ファイルをいつでも反映できます。
