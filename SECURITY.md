# Security Policy / セキュリティ方針

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

### Supported Versions

Security updates and fixes are provided for the latest released minor version of `dicom-organizer`.

| Version | Supported |
|---|---|
| 0.2.x | Yes |
| < 0.2.0 | No |

### Reporting a Vulnerability

Do not open a public issue with sensitive security vulnerabilities, DICOM data, patient information, credentials, or private machine paths.

1. **GitHub Private Vulnerability Reporting**: If available, please submit a report through the **Security** tab of the repository.
2. **Email Fallback**: If you cannot use GitHub private vulnerability reporting or prefer direct email, contact the maintainer at `sugimotokouhei@gmail.com`. Please include a clear description of the vulnerability and reproduction steps using synthetic files.

### Patient Data And Protected Health Information (PHI)

`dicom-organizer` is designed for organizing local files and extracting acquisition parameters; it is **not** a DICOM de-identification or anonymization tool.

When handling patient information:

- **DICOM Files Are Not Anonymized**: Organizing DICOM files (via copy, link, or move) preserves original DICOM headers completely. Patient identifiers remain inside the organized DICOM files.
- **CSV & Report Privacy Modes (`--patient-mode`)**:
  - `keep` (default): writes `PatientName` and `PatientID` verbatim to metadata CSVs.
  - `hash`: writes 16-character SHA-256 digests. Note that this is pseudonymization, not anonymization, and can be susceptible to dictionary attacks; it is not suitable for public sharing.
  - `drop`: strictly writes `N/A` for `PatientName`, `PatientID`, `PatientNameHash`, and `PatientIDHash`.
- **Other Identifiers Retained**: Study dates, Study/Series/SOP UIDs, equipment details, and original relative file paths (`SourceFileName`) remain in CSVs and `file_report.csv`. If source directory or file names contain patient identifiers, they will appear in reports.
- **Custom DICOM Tags**: If direct patient identifiers (e.g. `PatientBirthDate`, `AccessionNumber`) are specified via `--dicom-tag`, they are written verbatim regardless of `--patient-mode`.
- **List-Only Mode (`--list-only`)**: Generates parameter tables and reports without copying or creating DICOM files.

CLI usage examples:

```bash
dicom-organizer /path/to/dicom-root --patient-mode hash
dicom-organizer /path/to/dicom-root --patient-mode drop
dicom-organizer /path/to/dicom-root --list-only
```

Before sharing any outputs outside your secure local environment, follow your institution's privacy regulations and use dedicated, validated DICOM de-identification tools to remove protected health information (PHI).

### Medical Use

This software is provided for research and local data organization workflows. It is not a medical device, not intended for diagnosis, and not validated for clinical decision making.

---

<a id="japanese"></a>
## 日本語

### サポート対象の版

セキュリティ修正は、最新のマイナーリリースに対して提供されます。

| バージョン | サポート対象 |
|---|---|
| 0.2.x | 対象 |
| < 0.2.0 | 対象外 |

### 脆弱性の報告窓口

セキュリティ上の脆弱性、患者情報、実 DICOM データ、個人パスを公開 Issue に投稿しないでください。

1. **GitHub の非公開脆弱性報告**: 利用可能な場合は、リポジトリの「Security」タブにある非公開報告機能をご利用ください。
2. **メールでの報告**: 非公開報告が利用できない場合やメール連絡を希望される場合は、保守者アドレス `sugimotokouhei@gmail.com` へご連絡ください。脆弱性の内容と、合成データによる再現手順を添えてください。

### 患者情報（PHI）の取り扱いについて

`dicom-organizer` はローカル環境でのファイル整理と撮像条件の抽出を目的としたツールであり、**DICOM の匿名化・脱特定化ツールではありません**。

- **DICOM ファイル自体は匿名化されません**: ファイル整理（コピー、移動、シンボリックリンク作成）を行っても、DICOM ヘッダー内の患者情報はそのまま保持されます。
- **CSV やレポートのプライバシー設定 (`--patient-mode`)**:
  - `keep`（既定値）: `PatientName` と `PatientID` をそのまま CSV に書き込みます。
  - `hash`: SHA-256 の先頭 16 文字（ハッシュ値）を出力します。これは仮名化であり、辞書攻撃に弱いため外部への公開には適しません。
  - `drop`: `PatientName`、`PatientID`、および各ハッシュ値をすべて `N/A` で出力します。
- **残存する識別情報**: 検査日付、UID、装置情報、元の相対パス（`SourceFileName`）は CSV や `file_report.csv` に残ります。元のファイル名やフォルダ名に患者名や ID が含まれている場合、そのままレポートに記載されます。
- **追加タグ (`--dicom-tag`)**: 患者情報（生年月日など）を追加タグで指定した場合、`--patient-mode` にかかわらずそのまま書き込まれます。
- **一覧のみモード (`--list-only`)**: DICOM ファイルをコピーせずにメタデータ表とレポートだけを作成します。

出力結果を外部（共同研究先や学会等）に共有する前に、必ずご施設の個人情報保護規程を確認し、検証済みの匿名化ツールを用いて患者情報を適切に処理してください。

### 医療機器ではないことの明記

本ソフトウェアは研究および手元のデータ整理ワークフローを支援するものであり、医療機器ではありません。診断や臨床的判断の根拠としての検証は行われていません。
