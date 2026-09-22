# DICOM Support Matrix / 対応範囲と検証の根拠

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This document provides a rigorous matrix of supported DICOM modalities, transfer syntaxes, and structural objects in `dicom-organizer`.
Every capability tier is tied directly to either an **automated synthetic test function (`tests/`)** or **empirical real-scanner validation (see [docs/validation.md](validation.md))**. Items without test or real-data coverage are strictly marked as **Unverified** or **Unsupported**.

### 1. Capability Tiers

We define five distinct tiers of processing capability:
1. **File Organization**: Grouping, directory placement, and duplicate detection.
2. **Header Reading**: Safe parsing of file meta information and top-level datasets.
3. **Acquisition Parameter Extraction**: Populating modality-specific parameters in `dicom_parameters.csv` and `series_summary.csv`.
4. **Frame-Varying Expression**: Extracting and delimiting per-frame functional group parameters across multi-frame objects.
5. **Image Content & Clinical Verification**: Verifying pixel integrity, slice spacing geometry, or clinical completeness (**Explicit Non-Goal / Unsupported** across all modalities).

### 2. Comprehensive Support Matrix

| DICOM Data Type / Category | File Organization | Header Reading | Parameter Extraction | Frame-Varying Expression | Image & Clinical Integrity | Evidence (Synthetic Test vs. Real-Data) |
|---|---|---|---|---|---|---|
| **Classic MR** | Supported | Supported | Supported | N/A (single-frame) | Unsupported | Verified with real scanner data (MR 5 models across 4 vendors: Canon, GE, Philips, Siemens) and synthetic test (`test_auto_profile_writes_all_supported_modality_union_and_summary`) |
| **Classic CT** | Supported | Supported | Supported | N/A (single-frame) | Unsupported | Synthetic test only (`test_ct_profile_filters_to_ct_image_rows`, `test_auto_profile_writes_mixed_modality_union_csv`) |
| **Classic US, XA, PT** | Supported | Supported | Supported | N/A (single-frame) | Unsupported | Synthetic test only (`test_non_mr_profiles_write_supported_metadata`, `test_us_thermal_indices`) |
| **Enhanced MR (Multi-frame)** | Supported | Supported | Supported | Supported | Unsupported | Synthetic test only (`test_enhanced_mr_functional_groups`, `test_enhanced_mr_multiframe_and_varying_attributes`) |
| **Enhanced CT / Enhanced PET** | Unverified | Unverified | Unverified | Unverified | Unsupported | Unverified. File placement does not depend on SOP Class, but this data type has not been verified with synthetic tests or real data. |
| **Compressed Transfer Syntaxes**<br>(JPEG Baseline `1.2.840.10008.1.2.4.50`, JPEG 2000 `1.2.840.10008.1.2.4.90`) | Supported | Supported | Supported | N/A | Unsupported | Synthetic test only (`test_compressed_transfer_syntax_jpeg_baseline_and_lossless` byte-for-byte SHA-256 preservation) |
| **Character Sets**<br>(UTF-8 `ISO_IR 192`, Japanese `ISO 2022 IR 87`) | Supported | Supported | Supported | N/A | Unsupported | Synthetic test only (`test_charset_encoding_utf8_and_iso_2022_ir_87` sanitization verified) |
| **Missing Preamble (128-byte header missing)** | Supported (with default force-read) | Supported | Supported | N/A | Unsupported | Synthetic test only (`test_preamble_missing_force_read_and_no_force_read`) |
| **DICOMDIR Media Index** | Skipped gracefully (`dicomdir`) | Supported | Excluded from CSV | N/A | Unsupported | Verified with real scanner data (24 files skipped) and synthetic test (`test_dicomdir_handling`, `test_dicomdir_classification`) |
| **Non-Image Objects: SR (Structured Report)** | Supported (sorted to series folder) | Supported | Excluded from image CSV | N/A | Unsupported | Synthetic test only (`test_non_image_objects_sr_and_rtstruct`) |
| **Non-Image Objects: RTSTRUCT** | Supported (sorted to series folder) | Supported | Excluded from image CSV | N/A | Unsupported | Synthetic test only (`test_non_image_objects_sr_and_rtstruct`) |
| **Non-Image Objects: Presentation State (PR)** | Supported (sorted to series folder) | Supported | Excluded from image CSV | N/A | Unsupported | Verified with real scanner data (45 PR files organized) and synthetic test (`test_metadata_tables_exclude_non_image_objects`) |
| **Non-Image Objects: SEG (Segmentation)** | Unverified | Unverified | Unverified | Unverified | Unsupported | Unverified. Not tested with synthetic tests or real data. |
| **Vendor Private Tags: Siemens** (CSA Header, ASCCONV, `sPat.lAccelFactPE`) | Supported | Supported | Supported (fallback) | N/A | Unsupported | Verified with real scanner data and synthetic test (`test_siemens_private_parallel_reduction_factor_fallback_is_written`, `test_scan_duration_from_siemens_protocol`) |
| **Vendor Private Tags: GE** (Scan Duration `0019,105A`) | Supported | Supported | Supported (fallback) | N/A | Unsupported | Verified with real scanner data and synthetic test (`test_scan_duration_from_ge_private_tag`, `test_private_tag_fallback_siemens_and_ge`) |
| **Vendor Private Tags: Philips** (Sequence Name, private helper objects) | Supported | Supported | Supported (fallback) | N/A | Unsupported | Verified with real scanner data (30 private objects organized) and synthetic test (`test_philips_sequence_name_falls_back_to_private_sequence`) |

---

<a id="japanese"></a>
## 日本語

本文書は、`dicom-organizer` における DICOM モダリティ、転送構文、オブジェクト構造の対応状況を網羅した対応範囲表（サポートマトリクス）です。
各セルの根拠は、**合成データの自動テスト（`tests/` 配下のテスト名）** または **実機データ検証（[docs/validation.md](validation.md) を参照）** に基づいています。テストや実データによる確認が存在しない項目は、「対応」と表記せず **「未確認」** または **「非対応」** と記載しています。

### 1. 能力の段階（5つの階層）

処理能力を以下の 5 つの段階に分けて定義しています:
1. **ファイルとして整理**: フォルダ分類、配置、および重複ファイルの判定。
2. **ヘッダーを読む**: ファイルメタ情報およびデータセットの安全な読み込み。
3. **撮像条件を抽出**: `dicom_parameters.csv` および `series_summary.csv` へのパラメータ出力。
4. **フレームごとの違いを表現**: マルチフレームオブジェクトにおけるフレーム別パラメータ（`|` 区切り）の抽出。
5. **画像内容・検査の完全性を検証**: ピクセルデータの整合性やスライス欠落等の臨床的検証（**全データ種別において非対応 / 設計上の非目標**）。

### 2. 詳細対応マトリクス

| DICOM データの種類 | ファイルとして整理 | ヘッダーを読む | 撮像条件を抽出 | フレームごとの違いを表現 | 画像内容・検査の完全性を検証 | 根拠（合成テストのみ / 実データでも確認） |
|---|---|---|---|---|---|---|
| **Classic MR（単一フレーム）** | 対応 | 対応 | 対応 | 該当なし（単一フレーム） | 非対応 | 実データ（MR 4 社 5 機種: Canon, GE, Philips, Siemens）でも確認、合成テスト（`test_auto_profile_writes_all_supported_modality_union_and_summary`） |
| **Classic CT** | 対応 | 対応 | 対応 | 該当なし（単一フレーム） | 非対応 | 合成テストのみ（`test_ct_profile_filters_to_ct_image_rows`、`test_auto_profile_writes_mixed_modality_union_csv`） |
| **Classic US, XA, PT** | 対応 | 対応 | 対応 | 該当なし（単一フレーム） | 非対応 | 合成テストのみ（`test_non_mr_profiles_write_supported_metadata`、`test_us_thermal_indices`） |
| **Enhanced MR（マルチフレーム）** | 対応 | 対応 | 対応 | 対応 | 非対応 | 合成テストのみ（`test_enhanced_mr_functional_groups`、`test_enhanced_mr_multiframe_and_varying_attributes`） |
| **Enhanced CT / Enhanced PET** | 未確認 | 未確認 | 未確認 | 未確認 | 非対応 | 未確認。ファイル整理の基本処理は SOP Class に依存しない作りですが、この種類での動作は合成テスト・実データともに未確認です。 |
| **圧縮転送構文**<br>(JPEG Baseline `1.2.840.10008.1.2.4.50`、JPEG 2000 `1.2.840.10008.1.2.4.90`) | 対応 | 対応 | 対応 | 該当なし | 非対応 | 合成テストのみ（`test_compressed_transfer_syntax_jpeg_baseline_and_lossless` による SHA-256 バイト一致を検証） |
| **文字コード**<br>(UTF-8 `ISO_IR 192`、日本語 `ISO 2022 IR 87`) | 対応 | 対応 | 対応 | 該当なし | 非対応 | 合成テストのみ（`test_charset_encoding_utf8_and_iso_2022_ir_87` によるフォルダ名サニタイズ確認） |
| **preamble なし（先頭 128 バイト欠損）** | 対応（既定の force-read） | 対応 | 対応 | 該当なし | 非対応 | 合成テストのみ（`test_preamble_missing_force_read_and_no_force_read`） |
| **DICOMDIR（メディア索引）** | スキップ（`dicomdir`） | 対応 | 表から除外 | 該当なし | 非対応 | 実データでも確認（24 件スキップ）、合成テスト（`test_dicomdir_handling`、`test_dicomdir_classification`） |
| **非画像: SR（レポート）** | 対応（シリーズフォルダ配置） | 対応 | 表から除外 | 該当なし | 非対応 | 合成テストのみ（`test_non_image_objects_sr_and_rtstruct`） |
| **非画像: RTSTRUCT（放射線治療構造）** | 対応（シリーズフォルダ配置） | 対応 | 表から除外 | 該当なし | 非対応 | 合成テストのみ（`test_non_image_objects_sr_and_rtstruct`） |
| **非画像: PR（プレゼンテーションステート）** | 対応（シリーズフォルダ配置） | 対応 | 表から除外 | 該当なし | 非対応 | 実データでも確認（45 件整理）、合成テスト（`test_metadata_tables_exclude_non_image_objects`） |
| **非画像: SEG（セグメンテーション）** | 未確認 | 未確認 | 未確認 | 未確認 | 非対応 | 未確認。合成テスト・実データともに未検証です。 |
| **各社 private タグ: Siemens** (CSA Header, ASCCONV, `sPat.lAccelFactPE`) | 対応 | 対応 | 対応（代替読取） | 該当なし | 非対応 | 実データでも確認、合成テスト（`test_siemens_private_parallel_reduction_factor_fallback_is_written`、`test_scan_duration_from_siemens_protocol`） |
| **各社 private タグ: GE** (撮像時間 `0019,105A`) | 対応 | 対応 | 対応（代替読取） | 該当なし | 非対応 | 実データでも確認、合成テスト（`test_scan_duration_from_ge_private_tag`、`test_private_tag_fallback_siemens_and_ge`） |
| **各社 private タグ: Philips** (系列名, private オブジェクト) | 対応 | 対応 | 対応（代替読取） | 該当なし | 非対応 | 実データでも確認（30 件の private オブジェクト整理）、合成テスト（`test_philips_sequence_name_falls_back_to_private_sequence`） |

