# Stability Guarantees and Evolution Roadmap / 安定性の約束と進化方針

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This document defines the stability contracts, versioning policies, deprecation rules, and maturity progression criteria (Alpha → Beta → Stable) for `dicom-organizer`.

### 1. Stability Contracts and Public Interfaces

We make specific compatibility promises for the following public surfaces:
1. **CLI Commands and Arguments**: Core option names (e.g., `--profile`, `--layout`, `--patient-mode`, `--if-exists`, `--checksum`, `--list-only`) maintain stable semantics.
2. **CSV Column Names and Meanings**: Column headers defined in `docs/csv-columns.md` maintain consistent definitions, physical units, and `N/A` missing-value conventions. Readers must reference columns by header name rather than column index.
3. **Machine-Readable Schema (`output_schema_version`)**: `organize_summary.json` records `output_schema_version` as an integer (currently `2`).
   - **Schema Bump Policy**: Adding new columns or JSON keys does **not** increment the schema version. The `output_schema_version` integer is incremented by 1 only when existing columns or keys are removed or renamed, when the meaning, unit, or format of existing values changes, or when the default folder structure changes. Any such breaking changes are documented under Breaking Changes in `CHANGELOG.md` and `docs/upgrade-guide.md`.
4. **`file_report.csv` Format**: The 11 columns are maintained: `SourceFileName`, `Status`, `Reason`, `Detail`, `OrganizedFileName`, `DuplicateOf`, `SOPInstanceUID`, `SeriesUID`, `Modality`, `SizeBytes`, `SHA256`.
5. **Configuration Keys**: Configuration files use flat TOML without section tables. Exactly 16 configuration keys are supported (`core.CONFIG_KEYS`): `output`, `action`, `if_exists`, `profile`, `patient_mode`, `layout`, `list_only`, `dicom_tags`, `force_read`, `include_hidden`, `include_organized`, `series_dir_template`, `file_template`, `checksum`, `space_check`, `progress`.

### 2. Versioning Policy and Deprecation Process

- **While in `0.x` (Current Stage)**: Breaking changes may occur between minor versions (e.g., 0.1.x to 0.2.0) to improve architecture, but will be explicitly highlighted in [CHANGELOG.md](../CHANGELOG.md) and [docs/upgrade-guide.md](upgrade-guide.md).
- **Post `1.0`**: Strict Semantic Versioning (SemVer 2.0.0) applies. Breaking changes require a major version bump.
- **Deprecation Grace Period**: Deprecated CLI flags or columns will be announced one minor release in advance, issuing runtime deprecation warnings while maintaining backward-compatible aliases for at least one full minor cycle before removal.

### 3. Progression Criteria: Alpha → Beta → Stable

To progress transparently across maturity tiers, the project must meet empirical quality thresholds:

| Progression Stage | Required Objective Criteria | Current Status | Met? |
|---|---|---|---|
| **Alpha** (Current) | - Automated test coverage across core organization, GUI, and support matrix.<br>- Multi-vendor empirical verification on real MRI data (5 models).<br>- Zero data-loss defects during test runs. | Met in the 0.2.0 release (previously verified in the unreleased 0.2.0 development branch). | **MET (0.2.0)** |
| **Beta** | - Verified reports from at least 3 external institutions / hospitals.<br>- Minimum 3 consecutive months with zero data-loss or file-corruption issues reported.<br>- Code signing certificates acquired for macOS and Windows standalone binaries.<br>- Stable `output_schema_version` maintained across 2 consecutive releases. | External verification reports: 0 received; Standalone binary CI builds: succeeded, but code signing certificates unacquired; Consecutive schema-stable releases: 0. | In Progress |
| **Stable (1.0)** | - Verified scanner reports covering all 4 major vendors (GE, Siemens, Philips, Canon) across both MR and CT modalities.<br>- Documented continuous adoption in at least 5 clinical or academic research institutions.<br>- Schema unchanged for at least 6 months.<br>- Comprehensive user documentation and tutorial guides. | Scanner validation: MR verified across 4 vendors, CT unverified; Continuous adoption: 0 institutions; Schema stability: 0 months. | Planned |

---

<a id="japanese"></a>
## 日本語

本文書は、`dicom-organizer` における仕様互換性の約束、バージョン方針、非推奨化の手順、および開発段階（Alpha → Beta → Stable）の移行基準を定めたものです。

### 1. 互換性の約束と公開インターフェース

以下の項目を公開インターフェースとして定義し、安定性を保証します:
1. **CLI オプションと引数**: 主要なオプション（`--profile`, `--layout`, `--patient-mode`, `--if-exists`, `--checksum`, `--list-only` 等）の名称と意味。
2. **CSV の列名と物理単位**: `docs/csv-columns.md` で定義された列名、単位、および欠損値（`N/A`）の規則。読み手は列を名前で参照すること（列の位置・インデックスで参照しないこと）。
3. **機械可読スキーマ (`output_schema_version`)**: `organize_summary.json` に記録されるスキーマ版は整数の `2` です。
   - **スキーマ版を上げる条件**: 列やキーの**追加**では版を上げません。列・キーの**削除**や**改名**、値の意味・単位・書式の変更、既定のフォルダ構成の変更のときに `output_schema_version` を 1 つ増やし、`CHANGELOG.md` の Breaking changes と `docs/upgrade-guide.md` に記載します。
4. **`file_report.csv` の列構成**: 以下の 11 列の構成を維持します: `SourceFileName`, `Status`, `Reason`, `Detail`, `OrganizedFileName`, `DuplicateOf`, `SOPInstanceUID`, `SeriesUID`, `Modality`, `SizeBytes`, `SHA256`。
5. **設定ファイルのキー名**: 設定ファイルはセクションを持たない平坦な TOML であり、サポートされるキーは次の 16 個です（`core.CONFIG_KEYS`）: `output`, `action`, `if_exists`, `profile`, `patient_mode`, `layout`, `list_only`, `dicom_tags`, `force_read`, `include_hidden`, `include_organized`, `series_dir_template`, `file_template`, `checksum`, `space_check`, `progress`。

### 2. バージョン更新と非推奨化の手順

- **`0.x` の間（現在の開発段階）**: アーキテクチャの改善に伴いマイナーバージョン更新（0.1.x から 0.2.0 など）で仕様の変更が生じる場合がありますが、必ず [CHANGELOG.md](../CHANGELOG.md) および [docs/upgrade-guide.md](upgrade-guide.md) に影響と移行手順を明記します。
- **`1.0` 以降**: セマンティックバージョニング（SemVer 2.0.0）に厳密に従い、破壊的変更はメジャーバージョンの引き上げ時のみ実施します。
- **非推奨化の手順**: 廃止予定のオプションやカラムは、最低 1 つ前のマイナーリリースで予告（警告を出力）し、互換エイリアスを残したうえで段階的に廃止します。

### 3. Alpha → Beta → Stable への移行基準

品質を客観的に評価するため、以下の明確な条件を設定しています:

| 開発段階 | 移行に必要な客観的基準 | 現在の達成状況 | 判定 |
|---|---|---|---|
| **Alpha**（現在） | - 中核機能、GUI、対応規格に関する自動テストの網羅。<br>- 4 社 5 機種の MRI 実機データによる集計検証の完了。<br>- データ消失・破壊のないことの確認。 | 0.2.0 リリースで達成（未リリースの 0.2.0 開発版での検証を経て達成）。 | **達成済（0.2.0）** |
| **Beta** | - 外部の 3 施設以上からの実機検証報告の受領。<br>- データ破損・消失に関する致命的不具合ゼロの期間が 3 か月以上継続。<br>- macOS および Windows 単体バイナリへの正式なコード署名の取得。<br>- 2 リリース連続で `output_schema_version` が無変更であること。 | 外部施設からの検証報告 0 件、単体バイナリの CI ビルドは成功済みだがコード署名は未取得、スキーマ据え置きのリリース 0 回。 | 進行中 |
| **Stable (1.0)** | - 主要 4 社（GE、Siemens、Philips、Canon）の MR および CT 両方での実機検証完了。<br>- 5 つ以上の医療・研究施設での継続的な利用実績。<br>- 6 か月以上のスキーマ安定期間。<br>- 網羅的なドキュメントと利用チュートリアルの整備。 | MR 4 社のみ実機検証完了（CT 未検証）、継続利用施設 0 施設、スキーマ安定期間 0 か月。 | 計画中 |
