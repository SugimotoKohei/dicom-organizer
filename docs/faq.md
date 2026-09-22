# Frequently Asked Questions (FAQ) / よくある質問とトラブルシューティング

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

### 1. General Questions & Safety

#### Q: Is my patient data sent over the internet?
**A: No, absolutely not.** `dicom-organizer` operates 100% locally on your workstation. It contains no network transmission code, no telemetry, and does not check for updates automatically. Only when you click "Documentation" in the GUI Help menu (Help -> Documentation), your default web browser opens the GitHub documentation page (no network communication occurs unless you click this link). It functions normally in completely offline and air-gapped hospital environments.

#### Q: Are my DICOM files anonymized when organized?
**A: No.** Organizing DICOM files preserves the original headers and binary content bit-for-bit. While `--patient-mode hash` or `--patient-mode drop` modifies the generated CSV metadata tables, the DICOM files themselves still contain all original patient identifiers. To anonymize DICOM files, use a dedicated de-identification tool compliant with DICOM PS3.15 Annex E.

#### Q: Why did macOS or Windows show a security warning upon first launch?
**A: The application binaries are currently unsigned.** Formal developer certificates are planned for future milestones. On macOS, go to **System Settings -> Privacy & Security** and click **Open Anyway**. On Windows SmartScreen, click **More info** followed by **Run anyway**. See [docs/install.md](install.md) for step-by-step guidance.

### 2. Common Errors and Resolutions

#### Q: Error: "No DICOM files were organized"
**A:** This indicates that no readable DICOM image slices were recognized in the input directory.
- Check if your DICOM files lack the 128-byte preamble header. If you used `--no-force-read`, remove that option to enable default force-reading.
- Open `file_report.csv` to see how the candidate files were classified (e.g., `not_dicom`, `missing_required_uid`, or `read_error`).

#### Q: Error: "Target exists: <path>"
**A:** By default, `dicom-organizer` operates with `--if-exists error`. This is a per-file safety error raised when a file with the destination name already exists at the target location (`Target exists: <destination_path>. Re-run with --if-exists skip to continue into an existing output folder.`). To continue organization into an existing output folder without erroring on existing files, specify `--if-exists skip`.

#### Q: Why does the CSV row count not match the total number of organized files?
**A:** Non-image DICOM objects (such as Presentation States, Structured Reports, or vendor helper objects) are sorted into series folders, but are intentionally excluded from `dicom_parameters.csv` and `series_summary.csv` because they lack imaging parameters like TR, TE, or matrix size. Check `file_report.csv` to confirm their status.

#### Q: How do I interpret the unhandled / skipped reasons?
**A:** The `skipped_by_reason` section in `organize_summary.json` and the `Reason` column in `file_report.csv` report exactly 9 codes (`core.SKIP_REASONS`):
- `not_dicom`: Non-DICOM file (e.g., `.txt`, `.jpg`, non-DICOM binaries).
- `dicomdir`: Media storage directory index file (`DICOMDIR`).
- `missing_required_uid`: DICOM dataset lacking required `SeriesInstanceUID` or `SOPInstanceUID`.
- `read_error`: Corrupted file or invalid DICOM structure where dataset parsing failed.
- `permission_denied`: OS permission denied when accessing or reading the file.
- `io_error`: OS I/O error occurred while opening or reading the file.
- `excluded_hidden`: Hidden files or OS dotfiles (e.g., `.DS_Store`) excluded by default.
- `duplicate_identical`: Identical duplicate file matching an already-placed SOPInstanceUID and SHA-256 hash.
- `existing_output`: Target destination already exists in destination folder when `--if-exists skip` is used.

#### Q: How do Enhanced MR multi-frame values appear in CSV?
**A:** Multi-frame series store parameter variations across slices. If parameters such as echo time or flip angle change between frames, `dicom-organizer` joins the distinct values using a pipe delimiter (e.g., `12.0|24.0|36.0`). The `NumberOfFrames` and `FrameVaryingAttributes` columns indicate multi-frame objects.

#### Q: How do I handle Windows long path errors?
**A:** Very deep input directory structures may exceed Windows path length limits. We recommend:
1. Shortening the output destination path (e.g., `C:\DICOM\out`).
2. Specifying `--layout study` to make directory nesting one level shallower.
Note that enabling the Windows registry setting `LongPathsEnabled=1` is untested and unverified for this toolchain.

#### Q: How do I resume after an unexpected interruption or system sleep?
**A:** If an execution was cancelled or interrupted, rerun the command with `--if-exists skip`. The organizer detects already-placed files, skips identical destinations, and processes the remaining files.

#### Q: Warning: "Previous run was not completed"
**A:** The exact warning is:
`Previous run was not completed (status=...). Re-run with --if-exists skip to continue into an existing output folder.`
This occurs when a prior execution did not finish cleanly. Specifying `--if-exists skip` will inspect the existing output, resume placing remaining files, and rebuild consistent metadata CSV summaries.

---

<a id="japanese"></a>
## 日本語

### 1. 全般的な疑問と安全性

#### Q: 患者データがインターネット上に送信されることはありますか？
**A: 一切ありません。** `dicom-organizer` は完全にローカル環境（手元の PC）のみで動作します。外部へのネットワーク送信コードやテレメトリは一切含まれておらず、自動更新チェックも行いません。ただし、GUI の「ヘルプ」メニューから「ドキュメント」（Help → Documentation）をクリックしたときのみ、既定のブラウザで GitHub の文書ページが開きます（クリックしなければ一切通信しません）。電子カルテ網等の完全オフライン環境で安心してご利用いただけます。

#### Q: 整理された DICOM ファイルは匿名化されていますか？
**A: 匿名化されていません。** 本ツールはファイルを整理（コピー・移動）する際、DICOM ヘッダーおよび画像バイナリを 1 バイトも変更しません。`--patient-mode hash` や `--patient-mode drop` を指定した場合でも、変更されるのは生成される CSV メタデータ表のみであり、DICOM ファイル本体には患者氏名や ID がそのまま残ります。外部への共有には、DICOM PS3.15 Annex E に準拠した専門の匿名化ツールをご利用ください。

#### Q: 初回起動時に macOS や Windows で警告が出たのはなぜですか？
**A: 単体アプリ版に正式なコード署名証明書がまだ付与されていないためです。** 将来のリリースで署名取得を予定しています。macOS では「システム設定 → プライバシーとセキュリティ」から「このまま開く」を選択してください。Windows では SmartScreen 画面で「詳細情報」→「実行」をクリックしてください。詳細は [docs/install.md](install.md) を参照してください。

### 2. よくあるエラーと対処法

#### Q: エラー: "No DICOM files were organized"（DICOM ファイルが整理されませんでした）
**A:** 指定されたフォルダ内に認識可能な DICOM 画像ファイルが見つかりませんでした。
- 先頭の 128 バイトプリアンブルが欠損している可能性があります。`--no-force-read` オプションを指定している場合は外してください（既定で force-read が有効です）。
- 出力フォルダの `file_report.csv` を開き、候補ファイルがどのような理由（`not_dicom`、`missing_required_uid`、`read_error` 等）でスキップされたか確認してください。

#### Q: エラー: "Target exists: <パス>"（同名ファイルが既に存在します）
**A:** `dicom-organizer` は既定で `--if-exists error` として動作します。これは出力先フォルダが空でないときではなく、**同じ名前のファイルが既にあるとき**に出るファイル単位のエラーです（実際の文面は `Target exists: <パス>. Re-run with --if-exists skip to continue into an existing output folder.`）。中断した処理を再開する場合や既存フォルダに追加する場合は `--if-exists skip` を指定してください。

#### Q: CSV の行数が整理されたファイル総数より少ないのはなぜですか？
**A:** プレゼンテーションステート（PR）や構造化レポート（SR）、各社独自の補助オブジェクトなどの「非画像オブジェクト」は、シリーズフォルダへの整理は行われますが、TR や TE などの撮像パラメータを持たないため `dicom_parameters.csv` や `series_summary.csv` からは除外されます。除外された内訳は `file_report.csv` で確認できます。

#### Q: 未処理理由コードの読み方を教えてください
**A:** `organize_summary.json` の `skipped_by_reason` や `file_report.csv` の `Reason` 列には、次の 9 種のコード（`core.SKIP_REASONS`）が出力されます:
- `not_dicom`: 拡張子や内容が非 DICOM であるファイル（`.txt`, `.jpg` 等）。
- `dicomdir`: メディア索引ファイル（`DICOMDIR`）。
- `missing_required_uid`: `SeriesInstanceUID` または `SOPInstanceUID` が欠損しているファイル。
- `read_error`: ファイル破損等によりヘッダー解析に失敗したファイル。
- `permission_denied`: OS のファイル読み取り・アクセス権限がないファイル。
- `io_error`: ファイルオープンや読み込み時に OS の I/O エラーが発生したファイル。
- `excluded_hidden`: OS の隠しファイル（`.DS_Store` 等）。
- `duplicate_identical`: 先に処理されたファイルと SOPInstanceUID および SHA-256 ハッシュが完全に一致する同一内容の重複ファイル。
- `existing_output`: `--if-exists skip` 実行時に、出力先ファイルが既に存在していたためスキップされたファイル。

#### Q: Enhanced MR（マルチフレーム）の撮像条件はどのように表示されますか？
**A:** マルチフレーム画像では、スライス間でエコー時間やフリップ角が変化する場合があります。その場合、相異なる値がパイプ記号で連結されて出力されます（例: `12.0|24.0|36.0`）。`NumberOfFrames` 列および `FrameVaryingAttributes` 列でマルチフレームの有無を確認できます。

#### Q: Windows の長いパス名エラーへの対処法は？
**A:** フォルダ階層が深い場合、Windows のパス長制限に達することがあります。次の対策を推奨します:
1. 出力先を短いパス（例: `C:\DICOM\out`）にする。
2. `--layout study` を指定してフォルダの階層を 1 段浅くする。
なお、レジストリ設定（`LongPathsEnabled=1`）で解決する方法は、本ツールの環境では未検証です。

#### Q: PC のスリープ等で中断された処理を再開するには？
**A:** 同じ出力先を指定し、`--if-exists skip` オプションを付けて再実行してください（GUI の場合は「再開」ボタンを押します）。すでに配置済みのファイルを検知してスキップし、未処理のファイルだけを続行します。

#### Q: 警告: "Previous run was not completed" が出た場合
**A:** 実際の警告文面は以下のとおりです:
`Previous run was not completed (status=...). Re-run with --if-exists skip to continue into an existing output folder.`
前回の処理が中断され、メタデータ表が完成していない状態で残っている場合に表示されます。`--if-exists skip` を指定して再実行することで、既存の出力ファイルを走査し、完全なメタデータ表を再構築します。
