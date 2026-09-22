"""Internationalization (i18n) support for dicom-organizer GUI."""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES: tuple[str, ...] = ("ja", "en")


def default_language(locale_name: str | None = None) -> str:
    """Return 'ja' if locale starts with 'ja', otherwise 'en'."""
    if locale_name and locale_name.lower().startswith("ja"):
        return "ja"
    return "en"


REASON_TEXTS: dict[str, dict[str, dict[str, str]]] = {
    "not_dicom": {
        "label": {
            "ja": "非 DICOM ファイル",
            "en": "Non-DICOM file",
        },
        "help": {
            "ja": "DICOM 規格のファイルではないか、ヘッダーが存在しません。",
            "en": "Not a valid DICOM file or standard header is missing.",
        },
    },
    "dicomdir": {
        "label": {
            "ja": "DICOMDIR（目次）",
            "en": "DICOMDIR index file",
        },
        "help": {
            "ja": "媒体の目次ファイル（DICOMDIR）のため画像データではありません。",
            "en": "Directory index file (DICOMDIR), not an image file.",
        },
    },
    "missing_required_uid": {
        "label": {
            "ja": "UID 欠落",
            "en": "Missing required UID",
        },
        "help": {
            "ja": "整理に必要な識別子（SOP または Series UID）がありません。",
            "en": "Missing required SOP Instance UID or Series Instance UID.",
        },
    },
    "read_error": {
        "label": {
            "ja": "読み取りエラー",
            "en": "Header read error",
        },
        "help": {
            "ja": "破損などのため DICOM ヘッダーを正しく読み取れませんでした。",
            "en": "Could not read DICOM header properly, possibly corrupted.",
        },
    },
    "permission_denied": {
        "label": {
            "ja": "アクセス権限なし",
            "en": "Permission denied",
        },
        "help": {
            "ja": "ファイルの読み取り権限がありません。",
            "en": "Insufficient permissions to read the file.",
        },
    },
    "io_error": {
        "label": {
            "ja": "入出力エラー",
            "en": "I/O error",
        },
        "help": {
            "ja": "ファイルへのアクセス中に入出力エラーが発生しました。",
            "en": "Input/output error occurred while accessing the file.",
        },
    },
    "excluded_hidden": {
        "label": {
            "ja": "隠しファイル除外",
            "en": "Hidden file excluded",
        },
        "help": {
            "ja": "隠しファイル（ピリオドで始まるファイル）のため除外されました。",
            "en": "Excluded because it is a hidden file.",
        },
    },
    "duplicate_identical": {
        "label": {
            "ja": "同一内容の重複ファイル",
            "en": "Identical duplicate",
        },
        "help": {
            "ja": (
                "入力の中に、同じ SOPInstanceUID で内容も同じファイルが複数ありました。最初に見つけた 1 件だけを対象にし、"
                "残りは整理・一覧に含めていません（file_report.csv の DuplicateOf 列に元のファイルが出ます）。"
            ),
            "en": (
                "Several files in the input have the same SOPInstanceUID and identical content. Only the first one found is "
                "used; the other copies are not organized or listed (the DuplicateOf column in file_report.csv shows the "
                "original)."
            ),
        },
    },
    "existing_output": {
        "label": {
            "ja": "既存出力ファイル",
            "en": "Existing destination file",
        },
        "help": {
            "ja": "出力先に同じ名前のファイルが既にあったため、そのまま残しました（既存ファイルはスキップ）。",
            "en": "A file with the same name already exists in the destination folder; skipped to preserve existing output.",
        },
    },
    "duplicate_conflict": {
        "label": {
            "ja": "UID 重複（内容相違）",
            "en": "UID conflict (different content)",
        },
        "help": {
            "ja": "同じ SOPInstanceUID なのに内容が異なるファイルです。両方とも整理しました（ファイル名に番号が付きます）。念のため確認してください。",
            "en": "Files share the same SOPInstanceUID but have different content. Both were organized (with numbered filenames); please review them.",
        },
    },
    "cancelled": {
        "label": {
            "ja": "ユーザーによる中止",
            "en": "Cancelled by user",
        },
        "help": {
            "ja": "中止ボタンにより処理が中断されました。",
            "en": "Operation was cancelled by user.",
        },
    },
    "interrupted": {
        "label": {
            "ja": "処理の中断",
            "en": "Process interrupted",
        },
        "help": {
            "ja": "シグナル等により処理が中断されました。",
            "en": "Process was interrupted before completion.",
        },
    },
    "failed": {
        "label": {
            "ja": "エラーによる失敗",
            "en": "Failed with error",
        },
        "help": {
            "ja": "処理中にエラーが発生して停止しました。",
            "en": "Process encountered an error and stopped.",
        },
    },
}


def reason_label(code: str, lang: str = "en") -> str:
    """Return a human-friendly label for a skip or status reason code."""
    item = REASON_TEXTS.get(code)
    if not item:
        return code
    labels = item.get("label", {})
    return labels.get(lang) or labels.get("en", code)


def reason_help(code: str, lang: str = "en") -> str:
    """Return a human-friendly explanation for a skip or status reason code."""
    item = REASON_TEXTS.get(code)
    if not item:
        return code
    helps = item.get("help", {})
    return helps.get(lang) or helps.get("en", code)


def stage_text(stage: str, done: int, total: int | None, lang: str = "en") -> str:
    """Return a formatted stage progress message."""
    done_str = f"{done:,}"
    total_str = f"{total:,}" if total is not None else ""

    if stage == "discover":
        if lang == "ja":
            return f"ファイルを探しています（{done_str} 件）"
        return f"Discovering files ({done_str} found)"

    if stage == "read":
        if total is not None:
            if lang == "ja":
                return f"DICOM を読み取っています {done_str} / {total_str}"
            return f"Reading DICOM headers {done_str} / {total_str}"
        if lang == "ja":
            return f"DICOM を読み取っています {done_str} 件"
        return f"Reading DICOM headers {done_str} files"

    if stage == "plan":
        if lang == "ja":
            return "整理先を決めています"
        return "Planning output layout"

    if stage == "copy":
        if total is not None:
            if lang == "ja":
                return f"コピーしています {done_str} / {total_str}"
            return f"Copying files {done_str} / {total_str}"
        if lang == "ja":
            return f"コピーしています {done_str} 件"
        return f"Copying files {done_str} files"

    if stage == "link":
        if total is not None:
            if lang == "ja":
                return f"リンクを作成しています {done_str} / {total_str}"
            return f"Creating links {done_str} / {total_str}"
        if lang == "ja":
            return f"リンクを作成しています {done_str} 件"
        return f"Creating links {done_str} files"

    if stage == "move":
        if total is not None:
            if lang == "ja":
                return f"移動しています {done_str} / {total_str}"
            return f"Moving files {done_str} / {total_str}"
        if lang == "ja":
            return f"移動しています {done_str} 件"
        return f"Moving files {done_str} files"

    if stage in ("write", "write_tables", "metadata", "summary", "finalize"):
        if lang == "ja":
            return "表とレポートを書いています"
        return "Writing parameter tables and reports"

    if lang == "ja":
        return f"{stage} 処理中... ({done_str})"
    return f"Processing {stage}... ({done_str})"


STRINGS: dict[str, dict[str, str]] = {
    # App & Navigation
    "app_title": {
        "ja": "dicom-organizer",
        "en": "dicom-organizer",
    },
    "start_title": {
        "ja": "何をしますか？",
        "en": "What would you like to do?",
    },
    "start_subtitle": {
        "ja": "目的を選んでください。後からいつでも変更できます。",
        "en": "Choose your goal. You can change it anytime.",
    },
    "reselect_task": {
        "ja": "目的を選び直す",
        "en": "Change goal",
    },
    "try_sample_data": {
        "ja": "サンプルデータで試す",
        "en": "Try with sample data",
    },
    "start_sample_hint": {
        "ja": "はじめての方は、架空のデータで流れを確認できます。",
        "en": "New users can explore the workflow with synthetic data.",
    },
    # Tasks
    "task_list_title": {
        "ja": "撮像条件を一覧にする",
        "en": "List imaging parameters",
    },
    "task_list_desc": {
        "ja": "DICOM をコピーせず、シリーズごとの撮像条件の表（CSV）だけを作る。Excel で開ける",
        "en": "Create a CSV table of imaging parameters per series without copying DICOM files. Can be opened in Excel.",
    },
    "task_organize_title": {
        "ja": "コピーして整理する",
        "en": "Copy and organize",
    },
    "task_organize_desc": {
        "ja": "元のファイルは残したまま、装置・検査日・シリーズごとのフォルダにコピーし、表も作る",
        "en": "Copy into folders by device, study date, and series while leaving source files untouched, and generate parameter tables.",
    },
    "task_preview_title": {
        "ja": "整理前に内容を確認する",
        "en": "Preview before organizing",
    },
    "task_preview_desc": {
        "ja": "何も書き込まずに、見つかったシリーズと、対象外・読めなかったファイルを確認する",
        "en": "Check detected series, excluded files, and unreadable files without writing anything to disk.",
    },
    # Step 1: Input
    "step1_title": {
        "ja": "手順 1: 入力フォルダ",
        "en": "Step 1: Input folder",
    },
    "input_folder_label": {
        "ja": "入力フォルダ:",
        "en": "Input folder:",
    },
    "browse": {
        "ja": "参照…",
        "en": "Browse...",
    },
    "drop_hint": {
        "ja": "ここにフォルダをドラッグ＆ドロップできます",
        "en": "You can drag and drop a folder here",
    },
    "sample_note": {
        "ja": "架空のサンプルデータです。実在の患者情報は含みません。",
        "en": "Fictitious sample data. Contains no real patient information.",
    },
    # Step 2: Destination and Options
    "step2_title": {
        "ja": "手順 2: 出力先と設定",
        "en": "Step 2: Output destination and settings",
    },
    "output_folder_label": {
        "ja": "出力フォルダ:",
        "en": "Output folder:",
    },
    "patient_mode_label": {
        "ja": "CSV の患者情報:",
        "en": "Patient info in CSV:",
    },
    "patient_keep": {
        "ja": "そのまま書く（keep）",
        "en": "Keep original (keep)",
    },
    "patient_hash": {
        "ja": "ハッシュに置き換える（hash・仮名化）",
        "en": "Replace with hash (hash / pseudonymized)",
    },
    "patient_drop": {
        "ja": "書かない（drop）",
        "en": "Omit from CSV (drop)",
    },
    "layout_label": {
        "ja": "フォルダの分け方:",
        "en": "Folder structure:",
    },
    "layout_device_date": {
        "ja": "装置 → 検査日（撮像条件の比較向け）",
        "en": "Device -> Study date (for comparing imaging parameters)",
    },
    "layout_study": {
        "ja": "検査ごと（1 フォルダ = 1 検査）",
        "en": "By study (1 folder per study)",
    },
    "layout_patient_study": {
        "ja": "患者 → 検査",
        "en": "Patient -> Study",
    },
    "privacy_panel_title": {
        "ja": "患者情報の取り扱いについて:",
        "en": "Patient Information Notice:",
    },
    "advanced_title": {
        "ja": "詳細設定",
        "en": "Advanced Settings",
    },
    "action_label": {
        "ja": "配置方法:",
        "en": "Action:",
    },
    "action_copy": {
        "ja": "コピー（推奨・安全）",
        "en": "Copy (recommended / safe)",
    },
    "action_symlink": {
        "ja": "シンボリックリンク",
        "en": "Symbolic link",
    },
    "action_hardlink": {
        "ja": "ハードリンク",
        "en": "Hard link",
    },
    "action_move": {
        "ja": "移動（元ファイルを移動）",
        "en": "Move (relocates source files)",
    },
    "if_exists_label": {
        "ja": "既存ファイルの扱い:",
        "en": "If destination exists:",
    },
    "if_exists_error": {
        "ja": "エラーにして停止（error）",
        "en": "Stop with error (error)",
    },
    "if_exists_skip": {
        "ja": "スキップする（skip）",
        "en": "Skip existing (skip)",
    },
    "if_exists_overwrite": {
        "ja": "上書きする（overwrite）",
        "en": "Overwrite (overwrite)",
    },
    "if_exists_rename": {
        "ja": "別名で保存（rename）",
        "en": "Save with new name (rename)",
    },
    "profile_label": {
        "ja": "メタデータ プロファイル:",
        "en": "Metadata profile:",
    },
    "series_template_label": {
        "ja": "シリーズフォルダ名テンプレート:",
        "en": "Series folder template:",
    },
    "file_template_label": {
        "ja": "ファイル名テンプレート:",
        "en": "File template:",
    },
    "limit_label": {
        "ja": "処理件数の上限（0で無制限）:",
        "en": "File count limit (0 for unlimited):",
    },
    "force_read_label": {
        "ja": "非標準ヘッダーも読む（force-read）",
        "en": "Force-read non-standard headers",
    },
    "include_hidden_label": {
        "ja": "隠しファイルも対象にする",
        "en": "Include hidden files",
    },
    "include_organized_label": {
        "ja": "organized フォルダも対象にする",
        "en": "Include already organized folders",
    },
    "checksum_label": {
        "ja": "チェックサムで検証する（SHA-256）",
        "en": "Verify SHA-256 checksums",
    },
    "space_check_label": {
        "ja": "空き容量を確認する",
        "en": "Check available disk space",
    },
    "dicom_tags_label": {
        "ja": "追加タグ（カンマ区切り）:",
        "en": "Additional DICOM tags (comma-separated):",
    },
    "unsafe_move_warning": {
        "ja": "警告: 「移動」は元のファイルを別の場所に移動するため、元のフォルダから消えます。",
        "en": "Warning: 'Move' will relocate original files away from the source folder.",
    },
    "unsafe_overwrite_warning": {
        "ja": "警告: 「上書き」は既存の出力ファイルを置き換えます。",
        "en": "Warning: 'Overwrite' will replace existing output files.",
    },
    # Step 3: Run
    "step3_title": {
        "ja": "手順 3: 実行",
        "en": "Step 3: Run",
    },
    "btn_run_list": {
        "ja": "一覧を作成 (&R)",
        "en": "Create List (&R)",
    },
    "btn_run_organize": {
        "ja": "整理を開始 (&R)",
        "en": "Start Organizing (&R)",
    },
    "btn_run_preview": {
        "ja": "内容を確認 (&R)",
        "en": "Preview Content (&R)",
    },
    "btn_cancel": {
        "ja": "中止 (&C)",
        "en": "Cancel (&C)",
    },
    "btn_resume": {
        "ja": "続きから再開（既存スキップ）",
        "en": "Resume (skip existing)",
    },
    "status_ready": {
        "ja": "準備完了",
        "en": "Ready",
    },
    "status_running": {
        "ja": "処理中…",
        "en": "Running...",
    },
    # Step 4: Results
    "step4_title": {
        "ja": "手順 4: 結果",
        "en": "Step 4: Results",
    },
    "open_output_folder": {
        "ja": "出力フォルダを開く",
        "en": "Open Output Folder",
    },
    "open_series_csv": {
        "ja": "シリーズ一覧（all_series_summary.csv）を開く",
        "en": "Open Series Summary (all_series_summary.csv)",
    },
    "open_report_button": {
        "ja": "ファイル別の結果（file_report.csv）を開く",
        "en": "Open File Report (file_report.csv)",
    },
    "organize_now": {
        "ja": "この内容で整理する",
        "en": "Organize now with these settings",
    },
    "next_steps_title": {
        "ja": "次にやること:",
        "en": "Next steps:",
    },
    "next_steps_list": {
        "ja": "一覧（all_series_summary.csv）を Excel 等で開き、撮像条件の比較や対象シリーズの選定を行ってください。",
        "en": "Open all_series_summary.csv in Excel to compare imaging parameters or select target series.",
    },
    "next_steps_organize": {
        "ja": "整理されたフォルダを画像解析ソフトやビューアで開くか、一覧 CSV で撮像条件を確認してください。",
        "en": "Open organized folders in your analysis software or viewer, or check imaging parameters in the CSV summary.",
    },
    "next_steps_preview": {
        "ja": "内容に問題がなければ、上の「この内容で整理する」ボタンを押して実際の整理を実行できます。",
        "en": "If the preview looks good, click 'Organize now with these settings' above to perform the organization.",
    },
    "scope_limitation_note": {
        "ja": "入力フォルダで見つかったファイルについての結果です。検査のすべての画像が揃っているかは、入力元（PACS など）の情報がないと確認できません。",
        "en": "Results reflect files found in the input folder. Completeness of all images in a study cannot be verified without reference to the source system (e.g. PACS).",
    },
    "table_counts_title": {
        "ja": "処理件数の内訳:",
        "en": "Processed file counts:",
    },
    "table_reasons_title": {
        "ja": "未処理・スキップの理由:",
        "en": "Skipped or unhandled reasons:",
    },
    "table_series_title": {
        "ja": "見つかったシリーズ（上位プレビュー）:",
        "en": "Detected series preview:",
    },
    "col_reason": {
        "ja": "理由",
        "en": "Reason",
    },
    "col_count": {
        "ja": "件数",
        "en": "Count",
    },
    "col_description": {
        "ja": "説明",
        "en": "Description",
    },
    # Menu Items
    "menu_file": {
        "ja": "ファイル (&F)",
        "en": "&File",
    },
    "menu_load_config": {
        "ja": "設定ファイルを読み込む… (&O)",
        "en": "&Load configuration file...",
    },
    "menu_export_config": {
        "ja": "現在の設定を書き出す… (&S)",
        "en": "&Export settings to TOML...",
    },
    "menu_exit": {
        "ja": "終了 (&X)",
        "en": "E&xit",
    },
    "menu_view": {
        "ja": "表示 (&V)",
        "en": "&View",
    },
    "menu_language": {
        "ja": "言語 (&L)",
        "en": "&Language",
    },
    "menu_lang_ja": {
        "ja": "日本語",
        "en": "日本語 (Japanese)",
    },
    "menu_lang_en": {
        "ja": "English",
        "en": "English",
    },
    "menu_font_size": {
        "ja": "文字サイズ (&F)",
        "en": "&Font Size",
    },
    "menu_font_normal": {
        "ja": "標準",
        "en": "Normal",
    },
    "menu_font_large": {
        "ja": "大 (1.25倍)",
        "en": "Large (1.25x)",
    },
    "menu_help": {
        "ja": "ヘルプ (&H)",
        "en": "&Help",
    },
    "menu_glossary": {
        "ja": "用語集 (&G)…",
        "en": "&Glossary...",
    },
    "menu_selftest": {
        "ja": "動作確認（自己診断）を実行 (&T)…",
        "en": "Run &Self-Test...",
    },
    "menu_diagnostics": {
        "ja": "診断情報をコピー (&D)",
        "en": "Copy &Diagnostic Info",
    },
    "menu_docs": {
        "ja": "ドキュメントを開く (Web) (&W)",
        "en": "Open &Documentation (Web)",
    },
    "menu_contact": {
        "ja": "問い合わせ・不具合報告 (&C)…",
        "en": "&Contact & Bug Reports...",
    },
    "menu_about": {
        "ja": "バージョン情報 (&A)…",
        "en": "&About...",
    },
    # Dialogs & Messages
    "glossary_title": {
        "ja": "用語集",
        "en": "Glossary",
    },
    "glossary_content": {
        "ja": (
            "【用語の解説】\n\n"
            "■ DICOM (Digital Imaging and Communications in Medicine)\n"
            "医療用画像の国際標準規格です。画像データだけでなく患者情報や撮像条件ヘッダーが記録されています。\n\n"
            "■ 検査 (Study)\n"
            "患者が一度に来院・受診して行われた一連の撮影単位です。StudyInstanceUID で識別されます。\n\n"
            "■ シリーズ (Series)\n"
            "1 回の検査の中で、同じ撮像条件や断面で連続して撮影された画像の集まりです。SeriesInstanceUID で識別されます。\n\n"
            "■ UID (Unique Identifier)\n"
            "世界中で重複しないように発行される識別用の文字列番号です。\n\n"
            "■ プロファイル (Profile)\n"
            "モダリティ（MR, CT など）に応じた撮像パラメータの抽出設定です。auto を選ぶと自動で適切な項目が選ばれます。\n\n"
            "■ 仮名化 (Pseudonymization)\n"
            "患者名や患者IDをハッシュ値に置き換える処理です。元の値の推測が完全には防げないため、匿名化とは異なり外部公開には適しません。\n\n"
            "■ 一覧のみ (List only)\n"
            "DICOM ファイルをコピーせずに、手元の画像から撮像パラメータの表（CSV）だけを作成する高速なモードです。\n\n"
            "■ 確認 (Dry-run / Preview)\n"
            "ファイルへの書き込みを行わずに、整理対象のシリーズやエラーファイルを事前に確認するモードです。\n\n"
            "■ フォルダの分け方 (Layout)\n"
            "「装置 → 検査日」は異なる装置や日時の撮像パラメータ比較に適しています。「検査ごと」は1回の検査を1フォルダにまとめます。"
        ),
        "en": (
            "Glossary of Terms:\n\n"
            "- DICOM: International standard for medical digital images and headers.\n"
            "- Study: An imaging examination session, identified by StudyInstanceUID.\n"
            "- Series: A group of images acquired under the same parameters/slice, identified by SeriesInstanceUID.\n"
            "- UID: Globally unique identifier string.\n"
            "- Profile: Extraction template for modality-specific parameters (MR, CT, etc.). 'auto' detects automatically.\n"
            "- Pseudonymization: Replacing patient IDs with cryptographic hashes. Not full anonymization; not suitable for public release.\n"
            "- List only: Generates CSV parameter summaries without copying any DICOM image files.\n"
            "- Dry-run / Preview: Inspects what files and series would be processed without writing anything to disk.\n"
            "- Layout: Folder hierarchy organization (e.g. Device -> Date for parameter comparison, or Study for examination units)."
        ),
    },
    "contact_title": {
        "ja": "問い合わせ・不具合報告",
        "en": "Contact & Bug Reports",
    },
    "contact_body": {
        "ja": (
            "dicom-organizer の不具合報告や改善要望は、GitHub Issues またはメールでお知らせください。\n\n"
            "・GitHub Issues:\n  https://github.com/SugimotoKohei/dicom-organizer/issues\n\n"
            "・開発者メール:\n  sugimotokouhei@gmail.com\n\n"
            "--------------------------------------------------\n"
            "【重要なお願い（プライバシー保護）】\n"
            "・実際の DICOM ファイルや患者情報、個人情報を送らないでください。\n"
            "・患者名や個人フォルダ名が写った画面の写真も送らないでください。\n"
            "・報告の際は、メニューの「ヘルプ」→「診断情報をコピー」で取得した\n"
            "  テキスト（個人パスを含まない環境情報）を本文に貼り付けてください。\n"
            "--------------------------------------------------"
        ),
        "en": (
            "To report bugs or request features, please visit GitHub Issues or contact via email:\n\n"
            "- GitHub Issues:\n  https://github.com/SugimotoKohei/dicom-organizer/issues\n\n"
            "- Developer Email:\n  sugimotokouhei@gmail.com\n\n"
            "--------------------------------------------------\n"
            "[IMPORTANT PRIVACY NOTICE]\n"
            "- Never send real DICOM files, patient data, or identifiable information.\n"
            "- Never send screenshots containing patient names or private directory paths.\n"
            "- Please paste the text from 'Help' -> 'Copy Diagnostic Info'\n"
            "  (which sanitizes private paths) into your bug report.\n"
            "--------------------------------------------------"
        ),
    },
    "about_title": {
        "ja": "dicom-organizer について",
        "en": "About dicom-organizer",
    },
    "about_body": {
        "ja": (
            "dicom-organizer バージョン {version}\n\n"
            "手元（ローカル）の DICOM ファイルを整理し、撮像条件を一覧化するツールです。\n"
            "ドキュメント: https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/README.md\n"
            "リポジトリ: https://github.com/SugimotoKohei/dicom-organizer"
        ),
        "en": (
            "dicom-organizer version {version}\n\n"
            "A tool to organize local DICOM files and summarize imaging parameters.\n"
            "Documentation: https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/README.md\n"
            "Repository: https://github.com/SugimotoKohei/dicom-organizer"
        ),
    },
    "diagnostics_copied": {
        "ja": "診断情報をクリップボードにコピーしました。（ホームディレクトリ等の個人パスは除外されています）",
        "en": "Diagnostic information copied to clipboard. (Personal paths such as home directory have been sanitized.)",
    },
    "selftest_running": {
        "ja": "自己診断を実行しています…",
        "en": "Running self-test diagnostics...",
    },
    "selftest_result_title": {
        "ja": "自己診断結果",
        "en": "Self-Test Results",
    },
    "selftest_passed": {
        "ja": "すべての自己診断に合格しました ({passed}/{total})。",
        "en": "All self-test checks passed ({passed}/{total}).",
    },
    "selftest_failed": {
        "ja": "自己診断で一部失敗がありました ({passed}/{total})。",
        "en": "Self-test checks failed ({passed}/{total}).",
    },
    "confirm_move_title": {
        "ja": "元のファイルの移動の確認",
        "en": "Confirm Moving Original Files",
    },
    "confirm_move_msg": {
        "ja": "配置方法「移動」が選択されています。元の DICOM ファイルが別の場所に移動され、元のフォルダからは無くなります。よろしいですか？",
        "en": "'Move' action is selected. Source DICOM files will be relocated and deleted from their original locations. Do you wish to continue?",
    },
    "confirm_overwrite_title": {
        "ja": "上書きの確認",
        "en": "Confirm Overwrite",
    },
    "confirm_overwrite_msg": {
        "ja": "既存ファイルの扱い「上書き」が選択されています。出力先に既に同名ファイルが存在する場合、上書きされます。よろしいですか？",
        "en": "'Overwrite' mode is selected. Existing files in the destination folder will be overwritten. Do you wish to continue?",
    },
    "confirm_cancel_and_exit": {
        "ja": "処理中です。中止して閉じますか？",
        "en": "Operation is in progress. Cancel and exit?",
    },
    "error_input_required": {
        "ja": "入力フォルダを指定してください。",
        "en": "Please specify an input folder.",
    },
    "error_output_required": {
        "ja": "出力フォルダを指定してください。",
        "en": "Please specify an output folder.",
    },
    "error_invalid_limit": {
        "ja": "処理件数の上限には正の整数を指定してください: {value}",
        "en": "Limit must be a non-negative integer: {value}",
    },
    "error_limit_negative": {
        "ja": "処理件数の上限には 0 以上の数値を指定してください。",
        "en": "Limit must be 0 or greater.",
    },
    "config_loaded": {
        "ja": "設定ファイル '{path}' を読み込みました。",
        "en": "Successfully loaded configuration file '{path}'.",
    },
    "config_load_error": {
        "ja": "設定ファイルの読み込みに失敗しました: {error}",
        "en": "Failed to load configuration file: {error}",
    },
    "config_exported": {
        "ja": "設定を '{path}' に書き出しました。",
        "en": "Successfully exported configuration to '{path}'.",
    },
    "config_export_error": {
        "ja": "設定の書き出しに失敗しました: {error}",
        "en": "Failed to export configuration: {error}",
    },
    "status_completed": {
        "ja": "完了しました",
        "en": "Completed",
    },
    "status_preview_completed": {
        "ja": "確認が完了しました（ファイルは書き込んでいません）",
        "en": "Preview finished (no files were written)",
    },
    "status_cancelled": {
        "ja": "中止しました",
        "en": "Cancelled",
    },
    "status_failed": {
        "ja": "失敗しました",
        "en": "Failed",
    },
    "dialog_error_title": {
        "ja": "エラー",
        "en": "Error",
    },
    "dialog_input_required_title": {
        "ja": "入力が必要です",
        "en": "Input Required",
    },
    "dialog_diagnostics_title": {
        "ja": "診断情報",
        "en": "Diagnostics",
    },
    "dialog_config_title": {
        "ja": "設定ファイル",
        "en": "Configuration",
    },
    "dialog_confirm_title": {
        "ja": "確認",
        "en": "Confirmation",
    },
    "dialog_selftest_title": {
        "ja": "自己診断結果",
        "en": "Self-Test Results",
    },
    "error_file_exists": {
        "ja": "出力フォルダに前回の結果があります。既存のファイルはそのままにして続きから処理するには『続きから再開』を、最初からやり直すには別の出力フォルダを選んでください。",
        "en": "Output folder contains results from a previous run. To resume without overwriting, click 'Resume', or choose a different output folder to start fresh.",
    },
    "error_insufficient_space": {
        "ja": "保存先の空き容量が足りません。空き容量を確保するか、別の保存先を選んでください。",
        "en": "Insufficient disk space. Please free up disk space or choose another destination folder.",
    },
    "error_integrity": {
        "ja": "コピー後のファイルの整合性検証（チェックサム）に失敗しました。保存先のディスクに問題がないか確認してください。",
        "en": "File integrity check failed after copying. Please verify the destination storage.",
    },
    "error_permission": {
        "ja": "出力フォルダへの書き込み権限がありません。アクセス権限を確認するか、別の出力先を選んでください。",
        "en": "Permission denied writing to the output folder. Please check folder permissions or choose another destination.",
    },
    "error_general_failed": {
        "ja": "処理中にエラーが発生して停止しました。",
        "en": "Failed due to an error.",
    },
    "advanced_toggle_show": {
        "ja": "▶ 詳細設定を表示する",
        "en": "▶ Show advanced settings",
    },
    "advanced_toggle_hide": {
        "ja": "▼ 詳細設定を隠す",
        "en": "▼ Hide advanced settings",
    },
    "count_col_item": {
        "ja": "項目",
        "en": "Item",
    },
    "count_col_count": {
        "ja": "件数",
        "en": "Count",
    },
    "count_col_desc": {
        "ja": "説明",
        "en": "Description",
    },
    "count_item_organized": {
        "ja": "整理したファイル",
        "en": "Organized files",
    },
    "count_desc_organized": {
        "ja": "元の画像や非画像ファイルを含め、出力フォルダに整理（配置）された総ファイル数です。",
        "en": "Total files organized into destination folders.",
    },
    "count_item_organized_preview": {
        "ja": "整理予定のファイル",
        "en": "Planned organized files",
    },
    "count_desc_organized_preview": {
        "ja": "整理を実行した場合に出力フォルダへ配置される総ファイル数です。",
        "en": "Total files planned to be organized into destination folders.",
    },
    "count_item_organized_list": {
        "ja": "整理したファイル",
        "en": "Organized files",
    },
    "count_desc_organized_list": {
        "ja": "一覧のみモードのため DICOM ファイルのコピー・整理は行いません。",
        "en": "DICOM files are not copied or moved in list-only mode.",
    },
    "count_item_csv_targets": {
        "ja": "一覧に載せた画像",
        "en": "CSV target images",
    },
    "count_desc_csv_targets": {
        "ja": "撮像条件のメタデータ CSV（all_series_summary.csv 等）に載った画像ファイル数です。",
        "en": "Number of valid image files whose parameters are recorded in metadata CSV tables.",
    },
    "count_item_csv_excluded": {
        "ja": "表の対象外（非画像）",
        "en": "Excluded from table (non-image)",
    },
    "count_desc_csv_excluded": {
        "ja": (
            "見つかった DICOM のうち、撮像条件の表には載せないオブジェクト（プレゼンテーションステート、構造化レポート、"
            "各社独自のオブジェクトなど）の数です。整理するときは、画像と同じようにフォルダへ配置します。"
        ),
        "en": (
            "Number of DICOM objects found that are not included in the parameter table (Presentation States, Structured "
            "Reports, proprietary objects, etc.). When organizing, they are placed in folders like images."
        ),
    },
    "count_item_series": {
        "ja": "シリーズ数（非画像を含む）",
        "en": "Series count (including non-image)",
    },
    "count_desc_series": {
        "ja": "検出された全シリーズの総数です（非画像シリーズを含みます）。",
        "en": "Total number of all series detected, including non-image series.",
    },
    "count_item_image_series": {
        "ja": "一覧に載せたシリーズ（画像）",
        "en": "Series included in summary (images)",
    },
    "count_desc_image_series": {
        "ja": "撮像条件の一覧表（all_series_summary.csv）に載せた画像シリーズの数です（下のシリーズ表と一致）。",
        "en": "Number of image series included in the parameter summary CSV (matches the series table below).",
    },
    "count_item_studies": {
        "ja": "検査数",
        "en": "Study count",
    },
    "count_desc_studies": {
        "ja": "検出された検査（Study）の総数です。",
        "en": "Total number of distinct studies detected.",
    },
    "count_item_skipped": {
        "ja": "未処理・スキップ（合計）",
        "en": "Skipped / unhandled (total)",
    },
    "count_desc_skipped": {
        "ja": "整理・一覧の対象にしなかったファイルの合計です（内訳は下の表を参照）。",
        "en": "Total number of files not organized or included in the summary (see reason table below).",
    },
    "count_item_duplicates": {
        "ja": "内容の異なる重複",
        "en": "UID conflicts (different content)",
    },
    "count_desc_duplicates": {
        "ja": (
            "同じ SOPInstanceUID を持ちながら内容が異なるファイルの数です。どちらも対象にし、整理するときは番号を付けた"
            "別の名前で両方を配置します。"
        ),
        "en": (
            "Number of files that share an SOPInstanceUID but have different content. Both are kept; when organizing, "
            "both are placed under numbered names."
        ),
    },
    "table_series_title_count": {
        "ja": "見つかったシリーズ（{count} 件）:",
        "en": "Detected series ({count} series):",
    },
    "conclusion_failed": {
        "ja": "エラーにより停止しました。{count} ファイルが保存されています。",
        "en": "Failed due to error. {count} files were preserved.",
    },
    "conclusion_failed_no_writes": {
        "ja": "エラーにより停止しました。この実行ではファイルを書き込んでいません。",
        "en": "Stopped due to an error. No files were written in this run.",
    },
    "conclusion_cancelled": {
        "ja": "処理を中止しました。{count} ファイルが保存されています。",
        "en": "Operation cancelled. {count} files were preserved.",
    },
    "conclusion_dry_run": {
        "ja": "書き込みはしていません。{target_files} 件の対象ファイルから {series_count} シリーズを確認しました。",
        "en": "No files were written. Confirmed {series_count} series from {target_files} candidate files.",
    },
    "conclusion_list": {
        "ja": "完了しました。{target_files} 件の画像から {series_count} シリーズの一覧を作りました。",
        "en": "Completed. Generated a summary of {series_count} series from {target_files} images.",
    },
    "conclusion_organize": {
        "ja": "完了しました。{org_files} ファイルを整理し、そのうち {target_files} 件を撮像条件の表に載せました。",
        "en": "Completed. Organized {org_files} files and included {target_files} in the parameter summary.",
    },
    "results_placeholder": {
        "ja": "実行すると、ここに結果が表示されます。",
        "en": "Results will appear here after you run.",
    },
}


def tr(key: str, lang: str = "en", **kwargs: Any) -> str:
    """Retrieve translated string by key with fallback to English."""
    item = STRINGS.get(key)
    if not item:
        return key
    text = item.get(lang) or item.get("en", key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
