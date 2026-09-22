# Contributing Guide / 開発・貢献の手引き

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

Thank you for your interest in contributing to `dicom-organizer`. Whether you are fixing a bug, adding documentation, or reporting scanner compatibility, your help is appreciated.

### 1. Development Setup

This project uses Python 3.11 and `uv`.

```bash
git clone https://github.com/SugimotoKohei/dicom-organizer.git
cd dicom-organizer
uv sync --locked --extra gui
```

### 2. Running Tests and Checks

To run all automated tests (including GUI tests):

```bash
# Run pytest with GUI tests enabled in offscreen mode
DICOM_ORGANIZER_REQUIRE_GUI=1 QT_QPA_PLATFORM=offscreen uv run python -m pytest -q

# Run lint checks
uv run ruff check
```

#### Test Structure
- Core CLI tests (e.g., `test_run_writes_files_and_metadata` in `tests/`): Synthetic DICOM generation, duplicate resolution, layout variants, and failure recovery.
- Column schema tests (e.g., `test_column_coverage` in `tests/`): Column specifications, units, descriptions, and JSON schema.
- GUI tests (e.g., `test_start_page_buttons_and_language_switch` in `tests/`): Offscreen PySide6 GUI interactions, forms, i18n strings, and progress events.
- Support matrix tests (e.g., `test_compressed_transfer_syntax_jpeg_baseline_and_lossless` in `tests/`): Modality coverage, compressed transfer syntaxes, character sets, and non-image DICOM objects.

### 3. Accessible Areas to Contribute

You do not need deep Python internals experience to make a difference:
- **Scanner Compatibility Reports**: Test `dicom-organizer` with anonymized research data from your MRI, CT, or other scanners, and submit a [Scanner Verification Report](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=verification_report.yml).
- **Documentation and Workflow Guides**: Help improve tutorials or add workflows under `docs/workflows/`.
- **Translations**: Help keep Japanese and English documentation synchronized and natural.

### 4. Pull Request Guidelines

- **Synthetic Test Data Only**: Always write tests using synthetic DICOM generators (`write_dicom` helper in `tests/`). Never commit real patient data or clinical binaries.
- **Core Alignment**: CLI and GUI behaviors must remain strictly aligned by sharing `src/dicom_organizer/core.py`.
- **Maintainer Review**: Ensure tests and linter pass before opening a pull request.

---

<a id="japanese"></a>
## 日本語

`dicom-organizer` への貢献に関心をお寄せいただきありがとうございます。不具合修正、ドキュメントの改善、装置の互換性報告など、皆様のご参加をお待ちしています。

### 1. 開発環境のセットアップ

本プロジェクトは Python 3.11 と `uv` を前提としています。

```bash
git clone https://github.com/SugimotoKohei/dicom-organizer.git
cd dicom-organizer
uv sync --locked --extra gui
```

### 2. テストと構文チェックの実行

GUI テストを含むすべての自動テストを実行します:

```bash
# オフスクリーン環境で GUI テストを含めて pytest を実行
DICOM_ORGANIZER_REQUIRE_GUI=1 QT_QPA_PLATFORM=offscreen uv run python -m pytest -q

# ruff による構文チェック
uv run ruff check
```

#### テストの種類
- CLI 中核機能テスト（例: `test_run_writes_files_and_metadata`）: CLI の主要機能、整理ロジック、メタデータ抽出、オプションの挙動確認。
- カラム定義テスト（例: `test_column_coverage`）: カラム定義、単位、欠損値、JSON スキーマの整合性テスト。
- GUI テスト（例: `test_start_page_buttons_and_language_switch`）: オフスクリーンでの PySide6 GUI 動作、多言語表示、進捗イベントのテスト。
- 規格適合テスト（例: `test_compressed_transfer_syntax_jpeg_baseline_and_lossless`）: 圧縮転送構文、文字コード、非画像オブジェクト、Enhanced DICOM などの対応検証。

### 3. 貢献しやすい領域

高度な Python プログラミングに限らず、幅広い領域でご協力いただけます:
- **実機検証結果の報告**: お手元の研究用データで実行し、うまく読み取れた項目や N/A となった項目を [実機検証報告テンプレート](https://github.com/SugimotoKohei/dicom-organizer/issues/new?template=verification_report.yml) でお知らせください。
- **ワークフローやドキュメントの改善**: `docs/workflows/` への連携事例の追加や説明の平易化。
- **翻訳の推敲**: 英日併記ドキュメントの表現や用語の改善。

### 4. プルリクエスト（PR）のルール

- **合成データのみ使用**: テストはすべて合成 DICOM 生成ヘルパーを用いて記述してください。実患者データや臨床バイナリのコミットは厳禁です。
- **中核処理の共通化**: CLI と GUI は `src/dicom_organizer/core.py` を共有し、動作差を作らない設計を維持してください。
- **検証の実施**: PR 作成前に `pytest` と `ruff` が通ることをローカル環境で確認してください。
