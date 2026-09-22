# Product Positioning and Target Roles / 位置づけと対象ユーザー

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

`dicom-organizer` is designed with a focused, singular purpose: **to be the premier tool that users reach for first when organizing local DICOM files, verifying acquisition parameters, and preparing clean data for downstream workflows**.

### 1. Target Users and Core Tasks

| Role Category | Primary / Secondary | Specific Workflows and Core Tasks |
|---|---|---|
| **Radiological Technologists (MR/CT)** | **Primary** | - Checking acquisition protocols and scanning parameters across scanners.<br>- Verifying sequence settings (TR, TE, flip angle, acceleration factor) for quality assurance.<br>- Organizing messy exports from scanner consoles or optical media into clean study archives. |
| **Medical Imaging Researchers** | **Primary** | - Auditing retrospective imaging datasets before running cohort analyses.<br>- Filtering series based on specific acquisition criteria (e.g., TE ranges, slice thickness) before training machine learning models.<br>- Extracting standardized parameter tables into CSV for statistical analysis. |
| **Image Analysis Engineers** | **Primary** | - Cleaning and sorting raw DICOM inputs before feeding them to conversion pipelines (such as `dcm2niix`).<br>- Identifying corrupt or duplicate series before batch processing. |
| **Research Project Coordinators** | **Secondary** | - Cataloging incoming imaging data from multiple collaborating hospitals.<br>- Verifying that received datasets match the agreed study protocol without viewing medical image pixels. |
| **Facility IT Administrators** | **Secondary** | - Scripting automated intake sorting on local research staging workstations.<br>- Deploying a lightweight, self-contained desktop tool requiring zero network connectivity and zero administrative rights. |

### 2. The Vision of "The Standard Tool"

We aim to establish `dicom-organizer` as the natural first step in local imaging workflows:
- When a researcher receives a thumb drive or download link of DICOM data, their immediate thought is: *"Let me run dicom-organizer first to see what is inside."*
- When an imaging laboratory establishes standard operating procedures (SOPs), `dicom-organizer` is listed as the initial preparation and quality audit step.

#### Measurable Indicators of Success
To evaluate whether we are achieving this vision without relying on invasive telemetry, we monitor:
1. **Institutional Repeat Usage**: Institutions that regularly use the tool across multiple projects or clinical studies.
2. **Third-Party Documentation**: Inclusion of `dicom-organizer` in institutional analysis manuals, laboratory protocols, and university SOPs.
3. **Downstream Integration**: Tool usage embedded within community pipelines, research scripts, and batch processing wrappers.
4. **Peer Recommendations**: Technologists and researchers recommending the tool to colleagues in clinical study meetings or conferences.
5. **Open Workflow Sharing**: Verified pipeline repositories on GitHub that cite or call `dicom-organizer` in their data preparation steps.

### 3. Non-Goals and What to Use Instead

To maintain reliability, simplicity, and speed, `dicom-organizer` intentionally avoids replacing mature, specialized software.

| What `dicom-organizer` Does NOT Do | Dedicated Alternative Tools to Use |
|---|---|
| **Diagnostic Viewing & 3D Rendering** | Use **3D Slicer** or certified PACS workstations. |
| **PACS Server & Network C-STORE** | Use **Orthanc** or **DCMTK** (`storescu`). |
| **Certified Clinical Anonymization** | Use dedicated clinical de-identification tools compliant with DICOM PS3.15 Annex E approved by your institution. |
| **NIfTI Image Format Conversion** | Use **dcm2niix** (see [dcm2niix workflow](workflows/dcm2niix.md)). |
| **DICOM Pixel Editing or File Modification** | `dicom-organizer` treats input DICOM files as strictly read-only. |

---

<a id="japanese"></a>
## 日本語

`dicom-organizer` は明確な目的を持って設計されています: **「ローカル DICOM を整理し、撮像条件を確かめ、次の作業に渡すときに最初に使われる定番ツール」** を目指しています。

### 1. 対象利用者と具体的な仕事

| 利用者の分類 | 主対象 / 副対象 | 具体的な作業内容と解決する課題 |
|---|---|---|
| **診療放射線技師 (MR/CT)** | **主対象** | - 装置間での撮像プロトコルや撮像条件の整合性確認。<br>- 精度管理やプロトコル統一のためのシーケンス設定値（TR, TE, フリップ角, 倍速数等）の棚卸し。<br>- 装置コンソールや光ディスクから取り出した散らかったフォルダの整理。 |
| **画像研究者・医師** | **主対象** | - コホート研究や機械学習解析を始める前の、手元 DICOM の網羅的な棚卸し。<br>- 特定の撮像条件（スライス厚や TE の範囲など）を満たすシリーズの絞り込み。<br>- 撮像条件の一覧表（CSV）を作成し、Excel や統計ソフトでの分析へ渡す。 |
| **画像解析エンジニア** | **主対象** | - `dcm2niix` への変換パイプラインへ渡す前の前処理と選別。<br>- 解析失敗の原因となる重複データや非画像オブジェクトの事前把握。 |
| **多施設共同研究の事務局** | **副対象** | - 複数施設から送られてきた画像データがプロトコルに合致しているかの受入確認。<br>- 画像ピクセルを表示することなく、ヘッダー情報のみをカタログ化。 |
| **施設の医療情報・IT 担当者** | **副対象** | - 研究用ローカル端末でのデータ仕分けスクリプトの標準化。<br>- 管理者権限不要・外部通信一切なし・単体で動く安全なツールの配備。 |

### 2. 目指す「定番」の定義と到達指標

私たちが目指すのは、ローカルでの画像研究やデータ整理における「最初の選択肢」となることです:
- 外部メディアやダウンロードフォルダに DICOM が届いたとき、「まず dicom-organizer を通して中身を把握しよう」と自然に手が伸びる状態。
- 研究室や施設の手順書（SOP）において、解析前処理の標準手順として採用されている状態。

#### 到達を測る指標（プライバシーに配慮し、利用測定・外部通信は行いません）
1. **継続利用施設**: 複数の研究や部署で継続的に活用されている施設の存在。
2. **第三者の手順書への掲載**: 大学、研究室、学会ハンズオン等の手順書やマニュアルへの記載。
3. **他ソフト・解析からの利用**: 研究者の解析スクリプトやバッチ処理の前段としての組み込み。
4. **同僚への推薦**: 技師同士の勉強会や研究会での口コミ・紹介。
5. **公開ワークフローへの組み込み**: GitHub や研究成果リポジトリにおける本ツールの引用・言及。

### 3. 非目標（やらないこと）と代わりに使うべきツール

本ツールの信頼性と軽快さを保つため、すでに優れたオープンソースや専門システムが存在する領域にはあえて踏み込みません。

| 本ツールが行わないこと（非目標） | 代わりに使うべき専用ツール |
|---|---|
| **画像の診断表示・3D レンダリング** | **3D Slicer**、施設承認の医用画像ビューア |
| **PACS サーバー・ネットワーク通信 (C-STORE)** | **Orthanc**、**DCMTK** (`storescu`) |
| **認証された DICOM 匿名化・脱特定化** | 施設で承認された、DICOM PS3.15 Annex E に沿った専用ツール |
| **NIfTI への画像フォーマット変換** | **dcm2niix**（[dcm2niix 連携ガイド](workflows/dcm2niix.md) を参照） |
| **DICOM ファイル内容の改変・ピクセル編集** | 入力 DICOM は完全な読み取り専用として扱い、変更しません。 |
