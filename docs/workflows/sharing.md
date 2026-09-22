# Sharing Imaging Datasets with Collaborators / 共同研究者へのデータ共有

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

Collaborative clinical research often requires sharing imaging metadata or dataset catalogs with external institutions. This guide outlines how to safely generate sanitized summaries with `dicom-organizer` and what precautions must be observed.

### 1. Generating Privacy-Compliant Metadata Catalogs

To share acquisition parameter tables without exposing patient names or IDs, execute in list-only mode with `--patient-mode drop`:

```bash
dicom-organizer /path/to/study-data --list-only --patient-mode drop
```

- **Output Directory**: By default, writes to `organized_list/`.
- **Sanitized Values**: In `all_series_summary.csv` and `all_dicom_parameters.csv`, `PatientName`, `PatientID`, and their hashes are strictly replaced with `N/A`.
- **No DICOM Files Created**: No image slices are copied or moved.

### 2. Mandatory Pre-Flight Audit Before Sharing

Before sending the resulting CSV files to external collaborators:
1. **Audit `SourceFileName`**: Open `all_dicom_parameters.csv` and `file_report.csv` (`all_series_summary.csv` does not contain this column). Verify that relative source paths do not inadvertently contain patient names, physician names, or local clinical folders.
2. **Audit Custom Tags**: Ensure no direct patient identifiers (e.g., date of birth) were added via `-t / --dicom-tag`.
3. **Verify Header Columns**: Ensure all `PatientName` and `PatientID` fields show `N/A`.

### 3. If You Must Share the Actual DICOM Binary Files

> [!CAUTION]
> **Do not share `dicom-organizer` output folders directly as "anonymized data".**
> `dicom-organizer` does not alter DICOM headers. If full DICOM images must be shared with external research partners:
> - Use a dedicated clinical de-identification tool compliant with **DICOM PS3.15 Annex E**.
> - Anonymize UIDs, patient demographic headers, and burned-in text pixels.
> - Verify that institutional data sharing agreements and ethics board approvals are active.

---

<a id="japanese"></a>
## 日本語

共同研究先や学外の研究者と画像データや撮像条件のカタログを共有する際、患者プライバシーを保護しつつ必要なパラメータを安全に渡す手順を解説します。

### 1. 安全な撮像条件カタログの作成

患者氏名や患者 ID を伏せて撮像パラメータ表のみを作成・共有するには、一覧のみモードと `--patient-mode drop` を併用します:

```bash
dicom-organizer /path/to/study-data --list-only --patient-mode drop
```

- **出力先**: 既定では `organized_list/` に作成されます。
- **マスクされる項目**: `all_series_summary.csv` および `all_dicom_parameters.csv` 内の `PatientName`、`PatientID`、および各ハッシュ値がすべて厳格に `N/A` となります。
- **画像コピーなし**: DICOM 画像ファイル本体は一切コピー・生成されません。

### 2. 外部送付前の確認手順

生成された CSV ファイルを外部に送る前に、必ず以下の点を確認してください:
1. **元のパス名（`SourceFileName`）の確認**: `all_dicom_parameters.csv` や `file_report.csv` の元のファイル名・フォルダ名に、患者氏名や病院内の個人名が含まれていないか目視確認します（`all_series_summary.csv` にはこの列はありません）。
2. **追加タグの確認**: `--dicom-tag` で生年月日等の個人識別タグを追加していないか確認します。
3. **患者情報列の確認**: `PatientName` および `PatientID` 列がすべて `N/A` であることを確認します。

### 3. DICOM 画像ファイル本体も共有する場合の注意

> [!CAUTION]
> **整理された DICOM フォルダをそのまま「匿名化済み」として外部に送付してはなりません。**
> 本ツールは DICOM ファイル自体のヘッダーを変更しません。画像ファイル本体を外部へ提供する場合は:
> - **DICOM PS3.15 Annex E** に準拠した専門の匿名化ツールを用い、DICOM ファイル本体から患者情報・検査情報・UID を適切に消去・置換してください。
> - 施設内の研究倫理審査（IRB）の承認およびデータ提供規約を遵守してください。
