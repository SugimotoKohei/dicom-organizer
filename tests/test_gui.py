"""Tests for the PySide6 GUI and i18n support."""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path

import pytest
from pydicom.uid import generate_uid

from test_dicom_organizer import write_dicom


def _qt_app() -> object:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    require_gui = os.environ.get("DICOM_ORGANIZER_REQUIRE_GUI", "").strip() in ("1", "true", "yes")
    if require_gui:
        try:
            import PySide6.QtWidgets as widgets
        except ImportError as exc:
            pytest.fail(f"PySide6 is required when DICOM_ORGANIZER_REQUIRE_GUI=1: {exc}")
    else:
        widgets = pytest.importorskip("PySide6.QtWidgets")
    return widgets.QApplication.instance() or widgets.QApplication([])


JAPANESE_PATTERN = re.compile(r"[぀-ヿ一-鿿]")


DIALOG_MESSAGES: list[str] = []


@pytest.fixture(autouse=True)
def mock_messagebox(monkeypatch: pytest.MonkeyPatch) -> None:
    """H0: Prevent GUI tests from hanging on modal QMessageBox calls."""
    DIALOG_MESSAGES.clear()

    def fake_exec(self: object) -> int:
        title = getattr(self, "windowTitle", lambda: "")()
        text = getattr(self, "text", lambda: "")()
        DIALOG_MESSAGES.append(f"{title} {text}".strip())
        from PySide6.QtWidgets import QMessageBox

        return int(QMessageBox.StandardButton.Ok)

    def fake_static(*args: object, **kwargs: object) -> object:
        from PySide6.QtWidgets import QMessageBox

        msg = " ".join(str(a) for a in args[1:3]) if len(args) > 1 else ""
        DIALOG_MESSAGES.append(msg)
        return QMessageBox.StandardButton.Ok

    try:
        from PySide6.QtWidgets import QMessageBox

        monkeypatch.setattr(QMessageBox, "exec", fake_exec)
        for name in ("critical", "warning", "information", "question"):
            monkeypatch.setattr(QMessageBox, name, staticmethod(fake_static))
    except ImportError:
        pass


def _make_sample_input(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for num in (1, 2):
        s_uid = generate_uid()
        for inst in (1, 2):
            write_dicom(
                root / f"s{num}_{inst}.dcm",
                series_uid=s_uid,
                sop_uid=generate_uid(),
                series_number=num,
                instance_number=inst,
                modality="MR",
            )
    (root / "readme.txt").write_text("not dicom", encoding="utf-8")
    return root


def test_i18n_strings_and_reason_codes() -> None:
    """1. Verify i18n STRINGS have ja/en for all keys, and reason codes have translations."""
    from dicom_organizer import core, i18n

    assert tuple(i18n.SUPPORTED_LANGUAGES) == ("ja", "en")
    for key, texts in i18n.STRINGS.items():
        assert texts.get("ja", "").strip(), f"Missing ja for key: {key}"
        assert texts.get("en", "").strip(), f"Missing en for key: {key}"

    codes = list(core.SKIP_REASONS) + ["duplicate_conflict", "cancelled", "interrupted", "failed"]
    for code in codes:
        ja_label = i18n.reason_label(code, "ja")
        en_label = i18n.reason_label(code, "en")
        ja_help = i18n.reason_help(code, "ja")
        en_help = i18n.reason_help(code, "en")

        assert ja_label.strip() and en_label.strip()
        assert ja_help.strip() and en_help.strip()
        assert JAPANESE_PATTERN.search(ja_label), f"ja label not Japanese: {code}"
        assert not JAPANESE_PATTERN.search(en_label), f"en label contains Japanese: {code}"


def test_g8_reason_explanations_accuracy() -> None:
    """G8: Verify accuracy of reason explanations matching core behavior."""
    from dicom_organizer import i18n

    dup_help_ja = i18n.reason_help("duplicate_identical", "ja")
    assert "SOPInstanceUID" in dup_help_ja and "2 件目以降はコピーしませんでした" in dup_help_ja

    exist_help_ja = i18n.reason_help("existing_output", "ja")
    assert "同じ名前のファイルが既にあった" in exist_help_ja

    conflict_help_ja = i18n.reason_help("duplicate_conflict", "ja")
    assert "同じ SOPInstanceUID なのに内容が異なる" in conflict_help_ja and "番号" in conflict_help_ja


def test_g1_task_card_no_html_tags(tmp_path: Path) -> None:
    """G1, H1: Verify start buttons are TaskCard with plain title, description, and no overlap."""
    _qt_app()
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QLabel

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.show()
        for task in gui.TASKS:
            btn = window.task_buttons[task]
            assert isinstance(btn, gui.TaskCard), f"{task} is not TaskCard"
            title = btn.text()
            assert "<" not in title and ">" not in title and "<b>" not in title
            assert btn.description().strip()
            assert isinstance(btn.title_label, QLabel)
            assert isinstance(btn.description_label, QLabel)
            assert not btn.title_label.geometry().intersects(btn.description_label.geometry())
        assert not window.start_sample_hint_label.isHidden()
        assert "架空" in window.start_sample_hint_label.text()
    finally:
        window.close()


def test_g2_advanced_options_collapsed_by_default(tmp_path: Path) -> None:
    """G2: Verify advanced options are collapsed by default and toggleable."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("organize")
        window.show()
        assert window.advanced_content.isHidden()
        assert not window.advanced_content.isVisible()

        window.advanced_toggle_button.click()
        assert not window.advanced_content.isHidden()
        assert window.advanced_content.isVisible()

        window.advanced_toggle_button.click()
        assert window.advanced_content.isHidden()
        assert not window.advanced_content.isVisible()
    finally:
        window.close()


def test_g3_fixed_action_bar_and_scroll_on_completion(tmp_path: Path) -> None:
    """G3: Verify fixed bottom action bar and scroll area."""
    _qt_app()
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QScrollArea, QWidget

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        assert isinstance(window.scroll_area, QScrollArea)
        assert isinstance(window.action_bar, QWidget)
        assert window.run_button.parent() == window.action_bar
        assert window.progress_bar.parent() == window.action_bar
    finally:
        window.close()


def test_g4_counts_breakdown_table(tmp_path: Path) -> None:
    """G4: Verify counts breakdown table has 7 informative rows."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import core, gui

    input_dir = _make_sample_input(tmp_path / "in")
    output_dir = tmp_path / "out"
    result = core.run(core.OrganizeOptions(input_root=input_dir, output_root=output_dir))

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("organize")
        window.show_result(result)

        assert window.counts_table.rowCount() == 8
        items = [window.counts_table.item(r, 0).text() for r in range(8)]
        assert not any("件）" in it for it in items)
        assert any("整理したファイル" in it for it in items)
        assert any("一覧に載せた画像" in it for it in items)
        assert any("シリーズ数" in it for it in items)
        assert any("一覧に載せたシリーズ" in it for it in items)
        assert any("検査数" in it for it in items)
        assert any("未処理" in it for it in items)

        # In list-only mode
        list_res = core.run(core.OrganizeOptions(input_root=input_dir, output_root=tmp_path / "out_list", list_only=True))
        window.select_task("list")
        window.show_result(list_res)
        items_list = [window.counts_table.item(r, 0).text() for r in range(8)]
        assert not any("件）" in it for it in items_list)
        vals_list = [window.counts_table.item(r, 1).text() for r in range(8)]
        assert "0" in vals_list
    finally:
        window.close()


def test_g5_gui_source_has_no_missing_tr_or_hardcoded_messagebox_titles() -> None:
    """G5: Source static audit ensuring all tr keys exist and no hardcoded QMessageBox titles."""
    from dicom_organizer import i18n

    gui_file = Path(__file__).resolve().parents[1] / "src" / "dicom_organizer" / "gui.py"
    gui_code = gui_file.read_text(encoding="utf-8")

    tr_keys = re.findall(r"tr\([\"\']([a-zA-Z0-9_]+)[\"\']", gui_code)
    missing = [k for k in set(tr_keys) if k not in i18n.STRINGS]
    assert not missing, f"Missing i18n keys: {missing}"

    hardcoded = re.findall(r"QMessageBox\.[a-zA-Z]+\(\s*self,\s*[\"\']([^\"\']+)[\"\']", gui_code)
    assert not hardcoded, f"Hardcoded QMessageBox titles found: {hardcoded}"


def test_g6_failure_error_messages_and_resume_button(tmp_path: Path) -> None:
    """G6: Verify user-friendly error handling and resume button visibility on failure."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.show()
        window.result_summary_label.setText("完了しました。前回成功。")
        assert not window.resume_button.isVisible()

        window._run_failed("FileExistsError", "file already exists", "traceback...")
        assert "エラー" in window.result_summary_label.text()
        assert "完了しました" not in window.result_summary_label.text()
        assert not window.resume_button.isHidden()
    finally:
        window.close()


def test_g7_progress_stage_display() -> None:
    """G7: Verify stage_text recognizes 'write' and terminal states."""
    from dicom_organizer import i18n

    msg_ja = i18n.stage_text("write", 1, 10, "ja")
    assert "表とレポートを書いています" in msg_ja
    msg_en = i18n.stage_text("write", 1, 10, "en")
    assert "Writing" in msg_en


def test_g9_series_preview_table_order_and_columns(tmp_path: Path) -> None:
    """G9: Verify series table preserves summary row order, active columns, and tooltips."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import core, gui

    input_dir = _make_sample_input(tmp_path / "in")
    output_dir = tmp_path / "out"
    result = core.run(core.OrganizeOptions(input_root=input_dir, output_root=output_dir))

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("organize")
        window.show_result(result)

        assert window.series_table.rowCount() == 2
        assert "2 件" in window.series_table_title.text()

        # Check tooltips on headers
        header_item = window.series_table.horizontalHeaderItem(0)
        assert header_item is not None
        # StudyFolder description
        assert "検査" in header_item.toolTip() or "Study" in header_item.toolTip()
    finally:
        window.close()


def test_g10_window_minimum_size_hint(tmp_path: Path) -> None:
    """G10: Verify window minimum size hint width does not exceed 1100 in ja and en."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    for lang in ("ja", "en"):
        settings = QSettings(str(tmp_path / f"settings_{lang}.ini"), QSettings.Format.IniFormat)
        window = gui.MainWindow(settings=settings, language=lang)
        try:
            window.show()
            hint_w = window.minimumSizeHint().width()
            assert hint_w <= 1100, f"minimumSizeHint width={hint_w} for {lang}"
        finally:
            window.close()


def test_g11_work_page_sample_data_preserves_task(tmp_path: Path) -> None:
    """G11: Verify sample data on work page preserves current goal/task."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("preview")
        assert window.current_task == "preview"

        # Work page sample button preserves task
        window.work_sample_button.click()
        assert window.current_task == "preview"
        assert window.input_edit.text().strip()

        # Start page sample button switches to list
        window.select_task("organize")
        window.stack.setCurrentIndex(0)
        window.start_sample_button.click()
        assert window.current_task == "list"
    finally:
        window.close()


def test_g12_privacy_panel_title_and_visibility(tmp_path: Path) -> None:
    """G12: Verify privacy panel title is visibly displayed."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        assert not window.privacy_title_label.isHidden()
        assert "患者情報" in window.privacy_title_label.text()
    finally:
        window.close()


def test_start_page_buttons_and_language_switch(tmp_path: Path) -> None:
    """2. Verify start page task buttons and language switching retranslates UI."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        assert window.stack.currentIndex() == 0
        assert set(window.task_buttons.keys()) == set(gui.TASKS)

        ja_text = window.task_buttons["list"].text()
        assert "撮像条件を一覧にする" in ja_text
        assert "コピーして整理する" in window.task_buttons["organize"].text()
        assert "整理前に内容を確認する" in window.task_buttons["preview"].text()

        window.set_language("en")
        en_text = window.task_buttons["list"].text()
        assert not JAPANESE_PATTERN.search(en_text)

        window.select_task("organize")
        assert window.stack.currentIndex() == 1
        assert "Organizing" in window.run_button.text()

        window.set_language("ja")
        assert "整理を開始" in window.run_button.text()
    finally:
        window.close()


def test_task_options_and_auto_output_destination(tmp_path: Path) -> None:
    """3. Verify task options (list_only, action, dry_run) and default output paths."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    input_dir = _make_sample_input(tmp_path / "in")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("list")
        window.set_input_path(input_dir)
        assert Path(window.output_edit.text()) == input_dir / "organized_list"
        opts = window.build_options()
        assert opts.list_only is True

        window.select_task("organize")
        assert Path(window.output_edit.text()) == input_dir / "organized"
        opts = window.build_options()
        assert opts.list_only is False and opts.action == "copy" and opts.dry_run is False

        window.select_task("preview")
        opts = window.build_options()
        assert opts.dry_run is True

        manual_out = tmp_path / "custom_out"
        window.output_edit.setText(str(manual_out))
        window.output_edit.textEdited.emit(str(manual_out))
        window.select_task("list")
        window.set_input_path(input_dir)
        assert Path(window.output_edit.text()) == manual_out
    finally:
        window.close()


def test_handle_dropped_paths(tmp_path: Path) -> None:
    """4. Verify handle_dropped_paths accepts folders and file parents."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    input_dir = _make_sample_input(tmp_path / "in")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        assert window.handle_dropped_paths([input_dir]) is True
        assert Path(window.input_edit.text()) == input_dir

        file_path = input_dir / "readme.txt"
        assert window.handle_dropped_paths([file_path]) is True
        assert Path(window.input_edit.text()) == input_dir

        assert window.handle_dropped_paths([]) is False
    finally:
        window.close()


def test_use_sample_data(tmp_path: Path) -> None:
    """5. Verify sample data creation sets input and displays fictitious note."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        sample_path = window.use_sample_data()
        assert Path(window.input_edit.text()) == sample_path
        assert (sample_path / "EXPORT").is_dir()
        assert not window.sample_note_label.isHidden()
        assert "架空" in window.sample_note_label.text()
    finally:
        window.close()


def test_privacy_panel_always_visible(tmp_path: Path) -> None:
    """6. Verify privacy panel remains visible across keep/hash/drop modes."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui, messages

    input_dir = _make_sample_input(tmp_path / "in")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("organize")
        window.set_input_path(input_dir)
        for mode in ("keep", "hash", "drop"):
            idx = window.patient_combo.findData(mode)
            window.patient_combo.setCurrentIndex(idx)
            text = window.privacy_label.text()
            assert not window.privacy_label.isHidden()
            assert messages.notice_text("dicom_files_unchanged", "ja") in text
            assert messages.notice_text("csv_other_identifiers", "ja") in text

        idx = window.patient_combo.findData("drop")
        window.patient_combo.setCurrentIndex(idx)
        assert messages.notice_text("csv_patient_fields_dropped", "ja") in window.privacy_label.text()

        window.select_task("list")
        assert messages.notice_text("no_dicom_copies", "ja") in window.privacy_label.text()
    finally:
        window.close()


def test_settings_persistence(tmp_path: Path) -> None:
    """7. Verify settings are saved and restored in another instance."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    settings_file = tmp_path / "persist.ini"
    first = gui.MainWindow(
        settings=QSettings(str(settings_file), QSettings.Format.IniFormat), language="ja"
    )
    try:
        first.select_task("organize")
        idx_p = first.patient_combo.findData("drop")
        first.patient_combo.setCurrentIndex(idx_p)
        idx_l = first.layout_combo.findData("study")
        first.layout_combo.setCurrentIndex(idx_l)
        first.set_language("en")
        first.save_settings()
    finally:
        first.close()

    second = gui.MainWindow(
        settings=QSettings(str(settings_file), QSettings.Format.IniFormat)
    )
    try:
        assert second.patient_combo.currentData() == "drop"
        assert second.layout_combo.currentData() == "study"
        assert second.language == "en"
    finally:
        second.close()


def test_progress_and_cancel(tmp_path: Path) -> None:
    """8. Verify progress events update bar/label and cancel_event is set."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import core, gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("organize")
        window.on_progress(core.ProgressEvent("copy", 7, 10))
        assert window.progress_bar.maximum() == 10
        assert window.progress_bar.value() == 7
        assert "7" in window.stage_label.text() and "10" in window.stage_label.text()

        window.on_progress(core.ProgressEvent("discover", 2500, None))
        assert window.progress_bar.maximum() == 0
        assert "2,500" in window.stage_label.text()

        window.cancel_event = threading.Event()
        window.request_cancel()
        assert window.cancel_event.is_set()
    finally:
        window.close()


def test_show_result_with_synthetic_run(tmp_path: Path) -> None:
    """9. Verify show_result populates summary conclusion, reason table, and buttons."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import core, gui, i18n

    input_dir = _make_sample_input(tmp_path / "in")
    output_dir = tmp_path / "out"
    result = core.run(core.OrganizeOptions(input_root=input_dir, output_root=output_dir))

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("organize")
        window.set_input_path(input_dir)
        window.show_result(result)

        summary_text = window.result_summary_label.text()
        assert "4" in summary_text
        assert JAPANESE_PATTERN.search(summary_text)

        rows = {
            window.reason_table.item(r, 0).text(): window.reason_table.item(r, 1).text()
            for r in range(window.reason_table.rowCount())
        }
        assert rows.get(i18n.reason_label("not_dicom", "ja")) == "1"
        assert window.series_table.rowCount() == 2
        assert window.open_output_button.isEnabled()
        assert window.open_series_csv_button.isEnabled()
        assert window.open_report_button.isEnabled()

        preview_result = core.run(
            core.OrganizeOptions(input_root=input_dir, output_root=tmp_path / "never"),
            dry_run=True,
        )
        window.select_task("preview")
        window.show_result(preview_result)
        assert not window.open_series_csv_button.isEnabled()
        assert window.organize_now_button.isEnabled() and not window.organize_now_button.isHidden()
    finally:
        window.close()


def test_config_file_export_and_import(tmp_path: Path) -> None:
    """10. Verify settings file export and load round-trip."""
    _qt_app()
    import tomllib
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    config_path = tmp_path / "cfg.toml"
    first = gui.MainWindow(
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
        language="ja",
    )
    try:
        first.select_task("organize")
        idx_p = first.patient_combo.findData("hash")
        first.patient_combo.setCurrentIndex(idx_p)
        idx_l = first.layout_combo.findData("patient-study")
        first.layout_combo.setCurrentIndex(idx_l)
        first.export_settings_file(config_path)
    finally:
        first.close()

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed.get("patient_mode") == "hash"
    assert parsed.get("layout") == "patient-study"

    second = gui.MainWindow(
        settings=QSettings(str(tmp_path / "settings2.ini"), QSettings.Format.IniFormat),
        language="ja",
    )
    try:
        second.select_task("organize")
        second.load_settings_file(config_path)
        assert second.patient_combo.currentData() == "hash"
        assert second.layout_combo.currentData() == "patient-study"
    finally:
        second.close()


def test_copy_diagnostics_sanitizes_home(tmp_path: Path) -> None:
    """11. Verify copy_diagnostics does not leak home directory path."""
    _qt_app()
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        text = window.copy_diagnostics()
        assert "dicom-organizer:" in text
        assert str(Path.home()) not in text
        assert QApplication.clipboard().text() == text
    finally:
        window.close()


def test_main_cli_subcommands() -> None:
    """12. Verify gui.main --self-test, --version, and --diagnostics without creating GUI."""
    from dicom_organizer import gui

    assert gui.main(["--self-test"]) == 0
    assert gui.main(["--version"]) == 0
    assert gui.main(["--diagnostics"]) == 0
    assert gui.main(["--help"]) == 0


def test_font_scale_large(tmp_path: Path) -> None:
    """13. Verify font scale toggles font size by 1.25x."""
    _qt_app()
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from dicom_organizer import gui

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.set_font_scale("normal")
        base_size = QApplication.font().pointSizeF()
        window.set_font_scale("large")
        large_size = QApplication.font().pointSizeF()
        assert abs(large_size - base_size * 1.25) < 0.6
        window.set_font_scale("normal")
        assert abs(QApplication.font().pointSizeF() - base_size) < 0.1
    finally:
        window.close()


def test_h7_safe_persistence_no_carryover_of_move_or_overwrite(tmp_path: Path) -> None:
    """H7: Verify move action and overwrite if_exists are never carried over to next session."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    ini_path = tmp_path / "persist_danger.ini"
    first = gui.MainWindow(
        settings=QSettings(str(ini_path), QSettings.Format.IniFormat), language="ja"
    )
    try:
        first.select_task("organize")
        idx_m = first.action_combo.findData("move")
        first.action_combo.setCurrentIndex(idx_m)
        idx_o = first.exists_combo.findData("overwrite")
        first.exists_combo.setCurrentIndex(idx_o)
        first.save_settings()
    finally:
        first.close()

    second = gui.MainWindow(
        settings=QSettings(str(ini_path), QSettings.Format.IniFormat), language="ja"
    )
    try:
        assert second.action_combo.currentData() == "copy"
        assert second.exists_combo.currentData() == "error"
    finally:
        second.close()


def test_h8_execution_guards_and_input_validation(tmp_path: Path) -> None:
    """H8: Verify concurrent runs are blocked, invalid inputs prompt error dialogs, and close confirmation."""
    _qt_app()
    import time
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QCloseEvent

    from dicom_organizer import gui

    in_dir = _make_sample_input(tmp_path / "in")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = gui.MainWindow(settings=settings, language="ja")
    try:
        window.select_task("list")
        window.set_input_path(in_dir)
        window.start_run()
        worker = window.worker
        window._on_run_clicked()
        window.start_run()
        assert window.worker is worker

        # Close while running: should prompt dialog
        event = QCloseEvent()
        window.closeEvent(event)
        # Event is accepted in test because mock_messagebox returns Ok, and cancel_event is set
        assert window.cancel_event is not None and window.cancel_event.is_set()

        # Wait for thread to finish
        end = time.monotonic() + 10.0
        while window.is_running and time.monotonic() < end:
            from PySide6.QtWidgets import QApplication

            QApplication.processEvents()
            time.sleep(0.02)

        # Invalid limit input
        DIALOG_MESSAGES.clear()
        window.limit_edit.setText("invalid_number")
        window._on_run_clicked()
        assert not window.is_running
        assert any("上限" in msg or "Limit" in msg for msg in DIALOG_MESSAGES)
    finally:
        window.close()


def test_h9_advanced_settings_and_geometry_persistence(tmp_path: Path) -> None:
    """H9: Verify advanced settings expansion state, geometry, and last_browse_dir persistence."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    ini_path = tmp_path / "persist_adv.ini"
    first = gui.MainWindow(
        settings=QSettings(str(ini_path), QSettings.Format.IniFormat), language="ja"
    )
    try:
        first.select_task("organize")
        first.advanced_toggle_button.click()
        assert not first.advanced_content.isHidden()
        first._last_browse_dir = tmp_path / "some_dir"
        first.resize(1200, 800)
        first.save_settings()
    finally:
        first.close()

    second = gui.MainWindow(
        settings=QSettings(str(ini_path), QSettings.Format.IniFormat), language="ja"
    )
    try:
        assert not second.advanced_content.isHidden()
        assert getattr(second, "_last_browse_dir", None) == tmp_path / "some_dir"
    finally:
        second.close()


def test_h10_load_settings_file_switches_list_only(tmp_path: Path) -> None:
    """H10: Verify loading config with list_only toggles task between list and organize."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import gui

    window = gui.MainWindow(
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
        language="ja",
    )
    try:
        window.select_task("organize")
        cfg_list = tmp_path / "list_true.toml"
        cfg_list.write_text("list_only = true\n", encoding="utf-8")
        window.load_settings_file(cfg_list)
        assert window.current_task == "list"

        cfg_org = tmp_path / "list_false.toml"
        cfg_org.write_text("list_only = false\n", encoding="utf-8")
        window.load_settings_file(cfg_org)
        assert window.current_task == "organize"
    finally:
        window.close()


def test_j1_conclusion_counts_matches_csv_and_image_series(tmp_path: Path) -> None:
    """J1: Verify conclusion text uses csv_target_files and image series count."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import core, gui

    input_dir = _make_sample_input(tmp_path / "in")
    output_dir = tmp_path / "out"
    result = core.run(core.OrganizeOptions(input_root=input_dir, output_root=output_dir, list_only=True))

    window = gui.MainWindow(
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
        language="ja",
    )
    try:
        window.show_result(result)
        text = window.result_summary_label.text()
        assert f"{result.summary['csv_target_files']:,} 件の画像" in text
        assert f"{len(window.series_table.rowCount() * [1]):,} シリーズ" in text
    finally:
        window.close()


def test_j4_results_placeholder_and_reset_on_task_switch(tmp_path: Path) -> None:
    """J4: Verify results placeholder is visible before run and tables are hidden."""
    _qt_app()
    from PySide6.QtCore import QSettings

    from dicom_organizer import core, gui

    window = gui.MainWindow(
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
        language="ja",
    )
    try:
        window.select_task("list")
        assert window.counts_table.isHidden()
        assert window.series_table.isHidden()
        assert not window.result_placeholder_label.isHidden()
        assert "実行すると" in window.result_placeholder_label.text()

        # After showing result, tables become visible
        input_dir = _make_sample_input(tmp_path / "in")
        output_dir = tmp_path / "out"
        result = core.run(core.OrganizeOptions(input_root=input_dir, output_root=output_dir, list_only=True))
        window.show_result(result)
        assert not window.counts_table.isHidden()
        assert not window.series_table.isHidden()
        assert window.result_placeholder_label.isHidden()

        # Switching task resets to placeholder
        window.select_task("organize")
        assert window.counts_table.isHidden()
        assert window.series_table.isHidden()
        assert not window.result_placeholder_label.isHidden()
    finally:
        window.close()


def test_j7_j8_font_scale_and_form_growth(tmp_path: Path) -> None:
    """J7, J8: Verify no pixel font sizes, font scaling on conclusion, and form layout growth."""
    _qt_app()
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QFontInfo
    from PySide6.QtWidgets import QFormLayout

    from dicom_organizer import gui

    source = Path(gui.__file__).read_text(encoding="utf-8")
    assert not re.search(r"font-size:\s*\d+(\.\d+)?px", source)

    window = gui.MainWindow(
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
        language="ja",
    )
    try:
        layouts = window.findChildren(QFormLayout)
        assert layouts
        for layout in layouts:
            assert layout.fieldGrowthPolicy() == QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow

        window.set_font_scale("normal")
        normal_pt = QFontInfo(window.result_summary_label.font()).pointSizeF()
        window.set_font_scale("large")
        large_pt = QFontInfo(window.result_summary_label.font()).pointSizeF()
        assert large_pt > normal_pt
        assert window.result_summary_label.font().bold()
    finally:
        window.close()


def test_k1_secondary_text_contrast_and_palette_change(tmp_path: Path) -> None:
    """K1: Verify secondary text contrast >= 4.5 in dark mode and palette change handling."""
    app = _qt_app()
    from PySide6.QtCore import QEvent, QPoint, QRect, QSettings
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QLabel

    from dicom_organizer import gui

    source = Path(gui.__file__).read_text(encoding="utf-8")
    assert "palette(placeholder-text)" not in source

    dark_palette = QPalette()
    roles = QPalette.ColorRole
    for role, rgb in (
        (roles.Window, (50, 50, 50)),
        (roles.WindowText, (230, 230, 230)),
        (roles.Base, (30, 30, 30)),
        (roles.AlternateBase, (40, 40, 40)),
        (roles.Text, (230, 230, 230)),
        (roles.Button, (80, 80, 80)),
        (roles.ButtonText, (230, 230, 230)),
        (roles.PlaceholderText, (92, 92, 92)),
        (roles.Mid, (70, 70, 70)),
        (roles.Dark, (35, 35, 35)),
        (roles.Light, (110, 110, 110)),
        (roles.Highlight, (0, 100, 220)),
        (roles.HighlightedText, (255, 255, 255)),
    ):
        dark_palette.setColor(role, QColor(*rgb))

    orig_palette = app.palette()
    try:
        app.setPalette(dark_palette)
        window = gui.MainWindow(
            settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
            language="ja",
        )
        window.resize(1280, 860)
        try:
            window.show()
            app.processEvents()

            start = window.stack.widget(0)
            labels = [lab for lab in start.findChildren(QLabel) if lab.text().strip() and not lab.isHidden()]
            assert labels

            from collections import Counter

            for lab in labels:
                container = lab.parentWidget()
                rect = QRect(lab.mapTo(container, QPoint(0, 0)), lab.size())
                image = container.grab(rect).toImage()
                colors: Counter[int] = Counter()
                for y in range(image.height()):
                    for x in range(0, image.width(), 2):
                        colors[image.pixel(x, y) & 0xFFFFFF] += 1
                bg = QColor(colors.most_common(1)[0][0])
                lb = gui.relative_luminance(bg)
                best = 1.0
                for rgb in colors:
                    lp = gui.relative_luminance(QColor(rgb))
                    best = max(best, (max(lp, lb) + 0.05) / (min(lp, lb) + 0.05))
                assert best >= 4.5, f"Label '{lab.text()[:15]}' contrast {best:.2f} < 4.5"

            # Verify dynamic palette change updates
            orig_card_color = window.task_buttons["list"].title_label.styleSheet()
            window.changeEvent(QEvent(QEvent.Type.PaletteChange))
            new_card_color = window.task_buttons["list"].title_label.styleSheet()
            assert new_card_color == orig_card_color
        finally:
            window.close()
    finally:
        app.setPalette(orig_palette)


def test_gui_smoke_test_cli(tmp_path: Path) -> None:
    """Verify --gui-smoke-test and --gui-smoke-test-report via CLI execution."""
    import subprocess
    import sys

    report_path = tmp_path / "gui_smoke_report.txt"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    res = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from dicom_organizer.gui import main; "
            f"sys.exit(main(['--gui-smoke-test', '--gui-smoke-test-report', {str(report_path)!r}]))",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert res.returncode == 0, f"exit={res.returncode}\nstderr={res.stderr}"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "[PASS]" in content
    assert "gui-smoke-test: 1/1 checks passed" in content


