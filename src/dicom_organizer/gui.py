"""PySide6 GUI for dicom-organizer."""

from __future__ import annotations

import argparse
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import dicom_organizer.core as core
from dicom_organizer import columns, i18n, messages

try:
    from PySide6.QtCore import (
        QEvent,
        QEventLoop,
        QLocale,
        QObject,
        QPoint,
        QRectF,
        QSettings,
        QSize,
        Qt,
        QThread,
        QTimer,
        QUrl,
        Signal,
    )
    from PySide6.QtGui import (
        QAction,
        QBrush,
        QColor,
        QDesktopServices,
        QFont,
        QKeySequence,
        QPaintEvent,
        QPainter,
        QPalette,
        QPen,
        QShortcut,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QCommandLinkButton,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QStackedWidget,
        QStyle,
        QStyleOptionButton,
        QStylePainter,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    PYSIDE_IMPORT_ERROR: ImportError | None = exc

    class _MissingQt:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __call__(self, *args: object, **kwargs: object) -> "_MissingQt":
            return self

        def __getattr__(self, name: str) -> "_MissingQt":
            return self

    QEvent = _MissingQt
    QEventLoop = _MissingQt
    QLocale = _MissingQt
    QObject = _MissingQt
    QPoint = _MissingQt
    QRectF = _MissingQt
    QSettings = _MissingQt
    QSize = _MissingQt
    Qt = _MissingQt
    QThread = _MissingQt
    QTimer = _MissingQt
    QUrl = _MissingQt
    Signal = _MissingQt
    QAction = _MissingQt
    QBrush = _MissingQt
    QColor = _MissingQt
    QDesktopServices = _MissingQt
    QFont = _MissingQt
    QKeySequence = _MissingQt
    QPaintEvent = _MissingQt
    QPainter = _MissingQt
    QPalette = _MissingQt
    QPen = _MissingQt
    QShortcut = _MissingQt
    QApplication = _MissingQt
    QCheckBox = _MissingQt
    QComboBox = _MissingQt
    QCommandLinkButton = _MissingQt
    QDialog = _MissingQt
    QDialogButtonBox = _MissingQt
    QFileDialog = _MissingQt
    QFormLayout = _MissingQt
    QFrame = _MissingQt
    QGridLayout = _MissingQt
    QGroupBox = _MissingQt
    QHBoxLayout = _MissingQt
    QHeaderView = _MissingQt
    QLabel = _MissingQt
    QLineEdit = _MissingQt
    QMainWindow = _MissingQt
    QMessageBox = _MissingQt
    QProgressBar = _MissingQt
    QPushButton = _MissingQt
    QScrollArea = _MissingQt
    QStackedWidget = _MissingQt
    QStyle = _MissingQt
    QStyleOptionButton = _MissingQt
    QStylePainter = _MissingQt
    QTableWidget = _MissingQt
    QTableWidgetItem = _MissingQt
    QTextEdit = _MissingQt
    QVBoxLayout = _MissingQt
    QWidget = _MissingQt
else:
    PYSIDE_IMPORT_ERROR = None


TASKS: tuple[str, ...] = ("list", "organize", "preview")

DOCS_URL = "https://github.com/SugimotoKohei/dicom-organizer/blob/main/docs/README.md"
REPO_URL = "https://github.com/SugimotoKohei/dicom-organizer"
CONTACT_EMAIL = "sugimotokouhei@gmail.com"


def _channel_luminance(val: int) -> float:
    v = val / 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def relative_luminance(color: QColor) -> float:
    """Calculate relative luminance for WCAG contrast calculation."""
    return (
        0.2126 * _channel_luminance(color.red())
        + 0.7152 * _channel_luminance(color.green())
        + 0.0722 * _channel_luminance(color.blue())
    )


def contrast_ratio(c1: QColor, c2: QColor) -> float:
    """Calculate WCAG contrast ratio between two QColors."""
    l1 = relative_luminance(c1)
    l2 = relative_luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def blend_colors(fg: QColor, bg: QColor, fg_ratio: float) -> QColor:
    """Blend two QColors with the given fg ratio."""
    r = int(round(fg.red() * fg_ratio + bg.red() * (1.0 - fg_ratio)))
    g = int(round(fg.green() * fg_ratio + bg.green() * (1.0 - fg_ratio)))
    b = int(round(fg.blue() * fg_ratio + bg.blue() * (1.0 - fg_ratio)))
    return QColor(r, g, b)


def compute_secondary_text_color(
    palette: QPalette,
    fg_role: QPalette.ColorRole = QPalette.ColorRole.WindowText,
    bg_role: QPalette.ColorRole | QColor = QPalette.ColorRole.Window,
    min_contrast: float = 4.8,
) -> QColor:
    """Compute secondary text color by blending fg and bg, ensuring contrast >= min_contrast."""
    fg = palette.color(fg_role)
    if isinstance(bg_role, QColor):
        bg = bg_role
    else:
        bg = palette.color(bg_role)
    ratio = 0.70
    color = blend_colors(fg, bg, ratio)
    while contrast_ratio(color, bg) < min_contrast and ratio < 0.98:
        ratio += 0.02
        color = blend_colors(fg, bg, ratio)
    if contrast_ratio(color, bg) < min_contrast and contrast_ratio(fg, bg) >= min_contrast:
        color = fg
    return color


def _scaled_font(base_font: QFont, factor: float, *, bold: bool = False) -> QFont:
    """Scale a font by a factor, preserving either point size or pixel size (G1)."""
    font = QFont(base_font)
    if bold:
        font.setBold(True)
    if base_font.pointSizeF() > 0:
        font.setPointSizeF(base_font.pointSizeF() * factor)
    elif base_font.pixelSize() > 0:
        font.setPixelSize(round(base_font.pixelSize() * factor))
    else:
        font.setPointSizeF(12.0 * factor)
    return font


class TaskCard(QPushButton):
    """Card-style button with separated title and description labels (H1)."""

    def __init__(self, task: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task = task
        self.setCheckable(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 14, 18, 14)
        self._layout.setSpacing(6)

        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.update_font_sizes()
        self.update_palette_colors()

        self._layout.addWidget(self.title_label)
        self._layout.addWidget(self.description_label)

    def card_background_color(
        self,
        palette: QPalette | None = None,
        state: str | None = None,
    ) -> QColor:
        """Compute card background color from palette for given or current state."""
        pal = palette or self.palette()
        base_bg = pal.color(QPalette.ColorRole.Button)
        light_color = pal.color(QPalette.ColorRole.Light)
        dark_color = pal.color(QPalette.ColorRole.Dark)
        window_bg = pal.color(QPalette.ColorRole.Window)

        if state is None:
            if not self.isEnabled():
                state = "disabled"
            elif self.isDown():
                state = "pressed"
            elif self.underMouse():
                state = "hover"
            else:
                state = "normal"

        if state == "disabled":
            return blend_colors(window_bg, base_bg, 0.5)
        if state == "pressed":
            return blend_colors(dark_color, base_bg, 0.15)
        if state == "hover":
            return blend_colors(light_color, base_bg, 0.15)
        return base_bg

    def update_palette_colors(self, palette: QPalette | None = None) -> None:
        """Update title and description colors dynamically based on card background (K1)."""
        pal = palette or self.palette()
        card_bg = self.card_background_color(pal, state="normal")
        btn_fg = pal.color(QPalette.ColorRole.ButtonText)
        is_dark = relative_luminance(card_bg) < 0.5

        if is_dark:
            white = QColor(255, 255, 255)
            title_color = white if contrast_ratio(white, card_bg) >= 4.5 else btn_fg
            desc_color = compute_secondary_text_color(
                pal,
                fg_role=QPalette.ColorRole.ButtonText,
                bg_role=card_bg,
                min_contrast=6.0,
            )
        else:
            title_color = btn_fg
            desc_color = compute_secondary_text_color(
                pal,
                fg_role=QPalette.ColorRole.ButtonText,
                bg_role=card_bg,
                min_contrast=6.0,
            )

        if contrast_ratio(title_color, card_bg) < 4.5:
            title_color = btn_fg
        if contrast_ratio(desc_color, card_bg) < 6.0:
            if contrast_ratio(btn_fg, card_bg) >= 6.0:
                desc_color = btn_fg
            elif is_dark:
                white = QColor(255, 255, 255)
                if contrast_ratio(white, card_bg) >= 6.0:
                    ratio = 0.70
                    cand = blend_colors(white, card_bg, ratio)
                    while contrast_ratio(cand, card_bg) < 6.0 and ratio < 0.98:
                        ratio += 0.02
                        cand = blend_colors(white, card_bg, ratio)
                    desc_color = cand if contrast_ratio(cand, card_bg) >= 6.0 else white
                else:
                    desc_color = btn_fg
            else:
                black = QColor(0, 0, 0)
                if contrast_ratio(black, card_bg) >= 6.0:
                    ratio = 0.70
                    cand = blend_colors(black, card_bg, ratio)
                    while contrast_ratio(cand, card_bg) < 6.0 and ratio < 0.98:
                        ratio += 0.02
                        cand = blend_colors(black, card_bg, ratio)
                    desc_color = cand if contrast_ratio(cand, card_bg) >= 6.0 else black
                else:
                    desc_color = btn_fg

        self.title_label.setStyleSheet(f"QLabel {{ color: {title_color.name()}; }}")
        self.description_label.setStyleSheet(f"QLabel {{ color: {desc_color.name()}; }}")

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self.update_palette_colors()

    def set_content(self, title: str, description: str) -> None:
        self.title_label.setText(title)
        self.description_label.setText(description)
        self.setAccessibleName(title)
        self.setAccessibleDescription(description)

    def text(self) -> str:
        return self.title_label.text()

    def description(self) -> str:
        return self.description_label.text()

    def update_font_sizes(self) -> None:
        app_font = QApplication.font()
        self.title_label.setFont(_scaled_font(app_font, 1.15, bold=True))
        self.description_label.setFont(_scaled_font(app_font, 1.0))

    def enterEvent(self, event: Any) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event: Any) -> None:
        super().leaveEvent(event)
        self.update()

    def focusInEvent(self, event: Any) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event: Any) -> None:
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 6.0

        bg_color = self.card_background_color()
        painter.setBrush(QBrush(bg_color))

        pal = self.palette()
        if self.hasFocus():
            border_color = pal.color(QPalette.ColorRole.Highlight)
            pen = QPen(border_color, 2.0)
            rect = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        elif self.underMouse() and self.isEnabled():
            border_color = blend_colors(
                pal.color(QPalette.ColorRole.Highlight),
                pal.color(QPalette.ColorRole.Mid),
                0.4,
            )
            pen = QPen(border_color, 1.0)
        else:
            border_color = pal.color(QPalette.ColorRole.Mid)
            pen = QPen(border_color, 1.0)

        painter.setPen(pen)
        painter.drawRoundedRect(rect, radius, radius)

    def sizeHint(self) -> QSize:
        return self._layout.sizeHint()

    def minimumSizeHint(self) -> QSize:
        return self._layout.minimumSize()


BASE_SERIES_COLUMNS: list[str] = [
    "StudyFolder",
    "SeriesNumber",
    "SeriesDescription",
    "Modality",
    "ManufacturerModelName",
    "FileCount",
]

OPTIONAL_SERIES_COLUMNS: list[str] = [
    "TR_ms",
    "TE_ms",
    "FlipAngle_deg",
    "SliceThickness_mm",
    "Matrix_RowsxCols",
    "FOV_HxW_mm",
    "ScanDuration",
    "KVP_kV",
]


class RunWorker(QObject):
    """Worker object to run core.run() in a background QThread with throttled progress."""

    progress_signal = Signal(object)
    finished_signal = Signal(object)
    failed_signal = Signal(str, str, str)  # exc_type, message, details

    def __init__(self, options: core.OrganizeOptions, cancel_event: threading.Event) -> None:
        super().__init__()
        self.options = options
        self.cancel_event = cancel_event
        self._last_emit_time = 0.0

    def _on_progress(self, event: core.ProgressEvent) -> None:
        now = time.monotonic()
        is_terminal = (
            (event.total is not None and event.done >= event.total)
            or event.stage in ("write", "write_tables", "finalize")
        )
        if is_terminal or (now - self._last_emit_time >= 0.1):
            self._last_emit_time = now
            self.progress_signal.emit(event)

    def run(self) -> None:
        try:
            result = core.run(
                self.options,
                dry_run=self.options.dry_run,
                progress=self._on_progress,
                cancel_event=self.cancel_event,
            )
            self.finished_signal.emit(result)
        except Exception as exc:
            self.failed_signal.emit(type(exc).__name__, str(exc), traceback.format_exc())


class MainWindow(QMainWindow):
    """Main window with task-oriented workflow and fixed bottom action bar."""

    def __init__(
        self,
        settings: QSettings | None = None,
        language: str | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("dicom-organizer")
        self.resize(1120, 840)
        self.setAcceptDrops(True)

        if settings is not None:
            self.settings = settings
        else:
            self.settings = QSettings("dicom-organizer", "dicom-organizer")

        if language is not None:
            self.language = language
        else:
            saved_lang = self.settings.value("language", None)
            if saved_lang and saved_lang in i18n.SUPPORTED_LANGUAGES:
                self.language = str(saved_lang)
            else:
                system_locale = ""
                try:
                    system_locale = QLocale.system().name()
                except Exception:
                    pass
                self.language = i18n.default_language(system_locale)

        self._base_font_point_size: float = 12.0
        self._base_font_pixel_size: int = 0
        try:
            app_font = QApplication.font()
            pt = app_font.pointSizeF()
            px = app_font.pixelSize()
            if pt > 0:
                self._base_font_point_size = pt
            elif px > 0:
                self._base_font_pixel_size = px
        except Exception:
            pass

        self.font_scale: str = str(self.settings.value("font_scale", "normal"))
        if self.font_scale not in ("normal", "large"):
            self.font_scale = "normal"

        self.current_task: str = "list"
        self._output_manually_edited: bool = False
        self.cancel_event: threading.Event | None = None
        self.is_running: bool = False
        self.last_result: core.OrganizeResult | None = None
        self.last_output_root: Path | None = None
        self.thread: QThread | None = None
        self.worker: RunWorker | None = None

        self._init_widgets()
        self._build_ui()
        self._build_menu()
        self._setup_shortcuts()
        self._retranslate_ui()
        self._load_saved_options()
        self.set_font_scale(self.font_scale)
        self._update_secondary_colors()

    def _init_widgets(self) -> None:
        self.stack = QStackedWidget(self)

        # Start page widgets
        self.start_title_label = QLabel()
        self.start_title_label.setWordWrap(True)
        self.start_subtitle_label = QLabel()
        self.start_subtitle_label.setWordWrap(True)

        self.task_buttons: dict[str, TaskCard] = {
            "list": TaskCard("list"),
            "organize": TaskCard("organize"),
            "preview": TaskCard("preview"),
        }
        self.start_sample_button = QPushButton()
        self.start_sample_hint_label = QLabel()

        # Work page header
        self.current_task_label = QLabel()
        self.change_task_button = QPushButton()

        # Step 1: Input
        self.step1_group = QGroupBox()
        self.input_edit = QLineEdit()
        self.input_browse_button = QPushButton()
        self.work_sample_button = QPushButton()
        self.drop_hint_label = QLabel()
        self.drop_hint_label.setWordWrap(True)
        self.sample_note_label = QLabel()
        self.sample_note_label.setWordWrap(True)
        self.sample_note_label.setStyleSheet(
            "QLabel { color: #003a70; background: #e6f2fb; padding: 6px; "
            "border: 1px solid #9bc5e8; border-radius: 4px; }"
        )
        self.sample_note_label.setVisible(False)

        # Step 2: Output & Settings
        self.step2_group = QGroupBox()
        self.output_edit = QLineEdit()
        self.output_browse_button = QPushButton()
        self.patient_combo = QComboBox()
        self.layout_combo = QComboBox()

        # Privacy Panel
        self.privacy_panel_box = QWidget()
        privacy_box_layout = QVBoxLayout(self.privacy_panel_box)
        privacy_box_layout.setContentsMargins(8, 8, 8, 8)
        self.privacy_title_label = QLabel()
        self.privacy_title_label.setStyleSheet("QLabel { font-weight: bold; color: #4a2c00; background: transparent; }")
        self.privacy_label = QLabel()
        self.privacy_label.setWordWrap(True)
        self.privacy_label.setStyleSheet("QLabel { color: #4a2c00; background: transparent; }")
        privacy_box_layout.addWidget(self.privacy_title_label)
        privacy_box_layout.addWidget(self.privacy_label)
        self.privacy_panel_box.setStyleSheet(
            "QWidget#privacy_panel { background: #fff8e6; border: 1px solid #ebd08f; border-radius: 4px; } "
            "QWidget#privacy_panel QLabel { color: #4a2c00; background: transparent; }"
        )
        self.privacy_panel_box.setObjectName("privacy_panel")

        self.unsafe_warning_label = QLabel()
        self.unsafe_warning_label.setWordWrap(True)
        self.unsafe_warning_label.setStyleSheet(
            "QLabel { color: #5a0e0e; background: #fde7e7; padding: 6px; "
            "border: 1px solid #e08b8b; border-radius: 4px; }"
        )
        self.unsafe_warning_label.setVisible(False)

        # Collapsible Advanced Settings (G2)
        self.advanced_toggle_button = QPushButton()
        self.advanced_toggle_button.setFlat(True)
        self.advanced_toggle_button.setStyleSheet(
            "QPushButton { text-align: left; font-weight: bold; color: palette(link); padding: 4px 0; }"
        )
        self.advanced_content = QWidget()
        self.advanced_content.setVisible(False)

        self.action_combo = QComboBox()
        self.exists_combo = QComboBox()
        self.profile_combo = QComboBox()
        self.series_template_edit = QLineEdit(core.DEFAULT_SERIES_DIR_TEMPLATE)
        self.file_template_edit = QLineEdit(core.DEFAULT_FILE_TEMPLATE)
        self.limit_edit = QLineEdit("0")
        self.force_read_check = QCheckBox()
        self.force_read_check.setChecked(True)
        self.include_hidden_check = QCheckBox()
        self.include_organized_check = QCheckBox()
        self.checksum_check = QCheckBox()
        self.space_check_check = QCheckBox()
        self.space_check_check.setChecked(True)
        self.dicom_tags_edit = QLineEdit()

        # Step 4: Results
        self.step4_group = QGroupBox()
        self.result_placeholder_label = QLabel()
        self.result_placeholder_label.setWordWrap(True)
        self.result_summary_label = QLabel()
        self.result_summary_label.setWordWrap(True)
        self.result_summary_label.setStyleSheet("QLabel { font-weight: bold; padding: 4px; }")

        self.warnings_label = QLabel()
        self.warnings_label.setWordWrap(True)
        self.warnings_label.setStyleSheet(
            "QLabel { color: #5c2600; background: #fff1d6; padding: 6px; "
            "border: 1px solid #eec47d; border-radius: 4px; }"
        )
        self.warnings_label.setVisible(False)

        # G4: Counts breakdown table
        self.counts_table_title = QLabel()
        self.counts_table = QTableWidget(0, 3)
        self.counts_table.setAlternatingRowColors(True)
        self.counts_table.setWordWrap(True)
        self.counts_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.counts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.counts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.counts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Skip reasons table
        self.reason_table_title = QLabel()
        self.reason_table = QTableWidget(0, 3)
        self.reason_table.setWordWrap(True)
        self.reason_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.reason_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.reason_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.reason_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.reason_table.setAlternatingRowColors(True)

        # Series preview table (G9)
        self.series_table_title = QLabel()
        self.series_table = QTableWidget(0, len(BASE_SERIES_COLUMNS))
        self.series_table.setAlternatingRowColors(True)
        self.series_table.setSortingEnabled(False)

        self.open_output_button = QPushButton()
        self.open_output_button.setEnabled(False)
        self.open_series_csv_button = QPushButton()
        self.open_series_csv_button.setEnabled(False)
        self.open_report_button = QPushButton()
        self.open_report_button.setEnabled(False)
        self.organize_now_button = QPushButton()
        self.organize_now_button.setVisible(False)

        self.next_steps_title_label = QLabel()
        self.next_steps_body_label = QLabel()
        self.next_steps_body_label.setWordWrap(True)
        self.scope_note_label = QLabel()
        self.scope_note_label.setWordWrap(True)

        # G3: Fixed Bottom Action Bar
        self.action_bar = QWidget()
        self.step3_title_label = QLabel()
        self.step3_title_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.run_button = QPushButton()
        self.cancel_button = QPushButton()
        self.cancel_button.setEnabled(False)
        self.resume_button = QPushButton()
        self.resume_button.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.stage_label = QLabel()
        self.stage_label.setWordWrap(True)

    def _build_ui(self) -> None:
        # Build Start Page
        start_widget = QWidget()
        start_layout = QVBoxLayout(start_widget)
        start_layout.setContentsMargins(36, 36, 36, 36)
        start_layout.setSpacing(18)

        self.start_title_label.setStyleSheet("QLabel { font-weight: bold; }")
        start_layout.addWidget(self.start_title_label)
        start_layout.addWidget(self.start_subtitle_label)

        for task_id in TASKS:
            btn = self.task_buttons[task_id]
            btn.setMinimumHeight(64)
            start_layout.addWidget(btn)

        start_layout.addStretch()

        sample_box = QHBoxLayout()
        sample_box.addWidget(self.start_sample_button)
        sample_box.addWidget(self.start_sample_hint_label)
        sample_box.addStretch()
        start_layout.addLayout(sample_box)

        # Build Work Page Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        work_content = QWidget()
        work_layout = QVBoxLayout(work_content)
        work_layout.setContentsMargins(16, 16, 16, 16)
        work_layout.setSpacing(14)

        # Top Header
        header_box = QHBoxLayout()
        self.current_task_label.setStyleSheet("QLabel { font-weight: bold; }")
        header_box.addWidget(self.current_task_label)
        header_box.addStretch()
        header_box.addWidget(self.change_task_button)
        work_layout.addLayout(header_box)

        # Step 1: Input Layout
        s1_layout = QVBoxLayout(self.step1_group)
        s1_input_row = QHBoxLayout()
        s1_input_row.addWidget(self.input_edit, stretch=1)
        s1_input_row.addWidget(self.input_browse_button)
        s1_input_row.addWidget(self.work_sample_button)
        s1_layout.addLayout(s1_input_row)
        s1_layout.addWidget(self.drop_hint_label)
        s1_layout.addWidget(self.sample_note_label)
        work_layout.addWidget(self.step1_group)

        # Step 2: Output & Settings
        s2_layout = QVBoxLayout(self.step2_group)
        s2_form = QFormLayout()
        s2_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        s2_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit, stretch=1)
        out_row.addWidget(self.output_browse_button)
        self.out_label = QLabel()
        s2_form.addRow(self.out_label, out_row)
        self.patient_label = QLabel()
        s2_form.addRow(self.patient_label, self.patient_combo)
        self.layout_label = QLabel()
        s2_form.addRow(self.layout_label, self.layout_combo)
        s2_layout.addLayout(s2_form)

        s2_layout.addWidget(self.privacy_panel_box)
        s2_layout.addWidget(self.unsafe_warning_label)

        # Advanced options toggle & content (G2)
        s2_layout.addWidget(self.advanced_toggle_button)

        adv_layout = QFormLayout(self.advanced_content)
        adv_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        adv_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.action_label = QLabel()
        adv_layout.addRow(self.action_label, self.action_combo)
        self.exists_label = QLabel()
        adv_layout.addRow(self.exists_label, self.exists_combo)
        self.profile_label = QLabel()
        adv_layout.addRow(self.profile_label, self.profile_combo)
        self.series_template_lbl = QLabel()
        adv_layout.addRow(self.series_template_lbl, self.series_template_edit)
        self.file_template_lbl = QLabel()
        adv_layout.addRow(self.file_template_lbl, self.file_template_edit)
        self.limit_lbl = QLabel()
        adv_layout.addRow(self.limit_lbl, self.limit_edit)

        adv_checks_grid = QGridLayout()
        adv_checks_grid.addWidget(self.force_read_check, 0, 0)
        adv_checks_grid.addWidget(self.include_hidden_check, 0, 1)
        adv_checks_grid.addWidget(self.include_organized_check, 1, 0)
        adv_checks_grid.addWidget(self.checksum_check, 1, 1)
        adv_checks_grid.addWidget(self.space_check_check, 2, 0)
        adv_layout.addRow(adv_checks_grid)

        self.tags_lbl = QLabel()
        adv_layout.addRow(self.tags_lbl, self.dicom_tags_edit)
        s2_layout.addWidget(self.advanced_content)

        work_layout.addWidget(self.step2_group)

        # Step 4: Results (Inside Scroll Area)
        s4_layout = QVBoxLayout(self.step4_group)
        s4_layout.addWidget(self.result_placeholder_label)
        s4_layout.addWidget(self.result_summary_label)
        s4_layout.addWidget(self.warnings_label)

        res_btn_row = QHBoxLayout()
        res_btn_row.addWidget(self.open_output_button)
        res_btn_row.addWidget(self.open_series_csv_button)
        res_btn_row.addWidget(self.open_report_button)
        res_btn_row.addWidget(self.organize_now_button)
        res_btn_row.addStretch()
        s4_layout.addLayout(res_btn_row)

        s4_layout.addWidget(self.counts_table_title)
        self.counts_table.setMinimumHeight(170)
        s4_layout.addWidget(self.counts_table)

        s4_layout.addWidget(self.reason_table_title)
        self.reason_table.setMinimumHeight(130)
        s4_layout.addWidget(self.reason_table)

        s4_layout.addWidget(self.series_table_title)
        self.series_table.setMinimumHeight(180)
        s4_layout.addWidget(self.series_table)

        s4_layout.addWidget(self.next_steps_title_label)
        s4_layout.addWidget(self.next_steps_body_label)
        s4_layout.addWidget(self.scope_note_label)
        work_layout.addWidget(self.step4_group)

        self.scroll_area.setWidget(work_content)

        # Build G3: Fixed Bottom Action Bar
        action_bar_layout = QVBoxLayout(self.action_bar)
        action_bar_layout.setContentsMargins(16, 10, 16, 10)
        self.action_bar.setStyleSheet(
            "QWidget#action_bar { border-top: 1px solid palette(mid); background: palette(window); }"
        )
        self.action_bar.setObjectName("action_bar")

        act_btn_row = QHBoxLayout()
        act_btn_row.addWidget(self.step3_title_label)
        act_btn_row.addWidget(self.run_button)
        act_btn_row.addWidget(self.cancel_button)
        act_btn_row.addWidget(self.resume_button)
        act_btn_row.addStretch()
        action_bar_layout.addLayout(act_btn_row)

        action_bar_layout.addWidget(self.progress_bar)
        action_bar_layout.addWidget(self.stage_label)

        # Complete Work Page
        work_container = QWidget()
        work_container_layout = QVBoxLayout(work_container)
        work_container_layout.setContentsMargins(0, 0, 0, 0)
        work_container_layout.setSpacing(0)
        work_container_layout.addWidget(self.scroll_area, stretch=1)
        work_container_layout.addWidget(self.action_bar, stretch=0)

        # Stack Management
        self.stack.addWidget(start_widget)     # Index 0: Start page
        self.stack.addWidget(work_container)   # Index 1: Work page
        self.setCentralWidget(self.stack)

        self._reset_results_view()
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.task_buttons["list"].clicked.connect(lambda: self.select_task("list"))
        self.task_buttons["organize"].clicked.connect(lambda: self.select_task("organize"))
        self.task_buttons["preview"].clicked.connect(lambda: self.select_task("preview"))
        self.start_sample_button.clicked.connect(lambda: self.use_sample_data(switch_to_list=True))
        self.work_sample_button.clicked.connect(lambda: self.use_sample_data(switch_to_list=False))

        self.change_task_button.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        self.input_browse_button.clicked.connect(self._choose_input)
        self.output_browse_button.clicked.connect(self._choose_output)
        self.output_edit.textEdited.connect(self._on_output_text_edited)

        self.patient_combo.currentIndexChanged.connect(self._on_option_changed)
        self.layout_combo.currentIndexChanged.connect(self._on_option_changed)
        self.action_combo.currentIndexChanged.connect(self._on_option_changed)
        self.exists_combo.currentIndexChanged.connect(self._on_option_changed)

        self.advanced_toggle_button.clicked.connect(self._toggle_advanced_settings)

        self.run_button.clicked.connect(self._on_run_clicked)
        self.cancel_button.clicked.connect(self.request_cancel)
        self.resume_button.clicked.connect(self._on_resume_clicked)

        self.open_output_button.clicked.connect(self._open_output)
        self.open_series_csv_button.clicked.connect(self._open_series_csv)
        self.open_report_button.clicked.connect(self._open_report)
        self.organize_now_button.clicked.connect(self._on_organize_now_clicked)

    def _toggle_advanced_settings(self) -> None:
        expanded = not self.advanced_content.isVisible()
        self.advanced_content.setVisible(expanded)
        text_key = "advanced_toggle_hide" if expanded else "advanced_toggle_show"
        self.advanced_toggle_button.setText(i18n.tr(text_key, self.language))
        self.settings.setValue("advanced_expanded", expanded)

    def _setup_shortcuts(self) -> None:
        self.shortcut_open = QShortcut(QKeySequence.StandardKey.Open, self)
        self.shortcut_open.activated.connect(self._choose_input)

        self.shortcut_run = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_run.activated.connect(self._on_run_clicked)
        self.shortcut_enter = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.shortcut_enter.activated.connect(self._on_run_clicked)

        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._on_esc_shortcut)

    def _on_esc_shortcut(self) -> None:
        if self.is_running:
            self.request_cancel()

    def _on_output_text_edited(self, text: str) -> None:
        self._output_manually_edited = True

    def _on_option_changed(self) -> None:
        self._update_privacy_panel()
        self._update_unsafe_warning()

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        menubar.clear()

        # File menu
        self.file_menu = menubar.addMenu(i18n.tr("menu_file", self.language))
        self.act_load_config = QAction(i18n.tr("menu_load_config", self.language), self)
        self.act_load_config.triggered.connect(self._menu_load_config)
        self.file_menu.addAction(self.act_load_config)

        self.act_export_config = QAction(i18n.tr("menu_export_config", self.language), self)
        self.act_export_config.triggered.connect(self._menu_export_config)
        self.file_menu.addAction(self.act_export_config)

        self.file_menu.addSeparator()
        self.act_exit = QAction(i18n.tr("menu_exit", self.language), self)
        self.act_exit.triggered.connect(self.close)
        self.file_menu.addAction(self.act_exit)

        # View menu
        self.view_menu = menubar.addMenu(i18n.tr("menu_view", self.language))
        self.lang_menu = self.view_menu.addMenu(i18n.tr("menu_language", self.language))
        self.act_lang_ja = QAction(i18n.tr("menu_lang_ja", self.language), self)
        self.act_lang_ja.setCheckable(True)
        self.act_lang_ja.setChecked(self.language == "ja")
        self.act_lang_ja.triggered.connect(lambda: self.set_language("ja"))
        self.lang_menu.addAction(self.act_lang_ja)

        self.act_lang_en = QAction(i18n.tr("menu_lang_en", self.language), self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setChecked(self.language == "en")
        self.act_lang_en.triggered.connect(lambda: self.set_language("en"))
        self.lang_menu.addAction(self.act_lang_en)

        self.font_menu = self.view_menu.addMenu(i18n.tr("menu_font_size", self.language))
        self.act_font_normal = QAction(i18n.tr("menu_font_normal", self.language), self)
        self.act_font_normal.setCheckable(True)
        self.act_font_normal.setChecked(self.font_scale == "normal")
        self.act_font_normal.triggered.connect(lambda: self.set_font_scale("normal"))
        self.font_menu.addAction(self.act_font_normal)

        self.act_font_large = QAction(i18n.tr("menu_font_large", self.language), self)
        self.act_font_large.setCheckable(True)
        self.act_font_large.setChecked(self.font_scale == "large")
        self.act_font_large.triggered.connect(lambda: self.set_font_scale("large"))
        self.font_menu.addAction(self.act_font_large)

        # Help menu
        self.help_menu = menubar.addMenu(i18n.tr("menu_help", self.language))
        self.act_glossary = QAction(i18n.tr("menu_glossary", self.language), self)
        self.act_glossary.triggered.connect(self._show_glossary)
        self.help_menu.addAction(self.act_glossary)

        self.act_selftest = QAction(i18n.tr("menu_selftest", self.language), self)
        self.act_selftest.triggered.connect(self._run_selftest_dialog)
        self.help_menu.addAction(self.act_selftest)

        self.act_diagnostics = QAction(i18n.tr("menu_diagnostics", self.language), self)
        self.act_diagnostics.triggered.connect(self._action_copy_diagnostics)
        self.help_menu.addAction(self.act_diagnostics)

        self.act_docs = QAction(i18n.tr("menu_docs", self.language), self)
        self.act_docs.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(DOCS_URL)))
        self.help_menu.addAction(self.act_docs)

        self.act_contact = QAction(i18n.tr("menu_contact", self.language), self)
        self.act_contact.triggered.connect(self._show_contact)
        self.help_menu.addAction(self.act_contact)

        self.act_about = QAction(i18n.tr("menu_about", self.language), self)
        self.act_about.triggered.connect(self._show_about)
        self.help_menu.addAction(self.act_about)

    def _retranslate_ui(self) -> None:
        lang = self.language
        self.setWindowTitle(i18n.tr("app_title", lang))

        # Start page (G1: QCommandLinkButton with plain title and description)
        self.start_title_label.setText(i18n.tr("start_title", lang))
        self.start_subtitle_label.setText(i18n.tr("start_subtitle", lang))

        for task_id in TASKS:
            title = i18n.tr(f"task_{task_id}_title", lang)
            desc = i18n.tr(f"task_{task_id}_desc", lang)
            self.task_buttons[task_id].set_content(title, desc)

        self.start_sample_button.setText(i18n.tr("try_sample_data", lang))
        self.start_sample_hint_label.setText(i18n.tr("start_sample_hint", lang))

        # Work page
        self.change_task_button.setText(i18n.tr("reselect_task", lang))
        self._update_task_title()

        self.step1_group.setTitle(i18n.tr("step1_title", lang))
        self.input_browse_button.setText(i18n.tr("browse", lang))
        self.work_sample_button.setText(i18n.tr("try_sample_data", lang))
        self.drop_hint_label.setText(i18n.tr("drop_hint", lang))
        self.sample_note_label.setText(i18n.tr("sample_note", lang))

        self.step2_group.setTitle(i18n.tr("step2_title", lang))
        self.out_label.setText(i18n.tr("output_folder_label", lang))
        self.output_browse_button.setText(i18n.tr("browse", lang))
        self.patient_label.setText(i18n.tr("patient_mode_label", lang))
        self.layout_label.setText(i18n.tr("layout_label", lang))

        current_pm = self.patient_combo.currentData() or "keep"
        self.patient_combo.blockSignals(True)
        self.patient_combo.clear()
        self.patient_combo.addItem(i18n.tr("patient_keep", lang), "keep")
        self.patient_combo.addItem(i18n.tr("patient_hash", lang), "hash")
        self.patient_combo.addItem(i18n.tr("patient_drop", lang), "drop")
        idx = self.patient_combo.findData(current_pm)
        if idx >= 0:
            self.patient_combo.setCurrentIndex(idx)
        self.patient_combo.blockSignals(False)

        current_lo = self.layout_combo.currentData() or "device-date"
        self.layout_combo.blockSignals(True)
        self.layout_combo.clear()
        self.layout_combo.addItem(i18n.tr("layout_device_date", lang), "device-date")
        self.layout_combo.addItem(i18n.tr("layout_study", lang), "study")
        self.layout_combo.addItem(i18n.tr("layout_patient_study", lang), "patient-study")
        idx = self.layout_combo.findData(current_lo)
        if idx >= 0:
            self.layout_combo.setCurrentIndex(idx)
        self.layout_combo.blockSignals(False)

        # Advanced Settings toggle & controls (G2)
        expanded = self.advanced_content.isVisible()
        text_key = "advanced_toggle_hide" if expanded else "advanced_toggle_show"
        self.advanced_toggle_button.setText(i18n.tr(text_key, lang))

        self.action_label.setText(i18n.tr("action_label", lang))
        current_act = self.action_combo.currentData() or "copy"
        self.action_combo.blockSignals(True)
        self.action_combo.clear()
        self.action_combo.addItem(i18n.tr("action_copy", lang), "copy")
        self.action_combo.addItem(i18n.tr("action_symlink", lang), "symlink")
        self.action_combo.addItem(i18n.tr("action_hardlink", lang), "hardlink")
        self.action_combo.addItem(i18n.tr("action_move", lang), "move")
        idx = self.action_combo.findData(current_act)
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)
        self.action_combo.blockSignals(False)

        self.exists_label.setText(i18n.tr("if_exists_label", lang))
        current_ex = self.exists_combo.currentData() or "error"
        self.exists_combo.blockSignals(True)
        self.exists_combo.clear()
        self.exists_combo.addItem(i18n.tr("if_exists_error", lang), "error")
        self.exists_combo.addItem(i18n.tr("if_exists_skip", lang), "skip")
        self.exists_combo.addItem(i18n.tr("if_exists_overwrite", lang), "overwrite")
        self.exists_combo.addItem(i18n.tr("if_exists_rename", lang), "rename")
        idx = self.exists_combo.findData(current_ex)
        if idx >= 0:
            self.exists_combo.setCurrentIndex(idx)
        self.exists_combo.blockSignals(False)

        self.profile_label.setText(i18n.tr("profile_label", lang))
        current_prof = self.profile_combo.currentData() or "auto"
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for prof in core.PROFILE_NAMES:
            self.profile_combo.addItem(prof, prof)
        idx = self.profile_combo.findData(current_prof)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)

        self.series_template_lbl.setText(i18n.tr("series_template_label", lang))
        self.file_template_lbl.setText(i18n.tr("file_template_label", lang))
        self.limit_lbl.setText(i18n.tr("limit_label", lang))
        self.force_read_check.setText(i18n.tr("force_read_label", lang))
        self.include_hidden_check.setText(i18n.tr("include_hidden_label", lang))
        self.include_organized_check.setText(i18n.tr("include_organized_label", lang))
        self.checksum_check.setText(i18n.tr("checksum_label", lang))
        self.space_check_check.setText(i18n.tr("space_check_label", lang))
        self.tags_lbl.setText(i18n.tr("dicom_tags_label", lang))

        # Tooltips
        self.action_combo.setToolTip("copy, symlink, hardlink, or move original files.")
        self.exists_combo.setToolTip("Action when output file already exists.")
        self.profile_combo.setToolTip("Modality profile for parameter extraction.")
        self.checksum_check.setToolTip("Verify SHA-256 after copy.")

        # Fixed Action Bar controls (G3, G5, G7, H3)
        self.step3_title_label.setText(i18n.tr("step3_title", lang))
        self._update_run_button_text()
        self.cancel_button.setText(i18n.tr("btn_cancel", lang))
        self.resume_button.setText(i18n.tr("btn_resume", lang))
        if not self.is_running:
            self.stage_label.setText(i18n.tr("status_ready", lang))

        # Step 4: Results labels & headers (G4, G9, G12)
        self.step4_group.setTitle(i18n.tr("step4_title", lang))
        self.privacy_title_label.setText(i18n.tr("privacy_panel_title", lang))
        self.open_output_button.setText(i18n.tr("open_output_folder", lang))
        self.open_series_csv_button.setText(i18n.tr("open_series_csv", lang))
        self.open_report_button.setText(i18n.tr("open_report_button", lang))
        self.organize_now_button.setText(i18n.tr("organize_now", lang))

        self.counts_table_title.setText(i18n.tr("table_counts_title", lang))
        self.counts_table.setHorizontalHeaderLabels([
            i18n.tr("count_col_item", lang),
            i18n.tr("count_col_count", lang),
            i18n.tr("count_col_desc", lang),
        ])

        self.reason_table_title.setText(i18n.tr("table_reasons_title", lang))
        self.reason_table.setHorizontalHeaderLabels([
            i18n.tr("col_reason", lang),
            i18n.tr("col_count", lang),
            i18n.tr("col_description", lang),
        ])

        self.next_steps_title_label.setText(f"<b>{i18n.tr('next_steps_title', lang)}</b>")
        self._update_next_steps_text()
        self.scope_note_label.setText(i18n.tr("scope_limitation_note", lang))

        # Accessible names
        self.input_edit.setAccessibleName("Input folder path")
        self.output_edit.setAccessibleName("Output folder path")
        self.patient_combo.setAccessibleName("Patient information handling in CSV")
        self.layout_combo.setAccessibleName("Output folder structure layout")
        self.run_button.setAccessibleName("Execute current task")
        self.cancel_button.setAccessibleName("Cancel ongoing execution")
        self.counts_table.setAccessibleName("Table of processed file counts")
        self.reason_table.setAccessibleName("Table of skipped or unhandled files")
        self.series_table.setAccessibleName("Table of detected DICOM series")

        self._update_privacy_panel()
        self._update_unsafe_warning()
        self._build_menu()

        if self.last_result is not None:
            self.show_result(self.last_result)
        else:
            self.result_placeholder_label.setText(i18n.tr("results_placeholder", lang))

    def _update_task_title(self) -> None:
        lang = self.language
        title_key = f"task_{self.current_task}_title"
        self.current_task_label.setText(f"{i18n.tr(title_key, lang)}")

    def _update_run_button_text(self) -> None:
        lang = self.language
        btn_key = f"btn_run_{self.current_task}"
        self.run_button.setText(i18n.tr(btn_key, lang))

    def _update_next_steps_text(self) -> None:
        lang = self.language
        key = f"next_steps_{self.current_task}"
        self.next_steps_body_label.setText(i18n.tr(key, lang))

    def _update_privacy_panel(self) -> None:
        opts = self.build_options()
        notices = core.patient_data_notices(opts)
        lines = []
        for code in notices:
            text = messages.notice_text(code, self.language)
            lines.append(f"• {text}")
        self.privacy_label.setText("\n".join(lines))
        self.privacy_label.setVisible(True)

    def _update_unsafe_warning(self) -> None:
        action = self.action_combo.currentData() or "copy"
        if_exists = self.exists_combo.currentData() or "error"
        warnings = []
        if action == "move" and self.current_task == "organize":
            warnings.append(i18n.tr("unsafe_move_warning", self.language))
        if if_exists == "overwrite":
            warnings.append(i18n.tr("unsafe_overwrite_warning", self.language))
        if warnings:
            self.unsafe_warning_label.setText("\n".join(warnings))
            self.unsafe_warning_label.setVisible(True)
        else:
            self.unsafe_warning_label.setVisible(False)

    def _reset_results_view(self) -> None:
        """Reset results section to placeholder only (J4)."""
        self.last_result = None
        self.result_placeholder_label.setText(i18n.tr("results_placeholder", self.language))
        self.result_placeholder_label.setVisible(True)
        self.result_summary_label.setVisible(False)
        self.warnings_label.setVisible(False)
        self.open_output_button.setVisible(False)
        self.open_series_csv_button.setVisible(False)
        self.open_report_button.setVisible(False)
        self.organize_now_button.setVisible(False)
        self.counts_table_title.setVisible(False)
        self.counts_table.setVisible(False)
        self.reason_table_title.setVisible(False)
        self.reason_table.setVisible(False)
        self.series_table_title.setVisible(False)
        self.series_table.setVisible(False)
        self.next_steps_title_label.setVisible(False)
        self.next_steps_body_label.setVisible(False)
        self.scope_note_label.setVisible(False)

    def _update_label_fonts(self) -> None:
        """Update label fonts based on base font point or pixel size (J2, J7, G1)."""
        app_font = QApplication.font()

        for btn in self.task_buttons.values():
            if hasattr(btn, "update_font_sizes"):
                btn.update_font_sizes()

        self.result_summary_label.setFont(_scaled_font(app_font, 1.1, bold=True))
        self.start_title_label.setFont(_scaled_font(app_font, 1.5, bold=True))
        self.current_task_label.setFont(_scaled_font(app_font, 1.25, bold=True))
        self.step3_title_label.setFont(_scaled_font(app_font, 1.05, bold=True))
        self.scope_note_label.setFont(_scaled_font(app_font, 0.9))

    def _update_secondary_colors(self) -> None:
        """Update secondary label and card colors dynamically based on current palette (K1)."""
        pal = self.palette()
        sec_color = compute_secondary_text_color(
            pal, QPalette.ColorRole.WindowText, QPalette.ColorRole.Window
        )
        sec_style = f"QLabel {{ color: {sec_color.name()}; }}"
        self.start_subtitle_label.setStyleSheet(sec_style)
        self.start_sample_hint_label.setStyleSheet(sec_style)
        self.scope_note_label.setStyleSheet(sec_style)

        for btn in self.task_buttons.values():
            btn.update_palette_colors(pal)

    def select_task(self, task: str) -> None:
        """Switch to work page with specified task ('list', 'organize', 'preview')."""
        if task not in TASKS:
            task = "list"
        self.current_task = task
        self.stack.setCurrentIndex(1)
        self._update_task_title()
        self._update_run_button_text()
        self._update_next_steps_text()

        input_text = self.input_edit.text().strip()
        if input_text and not self._output_manually_edited:
            p = Path(input_text)
            sub = "organized_list" if self.current_task == "list" else "organized"
            self.output_edit.setText(str(p / sub))

        self.action_combo.setEnabled(self.current_task == "organize")
        self._update_privacy_panel()
        self._update_unsafe_warning()
        self._reset_results_view()

    def set_language(self, lang: str) -> None:
        """Switch GUI language and update all texts."""
        if lang not in i18n.SUPPORTED_LANGUAGES:
            lang = "en"
        self.language = lang
        self._retranslate_ui()
        self.save_settings()

    def set_font_scale(self, scale: str) -> None:
        """Switch font scale ('normal' or 'large') (G1)."""
        if scale not in ("normal", "large"):
            scale = "normal"
        self.font_scale = scale
        app_font = QApplication.font()
        factor = 1.25 if scale == "large" else 1.0
        if self._base_font_pixel_size > 0:
            app_font.setPixelSize(round(self._base_font_pixel_size * factor))
        else:
            app_font.setPointSizeF(self._base_font_point_size * factor)
        QApplication.setFont(app_font)
        self._update_label_fonts()
        self.save_settings()

    def set_input_path(self, path: Path | str) -> None:
        """Set input folder path and update default output path if untouched."""
        p = Path(path)
        self.input_edit.setText(str(p))
        if not self._output_manually_edited:
            sub = "organized_list" if self.current_task == "list" else "organized"
            self.output_edit.setText(str(p / sub))
        self._update_privacy_panel()

    def handle_dropped_paths(self, paths: list[Path]) -> bool:
        """Public handler for dropped files or folders."""
        if not paths:
            return False
        first = Path(paths[0])
        target = first.parent if first.is_file() else first
        self.set_input_path(target)
        return True

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        urls = event.mimeData().urls()
        paths = [Path(url.toLocalFile()) for url in urls if url.toLocalFile()]
        if self.handle_dropped_paths(paths):
            event.acceptProposedAction()

    def use_sample_data(self, *, switch_to_list: bool = False) -> Path:
        """Create sample dataset in temp dir and set up the GUI to test it (G11, H6)."""
        from dicom_organizer.sample_data import create_sample_dataset

        temp_dir = tempfile.mkdtemp(prefix="dicom-organizer-sample-")
        create_sample_dataset(temp_dir)
        path = Path(temp_dir)
        self.sample_note_label.setVisible(True)
        self.set_input_path(path)
        if switch_to_list:
            self.select_task("list")
        else:
            self.stack.setCurrentIndex(1)
        return path

    def _get_start_browse_dir(self) -> str:
        lbd = getattr(self, "_last_browse_dir", None)
        if lbd is not None:
            p = Path(lbd)
            if p.exists():
                return str(p)
            if p.parent.exists():
                return str(p.parent)
        return str(Path.home())

    def _choose_input(self) -> None:
        start_dir = self._get_start_browse_dir()
        dir_path = QFileDialog.getExistingDirectory(self, i18n.tr("input_folder_label", self.language), start_dir)
        if dir_path:
            p = Path(dir_path)
            self._last_browse_dir = p.parent if p.is_file() else p
            self.set_input_path(p)

    def _choose_output(self) -> None:
        start_dir = self._get_start_browse_dir()
        dir_path = QFileDialog.getExistingDirectory(self, i18n.tr("output_folder_label", self.language), start_dir)
        if dir_path:
            p = Path(dir_path)
            self._last_browse_dir = p.parent if p.is_file() else p
            self.output_edit.setText(dir_path)
            self._output_manually_edited = True

    def build_options(self, *, dry_run: bool | None = None) -> core.OrganizeOptions:
        """Build OrganizeOptions from current UI state."""
        input_text = self.input_edit.text().strip()
        output_text = self.output_edit.text().strip()
        input_path = Path(input_text) if input_text else Path(".")
        if output_text:
            output_path = Path(output_text)
        else:
            sub = "organized_list" if self.current_task == "list" else "organized"
            output_path = input_path / sub

        patient_mode = self.patient_combo.currentData() or "keep"
        layout = self.layout_combo.currentData() or "device-date"

        if self.current_task == "list":
            list_only = True
            action = "copy"
            is_dry = False if dry_run is None else dry_run
        elif self.current_task == "preview":
            list_only = False
            action = self.action_combo.currentData() or "copy"
            is_dry = True if dry_run is None else dry_run
        else:
            list_only = False
            action = self.action_combo.currentData() or "copy"
            is_dry = False if dry_run is None else dry_run

        if_exists = self.exists_combo.currentData() or "error"
        profile = self.profile_combo.currentData() or "auto"

        limit_str = self.limit_edit.text().strip()
        if limit_str:
            try:
                limit = int(limit_str)
                if limit < 0:
                    raise ValueError(i18n.tr("error_limit_negative", self.language))
            except ValueError as exc:
                if i18n.tr("error_limit_negative", self.language) in str(exc):
                    raise
                raise ValueError(i18n.tr("error_invalid_limit", self.language, value=limit_str)) from exc
        else:
            limit = 0

        tags_str = self.dicom_tags_edit.text().strip()
        dicom_tags = tuple(t.strip() for t in tags_str.split(",") if t.strip())

        return core.OrganizeOptions(
            input_root=input_path,
            output_root=output_path,
            action=action,
            confirm_move=(action == "move"),
            if_exists=if_exists,
            dry_run=is_dry,
            force_read=self.force_read_check.isChecked(),
            include_hidden=self.include_hidden_check.isChecked(),
            include_organized=self.include_organized_check.isChecked(),
            limit=limit,
            series_dir_template=self.series_template_edit.text().strip() or core.DEFAULT_SERIES_DIR_TEMPLATE,
            file_template=self.file_template_edit.text().strip() or core.DEFAULT_FILE_TEMPLATE,
            profile=profile,
            patient_mode=patient_mode,
            dicom_tags=dicom_tags,
            checksum=self.checksum_check.isChecked(),
            space_check=self.space_check_check.isChecked(),
            list_only=list_only,
            layout=layout,
        )

    def _on_run_clicked(self) -> None:
        if self.is_running:
            return

        try:
            self.build_options()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                i18n.tr("dialog_error_title", self.language),
                str(exc),
            )
            return

        if not self.input_edit.text().strip():
            QMessageBox.warning(
                self,
                i18n.tr("dialog_input_required_title", self.language),
                i18n.tr("error_input_required", self.language),
            )
            return

        action = self.action_combo.currentData() or "copy"
        if_exists = self.exists_combo.currentData() or "error"

        if self.current_task == "organize" and action == "move":
            ans = QMessageBox.warning(
                self,
                i18n.tr("confirm_move_title", self.language),
                i18n.tr("confirm_move_msg", self.language),
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if ans != QMessageBox.StandardButton.Ok:
                return

        if if_exists == "overwrite":
            ans = QMessageBox.warning(
                self,
                i18n.tr("confirm_overwrite_title", self.language),
                i18n.tr("confirm_overwrite_msg", self.language),
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if ans != QMessageBox.StandardButton.Ok:
                return

        self.start_run()

    def _on_resume_clicked(self) -> None:
        if self.is_running:
            return
        idx = self.exists_combo.findData("skip")
        if idx >= 0:
            self.exists_combo.setCurrentIndex(idx)
        self.start_run()

    def _on_organize_now_clicked(self) -> None:
        if self.is_running:
            return
        self.select_task("organize")
        self.start_run()

    def start_run(self) -> None:
        """Start organization process in worker thread."""
        if self.is_running:
            return

        self._current_run_start_time = time.time()
        opts = self.build_options()
        self.is_running = True
        self.cancel_event = threading.Event()

        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.resume_button.setVisible(False)
        self._set_inputs_enabled(False)

        self.progress_bar.setRange(0, 0)
        self.stage_label.setText(i18n.tr("status_running", self.language))

        self.thread = QThread(self)
        self.worker = RunWorker(opts, self.cancel_event)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.finished_signal.connect(self._run_finished)
        self.worker.failed_signal.connect(self._run_failed)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.failed_signal.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        self.save_settings()

    def request_cancel(self) -> None:
        """Signal cancel event."""
        if self.cancel_event is not None:
            self.cancel_event.set()
        self.cancel_button.setEnabled(False)

    def on_progress(self, event: core.ProgressEvent) -> None:
        """Immediate progress UI update."""
        if event.total is not None and event.total > 0:
            self.progress_bar.setMaximum(event.total)
            self.progress_bar.setValue(event.done)
        else:
            self.progress_bar.setMaximum(0)
            self.progress_bar.setValue(0)
        self.stage_label.setText(i18n.stage_text(event.stage, event.done, event.total, self.language))

    def _scroll_to_results(self) -> None:
        content = self.scroll_area.widget()
        if content is not None:
            content.adjustSize()
            QApplication.processEvents()
            y = self.result_summary_label.mapTo(content, QPoint(0, 0)).y()
            scroll_pos = max(0, y - 30)
            self.scroll_area.verticalScrollBar().setValue(scroll_pos)

    def _fit_table_height(self, table: QTableWidget, max_rows: int = 12) -> None:
        table.resizeRowsToContents()
        h = table.horizontalHeader().height()
        row_count = table.rowCount()
        for r in range(min(row_count, max_rows)):
            needed = table.sizeHintForRow(r)
            if needed > table.rowHeight(r):
                table.setRowHeight(r, needed)
            h += table.rowHeight(r)
        h += table.frameWidth() * 2 + 4
        table.setFixedHeight(max(60, h))
        if row_count <= max_rows:
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _run_finished(self, result: core.OrganizeResult) -> None:
        self.is_running = False
        self.last_result = result
        self.last_output_root = result.output_root

        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self._set_inputs_enabled(True)

        is_preview = (self.current_task == "preview") or result.dry_run

        if result.status == "completed":
            self.stage_label.setText(i18n.tr("status_completed", self.language))
            self.resume_button.setVisible(False)
        elif result.status == "dry_run":
            self.stage_label.setText(i18n.tr("status_preview_completed", self.language))
            self.resume_button.setVisible(False)
        elif result.status == "cancelled":
            self.stage_label.setText(i18n.tr("status_cancelled", self.language))
            self.resume_button.setVisible(not is_preview)
        else:
            self.stage_label.setText(i18n.tr("status_failed", self.language))
            self.resume_button.setVisible(not is_preview)

        if result.status in ("completed", "dry_run"):
            if self.progress_bar.maximum() <= 0:
                self.progress_bar.setRange(0, 1)
                self.progress_bar.setValue(1)
            else:
                self.progress_bar.setValue(self.progress_bar.maximum())
        else:
            if self.progress_bar.maximum() <= 0:
                self.progress_bar.setRange(0, 1)
                self.progress_bar.setValue(0)

        self.show_result(result)
        # Scroll down to reveal results (H2)
        self._scroll_to_results()

    def _run_failed(self, exc_type: str, message: str, details: str) -> None:
        """Handle execution exception with user-friendly messages (G6, H5)."""
        self.is_running = False
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        is_preview = self.current_task == "preview"
        self.resume_button.setVisible(not is_preview)
        self._set_inputs_enabled(True)

        if self.progress_bar.maximum() <= 0:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)

        self.stage_label.setText(i18n.tr("status_failed", self.language))

        # Check if the current run actually wrote any files before failing (H5)
        written_files: int | None = None
        out_text = self.output_edit.text().strip()
        if out_text:
            summary_json = Path(out_text) / "organize_summary.json"
            if summary_json.exists():
                try:
                    import json
                    from datetime import datetime

                    data = json.loads(summary_json.read_text(encoding="utf-8"))
                    if data.get("status") in ("failed", "interrupted", "cancelled"):
                        started_at_str = data.get("started_at")
                        if started_at_str:
                            dt = datetime.fromisoformat(started_at_str)
                            if dt.timestamp() >= getattr(self, "_current_run_start_time", 0.0) - 1.0:
                                written_files = data.get("organized_files")
                except Exception:
                    pass

        lang = self.language
        if written_files is not None and written_files > 0:
            self.result_summary_label.setText(
                i18n.tr("conclusion_failed", lang, count=f"{written_files:,}")
            )
        else:
            self.result_summary_label.setText(
                i18n.tr("conclusion_failed_no_writes", lang)
            )

        if "FileExistsError" in exc_type:
            user_msg = i18n.tr("error_file_exists", lang)
        elif "InsufficientSpaceError" in exc_type:
            user_msg = i18n.tr("error_insufficient_space", lang)
        elif "IntegrityError" in exc_type:
            user_msg = i18n.tr("error_integrity", lang)
        elif "PermissionError" in exc_type:
            user_msg = i18n.tr("error_permission", lang)
        else:
            user_msg = i18n.tr("error_general_failed", lang)

        msg_box = QMessageBox(
            QMessageBox.Icon.Critical,
            i18n.tr("dialog_error_title", lang),
            user_msg,
            QMessageBox.StandardButton.Ok,
            self,
        )
        msg_box.setDetailedText(details if details else message)
        msg_box.exec()

        # Scroll to reveal result area (H2)
        self._scroll_to_results()

    def _set_inputs_enabled(self, enabled: bool) -> None:
        self.input_edit.setEnabled(enabled)
        self.input_browse_button.setEnabled(enabled)
        self.work_sample_button.setEnabled(enabled)
        self.output_edit.setEnabled(enabled)
        self.output_browse_button.setEnabled(enabled)
        self.patient_combo.setEnabled(enabled)
        self.layout_combo.setEnabled(enabled)
        self.advanced_content.setEnabled(enabled)
        self.advanced_toggle_button.setEnabled(enabled)

    def show_result(self, result: core.OrganizeResult) -> None:
        """Populate results section with summary conclusion, counts, reasons, and series preview."""
        self.last_result = result
        self.last_output_root = result.output_root
        lang = self.language
        summary = result.summary

        # Reveal results section (J4)
        self.result_placeholder_label.setVisible(False)
        self.result_summary_label.setVisible(True)
        self.open_output_button.setVisible(True)
        self.open_series_csv_button.setVisible(True)
        self.open_report_button.setVisible(True)
        self.counts_table_title.setVisible(True)
        self.counts_table.setVisible(True)
        self.reason_table_title.setVisible(True)
        self.reason_table.setVisible(True)
        self.series_table_title.setVisible(True)
        self.series_table.setVisible(True)
        self.next_steps_title_label.setVisible(True)
        self.next_steps_body_label.setVisible(True)
        self.scope_note_label.setVisible(True)

        org_files = summary.get("organized_files", 0)
        target_files = summary.get("csv_target_files", 0)
        excluded_files = summary.get("csv_excluded_files", 0)
        series_count = summary.get("series_count", 0)
        study_count = summary.get("study_count", 0)
        skipped_dict = dict(summary.get("skipped_by_reason", {}))
        dup_conflict = summary.get("duplicate_conflicts", 0)

        # G9: Series preview table (natural row order from summary, dynamically shown columns, tooltips)
        rows = core.build_series_summary([item.row for item in result.items], result.profile)
        image_series_count = len(rows)

        # 1-sentence conclusion (G6, J1)
        if result.status == "cancelled":
            txt = i18n.tr("conclusion_cancelled", lang, count=f"{org_files:,}")
        elif result.status == "failed":
            txt = i18n.tr("conclusion_failed", lang, count=f"{org_files:,}")
        elif result.dry_run:
            txt = i18n.tr(
                "conclusion_dry_run",
                lang,
                target_files=f"{target_files:,}",
                series_count=f"{image_series_count:,}",
            )
        elif result.list_only:
            txt = i18n.tr(
                "conclusion_list",
                lang,
                target_files=f"{target_files:,}",
                series_count=f"{image_series_count:,}",
            )
        else:
            txt = i18n.tr(
                "conclusion_organize",
                lang,
                org_files=f"{org_files:,}",
                target_files=f"{target_files:,}",
            )
        self.result_summary_label.setText(txt)

        # Warnings
        if result.warnings:
            self.warnings_label.setText("\n".join(f"⚠️ {w}" for w in result.warnings))
            self.warnings_label.setVisible(True)
        else:
            self.warnings_label.setVisible(False)

        # Dynamic columns: base columns + optional columns that have at least one non-empty value
        active_cols = list(BASE_SERIES_COLUMNS)
        for opt_col in OPTIONAL_SERIES_COLUMNS:
            has_val = any(r.get(opt_col) not in (None, "", "N/A") for r in rows)
            if has_val:
                active_cols.append(opt_col)

        self.series_table_title.setText(i18n.tr("table_series_title_count", lang, count=len(rows)))
        self.series_table.setSortingEnabled(False)
        self.series_table.setColumnCount(len(active_cols))
        self.series_table.setHorizontalHeaderLabels(active_cols)

        # Header tooltips from column_spec
        for c_idx, col_name in enumerate(active_cols):
            item = self.series_table.horizontalHeaderItem(c_idx)
            if item:
                spec = columns.column_spec(col_name)
                if spec:
                    tip = spec.description_ja if lang == "ja" else spec.description_en
                    if spec.unit:
                        tip += f" [{spec.unit}]"
                    item.setToolTip(tip)

        self.series_table.setRowCount(len(rows))
        for r_idx, r_data in enumerate(rows):
            for c_idx, col in enumerate(active_cols):
                val = r_data.get(col, "")
                self.series_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

        self.series_table.resizeColumnsToContents()

        # G4, H4: Counts breakdown table (8 informative rows, no counts in names)
        if result.dry_run:
            org_item = i18n.tr("count_item_organized_preview", lang)
            org_desc = i18n.tr("count_desc_organized_preview", lang)
            org_cnt = str(org_files)
        elif result.list_only:
            org_item = i18n.tr("count_item_organized_list", lang)
            org_desc = i18n.tr("count_desc_organized_list", lang)
            org_cnt = "0"
        else:
            org_item = i18n.tr("count_item_organized", lang)
            org_desc = i18n.tr("count_desc_organized", lang)
            org_cnt = f"{org_files:,}"

        image_series_cnt = str(len(rows))

        counts_data = [
            (org_item, org_cnt, org_desc),
            (i18n.tr("count_item_csv_targets", lang), f"{target_files:,}", i18n.tr("count_desc_csv_targets", lang)),
            (i18n.tr("count_item_csv_excluded", lang), f"{excluded_files:,}", i18n.tr("count_desc_csv_excluded", lang)),
            (i18n.tr("count_item_series", lang), f"{series_count:,}", i18n.tr("count_desc_series", lang)),
            (i18n.tr("count_item_image_series", lang), image_series_cnt, i18n.tr("count_desc_image_series", lang)),
            (i18n.tr("count_item_studies", lang), f"{study_count:,}", i18n.tr("count_desc_studies", lang)),
            (i18n.tr("count_item_skipped", lang), f"{sum(skipped_dict.values()):,}", i18n.tr("count_desc_skipped", lang)),
            (i18n.tr("count_item_duplicates", lang), f"{dup_conflict:,}", i18n.tr("count_desc_duplicates", lang)),
        ]

        self.counts_table.setRowCount(len(counts_data))
        for r_idx, (item_name, item_cnt, item_desc) in enumerate(counts_data):
            self.counts_table.setItem(r_idx, 0, QTableWidgetItem(item_name))
            self.counts_table.setItem(r_idx, 1, QTableWidgetItem(item_cnt))
            self.counts_table.setItem(r_idx, 2, QTableWidgetItem(item_desc))

        self._fit_table_height(self.counts_table)

        # Skip reasons table
        reasons_map = dict(skipped_dict)
        if dup_conflict > 0:
            reasons_map["duplicate_conflict"] = dup_conflict

        self.reason_table.setRowCount(len(reasons_map))
        for row, (code, count) in enumerate(sorted(reasons_map.items())):
            self.reason_table.setItem(row, 0, QTableWidgetItem(i18n.reason_label(code, lang)))
            self.reason_table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.reason_table.setItem(row, 2, QTableWidgetItem(i18n.reason_help(code, lang)))

        self._fit_table_height(self.reason_table)

        # Buttons state
        out_root = result.output_root
        self.open_output_button.setEnabled(out_root.exists() and not result.dry_run)
        csv_file = out_root / "all_series_summary.csv"
        self.open_series_csv_button.setEnabled(csv_file.exists() and not result.dry_run)
        rpt_file = out_root / "file_report.csv"
        self.open_report_button.setEnabled(rpt_file.exists() and not result.dry_run)

        if result.dry_run:
            self.organize_now_button.setVisible(True)
            self.organize_now_button.setEnabled(True)
        else:
            self.organize_now_button.setVisible(False)

    def _open_output(self) -> None:
        if self.last_output_root and self.last_output_root.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output_root)))

    def _open_series_csv(self) -> None:
        if self.last_output_root:
            csv_path = self.last_output_root / "all_series_summary.csv"
            if csv_path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(csv_path)))

    def _open_report(self) -> None:
        if self.last_output_root:
            rpt_path = self.last_output_root / "file_report.csv"
            if rpt_path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(rpt_path)))

    def _menu_load_config(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            i18n.tr("menu_load_config", self.language),
            "",
            "TOML Files (*.toml);;All Files (*)",
        )
        if path_str:
            try:
                self.load_settings_file(Path(path_str))
                QMessageBox.information(
                    self,
                    i18n.tr("dialog_config_title", self.language),
                    i18n.tr("config_loaded", self.language, path=path_str),
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    i18n.tr("dialog_error_title", self.language),
                    i18n.tr("config_load_error", self.language, error=str(exc)),
                )

    def _menu_export_config(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            i18n.tr("menu_export_config", self.language),
            "dicom_organizer_config.toml",
            "TOML Files (*.toml);;All Files (*)",
        )
        if path_str:
            try:
                self.export_settings_file(Path(path_str))
                QMessageBox.information(
                    self,
                    i18n.tr("dialog_config_title", self.language),
                    i18n.tr("config_exported", self.language, path=path_str),
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    i18n.tr("dialog_error_title", self.language),
                    i18n.tr("config_export_error", self.language, error=str(exc)),
                )

    def load_settings_file(self, path: Path) -> None:
        """Load and apply facility config TOML file."""
        cfg = core.load_config(path)
        if "action" in cfg:
            idx = self.action_combo.findData(cfg["action"])
            if idx >= 0:
                self.action_combo.setCurrentIndex(idx)
        if "if_exists" in cfg:
            idx = self.exists_combo.findData(cfg["if_exists"])
            if idx >= 0:
                self.exists_combo.setCurrentIndex(idx)
        if "patient_mode" in cfg:
            idx = self.patient_combo.findData(cfg["patient_mode"])
            if idx >= 0:
                self.patient_combo.setCurrentIndex(idx)
        if "layout" in cfg:
            idx = self.layout_combo.findData(cfg["layout"])
            if idx >= 0:
                self.layout_combo.setCurrentIndex(idx)
        if "profile" in cfg:
            idx = self.profile_combo.findData(cfg["profile"])
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
        if "series_dir_template" in cfg:
            self.series_template_edit.setText(str(cfg["series_dir_template"]))
        if "file_template" in cfg:
            self.file_template_edit.setText(str(cfg["file_template"]))
        if "force_read" in cfg:
            self.force_read_check.setChecked(bool(cfg["force_read"]))
        if "include_hidden" in cfg:
            self.include_hidden_check.setChecked(bool(cfg["include_hidden"]))
        if "include_organized" in cfg:
            self.include_organized_check.setChecked(bool(cfg["include_organized"]))
        if "checksum" in cfg:
            self.checksum_check.setChecked(bool(cfg["checksum"]))
        if "space_check" in cfg:
            self.space_check_check.setChecked(bool(cfg["space_check"]))
        if "dicom_tags" in cfg:
            self.dicom_tags_edit.setText(", ".join(str(t) for t in cfg["dicom_tags"]))
        if "output" in cfg:
            self.output_edit.setText(str(cfg["output"]))
            self._output_manually_edited = True
        if "list_only" in cfg:
            if cfg["list_only"]:
                self.select_task("list")
            elif self.current_task == "list":
                self.select_task("organize")
        self._update_privacy_panel()
        self._update_unsafe_warning()

    def export_settings_file(self, path: Path) -> None:
        """Export current settings to TOML file."""
        opts = self.build_options()
        values: dict[str, Any] = {
            "action": opts.action,
            "if_exists": opts.if_exists,
            "profile": opts.profile,
            "patient_mode": opts.patient_mode,
            "layout": opts.layout,
            "list_only": opts.list_only,
            "force_read": opts.force_read,
            "include_hidden": opts.include_hidden,
            "include_organized": opts.include_organized,
            "series_dir_template": opts.series_dir_template,
            "file_template": opts.file_template,
            "checksum": opts.checksum,
            "space_check": opts.space_check,
        }
        if opts.dicom_tags:
            values["dicom_tags"] = list(opts.dicom_tags)
        out_text = self.output_edit.text().strip()
        if out_text:
            values["output"] = out_text

        toml_text = core.config_to_toml(values)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(toml_text, encoding="utf-8")

    def copy_diagnostics(self) -> str:
        """Generate sanitized diagnostics string, copy to clipboard, and return it."""
        lines = core.diagnostics_lines()
        home = str(Path.home())

        if self.last_result is not None:
            lines.append("last_run_status: " + str(self.last_result.status))
            lines.append("last_run_profile: " + str(self.last_result.profile))
            lines.append("last_run_dry_run: " + str(self.last_result.dry_run))
            lines.append("last_run_list_only: " + str(self.last_result.list_only))
            for k, v in self.last_result.summary.items():
                if k not in (
                    "organized_files_by_modality",
                    "csv_target_files_by_modality",
                    "csv_excluded_files_by_modality",
                    "skipped_by_reason",
                ):
                    lines.append(f"last_run_{k}: {v}")

        sanitized_lines = []
        for line in lines:
            if home in line:
                line = line.replace(home, "~")
            sanitized_lines.append(line)

        text = "\n".join(sanitized_lines) + "\n"
        QApplication.clipboard().setText(text)
        return text

    def _action_copy_diagnostics(self) -> None:
        self.copy_diagnostics()
        QMessageBox.information(
            self,
            i18n.tr("dialog_diagnostics_title", self.language),
            i18n.tr("diagnostics_copied", self.language),
        )

    def _show_glossary(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(i18n.tr("glossary_title", self.language))
        dlg.resize(650, 480)
        vbox = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(i18n.tr("glossary_content", self.language))
        vbox.addWidget(txt)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dlg.reject)
        vbox.addWidget(btn_box)
        dlg.exec()

    def _show_contact(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(i18n.tr("contact_title", self.language))
        dlg.resize(620, 380)
        vbox = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(i18n.tr("contact_body", self.language))
        vbox.addWidget(txt)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dlg.reject)
        vbox.addWidget(btn_box)
        dlg.exec()

    def _show_about(self) -> None:
        body = i18n.tr("about_body", self.language, version=core.package_version())
        QMessageBox.about(self, i18n.tr("about_title", self.language), body)

    def _run_selftest_dialog(self) -> None:
        from dicom_organizer.selftest import run_self_test

        code = run_self_test()
        if code == 0:
            QMessageBox.information(
                self,
                i18n.tr("dialog_selftest_title", self.language),
                i18n.tr("selftest_passed", self.language, passed=3, total=3),
            )
        else:
            QMessageBox.warning(
                self,
                i18n.tr("dialog_selftest_title", self.language),
                i18n.tr("selftest_failed", self.language, passed=0, total=3),
            )

    def save_settings(self) -> None:
        """Persist UI settings into QSettings (H7, H9)."""
        self.settings.setValue("language", self.language)
        self.settings.setValue("font_scale", self.font_scale)
        self.settings.setValue("last_task", self.current_task)
        if self.patient_combo.currentData():
            self.settings.setValue("patient_mode", self.patient_combo.currentData())
        if self.layout_combo.currentData():
            self.settings.setValue("layout", self.layout_combo.currentData())

        # Safe persistence: do not save 'move' or 'if_exists' (H7)
        act = self.action_combo.currentData()
        if act in ("copy", "symlink", "hardlink"):
            self.settings.setValue("action", act)
        else:
            self.settings.setValue("action", "copy")
        self.settings.remove("if_exists")

        if self.profile_combo.currentData():
            self.settings.setValue("profile", self.profile_combo.currentData())
        self.settings.setValue("series_dir_template", self.series_template_edit.text())
        self.settings.setValue("file_template", self.file_template_edit.text())
        self.settings.setValue("force_read", self.force_read_check.isChecked())
        self.settings.setValue("include_hidden", self.include_hidden_check.isChecked())
        self.settings.setValue("include_organized", self.include_organized_check.isChecked())
        self.settings.setValue("checksum", self.checksum_check.isChecked())
        self.settings.setValue("space_check", self.space_check_check.isChecked())

        # H9: Use not isHidden() for advanced settings state
        self.settings.setValue("advanced_expanded", not self.advanced_content.isHidden())

        # H9: Window geometry and last browse directory
        self.settings.setValue("geometry", self.saveGeometry())
        if getattr(self, "_last_browse_dir", None):
            self.settings.setValue("last_browse_dir", str(self._last_browse_dir))

        self.settings.sync()

    def _load_saved_options(self) -> None:
        # H9: Restore geometry and browse dir
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)

        lbd = self.settings.value("last_browse_dir")
        if lbd:
            self._last_browse_dir = Path(lbd)

        last_task = self.settings.value("last_task", "list")
        if last_task in self.task_buttons:
            self.task_buttons[last_task].setFocus()

        pm = self.settings.value("patient_mode", None)
        if pm:
            idx = self.patient_combo.findData(pm)
            if idx >= 0:
                self.patient_combo.setCurrentIndex(idx)

        lo = self.settings.value("layout", None)
        if lo:
            idx = self.layout_combo.findData(lo)
            if idx >= 0:
                self.layout_combo.setCurrentIndex(idx)

        # H7: Reset dangerous actions to safe defaults
        act = self.settings.value("action", "copy")
        if act not in ("copy", "symlink", "hardlink"):
            act = "copy"
        idx = self.action_combo.findData(act)
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)

        idx_ex = self.exists_combo.findData("error")
        if idx_ex >= 0:
            self.exists_combo.setCurrentIndex(idx_ex)

        prof = self.settings.value("profile", None)
        if prof:
            idx = self.profile_combo.findData(prof)
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)

        st = self.settings.value("series_dir_template", None)
        if st:
            self.series_template_edit.setText(str(st))

        ft = self.settings.value("file_template", None)
        if ft:
            self.file_template_edit.setText(str(ft))

        if self.settings.contains("force_read"):
            self.force_read_check.setChecked(self.settings.value("force_read", type=bool))
        if self.settings.contains("include_hidden"):
            self.include_hidden_check.setChecked(self.settings.value("include_hidden", type=bool))
        if self.settings.contains("include_organized"):
            self.include_organized_check.setChecked(self.settings.value("include_organized", type=bool))
        if self.settings.contains("checksum"):
            self.checksum_check.setChecked(self.settings.value("checksum", type=bool))
        if self.settings.contains("space_check"):
            self.space_check_check.setChecked(self.settings.value("space_check", type=bool))

        adv_exp = self.settings.value("advanced_expanded", False, type=bool)
        self.advanced_content.setVisible(adv_exp)
        text_key = "advanced_toggle_hide" if adv_exp else "advanced_toggle_show"
        self.advanced_toggle_button.setText(i18n.tr(text_key, self.language))

    def changeEvent(self, event: QEvent) -> None:
        """Handle palette and style changes dynamically (K1)."""
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self._update_secondary_colors()

    def closeEvent(self, event: Any) -> None:
        """Protect against closing during active execution (H8)."""
        if self.is_running:
            ans = QMessageBox.question(
                self,
                i18n.tr("dialog_confirm_title", self.language),
                i18n.tr("confirm_cancel_and_exit", self.language),
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Ok:
                self.request_cancel()
                if hasattr(self, "thread") and self.thread.isRunning():
                    self.thread.wait(3000)
                self.save_settings()
                event.accept()
            else:
                event.ignore()
                return
        else:
            self.save_settings()
            event.accept()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the GUI application."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="dicom-organizer-gui",
        description="Launch the PySide6 GUI for dicom-organizer.",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-v", "--version", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--self-test-report", type=Path)
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--gui-smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--gui-smoke-test-report", type=Path, help=argparse.SUPPRESS)
    args, _ = parser.parse_known_args(argv)

    if args.help:
        print("usage: dicom-organizer-gui [options]")
        print()
        print("Launch the PySide6 GUI for dicom-organizer.")
        print()
        print("options:")
        print("  -h, --help            show this help message and exit")
        print("  -v, --version         show program version and exit")
        print("  --self-test           run diagnostic self-tests without launching GUI")
        print("  --self-test-report PATH save self-test report to PATH")
        print("  --diagnostics         print diagnostic environment details and exit")
        return 0

    if args.version:
        print(f"dicom-organizer-gui {core.package_version()}")
        return 0

    if args.self_test:
        from dicom_organizer.selftest import run_self_test

        return run_self_test(report_path=args.self_test_report)

    if args.diagnostics:
        for line in core.diagnostics_lines():
            print(line)
        return 0

    if args.gui_smoke_test:
        if PYSIDE_IMPORT_ERROR is not None:
            print(f"PySide6 import error: {PYSIDE_IMPORT_ERROR}", file=sys.stderr)
            return 2

        existing_app = QApplication.instance() is not None
        app = QApplication.instance() or QApplication([sys.argv[0]] + argv)
        window = MainWindow()
        window.show()

        sample_dir = window.use_sample_data(switch_to_list=True)

        loop = QEventLoop()
        success = [False]
        error_msg = [""]

        def on_finished(result: core.OrganizeResult) -> None:
            success[0] = True
            loop.quit()

        def on_failed(exc_type: str, message: str, details: str) -> None:
            success[0] = False
            error_msg[0] = f"{exc_type}: {message}\n{details}"
            loop.quit()

        window.start_run()
        if hasattr(window, "worker") and window.worker is not None:
            window.worker.finished_signal.connect(on_finished)
            window.worker.failed_signal.connect(on_failed)
        else:
            success[0] = False
            error_msg[0] = "Worker not initialized"

        if window.is_running:
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)

            def on_timeout() -> None:
                error_msg[0] = "GUI smoke test timed out (120s watchdog)"
                window.request_cancel()
                loop.quit()

            timeout_timer.timeout.connect(on_timeout)
            timeout_timer.start(120000)

            loop.exec()
            timeout_timer.stop()
        else:
            if window.last_result is not None:
                success[0] = True

        if hasattr(window, "thread"):
            if window.thread.isRunning():
                window.thread.quit()
                window.thread.wait(5000)
            app.processEvents()

        report_lines = [
            f"[{'PASS' if success[0] else 'FAIL'}] GUI smoke test: list task with sample data",
        ]
        if error_msg[0]:
            report_lines.append(f"       error: {error_msg[0]}")
        if hasattr(window, "last_result") and window.last_result is not None:
            summary = window.last_result.summary
            report_lines.append(f"       status: {summary.get('status')}")
            report_lines.append(f"       target_files: {summary.get('csv_target_files', 0)}")
            report_lines.append(f"       series_count: {summary.get('series_count', 0)}")
        summary_line = f"gui-smoke-test: {'1/1' if success[0] else '0/1'} checks passed"
        report_lines.append(summary_line)
        report_text = "\n".join(report_lines) + "\n"

        if args.gui_smoke_test_report:
            report_path = Path(args.gui_smoke_test_report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")

        print(report_text.strip())
        window.close()
        app.processEvents()
        if not existing_app:
            app.quit()

        try:
            import shutil

            if sample_dir.exists():
                shutil.rmtree(sample_dir, ignore_errors=True)
        except Exception:
            pass

        return 0 if success[0] else 1

    if PYSIDE_IMPORT_ERROR is not None:
        print(
            "PySide6 が見つかりません。GUI を使うには次を実行してインストールしてください:\n"
            "  uv tool install 'dicom-organizer[gui]'\n"
            "または開発環境で:\n"
            "  uv add --extra gui PySide6\n"
            f"詳細: {PYSIDE_IMPORT_ERROR}",
            file=sys.stderr,
        )
        return 2

    app = QApplication.instance() or QApplication([sys.argv[0]] + argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
