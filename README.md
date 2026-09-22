# dicom-organizer

[![CI](https://github.com/SugimotoKohei/dicom-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/SugimotoKohei/dicom-organizer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dicom-organizer.svg)](https://pypi.org/project/dicom-organizer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/SugimotoKohei/dicom-organizer/blob/main/LICENSE)

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

A safe, offline desktop tool and command-line utility that organizes local messy DICOM directories into standardized series folders, audits acquisition parameters into unified CSV summaries, and prepares clean data for downstream research workflows.

### 1. Built for These Core Tasks

- **List Imaging Parameters**: Extract standardized acquisition parameters (TR, TE, flip angle, bandwidth, slice thickness, phase encoding direction, and parallel acceleration factor) into CSV tables across scanners without copying files.
- **Copy and Organize**: Safely sort messy slice exports into structured `<Device>/<StudyDate>/<SeriesNumber>_<SeriesFolderLabel>/` directories (using `ProtocolName` by default, or `SeriesDescription` for Philips, GE, and Canon/Toshiba systems) while tracking identical duplicate slices.
- **Preview Before Organizing**: Safely simulate organization and review planned directory layouts and metadata summaries before writing anything to disk.

### 2. Before and After Organization

See [`docs/images/before-after.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/images/before-after.md) for full details.

#### Input Structure (Disorganized Exports)
```text
sample_dataset/
├── BACKUP/
│   └── IM00001
└── EXPORT/
    ├── DISK1/
    │   ├── 0001/
    │   │   ├── IM00001
    │   │   ├── IM00002
    │   │   ├── IM00003
    │   │   └── ...
    │   ├── 0002/
    │   │   ├── IM00010
    │   │   ├── IM00011
    │   │   ├── IM00012
    │   │   └── ...
    │   ├── 0003/
    │   │   ├── IM00019
    │   │   ├── IM00020
    │   │   ├── IM00021
    │   │   └── ...
    │   └── 0004/
    │       ├── IM00028
    │       ├── IM00029
    │       └── IM00030
    └── README.TXT
```

#### Organized Output Structure
```text
organized/
├── Example-Medical_Demo-CT/
│   └── 20260604/
│       ├── 000001_Axial-CT/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── Example-Medical_Demo-MR-1.5T/
│   └── 20260603/
│       ├── 000001_T1/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000002_T2/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000003_FLAIR/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── Example-Medical_Demo-MR-3T/
│   ├── 20260601/
│   │   ├── 000001_T1/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000002_T2/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000003_FLAIR/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000099_PR/
│   │   │   └── 000001.dcm
│   │   ├── dicom_parameters.csv
│   │   └── series_summary.csv
│   └── 20260602/
│       ├── 000001_T1/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000002_T2/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000003_FLAIR/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── all_series_summary.csv
├── file_report.csv
└── organize_summary.json
```

#### Extracted Parameter Summary (`all_series_summary.csv`)
| StudyFolder | SeriesFolder | SeriesDescription | Modality | TR_ms | TE_ms | FlipAngle_deg | ScanDuration |
|---|---|---|---|---|---|---|---|
| Example-Medical_Demo-CT/20260604 | Example-Medical_Demo-CT/20260604/000001_Axial-CT | Demo CT Axial CT | CT | N/A | N/A | N/A | N/A |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000001_T1 | Demo MR 1.5T T1 | MR | 450.0 | 12.0 | 70.0 | 00:01:40 |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000002_T2 | Demo MR 1.5T T2 | MR | 3500.0 | 90.0 | 90.0 | 00:02:40 |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000003_FLAIR | Demo MR 1.5T FLAIR | MR | 8000.0 | 110.0 | 140.0 | 00:03:30 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000001_T1 | Demo MR 3T T1 | MR | 500.0 | 10.0 | 70.0 | 00:02:00 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000002_T2 | Demo MR 3T T2 | MR | 4000.0 | 80.0 | 90.0 | 00:03:00 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000003_FLAIR | Demo MR 3T FLAIR | MR | 9000.0 | 120.0 | 150.0 | 00:04:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000001_T1 | Demo MR 3T T1 | MR | 500.0 | 10.0 | 70.0 | 00:02:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000002_T2 | Demo MR 3T T2 | MR | 4000.0 | 100.0 | 90.0 | 00:03:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000003_FLAIR | Demo MR 3T FLAIR | MR | 9000.0 | 120.0 | 150.0 | 00:04:00 |

#### Interactive GUI Demonstration
![dicom-organizer demo](https://raw.githubusercontent.com/SugimotoKohei/dicom-organizer/main/docs/images/demo-ja.gif)

![dicom-organizer English GUI](https://raw.githubusercontent.com/SugimotoKohei/dicom-organizer/main/docs/images/result-list-en.png)

More screenshots are available in [`docs/images/`](https://github.com/SugimotoKohei/dicom-organizer/tree/main/docs/images).

### 3. Getting Started

#### Standalone Desktop App (Recommended for most users)
Download the application bundle for Windows or macOS from [GitHub Releases](https://github.com/SugimotoKohei/dicom-organizer/releases).
> [!NOTE]
> Standalone executable packages will be provided starting with the **0.2.0** release. Prior to 0.2.0, please use the Python package. The published PyPI package may differ slightly from the unreleased main branch documentation.
> Unsigned binaries trigger first-launch warnings; see [`docs/install.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/install.md) for dismissal instructions.

#### Python Package Edition
Requires Python 3.11:
```bash
# Command-line tool only
uv tool install dicom-organizer

# Command-line tool + PySide6 desktop GUI
uv tool install 'dicom-organizer[gui]'
```

#### Try with Synthetic Samples
- In the GUI: Click **"Try with Sample Data"** on the start screen.
- In terminal: Run the built-in self-test:
  ```bash
  dicom-organizer --self-test
  ```

For comprehensive CLI arguments and column derivations, see [`docs/usage.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/usage.md).

### 4. Generated Output Files

When organizing completes, the following files are produced:
- `all_series_summary.csv`: Root-level table concatenating imaging parameter summaries across all processed series and studies.
- `<StudyFolder>/series_summary.csv` & `dicom_parameters.csv`: Detailed parameter tables generated per examination folder.
- `file_report.csv`: Complete audit log tracking every candidate file, destination path, status, and skip reasons.
- `organize_summary.json`: Machine-readable execution summary recording configuration, timestamps (`started_at`, `ended_at`), and categorized skip counts.

In list-only mode (`--list-only`), `all_series_summary.csv`, `all_dicom_parameters.csv`, `file_report.csv`, and `organize_summary.json` are generated directly under the output root without per-study directories.

### 5. Essential Notices & Limitations

- **Patient Information Safety**:
  - `dicom-organizer` is **not an anonymization tool**. DICOM file binaries are never altered; patient identifiers remain embedded inside all organized DICOM slices.
  - `--patient-mode keep` (default) writes patient names and IDs to CSV tables. Use `--patient-mode hash` (pseudonymization) or `--patient-mode drop` (omission) to sanitize CSV outputs. See [`docs/privacy.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/privacy.md).
- **Not a Medical Device**: Provided solely for research and local data organization workflows. It is not intended for diagnostic or clinical decision making.
- **Modality Support Boundaries**: Real scanner validation was performed on MR (5 scanner models across 4 manufacturers). CT, US, XA, and PT modalities, along with compressed transfer syntaxes and Japanese character sets, are verified using synthetic test datasets. See [`docs/support-matrix.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/support-matrix.md) and [`docs/validation.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/validation.md).

### 6. Documentation Index by Role

- **New Users & Technologists**: [`docs/install.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/install.md), [`docs/faq.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/faq.md), [`docs/usage.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/usage.md).
- **Researchers & Engineers**: [`docs/positioning.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/positioning.md), [`docs/support-matrix.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/support-matrix.md), [`docs/privacy.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/privacy.md), [`docs/performance.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/performance.md).
- **IT Administrators**: [`docs/deployment-guide.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/deployment-guide.md), [`docs/validation.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/validation.md).
- **Full Library**: [`docs/README.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/README.md).

### 7. Support & Contact

If you have questions or encounter issues, refer to [`SUPPORT.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/SUPPORT.md).
- For general questions: [GitHub Discussions](https://github.com/SugimotoKohei/dicom-organizer/discussions).
- For bugs: [Bug Report Template](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=bug_report.yml).
- Email contact: `sugimotokouhei@gmail.com`
> [!CAUTION]
> **Never send real patient data, clinical DICOM files, or private paths via GitHub or email.**

### 8. Governance & Contributing

See [`GOVERNANCE.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/GOVERNANCE.md) and [`CONTRIBUTING.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/CONTRIBUTING.md). Released under the [MIT License](https://github.com/SugimotoKohei/dicom-organizer/blob/main/LICENSE).

---

<a id="japanese"></a>
## 日本語

手元の PC で安全に動作し、散らばった DICOM フォルダを規格化されたシリーズ階層に自動整理するとともに、撮像条件（TR、TE、フリップ角、スライス厚、倍速数など）を 1 つの CSV 表に抽出するオープンソースツールです。

### 1. こんな作業に

- **撮像条件を一覧にする**: 画像をコピーせず、複数メーカーの MR/CT 撮像パラメータ（TR, TE, フリップ角, スライス厚, 位相エンコード方向, 倍速数等）を 1 つの CSV に抽出します。
- **コピーして整理する**: コンソールやディスクから取り出した散乱スライスを、`<装置名>/<検査日>/<シリーズ番号>_<系列名>/`（系列名は通常 `ProtocolName`、Philips・GE・Canon/Toshiba では `SeriesDescription`）の階層へコピーし、同一重複を除外します。
- **整理前に内容を確認する**: 実際にディスクへ書き込む前に、整理対象ファイル数、スキップ理由、作成予定のフォルダ階層を画面上で安全に事前シミュレーションします。

### 2. 整理前と整理後

詳細は [`docs/images/before-after.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/images/before-after.md) をご覧ください。

#### 整理前の入力ツリー（散乱したエクスポート）
```text
sample_dataset/
├── BACKUP/
│   └── IM00001
└── EXPORT/
    ├── DISK1/
    │   ├── 0001/
    │   │   ├── IM00001
    │   │   ├── IM00002
    │   │   ├── IM00003
    │   │   └── ...
    │   ├── 0002/
    │   │   ├── IM00010
    │   │   ├── IM00011
    │   │   ├── IM00012
    │   │   └── ...
    │   ├── 0003/
    │   │   ├── IM00019
    │   │   ├── IM00020
    │   │   ├── IM00021
    │   │   └── ...
    │   └── 0004/
    │       ├── IM00028
    │       ├── IM00029
    │       └── IM00030
    └── README.TXT
```

#### 整理後の出力ツリー
```text
organized/
├── Example-Medical_Demo-CT/
│   └── 20260604/
│       ├── 000001_Axial-CT/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── Example-Medical_Demo-MR-1.5T/
│   └── 20260603/
│       ├── 000001_T1/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000002_T2/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000003_FLAIR/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── Example-Medical_Demo-MR-3T/
│   ├── 20260601/
│   │   ├── 000001_T1/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000002_T2/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000003_FLAIR/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000099_PR/
│   │   │   └── 000001.dcm
│   │   ├── dicom_parameters.csv
│   │   └── series_summary.csv
│   └── 20260602/
│       ├── 000001_T1/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000002_T2/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000003_FLAIR/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── all_series_summary.csv
├── file_report.csv
└── organize_summary.json
```

#### 抽出された撮像条件の抜粋 (`all_series_summary.csv`)
| StudyFolder | SeriesFolder | SeriesDescription | Modality | TR_ms | TE_ms | FlipAngle_deg | ScanDuration |
|---|---|---|---|---|---|---|---|
| Example-Medical_Demo-CT/20260604 | Example-Medical_Demo-CT/20260604/000001_Axial-CT | Demo CT Axial CT | CT | N/A | N/A | N/A | N/A |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000001_T1 | Demo MR 1.5T T1 | MR | 450.0 | 12.0 | 70.0 | 00:01:40 |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000002_T2 | Demo MR 1.5T T2 | MR | 3500.0 | 90.0 | 90.0 | 00:02:40 |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000003_FLAIR | Demo MR 1.5T FLAIR | MR | 8000.0 | 110.0 | 140.0 | 00:03:30 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000001_T1 | Demo MR 3T T1 | MR | 500.0 | 10.0 | 70.0 | 00:02:00 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000002_T2 | Demo MR 3T T2 | MR | 4000.0 | 80.0 | 90.0 | 00:03:00 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000003_FLAIR | Demo MR 3T FLAIR | MR | 9000.0 | 120.0 | 150.0 | 00:04:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000001_T1 | Demo MR 3T T1 | MR | 500.0 | 10.0 | 70.0 | 00:02:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000002_T2 | Demo MR 3T T2 | MR | 4000.0 | 100.0 | 90.0 | 00:03:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000003_FLAIR | Demo MR 3T FLAIR | MR | 9000.0 | 120.0 | 150.0 | 00:04:00 |

#### デスクトップ GUI の操作例
![dicom-organizer 操作デモ](https://raw.githubusercontent.com/SugimotoKohei/dicom-organizer/main/docs/images/demo-ja.gif)

その他の画面例は [`docs/images/`](https://github.com/SugimotoKohei/dicom-organizer/tree/main/docs/images) を参照してください。

### 3. はじめ方

#### 単体デスクトップアプリ版（Python 不要・おすすめ）
[GitHub Releases](https://github.com/SugimotoKohei/dicom-organizer/releases) から Windows 版または macOS 版の zip をダウンロードして展開します。
> [!NOTE]
> 単体アプリ版は本改定を含むリリース **0.2.0** から提供されます。それまでは Python パッケージ版をご利用ください。PyPI で公開中のバージョンと、本 README（main ブランチ）の内容が異なる場合があります。
> 未署名アプリのため初回起動時にセキュリティ警告が表示されます。解除方法は [`docs/install.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/install.md) を参照してください。

#### Python パッケージ版
Python 3.11 環境で `uv` を用いてインストールします:
```bash
# コマンドラインツールのみ
uv tool install dicom-organizer

# コマンドラインツール + PySide6 デスクトップ GUI
uv tool install 'dicom-organizer[gui]'
```

#### 合成サンプルで試す（実データ不要）
- GUI の場合: 初期画面の「**サンプルデータで試す**」ボタンをクリック。
- コマンドラインの場合: 自己診断コマンドを実行:
  ```bash
  dicom-organizer --self-test
  ```

CLI オプションの詳細や各パラメータの解説は [`docs/usage.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/usage.md) をご覧ください。

### 4. 出力されるもの

整理完了後、以下のファイルが作成されます:
- `all_series_summary.csv`: 出力ルート直下に作成される、全検査・全シリーズを横断した撮像パラメータ一覧表。
- `<検査フォルダ>/series_summary.csv` & `dicom_parameters.csv`: 検査フォルダごとに作成される詳細パラメータ表。
- `file_report.csv`: 検出された全ファイルの元パス、整理先パス、処理成否、スキップ理由を記録した監査レポート。
- `organize_summary.json`: 実行オプション、開始・終了時刻（`started_at`、`ended_at`）、スキップ理由別の件数を記録した機械可読サマリ。

なお、一覧のみモード（`--list-only`）では、出力ルート直下に `all_series_summary.csv`、`all_dicom_parameters.csv`、`file_report.csv`、`organize_summary.json` が生成されます。

### 5. 大事な注意点

- **患者情報の保護**:
  - `dicom-organizer` は **匿名化ツールではありません**。整理された DICOM ファイルのバイナリやヘッダーは変更されず、患者情報は内部に残ります。
  - `--patient-mode keep`（既定値）では患者氏名や ID が CSV に出力されます。外部共有時は `--patient-mode hash`（仮名化）または `--patient-mode drop`（除外）を指定し、事前に CSV を確認してください。詳細は [`docs/privacy.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/privacy.md) を参照してください。
- **医療機器ではありません**: 本ソフトウェアは研究およびデータ整理ワークフローを支援するものであり、診断や治療等の医療行為には使用できません。
- **対応範囲**: 実データで検証したのは MR（4 社 5 機種）です。CT、US、XA、PT、圧縮転送構文、および日本語文字コードは合成データのテストで確認しています。詳細は [`docs/support-matrix.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/support-matrix.md) および [`docs/validation.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/validation.md) をご覧ください。

### 6. ドキュメントの案内（利用者別）

- **はじめて使う方・診療放射線技師**: [`docs/install.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/install.md), [`docs/faq.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/faq.md), [`docs/usage.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/usage.md).
- **医用画像研究者・解析者**: [`docs/positioning.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/positioning.md), [`docs/support-matrix.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/support-matrix.md), [`docs/privacy.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/privacy.md), [`docs/performance.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/performance.md).
- **施設の IT 管理者**: [`docs/deployment-guide.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/deployment-guide.md), [`docs/validation.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/validation.md).
- **ドキュメント目次**: [`docs/README.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/README.md).

### 7. 困ったとき・お問い合わせ

困ったときは [`SUPPORT.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/SUPPORT.md) の手順をご確認ください。
- 使い方の質問や相談: [GitHub Discussions](https://github.com/SugimotoKohei/dicom-organizer/discussions)
- 不具合の報告: [Bug Report](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=bug_report.yml)
- メールでのお問い合わせ: `sugimotokouhei@gmail.com`
> [!CAUTION]
> **Issue やメールには、患者情報（PHI）や実際の DICOM ファイルを絶対に含めないでください。**

### 8. 運営方針と貢献

プロジェクトの運営体制は [`GOVERNANCE.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/GOVERNANCE.md)、開発や貢献の手順は [`CONTRIBUTING.md`](https://github.com/SugimotoKohei/dicom-organizer/blob/main/CONTRIBUTING.md) をご覧ください。本ソフトウェアは [MIT License](https://github.com/SugimotoKohei/dicom-organizer/blob/main/LICENSE) のもとで公開されています。
