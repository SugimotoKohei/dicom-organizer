# Institutional Deployment and IT Administrator Guide / 施設・チーム導入ガイド

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This guide provides institutional IT administrators, security officers, and research coordinators with the necessary technical and governance information to approve, deploy, and maintain `dicom-organizer` within hospital and academic environments.

### 1. Executive Summary and Intended Purpose

- **Intended Purpose**: Local organization of messy exported DICOM directory trees into standardized series hierarchies; extraction of acquisition parameters into summary CSVs for quality assurance, protocol audits, and research preprocessing.
- **Explicit Non-Goals**: Not a diagnostic viewer, not a PACS archive, not a clinical decision support system, and not an anonymizer.
- **Regulatory Status**: **Not a medical device**. It is designed solely for retrospective research and offline file organization.

### 2. Security and System Profile

| Consideration | Technical Specification / Policy |
|---|---|
| **Supported Platforms** | Automated tests are executed in CI (GitHub Actions) on `ubuntu-latest`, `macos-latest`, and `windows-latest` for Python 3.14, plus test matrix on Ubuntu for Python 3.11, 3.12, and 3.13. Standalone desktop apps are built for Windows (x64) and macOS (arm64 & x86_64). Operation on other OS versions is unverified. |
| **User Privileges Required** | **Standard user only**. No administrator (root / sudo) privileges are required. |
| **Network Communications** | **No background network activity**. The application contains no network transmission code, no telemetry, and performs no automatic updates. Only when a user clicks "Documentation" in the GUI Help menu (Help -> Documentation), the default web browser opens the GitHub documentation page. |
| **Input Data Safety** | **Read-only by default**: In default copy mode, list-only mode, and dry-run mode, source files are strictly opened in read-only mode and never modified. Source files are moved only when `--action move` is explicitly requested alongside `--confirm-move`. |
| **Write Destinations** | Writes are strictly constrained to: (1) The user-specified output folder, (2) The file specified via `--self-test-report`, (3) GUI settings saved in the OS per-user settings store (on macOS: `~/Library/Preferences/com.dicom-organizer.dicom-organizer.plist`), (4) An OS temporary directory used transiently by `--self-test` and "Try with Sample Data", and (5) `~/Applications/dicom-organizer.app` created by `dicom-organizer-gui-app`. |
| **Dependencies** | Standalone executables are fully self-contained (bundled Python and Qt runtimes). Python packages require Python 3.11 or later (automated test suite verifies 3.11, 3.12, 3.13, and 3.14; using the GUI extra follows PySide6 version support, which is Python >=3.10,<3.15 as of PySide6 6.11.1 in 2026-09) with `pydicom` and optional `pyside6`. |
| **Disk Space Safety** | Pre-checks destination available disk space before initiating copy operations (fails safely if insufficient). |

### 3. Verification and Acceptance Testing

Administrators can verify tool integrity immediately upon installation:
1. **Self-Test Diagnostic (`--self-test`)**:
   Runs a deterministic synthetic test that verifies three distinct behaviors: (1) Normal file organization and report file generation, (2) List-only parameter table creation, and (3) Verification that dry-run mode writes nothing to disk.
   ```bash
   dicom-organizer --self-test
   ```
2. **Interactive GUI Verification**:
   Launch GUI and click **"Try with Sample Data"** on the start screen.

### 4. Enterprise Configuration Deployment (`--config`)

Facilities can enforce standardized naming, profiles, and privacy settings across all user workstations via a central configuration file.
- Specify path via CLI option: `--config /path/to/facility_config.toml`
- Or configure via environment variable: `DICOM_ORGANIZER_CONFIG=/path/to/facility_config.toml`

Example `facility_config.toml` (flat TOML without section headers):
```toml
layout = "device-date"
profile = "auto"
patient_mode = "drop"
if_exists = "skip"
checksum = true
```

### 5. Failure Recovery and Audit Trails

- **Auditing (`file_report.csv`)**: Every candidate file is audited in `file_report.csv` with source path, target path, status (`organized` / `skipped`), and specific reason code (`not_dicom`, `duplicate_identical`, `read_error`).
- **Resuming Interrupted Runs**: If an execution is interrupted (system sleep or cancellation), simply re-run the same command or click **Resume** in GUI; with `--if-exists skip`, already organized files are safely bypassed.

### 6. Institutional Security Checklist for Approval

- [x] Application requires no administrative / root privileges.
- [x] Zero background network connectivity, telemetry, or outbound analytics (browser opens only on clicking Help -> Documentation).
- [x] Input clinical files are treated strictly read-only (except when `--action move` is explicitly requested).
- [x] No automatic updates modifying files without IT intervention.
- [x] Audit log generated for all files (`file_report.csv`).
- [x] Built-in automated acceptance testing via `--self-test` (verifying organization, list-only, and dry-run).
- [x] Contact email provided for security issues: `sugimotokouhei@gmail.com`.

---

<a id="japanese"></a>
## 日本語

本文書は、病院・大学・研究所等の情報システム管理者、セキュリティ責任者、および研究責任者が、`dicom-organizer` の導入を審査・承認・運用するための技術資料です。

### 1. 概要と想定用途

- **想定用途**: 外付けメディアや装置コンソールから取り出された散乱 DICOM フォルダの階層整理、撮像条件（TR, TE, フリップ角, スライス厚等）の CSV 一覧抽出、研究前処理の標準化。
- **非想定用途**: 画像の診断表示、PACS 保管、診断意思決定支援、DICOM データの完全匿名化。
- **法的位置づけ**: **医療機器ではありません**。研究およびデータ整理専用のオフラインツールです。

### 2. セキュリティおよびシステム特性

| 項目 | 仕様および方針 |
|---|---|
| **対応 OS** | CI（GitHub Actions）で自動テストを実行しているのは `ubuntu-latest`、`macos-latest`、`windows-latest`（Python 3.14）、および Linux 上での Python 3.11・3.12・3.13 です。単体アプリをビルドするのは Windows（x64）と macOS（arm64・x86_64）です。これら以外の OS バージョンでの動作は未確認です。 |
| **必要権限** | **一般ユーザー権限のみ**。管理者権限（UAC 昇格、root、sudo）は一切不要です。 |
| **ネットワーク通信** | **バックグラウンド通信ゼロ**。本体に通信コードはなく、利用状況やテレメトリ送信、自動更新チェック等も行いません。ただし、GUI の「ヘルプ」メニューから「ドキュメント」をクリックしたときだけ、既定のブラウザで GitHub の文書ページが開きます（クリックしなければ通信しません）。 |
| **データの流れ（入力）** | **原則読み取り専用**: 既定の copy、一覧のみ（`--list-only`）、確認（`--dry-run`）では入力ファイルを読むだけで変更しません。明示的に `--action move`（要 `--confirm-move`）を選んだときだけ入力ファイルを移動します。 |
| **書き込み先** | 実際に書き込む先は以下の場所に限定されます:<br>1. ユーザーが指定した出力フォルダ（`organized/` や `organized_list/`）<br>2. `--self-test-report` で指定したファイル<br>3. GUI の設定（OS ごとの設定保存領域。macOS では `~/Library/Preferences/com.dicom-organizer.dicom-organizer.plist`）<br>4. `--self-test` や GUI の「サンプルデータで試す」が使用する OS の一時フォルダ<br>5. `dicom-organizer-gui-app` が作成する `~/Applications/dicom-organizer.app` |
| **外部依存性** | 単体アプリ版は Python および Qt ランタイムを同梱（追加インストール不要）。Python 版は Python 3.11 以上（自動テストで確認しているのは 3.11・3.12・3.13・3.14。GUI を使う場合は PySide6 の対応範囲に従い、2026-09 時点の PySide6 6.11.1 は 3.10 以上 3.15 未満）、pydicom、PySide6 を使用。 |
| **空き容量の保護** | コピー開始前に出力先ドライブの空き容量を事前検証し、容量不足時は安全に処理を停止します。 |

### 3. 受け入れ確認（動作確認）

インストール後、以下の手順で即座に動作確認を実施できます:
1. **自己診断コマンド (`--self-test`)**:
   内蔵の合成 DICOM データを用いて、(1) 通常の整理と報告ファイルの生成、(2) 一覧のみモードの表生成、(3) 確認（dry-run）でディスクに何も書かないこと、の 3 項目を自己検証します:
   ```bash
   dicom-organizer --self-test
   ```
2. **GUI 上での確認**:
   アプリを起動し、初期画面の「サンプルデータで試す」をクリックして動作を確認します。

### 4. 施設共通設定の配り方 (`--config`)

組織内でフォルダ構成やプライバシー設定を統一するために、施設共通の設定ファイルを配布できます。
- CLI オプション: `--config /path/to/facility_config.toml`
- 環境変数での指定: `DICOM_ORGANIZER_CONFIG=/path/to/facility_config.toml`

設定ファイルの例（`facility_config.toml`。セクションを持たない平坦な TOML）:
```toml
layout = "device-date"
profile = "auto"
patient_mode = "drop"
if_exists = "skip"
checksum = true
```

### 5. 障害時の対応と監査証跡

- **全ファイルの監査証跡 (`file_report.csv`)**: 検出された全ファイルについて、元の相対パス、整理先パス、処理状態（整理済 / スキップ）、理由コード（`not_dicom`, `duplicate_identical`, `read_error` 等）が記録されます。
- **中断後の再開**: PC のスリープや手動キャンセルで中断した場合、同じコマンドに `--if-exists skip` を付ける（または GUI で「再開」を押す）ことで、整理済みのファイルをスキップして未処理ファイルのみを安全に続行できます。

### 6. 導入審査用チェックリスト

- [x] 管理者権限を必要とせず、一般ユーザー領域で動作する。
- [x] バックグラウンドでの通信やテレメトリ送信を行わない（ブラウザ起動はヘルプのドキュメントリンクを押したときのみ）。
- [x] 入力元の臨床データ・フォルダを変更せず、読み取り専用で扱う（`--action move` 実行時を除く）。
- [x] 利用者に無断でファイルを改変する自動更新機能を持たない。
- [x] 処理結果およびスキップ理由の完全な証跡（`file_report.csv`）が残る。
- [x] `--self-test` による客観的な受け入れ試験が可能（通常整理・一覧のみ・dry-run の 3 項目）。
- [x] セキュリティ窓口が明記されている（`sugimotokouhei@gmail.com`）。
