## Summary of Changes / 変更内容の概要

<!-- Please provide a concise explanation of what this PR does and why it is needed. / 変更の目的と概要を簡潔に記述してください。 -->

## Related Issues / 関連 Issue

Fixes #

## Checklist / 確認項目

- [ ] **No PHI / Real Data**: I have verified that NO real patient data, protected health information (PHI), clinical DICOM files, or private file system paths are included in this PR or tests. / 実患者データ、個人情報、臨床DICOMファイル、個人パスが含まれていないことを確認しました。
- [ ] **Synthetic Tests**: All tests use synthetic DICOM fixtures or unit test mocks. / テストはすべて合成 DICOM またはモックを使用しています。
- [ ] **Core Alignment**: CLI and GUI behaviors remain aligned through `src/dicom_organizer/core.py`. / CLI と GUI の動作差を作らず、core.py を共有しています。
- [ ] **Documentation**: Documentation (README, docs, docstrings) has been updated for public-facing changes (in English and Japanese where applicable). / 外部仕様の変更に伴い、ドキュメントを更新しました。
- [ ] **Test Execution**: Ran tests and lint locally:
  - `uv run python -m pytest -q`
  - `uv run ruff check`
