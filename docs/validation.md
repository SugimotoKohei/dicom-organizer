# Validation and Empirical Verification / 検証実績と動作確認

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This document provides transparent records of how `dicom-organizer` is verified, including continuous integration (CI) test suites, multi-vendor scanner testing on real data, known limitations, and how community members can contribute verification reports.

### 1. Automated Testing and CI Matrix

Every code change is tested through automated test suites in continuous integration across three operating systems (Ubuntu Linux, macOS, and Windows):
- **Core CLI & Organization Tests** (e.g., `test_run_writes_files_and_metadata`): Synthetic DICOM generation, duplicate resolution, layout variants, and failure recovery.
- **GUI Test Suite** (e.g., `test_start_page_buttons_and_language_switch`): Tested in headless offscreen mode with `DICOM_ORGANIZER_REQUIRE_GUI=1` and `QT_QPA_PLATFORM=offscreen`.
- **DICOM Specification Suite** (e.g., `test_compressed_transfer_syntax_jpeg_baseline_and_lossless`): Compression integrity, Japanese character sets, and functional groups.
- **Packaging and Install Tests**: Building wheel distributions and installing them into a clean Python 3.11 virtual environment to verify `--version`, `--self-test` (and `--gui-smoke-test` for the GUI extra) across Linux, macOS, and Windows.

> [!NOTE]
> **Standalone Executable CI Builds**: Automated workflows for standalone desktop executables (`.github/workflows/standalone.yml`) have been prepared, but executable artifact builds have **not yet been verified** on GitHub Actions until this branch is pushed and executed on remote runners.

### 2. Empirical Real-Scanner Verification

On 2026-09-22, empirical verification was performed on MR scan data acquired for research purposes from five scanner models across four major vendors (commit `415f165` / `a656572`). The dataset comprised 2,157 candidate files (approx. 1.12 GB).

| Manufacturer / Vendor | Scanner Model (`ManufacturerModelName`) | Image Series Count | Images in CSV | TR / TE / FA | Bandwidth / ETL | Geometry (FOV/Matrix) | Parallel Reduction Factor | Scan Duration Source |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **Canon** | Galan 3T (`CANON_MEC`) | 24 | 576 | 100% | 100% | 100% | 100% (standard tag) | Standard `(0018,9073)` |
| **GE** | SIGNA Architect (`GE MEDICAL SYSTEMS`) | 8 | 192 | 100% | 100% | 100% | **0% (N/A)** | Private `(0019,105A)` |
| **Philips** | MR 7700 (`Philips`) | 24 | 576 | 100% | 100% | 100% | **0% (N/A)** | Standard `(0018,9073)` |
| **Siemens** | MAGNETOM Skyra (`Siemens Healthineers`) | 12 | 288 | 100% | 100% | 100% | 100% (CSA `sPat.lAccelFactPE`) | ASCCONV `lTotalScanTimeSec` |
| **Siemens** | MAGNETOM Avanto Fit (`Siemens Healthineers`) | 13 | 312 | 100% | 100% | 100% | 100% (CSA `sPat.lAccelFactPE`) | ASCCONV `lTotalScanTimeSec` |
| **Total / Summary** | 5 scanner models | 81 image series | 1,944 images | 100% | 100% | 100% | Canon & Siemens 100%, GE & Philips 0% | Vendor-specific routing |

In addition to image series, 75 non-image or vendor helper objects (45 Grayscale Softcopy Presentation States and 30 Philips private SOP Class `1.3.46.670589.11.0.0.12.x` objects) were correctly organized into directories while being appropriately excluded from image CSV tables. 82 identical duplicate files were skipped with zero conflicts.

### 3. Known Limitations and Unverified Boundaries

Honest disclosures of current testing boundaries:
- **Parallel Reduction Factor on GE / Philips**: `ParallelReductionFactorInPlane` is reported as `N/A` for GE and Philips scans when standard tag `(0018,9069)` is missing, as fallback to proprietary private tags is not currently implemented.
- **Unverified Real-Data Scope**: Compressed transfer syntaxes, Japanese character sets, Enhanced multi-frame objects, and non-MR modalities (CT, US, XA, PT) are not verified on real scanner data (verified via synthetic tests only).

### 4. How to Submit a Verification Report

We encourage users to report compatibility with their own clinical or research scanners. Please use our GitHub issue template:
- Open a [Scanner Verification Report](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=verification_report.yml) (`verification_report`).
- Report manufacturer, model, software version, modality, and extraction completeness.
- Confirm that no patient identifiers (PHI) or binary files are attached.

---

<a id="japanese"></a>
## 日本語

本文書は、`dicom-organizer` の信頼性を担保する検証実績、CI（継続的インテグレーション）での自動テスト、主要 4 社の MRI 実機データによる集計結果、既知の制限事項、および利用者による検証報告の手順を記録したものです。

### 1. 自動テストと CI マトリクス

すべてのコード変更は、Linux、macOS、Windows の 3 つの OS 上で自動テストによって検証されています:
- **CLI 中核機能テスト**（例: `test_run_writes_files_and_metadata`）: 合成 DICOM を用いたファイル整理、重複検出、レイアウト切替、障害復旧の確認。
- **GUI テスト**（例: `test_start_page_buttons_and_language_switch`）: `DICOM_ORGANIZER_REQUIRE_GUI=1` および `QT_QPA_PLATFORM=offscreen` 環境下で、オフスクリーンによる PySide6 GUI の網羅的動作確認。
- **DICOM 規格適合テスト**（例: `test_compressed_transfer_syntax_jpeg_baseline_and_lossless`）: 圧縮転送構文のバイト完全性、日本語文字コード、非画像オブジェクト、Enhanced MR の検証。
- **パッケージング・配布テスト**: ビルドした wheel を Python 3.11 のクリーンな仮想環境にインストールし、`--version`、`--self-test`（GUI 版は `--gui-smoke-test`）を実行して 3 OS 上での動作を確認。

> [!NOTE]
> **単体アプリの CI ビルドについて**: 単体配布用バイナリの自動ビルドワークフロー（`.github/workflows/standalone.yml`）は定義済みですが、本リポジトリがリモートに push されて GitHub Actions 上で実行されるまで、**単体アプリの CI ビルドは未検証**です。

### 2. 実機データによる検証実績

2026-09-22 に、研究用に取得した MR 検査データ（4 社 5 機種、6 検査、候補 2,157 ファイル、約 1.12 GB）を用いて実データ検証を実施しました（commit `415f165` / `a656572`）。

| 製造者 (`Manufacturer`) | 機種名 (`ManufacturerModelName`) | 画像シリーズ数 | CSV 対象画像数 | TR / TE / FA | 帯域 / ETL | 幾何情報 (FOV/行列) | パラレル倍速数 | 撮像時間取得元 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **Canon** | Galan 3T (`CANON_MEC`) | 24 | 576 | 100% | 100% | 100% | 100%（標準タグ） | 標準タグ `(0018,9073)` |
| **GE** | SIGNA Architect (`GE MEDICAL SYSTEMS`) | 8 | 192 | 100% | 100% | 100% | **0% (N/A)** | private `(0019,105A)` |
| **Philips** | MR 7700 (`Philips`) | 24 | 576 | 100% | 100% | 100% | **0% (N/A)** | 標準タグ `(0018,9073)` |
| **Siemens** | MAGNETOM Skyra (`Siemens Healthineers`) | 12 | 288 | 100% | 100% | 100% | 100%（CSA `sPat.lAccelFactPE`） | ASCCONV `lTotalScanTimeSec` |
| **Siemens** | MAGNETOM Avanto Fit (`Siemens Healthineers`) | 13 | 312 | 100% | 100% | 100% | 100%（CSA `sPat.lAccelFactPE`） | ASCCONV `lTotalScanTimeSec` |
| **合計 / 集計** | 5 機種 | 81 画像系列 | 1,944 画像 | 100% | 100% | 100% | Canon・Siemens 100%、GE・Philips 0% | 各社固有ルーティング |

画像シリーズに加えて、非画像オブジェクト 75 件（Presentation State 45 件、Philips private オブジェクト 30 件）が適切にフォルダ整理され、画像 CSV からは正しく除外されました。また同一内容の重複 82 件が競合なくスキップされました。

### 3. 既知の制限と未検証の領域

事実に基づく正直な情報開示を行っています:
- **GE および Philips のパラレルイメージング倍速数**: 標準タグ `(0018,9069)` を持たない場合、独自の private タグからの取得に対応していないため `N/A` となります。
- **実機データでの未検証領域**: 圧縮転送構文・日本語の文字コード・Enhanced（マルチフレーム）・非 MR モダリティ（CT、超音波、血管造影、PET）は実データでは未検証です（合成データのテストのみで確認）。

### 4. 利用者による検証結果の報告方法

ご施設でお使いの装置での検証結果の共有を歓迎しています:
- GitHub の [実機検証報告テンプレート](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=verification_report.yml)（`verification_report`）を開きます。
- 製造者、機種名、ソフトウェア版、モダリティ、取得できた項目・N/A になった項目を記入します。
- 患者情報や DICOM バイナリが含まれていないことを確認のうえ送信してください。
