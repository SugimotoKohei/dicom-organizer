# Documentation Index / ドキュメント目次

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

Welcome to the `dicom-organizer` documentation library. This guide provides recommended reading paths tailored to different roles and workflows.

### 1. Recommended Reading Paths by Role

#### First-Time Users & Technologists
1. [Installation & Setup Guide](install.md): How to download the standalone app or install the Python package.
2. [Frequently Asked Questions (FAQ)](faq.md): Solutions for first-launch security warnings and common errors.
3. [CLI Usage Guide](usage.md): Command options, parameter derivations, and modes.
4. [Cross-Scanner Protocol Comparison](workflows/protocol-comparison.md): Comparing sequence parameters across scanners.

#### Researchers & Image Analysis Engineers
1. [Positioning & Target Roles](positioning.md): What `dicom-organizer` does and non-goals.
2. [DICOM Support Matrix](support-matrix.md): Modality coverage backed by automated tests and scanner facts.
3. [Patient Privacy & Data Safety](privacy.md): De-identification rules, retained identifiers, and DICOM PS3.15 Annex E.
4. [CSV Schema Reference](csv-schema.md) & [Column Dictionary](csv-columns.md): Complete specifications for all 100 CSV columns.
5. Downstream Integration Guides:
   - [3D Slicer Integration](workflows/slicer.md)
   - [dcm2niix Conversion](workflows/dcm2niix.md)
   - [Research Sharing](workflows/sharing.md)
   - [Orthanc Storing](workflows/orthanc.md)

#### Institutional IT Administrators & Security Officers
1. [Deployment Guide](deployment-guide.md): One-page institutional guide on permissions, offline operation, and audits.
2. [Validation Records](validation.md): CI multi-OS test matrix and real-scanner empirical validation data.
3. [Performance Benchmarks](performance.md): Throughput benchmarks and memory scaling characteristics.
4. [Configuration Guide](configuration.md): Standardizing institution-wide settings with TOML files.
5. [Routine Workflows & Repeat Ingestion](workflows/repeat-use.md): Handling recurring study intakes safely.

#### Contributors & Maintainers
1. [Project Governance](../GOVERNANCE.md) & [Contributing Guide](../CONTRIBUTING.md): Decision making and development setup.
2. [Stability Guarantees](stability.md): Versioning contracts and Alpha -> Beta -> Stable progression.
3. [Upgrade Guide](upgrade-guide.md): Migration notes between major and minor releases.
4. [Release Publication Checklist](publication-checklist.md): Step-by-step verification before publishing.
5. [User Research Plan](research/user-research-plan.md): User interviews and usability observation protocols.

---

<a id="japanese"></a>
## 日本語

`dicom-organizer` のドキュメントへようこそ。利用者の役割や目的に応じたおすすめの読み順をご案内します。

### 1. 利用者の役割別・おすすめの読み順

#### はじめて使う方・診療放射線技師
1. [インストール手順書](install.md): 単体アプリの入手方法や Python 版のインストール手順。
2. [よくある質問（FAQ）](faq.md): 初回起動時の警告解除や、未処理ファイルの対処法。
3. [CLI 利用ガイド](usage.md): コマンドラインのオプションや各パラメータの意味。
4. [紹介シート（1枚資料）](intro-onepager-ja.md): 同僚や勉強会でツールを紹介するための資料。
5. [装置間プロトコル比較ガイド](workflows/protocol-comparison.md): メーカーをまたいだ撮像パラメータの確認手順。

#### 画像研究者・解析エンジニア
1. [製品の位置づけと対象](positioning.md): 本ツールが目指す定番の姿と、他ツールとの役割分担。
2. [対応範囲表（サポートマトリクス）](support-matrix.md): テストと実機データに基づく対応規格一覧。
3. [患者プライバシーと安全管理](privacy.md): 個人情報保護モード、残存する識別子、DICOM PS3.15 Annex E。
4. [CSV スキーマ解説](csv-schema.md) および [全100カラム定義辞典](csv-columns.md): 出力される各列の詳細仕様。
5. 後続ワークフロー連携ガイド:
   - [3D Slicer 連携](workflows/slicer.md)
   - [dcm2niix NIfTI 変換連携](workflows/dcm2niix.md)
   - [共同研究者へのデータ共有](workflows/sharing.md)
   - [Orthanc 登録連携](workflows/orthanc.md)

#### 施設の医療情報・IT 管理者
1. [施設・チーム導入ガイド](deployment-guide.md): 権限、外部通信ゼロの保証、監査証跡の 1 枚まとめ。
2. [検証実績と動作確認](validation.md): 自動テスト環境と 4 社 5 機種の実機検証データ。
3. [性能ベンチマークとメモリ](performance.md): 処理速度実測値とファイル数に応じたメモリ増加傾向。
4. [設定ファイル仕様](configuration.md): 施設共通設定（TOML）による運用の標準化。
5. [継続運用と差分取り込み](workflows/repeat-use.md): 新着データの安全な追記整理。

#### 開発者・プロジェクト運営
1. [プロジェクト運営方針](../GOVERNANCE.md) & [コントリビューション手引き](../CONTRIBUTING.md): 開発参加と意思決定。
2. [安定性の約束と移行基準](stability.md): 互換性ポリシーと Alpha → Beta → Stable の条件。
3. [アップグレードガイド](upgrade-guide.md): 0.1.x から 0.2.0 への移行注意点。
4. [リリース公開チェックリスト](publication-checklist.md): 配布物公開前の確認手順。
5. [利用者調査計画書](research/user-research-plan.md): ユーザビリティ観察と仮説検証の設計。
