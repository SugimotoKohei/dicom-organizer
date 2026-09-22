"""User-facing messages and privacy notice texts (English and Japanese)."""

from __future__ import annotations

NOTICE_CODES = (
    "csv_patient_fields_kept",
    "csv_patient_fields_hashed",
    "csv_patient_fields_dropped",
    "dicom_files_unchanged",
    "no_dicom_copies",
    "csv_other_identifiers",
    "custom_tags_written",
    "folder_names_contain_patient_id",
    "folder_names_contain_patient_key",
)

NOTICE_TEXT: dict[str, dict[str, str]] = {
    "csv_patient_fields_kept": {
        "en": "Metadata CSV files retain PatientName and PatientID as read from DICOM headers.",
        "ja": "メタデータ CSV には DICOM ヘッダーの患者名（PatientName）と患者 ID（PatientID）がそのまま記録されます。",
    },
    "csv_patient_fields_hashed": {
        "en": (
            "Metadata CSV files replace PatientName and PatientID with 16-character SHA-256 digests. "
            "This is pseudonymization, not anonymization, and can be vulnerable to dictionary attacks; "
            "it is not suitable for public sharing."
        ),
        "ja": (
            "メタデータ CSV では患者名と患者 ID を 16 桁のハッシュ値（SHA-256）に置き換えます。"
            "これは仮名化であり匿名化ではありません（総当たり推測が可能な場合があります）。"
            "外部への公開・共有には適しません。"
        ),
    },
    "csv_patient_fields_dropped": {
        "en": "Metadata CSV files omit PatientName, PatientID, and their hashes (written as N/A).",
        "ja": "メタデータ CSV には患者名・患者 ID およびそのハッシュ値を記録しません（N/A と表記されます）。",
    },
    "dicom_files_unchanged": {
        "en": (
            "Organized DICOM files are copied, linked, or moved without changing their contents, "
            "so all original patient information remains inside them. This tool does not anonymize DICOM files."
        ),
        "ja": (
            "整理後の DICOM ファイルは中身を変えずにコピー・リンク・移動されるため、"
            "元の患者情報がファイルの中にすべて残ります。このツールは DICOM ファイルを匿名化しません。"
        ),
    },
    "no_dicom_copies": {
        "en": "No DICOM files are copied or created (only parameter tables and reports are generated).",
        "ja": "DICOM ファイルのコピーや生成は行われません（パラメータ表とレポートのみ作成されます）。",
    },
    "csv_other_identifiers": {
        "en": (
            "Metadata CSV files and reports retain study dates, UIDs, equipment details, and "
            "original relative file paths (SourceFileName); if source directory names contain "
            "patient identifiers, they may remain in reports."
        ),
        "ja": (
            "メタデータ CSV やレポートには検査日時、UID、装置情報、元ファイルの相対パス（SourceFileName）が記録されます。"
            "元フォルダ名に患者名等が含まれている場合はそのまま残ります。"
        ),
    },
    "custom_tags_written": {
        "en": (
            "Custom DICOM tags specified via --dicom-tag are written directly to metadata CSV files "
            "regardless of --patient-mode."
        ),
        "ja": (
            "追加タグ（--dicom-tag）で指定された属性の値は、"
            "--patient-mode の設定にかかわらずそのままメタデータ CSV に記録されます。"
        ),
    },
    "folder_names_contain_patient_id": {
        "en": "Output folder hierarchy includes PatientID in folder names.",
        "ja": "出力フォルダの階層名に患者 ID（PatientID）が含まれます。",
    },
    "folder_names_contain_patient_key": {
        "en": (
            "Output folder hierarchy includes pseudonymized patient keys (hashes) in folder names; "
            "this is not anonymization."
        ),
        "ja": (
            "出力フォルダの階層名に患者の仮名キー（ハッシュ値）が含まれます。"
            "これは匿名化ではありません。"
        ),
    },
}


def notice_text(code: str, lang: str = "en") -> str:
    texts = NOTICE_TEXT.get(code)
    if not texts:
        return code
    return texts.get(lang) or texts.get("en", code)
