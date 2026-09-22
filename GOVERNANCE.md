# Project Governance / プロジェクト運営方針

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This document outlines the governance structure, decision-making process, release procedures, and sustainability status of the `dicom-organizer` project.

### 1. Roles and Current Maintainership

- **Primary Maintainer**: Currently, the project is maintained by a single individual (Kohei Sugimoto, `@SugimotoKohei`).
- **Co-Maintainers Welcome**: We actively welcome potential co-maintainers, especially clinicians, radiological technologists, and medical imaging researchers interested in long-term stewardship.

### 2. Decision-Making Process

- **Proposals**: Bug reports, feature suggestions, and workflow improvements should be submitted via GitHub Issues or Discussions.
- **Review and Decision**: Proposals are discussed openly. Final design and architectural decisions are made by the primary maintainer, balancing stability, usability, and maintenance overhead.
- **Breaking Changes**: Any breaking changes to CLI options, CSV column definitions, or default output hierarchies will be announced in advance through Discussions, marked in [CHANGELOG.md](CHANGELOG.md), and follow the guidelines in [docs/stability.md](docs/stability.md).

### 3. Maintenance Scope

- **In Scope**:
  - Local organization of messy DICOM export trees into standardized hierarchies.
  - Extraction and consolidation of key imaging acquisition parameters into CSV summaries.
  - Transparent tracking and reporting of skipped, duplicated, or corrupted DICOM files.
  - Standalone desktop app (Windows and macOS) and Python package (CLI and GUI across Windows, macOS, and Linux).
- **Out of Scope**:
  - Diagnostic image viewing or 3D volume rendering (use tools like 3D Slicer).
  - Network PACS server or DICOM networking (C-STORE/C-FIND) client functionality (use Orthanc or DCMTK).
  - Certified DICOM de-identification and anonymization (use dedicated compliance tools).
  - NIfTI / BIDS image format conversion (use tools like `dcm2niix`).

### 4. Release Authority and Procedures

- Releases are tagged and published exclusively by repository maintainers.
- Automated packaging and deployment follow strict verification checklists outlined in [docs/publication-checklist.md](docs/publication-checklist.md).
- Python package releases to PyPI use GitHub Actions Trusted Publishing.

### 5. Getting Involved and Accessible Contributions

You do not need to write complex Python code to contribute. High-value, welcoming areas include:
- **Scanner Verification Reports**: Testing with exports from different MRI/CT scanner models and submitting a [Verification Report](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=verification_report.yml).
- **Documentation and Translation**: Refining guides, improving Japanese/English explanations, or clarifying terminology.
- **Good First Issues**: Tackling labeled starter issues in the tracker.

### 6. Project Sustainability and Funding Status

Currently, development and maintenance of `dicom-organizer` are conducted entirely during volunteer personal time without institutional grants, corporate sponsorship, or dedicated financial funding. We strive for robust software quality, but feature development pace is subject to available volunteer capacity.

---

<a id="japanese"></a>
## 日本語

本文書は、`dicom-organizer` プロジェクトの運営体制、意思決定プロセス、リリース手順、および継続性に関する現状を説明します。

### 1. 役割と現在の体制

- **現在の保守者**: 現在、本プロジェクトは 1 名の保守者（Kohei Sugimoto, `@SugimotoKohei`）によって個人で運営されています。
- **共同保守者の募集**: 診療放射線技師、研究者、画像解析エンジニアなど、共同でプロジェクトを保守・発展させていただける方を広く募っています。

### 2. 意思決定プロセス

- **提案**: 不具合報告、機能要望、ワークフローの改善提案は GitHub Issues または Discussions から受け付けます。
- **検討と決定**: 提案は公開の場で議論されます。設計方針や採用の可否は、操作の平易さ、安定性、保守負荷のバランスを考慮し保守者が判断します。
- **破壊的変更**: CLI オプション、CSV 列の定義、フォルダ構成の破壊的変更は事前に Discussions で告知し、[CHANGELOG.md](CHANGELOG.md) および [docs/stability.md](docs/stability.md) に明記します。

### 3. 保守の範囲

- **対象とする範囲**:
  - 散らばったローカル DICOM フォルダの規格化された階層への整理。
  - 重要な撮像パラメータの抽出と CSV サマリへの集約。
  - 重複・破損・未処理ファイルの透明性ある追跡とレポート（`file_report.csv`）。
  - 単体デスクトップアプリ（Windows / macOS）および Python パッケージ（Windows / macOS / Linux での CLI および GUI）の提供。
- **対象外とする範囲**:
  - 画像の診断表示や 3D ボリュームレンダリング（3D Slicer 等の専門ツールと連携）。
  - PACS サーバー機能や DICOM ネットワーク通信（Orthanc 等を利用）。
  - 認証された DICOM 匿名化・脱特定化処理（施設承認の匿名化ツールを利用）。
  - NIfTI / BIDS 形式への画像変換（dcm2niix 等を利用）。

### 4. リリース権限と手順

- リリースは保守者のみがタグを発行して行います。
- ビルドと公開の手順は [docs/publication-checklist.md](docs/publication-checklist.md) のチェックリストに従い、テストと検証を実施したうえで行われます。
- PyPI への公開は GitHub Actions の Trusted Publishing を使用します。

### 5. 参加しやすい貢献

コードの記述に限らず、以下のような形での貢献を大歓迎しています:
- **装置ごとの検証報告**: ご自身の施設でお使いの CT/MRI 装置での実行結果を [実機検証報告テンプレート](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=verification_report.yml) でご共有いただくこと。
- **ドキュメントの改善と翻訳**: 説明の分かりやすさ向上や英日対訳の改善。
- **Good First Issue**: リポジトリで初心者向けラベルの付いた課題への取り組み。

### 6. 継続性の現状（資金・時間）

現在、本ソフトウェアの開発・保守は公的助成金や企業スポンサー等の資金援助を受けず、保守者の個人の空き時間により無償で行われています。そのため、安定した品質の維持に注力しつつも、新機能の実装速度は保守者の稼働状況に依存します。
