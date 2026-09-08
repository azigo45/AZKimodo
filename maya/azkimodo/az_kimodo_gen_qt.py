# -*- coding: utf-8 -*-
"""
AZ Kimodo Motion - PySide2 UI (PySide6 fallback for Maya 2025+)

UI only. Every button reads widget values and calls a function in
az_kimodo_gen (imported as `core`). Do not fork logic here.

The generator is an external executable that takes about a minute per take,
so it runs through QProcess rather than subprocess: Maya's event loop keeps
turning and the scene is only touched from the finished handler, on the main
thread.

The version shown in the header pill, printed on open and printed by every
core operation is az_kimodo_gen.VERSION - this module never carries its own,
so the two files can never disagree about which build is running.

Launch in Maya:
    from azkimodo import az_kimodo_gen_qt
    az_kimodo_gen_qt.show()
"""

from __future__ import print_function

import os
import time
import traceback

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
    _QT_BINDING = 2
except Exception:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
    _QT_BINDING = 6

try:
    import maya.cmds as cmds
    import maya.OpenMayaUI as omui
except Exception:
    cmds = None
    omui = None

from azkimodo import az_kimodo_gen as core

UI_VERSION = getattr(core, "VERSION", "?")
WORDMARK = "AZ KIMODO MOTION"
TAGLINE = "TEXT-TO-MOTION SKELETON GENERATOR"
AUTHOR = "Alexander Antonov"
WINDOW_OBJECT_NAME = "AZ_KimodoMotion_Qt"

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOGO_CANDIDATES = (
    os.path.join(_HERE, "az_kimodo_logo.png"),
    os.path.join(_HERE, "az_logo.png"),
)
_CHECK_SVG_PATH = os.path.join(_HERE, "_azkim_check.svg")

_WIN = None

PLACEHOLDER = ("A person throws a fast front kick with their right leg "
               "and plants the foot back down.")


# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #

def _write_check_svg():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
        'viewBox="0 0 15 15"><path d="M3 8 L6 11 L12 4" stroke="#ffffff" '
        'stroke-width="2.2" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round"/></svg>'
    )
    try:
        with open(_CHECK_SVG_PATH, "w") as handle:
            handle.write(svg)
        return _CHECK_SVG_PATH.replace("\\", "/")
    except Exception:
        return ""


_STYLE_TMPL = """
QWidget {
    background: #2b2d31;
    color: #d7dae0;
    font-family: 'Segoe UI', 'Inter', Arial;
    font-size: 11px;
}
QDialog { background: #2b2d31; }

QGroupBox {
    background: #35383e; border: 1px solid #202225; border-radius: 6px;
    margin-top: 10px; padding: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left; left: 8px;
    padding: 0 4px; color: #7ea6d8; font-size: 9px; font-weight: 700;
}

QLabel { background: transparent; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QAbstractSpinBox {
    background: #232529; border: 1px solid #202225; border-radius: 4px;
    padding: 2px 5px; min-height: 10px; color: #d7dae0;
    selection-background-color: #3f6ea8;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus {
    border: 1px solid #5c9ded; background: #26282d;
}
QComboBox::drop-down { border: none; width: 16px; }
QComboBox::down-arrow {
    width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid #9aa0aa; margin-right: 5px;
}
QComboBox QAbstractItemView {
    background: #232529; border: 1px solid #3f6ea8;
    selection-background-color: #3f6ea8; outline: none;
}

QPushButton {
    background: #484c54; border: 1px solid #202225; border-radius: 4px;
    padding: 6px 10px; min-height: 12px; color: #e7e9ee;
}
QPushButton:hover { background: #52565f; }
QPushButton:pressed { background: #3d4148; }
QPushButton:disabled { background: #34363b; color: #6a6f78; }
QPushButton#primary { background: #4f8a4b; border: 1px solid #3c6b39; }
QPushButton#primary:hover { background: #599a54; }
QPushButton#accent { background: #3f6ea8; border: 1px solid #315687; }
QPushButton#accent:hover { background: #497cbb; }
QPushButton#danger { background: #8a4a44; border: 1px solid #6d3a35; }
QPushButton#danger:hover { background: #9a534c; }
QPushButton#sm { padding: 3px 8px; min-height: 10px; background: #40444b; }
QPushButton#help {
    background: #33363c; border: 1px solid #3f6ea8; border-radius: 12px;
    min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
    color: #9ec2f0; font-weight: 700;
}
QPushButton#help:hover { background: #26303c; }

QCheckBox { spacing: 6px; background: transparent; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #202225; background: #232529;
}
QCheckBox::indicator:checked {
    background: #4f8a4b; border: 1px solid #3c6b39; %(chk)s
}
QCheckBox:disabled { color: #6a6f78; }

QFrame#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #30343b, stop:1 #363b43);
    border: 1px solid #202225; border-radius: 8px;
}
QLabel#logoMono {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3f6ea8, stop:1 #4f8a4b);
    border-radius: 9px; color: #ffffff; font-size: 20px; font-weight: 800;
    min-width: 46px; max-width: 46px; min-height: 46px; max-height: 46px;
}
QLabel#wordmark { font-size: 16px; font-weight: 800; color: #eef1f6; }
QLabel#tagline { font-size: 9px; color: #7d828c; }
QLabel#vpill {
    background: #26303c; border: 1px solid #33578a; border-radius: 9px;
    padding: 2px 9px; color: #9ec2f0; font-size: 10px; font-weight: 700;
}
QFrame#accentBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5c9ded, stop:0.5 #4f8a4b, stop:1 #35383e);
    border: none; border-radius: 1px;
}
QFrame#segment {
    background: #303338; border: 1px solid #23262a; border-radius: 5px;
}

QTextBrowser {
    background: #232529; border: 1px solid #202225; border-radius: 4px;
}

QTableWidget {
    background: #232529; border: 1px solid #202225; border-radius: 4px;
    gridline-color: #2b2f36; outline: none;
}
QTableWidget::item { padding: 2px 4px; color: #d7dae0; }
QTableWidget::item:selected { background: #2c4468; }
QHeaderView::section {
    background: #2f333a; color: #8b95a3; border: 0;
    border-bottom: 1px solid #202225; padding: 4px 6px;
    font-size: 9px; font-weight: 700; letter-spacing: 0.08em;
}

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: #484c54; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #565b64; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QToolTip {
    background: #1c1e22; color: #d7dae0; border: 1px solid #3f6ea8;
    border-radius: 4px; padding: 3px 6px;
}
"""


def _build_stylesheet():
    path = _write_check_svg()
    chk = ("image: url(%s);" % path) if path else ""
    return _STYLE_TMPL % {"chk": chk}


# --------------------------------------------------------------------------- #
# Widget helpers
# --------------------------------------------------------------------------- #

def _label(text, object_name=""):
    widget = QtWidgets.QLabel(text)
    if object_name:
        widget.setObjectName(object_name)
    return widget


def _combo(items, tip=""):
    widget = QtWidgets.QComboBox()
    widget.addItems(list(items))
    if tip:
        widget.setToolTip(tip)
    return widget


def _check(text, checked=False, tip=""):
    widget = QtWidgets.QCheckBox(text)
    widget.setChecked(bool(checked))
    if tip:
        widget.setToolTip(tip)
    return widget


def _spin(value, low, high, step=0.5, decimals=2, tip=""):
    widget = QtWidgets.QDoubleSpinBox()
    widget.setRange(low, high)
    widget.setSingleStep(step)
    widget.setDecimals(decimals)
    widget.setValue(float(value))
    widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
    if tip:
        widget.setToolTip(tip)
    return widget


def _ispin(value, low, high, tip=""):
    widget = QtWidgets.QSpinBox()
    widget.setRange(int(low), int(high))
    widget.setValue(int(value))
    widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
    if tip:
        widget.setToolTip(tip)
    return widget


def _btn(text, role="", tip="", cb=None):
    button = QtWidgets.QPushButton(text)
    if role:
        button.setObjectName(role)
    if tip:
        button.setToolTip(tip)
    if cb is not None:
        button.clicked.connect(cb)
    return button


def _row(*widgets):
    holder = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    for widget in widgets:
        if widget is None:
            layout.addStretch(1)
        elif isinstance(widget, QtWidgets.QLayout):
            layout.addLayout(widget)
        else:
            layout.addWidget(widget)
    return holder


def _labeled(label, widget, width=96):
    name = _label(label)
    name.setMinimumWidth(width)
    return _row(name, widget)


def _group(title):
    box = QtWidgets.QGroupBox(title)
    outer = QtWidgets.QVBoxLayout(box)
    outer.setContentsMargins(8, 14, 8, 8)
    outer.setSpacing(5)
    return box, outer


def _maya_main_window():
    if omui is None:
        return None
    ptr = omui.MQtUtil.mainWindow()
    if ptr is None:
        return None
    return wrapInstance(int(ptr), QtWidgets.QWidget)


# --------------------------------------------------------------------------- #
# Prompt segment row
# --------------------------------------------------------------------------- #

class SegmentWidget(QtWidgets.QFrame):
    """One prompt plus its frame count."""

    removed = QtCore.Signal(object)

    def __init__(self, index, frames=90, parent=None):
        super(SegmentWidget, self).__init__(parent)
        self.setObjectName("segment")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(7, 6, 7, 7)
        layout.setSpacing(5)

        self.lbl_index = _label("SEGMENT %d" % index)
        self.lbl_index.setStyleSheet("color:#7ea6d8;font-size:9px;font-weight:700;")
        self.btn_remove = _btn("x", "sm", "Remove this segment",
                               lambda: self.removed.emit(self))
        self.btn_remove.setFixedWidth(24)
        layout.addWidget(_row(self.lbl_index, None, self.btn_remove))

        self.txt_prompt = QtWidgets.QPlainTextEdit()
        self.txt_prompt.setPlaceholderText(PLACEHOLDER)
        self.txt_prompt.setFixedHeight(52)
        self.txt_prompt.setToolTip(
            "English, third person, describe the body:\n"
            "  \"A person ... with their right leg ... and plants the foot back down.\"\n"
            "Name the side and the end of the movement, or the model picks for you.")
        layout.addWidget(self.txt_prompt)

        self.spin_frames = _ispin(frames, core.MIN_FRAMES, core.MAX_FRAMES,
                                  "Frames for this segment (30 fps)")
        self.spin_frames.valueChanged.connect(self._update_seconds)
        self.lbl_seconds = _label("")
        self.lbl_seconds.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(_row(_label("Frames"), self.spin_frames,
                              self.lbl_seconds, None))
        self._update_seconds()

    def _update_seconds(self):
        self.lbl_seconds.setText("%.1f s" % (self.spin_frames.value() / core.FPS))

    def set_index(self, index):
        self.lbl_index.setText("SEGMENT %d" % index)

    def prompt(self):
        return self.txt_prompt.toPlainText().strip()

    def frames(self):
        return int(self.spin_frames.value())


# --------------------------------------------------------------------------- #
# Help
# --------------------------------------------------------------------------- #

class _HelpDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(_HelpDialog, self).__init__(parent)
        self.setWindowTitle("AZ Kimodo Motion - quick start")
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(460, 440)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        browser = QtWidgets.QTextBrowser()
        browser.setHtml(
            "<h3 style='color:#9ec2f0'>What this does</h3>"
            "<p>Generates a skeletal animation from an English text prompt and "
            "keys it onto a fresh joint chain in the scene. The solve runs in "
            "an external process, so Maya stays responsive.</p>"
            "<h3 style='color:#9ec2f0'>Writing prompts</h3>"
            "<ul>"
            "<li>English only, third person: <i>A person ...</i></li>"
            "<li>Name the side: <i>right leg</i>, <i>left fist</i>.</li>"
            "<li>Describe how the move ends, or limbs hang in the air at the "
            "segment boundary.</li>"
            "<li>No character names, no camera directions, no emotions "
            "without a physical action.</li>"
            "</ul>"
            "<h3 style='color:#9ec2f0'>Segments</h3>"
            "<p>One take is capped at 150 frames (5 s at 30 fps). Chain "
            "actions by adding segments; they are blended over the transition "
            "frame count. Use 5-8 for sharp hits, more for soft moves.</p>"
            "<h3 style='color:#9ec2f0'>Models</h3>"
            "<p><b>SOMA</b> is the 30-joint human skeleton - use it. "
            "<b>G1</b> is the Unitree G1 robot: 34 joints, different pelvis "
            "structure, nothing above the neck. <b>RP</b> and <b>SEED</b> "
            "differ only in training data.</p>"
            "<h3 style='color:#9ec2f0'>Install</h3>"
            "<p>Set <b>AZ_KIMODO_ROOT</b> if kimodo.cpp moves; it defaults to "
            "<i>%s</i>.</p>" % core.DEFAULT_ROOT)
        layout.addWidget(browser)
        footer = _label("%s - AZ Kimodo Motion v%s" % (AUTHOR, UI_VERSION))
        footer.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(footer)


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #

class AZKimodoMotionWindow(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(AZKimodoMotionWindow, self).__init__(parent)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle("AZ Kimodo Motion")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setMinimumWidth(400)
        self.resize(430, 780)
        self.setStyleSheet(_build_stylesheet())

        self._help_dialog = None
        self._segments = []
        self._process = None
        self._started_at = 0.0
        self._take_dir = ""
        self._last_take = None
        self._pins = []
        self._building_pins = False
        self._install = core.probe()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addWidget(self._build_header())
        root.addWidget(self._build_body(), 1)

        self.lbl_status = _label("")
        self.lbl_status.setStyleSheet("color:#7d828c;font-size:9px;")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        self._add_segment()
        self._report_install()

    # -- header ----------------------------------------------------------- #

    def _build_header(self):
        container = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QtWidgets.QFrame()
        header.setObjectName("header")
        header.setFixedHeight(64)
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)
        hl.addWidget(self._build_logo())

        text_box = QtWidgets.QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(0)
        text_box.addStretch(1)
        text_box.addWidget(_label(WORDMARK, "wordmark"))
        text_box.addWidget(_label(TAGLINE, "tagline"))
        text_box.addStretch(1)
        hl.addLayout(text_box)
        hl.addStretch(1)

        vpill = _label("v{0}".format(UI_VERSION), "vpill")
        vpill.setAlignment(QtCore.Qt.AlignCenter)
        hl.addWidget(vpill, 0, QtCore.Qt.AlignTop)
        hl.addWidget(_btn("?", "help", "Quick start", self._open_help),
                     0, QtCore.Qt.AlignTop)

        outer.addWidget(header)
        accent = QtWidgets.QFrame()
        accent.setObjectName("accentBar")
        accent.setFixedHeight(2)
        outer.addWidget(accent)
        return container

    def _build_logo(self):
        for path in _LOGO_CANDIDATES:
            if os.path.isfile(path):
                pixmap = QtGui.QPixmap(path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaledToHeight(46, QtCore.Qt.SmoothTransformation)
                    label = QtWidgets.QLabel()
                    label.setPixmap(pixmap)
                    label.setFixedSize(pixmap.width(), 46)
                    return label
        mono = _label("aZ", "logoMono")
        mono.setAlignment(QtCore.Qt.AlignCenter)
        return mono

    def _open_help(self):
        # Keep a Python reference: a modeless Qt dialog held only by a local
        # is collected the moment the handler returns.
        self._help_dialog = _HelpDialog(self)
        self._help_dialog.setStyleSheet(self.styleSheet())
        self._help_dialog.show()

    # -- body ------------------------------------------------------------- #

    def _build_body(self):
        inner = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._build_model_group())
        layout.addWidget(self._build_prompt_group())
        layout.addWidget(self._build_solver_group())
        layout.addWidget(self._build_scene_group())
        layout.addWidget(self._build_pins_group())
        layout.addWidget(self._build_retarget_group())
        layout.addWidget(self._build_action_group())
        layout.addStretch(1)

        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(inner)
        area.setFrameShape(QtWidgets.QFrame.NoFrame)
        return area

    def _build_model_group(self):
        box, layout = _group("MODEL")
        labels = [model["label"] for model in self._install["models"]]
        self.cmb_model = _combo(labels or ["<none found>"],
                                "Motion model to solve with")
        self.cmb_model.setEnabled(bool(labels))
        self.cmb_model.currentIndexChanged.connect(self._describe_model)
        layout.addWidget(self.cmb_model)

        self.lbl_model_note = _label("")
        self.lbl_model_note.setWordWrap(True)
        self.lbl_model_note.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(self.lbl_model_note)
        self._describe_model()
        return box

    def _build_prompt_group(self):
        box, layout = _group("PROMPT")
        self.seg_layout = QtWidgets.QVBoxLayout()
        self.seg_layout.setContentsMargins(0, 0, 0, 0)
        self.seg_layout.setSpacing(6)
        layout.addLayout(self.seg_layout)

        self.lbl_total = _label("")
        self.lbl_total.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(_row(
            _btn("+ Add segment", "sm", "Chain another action onto this take",
                 self._add_segment),
            None,
            self.lbl_total))
        return box

    def _build_solver_group(self):
        box, layout = _group("SOLVER")
        self.spin_steps = _ispin(100, 1, 1000,
                                 "Diffusion steps. 100 matches the reference "
                                 "demo; 20 is quick and rough.")
        layout.addWidget(_labeled("Steps", self.spin_steps))

        self.spin_seed = _ispin(42, 0, 2147483647,
                                "Same prompt, different seed = a different take")
        layout.addWidget(_labeled("Seed", self.spin_seed))

        self.spin_transition = _ispin(8, 1, 60,
                                      "Frames blended between segments. "
                                      "5-8 keeps hits sharp.")
        layout.addWidget(_labeled("Transition", self.spin_transition))
        return box

    def _build_scene_group(self):
        box, layout = _group("SCENE")
        self.spin_start = _ispin(1, -10000, 100000, "First frame of the take")
        layout.addWidget(_labeled("Start frame", self.spin_start))

        self.line_prefix = QtWidgets.QLineEdit("kimodo_")
        self.line_prefix.setToolTip("Prefix for the generated joints")
        layout.addWidget(_labeled("Prefix", self.line_prefix))

        self.chk_range = _check("Set playback range", True,
                                "Fit the timeline to the imported take")
        self.chk_group = _check("Group under a take node", True,
                                "Parent the skeleton under a group tagged "
                                "with the source folder")
        layout.addWidget(self.chk_range)
        layout.addWidget(self.chk_group)
        return box

    def _build_pins_group(self):
        box, layout = _group("POSE PINS")

        self.chk_use_pins = _check(
            "Generate through pinned poses", False,
            "Hold the pinned frames and let the model fill in the motion\n"
            "around them, instead of generating from the prompt alone.")
        layout.addWidget(self.chk_use_pins)

        self.cmb_pin_source = _combo(
            ["Pose rig (kimodo skeleton)", "Target rig (the character)"],
            "Where a pose is read from. Reading the target rig inverts the\n"
            "retarget, which is exact for every mapped joint - the ones it has\n"
            "no bone for are left unpinned rather than guessed.")
        self.cmb_pin_source.currentIndexChanged.connect(self._describe_pin_mode)
        layout.addWidget(_labeled("Read from", self.cmb_pin_source))

        layout.addWidget(_btn(
            "Create pose rig", "sm",
            "Build a posable copy of the generator's own skeleton.\n"
            "Only needed when reading from the pose rig.",
            self._create_pose_rig))

        self.cmb_pin_mode = _combo([mode[1] for mode in core.PIN_MODES])
        self.cmb_pin_mode.currentIndexChanged.connect(self._describe_pin_mode)
        layout.addWidget(_labeled("Hold", self.cmb_pin_mode))

        self.lbl_pin_mode = _label("")
        self.lbl_pin_mode.setWordWrap(True)
        self.lbl_pin_mode.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(self.lbl_pin_mode)

        self.spin_pin_frame = _ispin(0, 0, 10000,
                                     "Frame of the take this pose belongs to "
                                     "(0 = first frame)")
        layout.addWidget(_row(
            _label("Pin at frame"), self.spin_pin_frame,
            _btn("Pin pose", "sm", "Snapshot the pose rig at this frame",
                 self._pin_pose)))

        self.spin_pin_last = _ispin(0, 0, 10000,
                                    "Last frame of the range to pin")
        self.spin_pin_step = _ispin(1, 1, 60,
                                    "Pin every Nth frame of the range")
        layout.addWidget(_row(
            _label("...through"), self.spin_pin_last,
            _label("every"), self.spin_pin_step,
            _btn("Pin range", "sm",
                 "Hold this pose across a run of frames - what it takes to\n"
                 "keep a hand in place rather than only touch it once",
                 self._pin_range)))

        self.chk_pin_ghosts = _check(
            "Show pinned poses on the timeline", True,
            "Stand each pinned pose up in the scene as a coloured skeleton\n"
            "that appears only on its own frame, so you can scrub to a pin\n"
            "and look at it before spending a solve on it.")
        layout.addWidget(self.chk_pin_ghosts)

        # One row per pin, everything about it editable in place: the frame it
        # sits on, what it holds, and the two things you do to it. The list it
        # replaces showed the same facts but made you select a row and then
        # hunt for the button that applied to it.
        self.table_pins = QtWidgets.QTableWidget(0, 6)
        self.table_pins.setHorizontalHeaderLabels(
            ["Frame", "Until", "Hold", "Time", "", ""])
        self.table_pins.verticalHeader().setVisible(False)
        self.table_pins.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self.table_pins.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.table_pins.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_pins.setFixedHeight(150)
        head = self.table_pins.horizontalHeader()
        head.setStretchLastSection(False)
        for column, width in ((0, 58), (1, 58), (3, 56), (4, 62), (5, 28)):
            self.table_pins.setColumnWidth(column, width)
        head.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table_pins.currentCellChanged.connect(self._select_pin_cell)
        layout.addWidget(self.table_pins)

        layout.addWidget(_row(
            _btn("Insert here", "sm",
                 "Add a pose at wherever the timeline is standing. If that\n"
                 "frame already has a pin, it takes the new pose.",
                 self._insert_here),
            _btn("Insert midway", "sm",
                 "Add a pose half way between the selected pin and the next\n"
                 "one - the breakdown between two keys.",
                 self._insert_midway),
            _btn("Clear", "sm", "Drop every pin", self._clear_pins),
            None))

        self.spin_pin_weight = _spin(2.0, 0.0, 20.0, 0.5, 2,
                                     "How hard the solve is pulled toward the "
                                     "pins.\n2 is the default; raise it if the "
                                     "poses are not held tightly enough.")
        layout.addWidget(_labeled("Pin strength", self.spin_pin_weight))

        self.chk_even_travel = _check(
            "Even out travel between pins", True,
            "Pin the root along a straight line between key poses, so the\n"
            "character walks the distance instead of loitering by one pin\n"
            "and bolting to the next. Only the root is added - the gait that\n"
            "carries the body is still the model's.")
        layout.addWidget(self.chk_even_travel)

        self.chk_ease_pins = _check(
            "Ease hard pins in and out", True,
            "Fade a hard pin over a few frames at each end instead of\n"
            "switching it on. Without this the solve lurches to meet it -\n"
            "measured at 133 cm of movement in one frame where 18 was normal.")
        layout.addWidget(self.chk_ease_pins)

        self.chk_hard_pins = _check(
            "Hard pinning", False,
            "Force the pinned channels to their exact values at every step\n"
            "instead of pulling toward them. Rigid, but the motion around a\n"
            "hard pin has less room to stay natural.")
        layout.addWidget(self.chk_hard_pins)
        self._describe_pin_mode()
        return box

    def _build_retarget_group(self):
        box, layout = _group("RETARGET")

        self.line_target = QtWidgets.QLineEdit("")
        self.line_target.setPlaceholderText("target root joint")
        self.line_target.setToolTip("Root joint of the rig to drive. "
                                    "UE5 Mannequin is recognised by name.")
        layout.addWidget(_row(
            self.line_target,
            _btn("<<", "sm", "Use the selected joint", self._pick_target)))

        layout.addWidget(_row(
            _btn("Import skeleton FBX...", "sm",
                 "Import a rig to retarget onto", self._import_target),
            _btn("Remember bind pose", "sm",
                 "Record the rig's current pose as the reference every\n"
                 "retarget and pin is measured against. Only needed for a rig\n"
                 "that was opened rather than imported here - and the rig must\n"
                 "be at bind when you press it.",
                 self._remember_bind_pose),
            None))

        self.lbl_target = _label("No target set.")
        self.lbl_target.setWordWrap(True)
        self.lbl_target.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(self.lbl_target)

        self.spin_neck = _spin(1.0, 0.0, 1.0, 0.1, 2,
                               "How much of the generator's head and neck\n"
                               "motion to keep. 1 is all of it; lower calms a\n"
                               "head that wanders, which this rig exaggerates\n"
                               "because its second neck bone has no driver.")
        layout.addWidget(_labeled("Head & neck", self.spin_neck))

        self.chk_align = _check(
            "Align rest pose", True,
            "Swing the target onto the generated skeleton's T-pose before\n"
            "measuring. Without this an A-posed rig replays every limb\n"
            "offset by the difference between the two rest poses.")
        self.chk_auto_retarget = _check(
            "Retarget after generate", False,
            "Run the retarget as soon as a take is imported")
        self.chk_hide_source = _check(
            "Delete source skeleton", True,
            "Remove the generated joints once the motion is on the target,\n"
            "so takes do not pile up in the scene")
        layout.addWidget(self.chk_align)
        layout.addWidget(self.chk_auto_retarget)
        layout.addWidget(self.chk_hide_source)

        self.cmb_mode = _combo(
            ["Replace animation", "Append after last key"],
            "Replace wipes what the rig already carries and writes the take\n"
            "at the start frame. Append keeps it and writes after the last key.")
        layout.addWidget(_labeled("New take", self.cmb_mode))

        self.btn_retarget = _btn("RETARGET LAST TAKE", "accent",
                                 "Bake the last imported take onto the target",
                                 self._retarget)
        self.btn_retarget.setEnabled(False)
        layout.addWidget(self.btn_retarget)

        layout.addWidget(_btn(
            "Clear rig animation", "danger",
            "Wipe the baked keys and the cached reference pose.\n"
            "Use this if the first retarget ran on a rig that was not in its\n"
            "bind pose - that wrong reference is reused by every later take.",
            self._clear_rig))
        return box

    def _build_action_group(self):
        box, layout = _group("ACTIONS")
        self.btn_generate = _btn("GENERATE MOTION", "primary",
                                 "Solve the prompt and import the result",
                                 self._generate)
        layout.addWidget(self.btn_generate)

        self.btn_cancel = _btn("Cancel", "danger", "Stop the running solve",
                               self._cancel)
        self.btn_cancel.setEnabled(False)
        layout.addWidget(self.btn_cancel)

        layout.addWidget(_btn("Import existing take...", "accent",
                              "Pick a folder that already holds "
                              "root_positions.f32", self._import_folder))
        return box

    # -- segments --------------------------------------------------------- #

    def _add_segment(self):
        first = not self._segments
        frames = 90 if first else 60
        widget = SegmentWidget(len(self._segments) + 1, frames, self)
        if first:
            # Ship the window ready to press Generate, the way the reference
            # web demo does - an empty box next to a grey example reads as
            # already filled in.
            widget.txt_prompt.setPlainText(PLACEHOLDER)
        widget.removed.connect(self._remove_segment)
        widget.spin_frames.valueChanged.connect(self._update_total)
        self._segments.append(widget)
        self.seg_layout.addWidget(widget)
        self._renumber()

    def _remove_segment(self, widget):
        if len(self._segments) <= 1:
            self._say("A take needs at least one segment.")
            return
        self._segments.remove(widget)
        self.seg_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()
        self._renumber()

    def _renumber(self):
        for index, widget in enumerate(self._segments):
            widget.set_index(index + 1)
            widget.btn_remove.setEnabled(len(self._segments) > 1)
        self._update_total()

    def _update_total(self):
        frames = sum(widget.frames() for widget in self._segments)
        self.lbl_total.setText("total %d frames - %.1f s"
                               % (frames, frames / core.FPS))

    # -- install ---------------------------------------------------------- #

    def _describe_model(self):
        models = self._install["models"]
        index = self.cmb_model.currentIndex() if models else -1
        if 0 <= index < len(models):
            self.lbl_model_note.setText(models[index]["note"])
        else:
            self.lbl_model_note.setText("No motion GGUF found - check the install.")

    def _current_model(self):
        models = self._install["models"]
        index = self.cmb_model.currentIndex()
        if not models or not (0 <= index < len(models)):
            return None
        return models[index]

    def _report_install(self):
        if self._install["ok"]:
            self._say("Ready - %s" % self._install["generator"])
            return
        self.btn_generate.setEnabled(False)
        self._say("Install problem: " + "; ".join(self._install["problems"]))

    def _say(self, message):
        self.lbl_status.setText(message)

    # -- generation ------------------------------------------------------- #

    def _collect_segments(self):
        segments = []
        for index, widget in enumerate(self._segments):
            prompt = widget.prompt()
            if not prompt:
                widget.txt_prompt.setFocus()
                raise ValueError(
                    "Segment %d is empty - type what the body does, in English "
                    "(the grey text is only an example)." % (index + 1))
            segments.append({"prompt": prompt, "frames": widget.frames()})
        return segments

    def _generate(self):
        if self._process is not None:
            self._say("A solve is already running.")
            return

        model = self._current_model()
        if model is None:
            self._say("No model selected.")
            return

        try:
            # A missing prompt is ordinary input, not a fault: say so plainly
            # and keep the Script Editor clean.
            segments = self._collect_segments()
        except ValueError as error:
            self._say(str(error))
            return

        use_pins = self.chk_use_pins.isChecked() and self._pins
        if self.chk_use_pins.isChecked() and not self._pins:
            self._say("Pinned generation is on but nothing is pinned - "
                      "pin a pose, or turn the option off.")
            return
        if use_pins and len(segments) > 1:
            self._say("Pinned generation takes one prompt: the pins already "
                      "say where the body goes. Remove the extra segments.")
            return
        if use_pins:
            # Cheap to check, and the alternative is finding out a minute into
            # the solve, from the generator.
            limit = segments[0]["frames"]
            beyond = [pin["frame"] for pin in self._pins if pin["frame"] >= limit]
            if beyond:
                self._say("Frame %s is pinned but the take is %d frames long, "
                          "so the last frame is %d (they count from 0). Raise "
                          "the frame count or move the pin."
                          % (", ".join(str(frame) for frame in beyond),
                             limit, limit - 1))
                return

        hard = self.chk_hard_pins.isChecked()
        if use_pins and not hard and any(
                pin.get("mode") in core.PIN_MODES_NEEDING_HARD for pin in self._pins):
            # These modes overwrite channels the model was never conditioned
            # on; asking politely does nothing, so the switch is thrown here
            # rather than letting the pin quietly not hold.
            hard = True
            self.chk_hard_pins.setChecked(True)

        try:
            self._take_dir = core.new_take_dir(self._install["root"])
            if use_pins:
                # Spread the holds first, then fill the travel between what
                # is left - the travel pass skips pairs that are already close.
                solved = core.expand_held_pins(self._pins)
                if self.chk_even_travel.isChecked():
                    solved = core.interpolate_root_pins(solved)
                if hard and self.chk_ease_pins.isChecked():
                    solved = core.ramp_pins(solved)
                argv = core.build_constrain_command(
                    model["path"], self._take_dir, segments[0]["prompt"],
                    segments[0]["frames"], self.spin_steps.value(),
                    self.spin_seed.value(), solved, self._install["root"],
                    pin_weight=self.spin_pin_weight.value(), hard=hard)
                if len(solved) != len(self._pins):
                    self._say("Solving with %d pins - %d of yours, %d added "
                              "to carry the holds and the travel..."
                              % (len(solved), len(self._pins),
                                 len(solved) - len(self._pins)))
            else:
                argv = core.build_command(model["path"], self._take_dir,
                                          segments,
                                          self.spin_steps.value(),
                                          self.spin_seed.value(),
                                          self.spin_transition.value(),
                                          self._install["root"])
        except Exception as error:
            self._say("Cannot start: %s" % error)
            traceback.print_exc()
            return

        environment = QtCore.QProcessEnvironment.systemEnvironment()
        for key, value in core.child_environment(argv[0]).items():
            environment.insert(key, value)

        self._process = QtCore.QProcess(self)
        self._process.setWorkingDirectory(self._install["root"])
        self._process.setProcessEnvironment(environment)
        self._process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        self._started_at = time.time()
        self._timer.start()
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self._say("Solving...")
        self._process.start(argv[0], argv[1:])

    def _tick(self):
        elapsed = int(time.time() - self._started_at)
        self._say("Solving... %ds elapsed" % elapsed)

    def _cancel(self):
        if self._process is None:
            return
        self._say("Cancelling...")
        self._process.kill()

    def _teardown_process(self):
        self._timer.stop()
        self.btn_generate.setEnabled(self._install["ok"])
        self.btn_cancel.setEnabled(False)
        process, self._process = self._process, None
        return process

    def _on_error(self, error):
        process = self._process
        if process is None:
            return
        self._teardown_process()
        self._say("Generator failed to run (%s). Check that the build and its "
                  "ggml DLLs are in place." % error)

    def _on_finished(self, exit_code, exit_status):
        process = self._teardown_process()
        if process is None:
            return

        log = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        if log.strip():
            print(log.strip())

        if exit_code != 0:
            self._say("Generator exited with code %d - see the Script Editor."
                      % exit_code)
            return

        elapsed = int(time.time() - self._started_at)
        # File the embedding this run produced, so the next run of the same
        # prompt skips loading the text model.
        if self._pins and self.chk_use_pins.isChecked():
            try:
                core.keep_embedding(self._take_dir,
                                    self._segments[0].prompt(),
                                    self._install["root"])
            except Exception:
                traceback.print_exc()

        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion import")
            try:
                result = core.import_take(
                    self._take_dir,
                    start_frame=self.spin_start.value(),
                    prefix=self.line_prefix.text().strip() or "kimodo_",
                    set_range=self.chk_range.isChecked(),
                    group=self.chk_group.isChecked())
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Solved, but the import failed: %s" % error)
            traceback.print_exc()
            return

        cmds.select(result["top"], replace=True)
        self._remember_take(result)
        self._say("Done in %ds - %d frames, %d joints (%s)"
                  % (elapsed, result["frames"], result["joint_count"],
                     result["skeleton"]))
        if self.chk_auto_retarget.isChecked() and self.line_target.text().strip():
            self._retarget()

    def _import_folder(self):
        picked = cmds.fileDialog2(fileMode=3, okCaption="Import",
                                  caption="Pick a kimodo take folder",
                                  startingDirectory=self._install["root"])
        if not picked:
            return
        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion import")
            try:
                result = core.import_take(
                    picked[0].replace("\\", "/"),
                    start_frame=self.spin_start.value(),
                    prefix=self.line_prefix.text().strip() or "kimodo_",
                    set_range=self.chk_range.isChecked(),
                    group=self.chk_group.isChecked())
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Import failed: %s" % error)
            traceback.print_exc()
            return
        cmds.select(result["top"], replace=True)
        self._remember_take(result)
        self._say("Imported %d frames, %d joints (%s)"
                  % (result["frames"], result["joint_count"], result["skeleton"]))
        if self.chk_auto_retarget.isChecked() and self.line_target.text().strip():
            self._retarget()

    # -- retarget --------------------------------------------------------- #

    def _pick_target(self):
        # A control rig is driven through curve transforms, not joints, so the
        # selection is not narrowed to joints here.
        selected = cmds.ls(selection=True, type="transform", long=True) or []
        if not selected:
            self._say("Select the target rig's top node or root joint first.")
            return
        if core.is_generated_skeleton(selected[0]):
            # Generation leaves the take selected, so this is the easy mistake
            # to make - and it would ask the tool to retarget a take onto
            # itself.
            self._say("That is the generated skeleton, not a rig to drive. "
                      "Select your character's root joint (SKM_Manny's "
                      "'root'), or use Import skeleton FBX.")
            return
        self._set_target(selected[0])

    def _import_target(self):
        picked = cmds.fileDialog2(fileMode=1, okCaption="Import",
                                  caption="Pick a skeleton FBX",
                                  fileFilter="FBX (*.fbx *.FBX)")
        if not picked:
            return
        try:
            root = core.import_target_fbx(picked[0].replace("\\", "/"))
        except Exception as error:
            self._say("FBX import failed: %s" % error)
            traceback.print_exc()
            return
        self._set_target(root)

    def _set_target(self, root):
        self.line_target.setText(root)
        note = ""
        try:
            key = core.identify_target(root)
            self.lbl_target.setText(
                "Recognised: %s" % core.TARGET_LABELS.get(key, key) if key
                else core.describe_target(root).capitalize())
            # A rig opened from a file has no recorded bind pose. Taking it
            # now is safe while nothing is animated; once it is, only the
            # animator knows which pose is bind.
            if key and not core.has_bind_pose(root):
                if core.is_animated(root, target_key=key):
                    note = (" - the rig is animated and has no recorded bind "
                            "pose; put it at bind and press Remember bind pose")
                else:
                    core.capture_bind_pose(root)
                    primed = core.prime_references(root)
                    note = (" - bind pose recorded"
                            + (" and reference measured" if primed else ""))
        except Exception as error:
            self.lbl_target.setText("Cannot read that hierarchy: %s" % error)
        self._refresh_retarget_button()
        if note:
            self._say(self.lbl_target.text() + note)

    def _remember_bind_pose(self):
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("Set the target rig first.")
            return
        try:
            pose = core.capture_bind_pose(target)
        except Exception as error:
            self._say("Could not record the bind pose: %s" % error)
            traceback.print_exc()
            return
        primed = core.prime_references(target)
        self._say("Recorded the bind pose of %s (%d nodes)%s. Every retarget "
                  "and pin is measured from it, so re-record it only if the "
                  "rig's bind pose really changes."
                  % (target.split("|")[-1], len(pose),
                     " and measured the reference" if primed else ""))

    def _refresh_retarget_button(self):
        self.btn_retarget.setEnabled(
            bool(self._last_take and self.line_target.text().strip()))

    def _retarget(self):
        if not self._last_take:
            self._say("Generate or import a take first.")
            return
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("Target root joint not found in the scene.")
            return

        take = self._last_take
        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion retarget")
            try:
                info = core.retarget(
                    take["joints"], take["skeleton"], target,
                    start_frame=take["start_frame"],
                    frames=take["frames"],
                    align_rest=self.chk_align.isChecked(),
                    neck_damping=self.spin_neck.value(),
                    mode=("replace" if self.cmb_mode.currentIndex() == 0
                          else "append"))
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Retarget failed: %s" % error)
            traceback.print_exc()
            return

        if self.chk_hide_source.isChecked():
            try:
                core.delete_take(take["top"])
                self._last_take = None
                self._refresh_retarget_button()
            except Exception:
                traceback.print_exc()

        self._say("Retargeted %d joints onto %s - %s, frames %d-%d%s%s"
                  % (len(info["pairs"]),
                     core.TARGET_LABELS.get(info["target_key"],
                                            info["target_key"]),
                     info["mode"], info["start"], info["end"],
                     " (cached rest pose)" if info["reused_rest"] else "",
                     ("; unmapped: " + ", ".join(info["missing"]))
                     if info["missing"] else ""))

    # -- pose pins -------------------------------------------------------- #

    def _pose_rig(self, create=False):
        rig = core.find_pose_rig()
        if rig is None and create:
            rig = core.build_pose_rig()
        return rig

    def _create_pose_rig(self):
        existing = core.find_pose_rig()
        if existing is not None:
            cmds.select(existing["top"], replace=True)
            self._say("A pose rig is already in the scene - pose it and pin.")
            return
        try:
            rig = core.build_pose_rig()
        except Exception as error:
            self._say("Could not build the pose rig: %s" % error)
            traceback.print_exc()
            return
        cmds.select(rig["top"], replace=True)
        self._say("Pose rig built. Pose it, set the frame, then Pin pose.")

    def _pin_pose(self):
        from_target = self.cmb_pin_source.currentIndex() == 1
        rig = None
        target = self.line_target.text().strip()
        if from_target:
            if not target or not cmds.objExists(target):
                self._say("Set the target rig in RETARGET first, or read from "
                          "the pose rig.")
                return
        else:
            rig = core.find_pose_rig()
            if rig is None:
                self._say("No pose rig in the scene - press Create pose rig "
                          "first.")
                return
        frame = int(self.spin_pin_frame.value())
        if any(pin["frame"] == frame for pin in self._pins):
            self._say("Frame %d is already pinned - remove it first." % frame)
            return
        limit = sum(widget.frames() for widget in self._segments)
        if frame >= limit:
            self._say("Frame %d is past the end: the take is %d frames long, "
                      "so pins go from 0 to %d." % (frame, limit, limit - 1))
            return
        mode = core.PIN_MODE_KEYS[self.cmb_pin_mode.currentIndex()]
        try:
            pin = self._read_pose_now(frame, mode)
            self._pins.append(pin)
            self._show_ghost(pin)
        except Exception as error:
            self._say("Could not read the pose: %s" % error)
            traceback.print_exc()
            return
        self._refresh_pins()
        note = ""
        if from_target and core.is_animated(target):
            note = (" - note the rig is animated, so this is its pose ON that "
                    "frame; clear its animation to author poses by hand")
        self._say("Pinned %s at frame %d (%d total)%s"
                  % (core.PIN_MODES[self.cmb_pin_mode.currentIndex()][1].lower(),
                     frame, len(self._pins), note or "."))

    def _pin_range(self):
        first = int(self.spin_pin_frame.value())
        last = int(self.spin_pin_last.value())
        if last < first:
            self._say("The range ends before it starts - set 'through' to a "
                      "frame at or after %d." % first)
            return
        limit = sum(widget.frames() for widget in self._segments)
        if last >= limit:
            self._say("Frame %d is past the end: the take is %d frames long, "
                      "so pins go from 0 to %d." % (last, limit, limit - 1))
            return

        from_target = self.cmb_pin_source.currentIndex() == 1
        target = self.line_target.text().strip()
        rig = None
        if from_target:
            if not target or not cmds.objExists(target):
                self._say("Set the target rig in RETARGET first.")
                return
        else:
            rig = core.find_pose_rig()
            if rig is None:
                self._say("No pose rig in the scene - press Create pose rig "
                          "first.")
                return

        mode = core.PIN_MODE_KEYS[self.cmb_pin_mode.currentIndex()]
        try:
            fresh = core.capture_range(
                target if from_target else rig["joints"], first, last,
                self.spin_pin_step.value(), mode, from_target,
                self.spin_start.value())
        except Exception as error:
            self._say("Could not read the range: %s" % error)
            traceback.print_exc()
            return

        taken = set(pin["frame"] for pin in self._pins)
        added = [pin for pin in fresh if pin["frame"] not in taken]
        self._pins.extend(added)
        for pin in added:
            self._show_ghost(pin)
        self._refresh_pins()
        self._say("Pinned %d frames (%d already had a pin and were left alone)."
                  % (len(added), len(fresh) - len(added)))

    def _add_or_replace(self, frame, mode, what):
        """Put a pose at `frame`, whether or not something is already there."""
        limit = sum(widget.frames() for widget in self._segments)
        if frame < 0 or frame >= limit:
            self._say("Frame %d is outside the take, which runs 0 to %d."
                      % (frame, limit - 1))
            return
        try:
            pin = self._read_pose_now(frame, mode)
        except Exception as error:
            self._say("Could not read the pose: %s" % error)
            traceback.print_exc()
            return

        replaced = False
        for index, existing in enumerate(self._pins):
            if existing["frame"] == frame:
                self._pins[index] = pin
                replaced = True
                break
        if not replaced:
            self._pins.append(pin)

        self._show_ghost(pin)
        self._refresh_pins()
        self.table_pins.selectRow(self._row_of(pin))
        self._say("%s frame %d (%d pins)."
                  % ("Replaced the pose at" if replaced else what, frame,
                     len(self._pins)))

    def _insert_here(self):
        scene = cmds.currentTime(query=True)
        frame = int(round((scene - self.spin_start.value())
                          * core.MODEL_FPS / core.scene_fps()))
        mode = core.PIN_MODE_KEYS[self.cmb_pin_mode.currentIndex()]
        self._add_or_replace(frame, mode, "Inserted a pose at")

    def _insert_midway(self):
        if len(self._pins) < 2:
            self._say("Two pins are needed before there is a middle.")
            return
        row = self.table_pins.currentRow()
        if row < 0:
            row = 0
        if row >= len(self._pins) - 1:
            row = len(self._pins) - 2
        first, second = self._pins[row], self._pins[row + 1]
        frame = (first["frame"] + second["frame"]) // 2
        if frame in (first["frame"], second["frame"]):
            self._say("Frames %d and %d are neighbours - no room between them."
                      % (first["frame"], second["frame"]))
            return
        mode = core.PIN_MODE_KEYS[self.cmb_pin_mode.currentIndex()]
        self._add_or_replace(frame, mode, "Inserted a breakdown at")

    def _select_pin(self, row):
        """Follow the list: show the pin's frame and what it holds."""
        if row < 0 or row >= len(self._pins):
            return
        pin = self._pins[row]
        self.spin_pin_frame.setValue(pin["frame"])
        if pin.get("mode") in core.PIN_MODE_KEYS:
            self.cmb_pin_mode.setCurrentIndex(
                core.PIN_MODE_KEYS.index(pin["mode"]))
        try:
            cmds.currentTime(core.take_frame_to_scene(pin["frame"],
                                                      self.spin_start.value()),
                             edit=True)
        except Exception:
            pass

    def _read_pose_now(self, frame, mode):
        """Read a pose at `frame` from whichever source is selected.

        The scene is moved to that frame first. A rig carrying a retargeted
        take is animated, so reading it wherever the timeline happens to sit
        captures that frame's pose - press Update while parked on frame 1 and
        the first pose lands in whichever pin you were editing.
        """
        restore = cmds.currentTime(query=True)
        cmds.currentTime(core.take_frame_to_scene(frame,
                                                  self.spin_start.value()),
                         edit=True)
        try:
            if self.cmb_pin_source.currentIndex() == 1:
                target = self.line_target.text().strip()
                if not target or not cmds.objExists(target):
                    raise RuntimeError("set the target rig in RETARGET first")
                return core.capture_pose_from_rig(target, frame, mode)
            rig = core.find_pose_rig()
            if rig is None:
                raise RuntimeError("no pose rig in the scene")
            return core.capture_pose(rig["joints"], frame, mode,
                                     rig["skeleton"])
        finally:
            cmds.currentTime(restore, edit=True)

    def _clear_pins(self):
        self._pins = []
        removed = core.delete_pin_previews()
        self._refresh_pins()
        self._say("Cleared every pin%s."
                  % (" and %d preview(s)" % removed if removed else ""))

    def _show_ghost(self, pin):
        if not self.chk_pin_ghosts.isChecked():
            return
        try:
            core.delete_pin_previews(pin["frame"])
            core.build_pin_preview(
                pin, core.take_frame_to_scene(pin["frame"],
                                              self.spin_start.value()))
        except Exception:
            # A missing ghost is cosmetic; the pin itself is what matters.
            traceback.print_exc()

    def _refresh_pins(self):
        """Rebuild the table from the pins.

        Rows are rebuilt rather than patched, and each row widget closes over
        the pin itself rather than its index - so a pin that moves to another
        frame sorts to a new row without its buttons pointing at a neighbour.
        """
        self._pins.sort(key=lambda pin: pin["frame"])
        self._building_pins = True
        try:
            limit = max(1, sum(w.frames() for w in self._segments))
            self.table_pins.setRowCount(len(self._pins))
            for row, pin in enumerate(self._pins):
                frame = _ispin(pin["frame"], 0, limit - 1,
                               "Move this pin to another frame")
                frame.editingFinished.connect(
                    lambda box=frame, target=pin:
                    self._pin_frame_changed(target, box.value()))
                self.table_pins.setCellWidget(row, 0, frame)

                until = _ispin(int(pin.get("hold_until", pin["frame"])),
                               0, limit - 1,
                               "Hold this pose until this frame. Same as the\n"
                               "frame means it lasts an instant; a grab wants\n"
                               "the frame it lets go on.")
                until.editingFinished.connect(
                    lambda box=until, target=pin:
                    self._pin_until_changed(target, box.value()))
                self.table_pins.setCellWidget(row, 1, until)

                hold = _combo([mode[1] for mode in core.PIN_MODES],
                              "What this pin holds")
                if pin.get("mode") in core.PIN_MODE_KEYS:
                    hold.setCurrentIndex(core.PIN_MODE_KEYS.index(pin["mode"]))
                hold.currentIndexChanged.connect(
                    lambda index, target=pin: self._pin_hold_changed(target, index))
                self.table_pins.setCellWidget(row, 2, hold)

                span = int(pin.get("hold_until", pin["frame"])) - pin["frame"]
                seconds = QtWidgets.QTableWidgetItem(
                    "%.2f s" % (pin["frame"] / core.FPS) if span <= 0
                    else "%.2f +%.2f" % (pin["frame"] / core.FPS,
                                         span / core.FPS))
                seconds.setFlags(QtCore.Qt.ItemIsEnabled)
                self.table_pins.setItem(row, 3, seconds)

                self.table_pins.setCellWidget(row, 4, _btn(
                    "Pose", "sm",
                    "Read the rig again at this frame, keeping what the pin "
                    "holds",
                    lambda checked=False, target=pin: self._update_pin(target)))
                self.table_pins.setCellWidget(row, 5, _btn(
                    "x", "danger", "Remove this pin",
                    lambda checked=False, target=pin: self._delete_pin(target)))
        finally:
            self._building_pins = False

    def _later(self, call):
        """Run after the current signal has finished delivering."""
        QtCore.QTimer.singleShot(0, call)

    def _row_of(self, pin):
        for row, existing in enumerate(self._pins):
            if existing is pin:
                return row
        return -1

    def _pin_frame_changed(self, pin, frame):
        if self._building_pins or int(frame) == pin["frame"]:
            return
        if any(other["frame"] == frame for other in self._pins
               if other is not pin):
            self._say("Frame %d already has a pin." % frame)
            self._later(self._refresh_pins)
            return
        core.delete_pin_previews(pin["frame"])
        was = pin["frame"]
        pin["frame"] = int(frame)
        if pin.get("hold_until", frame) < frame:
            pin["hold_until"] = int(frame)
        self._show_ghost(pin)
        self._later(self._refresh_pins)
        self._say("Moved the pin from frame %d to %d." % (was, frame))

    def _pin_until_changed(self, pin, until):
        if self._building_pins or int(until) == int(
                pin.get("hold_until", pin["frame"])):
            return
        if until < pin["frame"]:
            self._say("A hold cannot end before it starts - frame %d is "
                      "earlier than %d." % (until, pin["frame"]))
            self._later(self._refresh_pins)
            return
        pin["hold_until"] = int(until)
        span = int(until) - pin["frame"]
        # Only the time cell changes, so touch that rather than rebuilding the
        # table under the field the user is still working in.
        row = self._row_of(pin)
        if row >= 0 and self.table_pins.item(row, 3):
            self.table_pins.item(row, 3).setText(
                "%.2f s" % (pin["frame"] / core.FPS) if span <= 0
                else "%.2f +%.2f" % (pin["frame"] / core.FPS, span / core.FPS))
        self._say("Frame %d holds for %d frames (%.2f s)."
                  % (pin["frame"], span, span / core.FPS) if span
                  else "Frame %d holds for an instant." % pin["frame"])

    def _pin_hold_changed(self, pin, index):
        if self._building_pins or not (0 <= index < len(core.PIN_MODES)):
            return
        mode = core.PIN_MODE_KEYS[index]
        if mode == pin.get("mode"):
            return
        core.reshape_pin(pin, mode)
        self._show_ghost(pin)
        self._say("Frame %d now holds %s."
                  % (pin["frame"], core.PIN_MODES[index][1].lower()))

    def _update_pin(self, pin):
        row = self._row_of(pin)
        if row < 0:
            return
        try:
            fresh = self._read_pose_now(pin["frame"], pin.get("mode", "full"))
        except Exception as error:
            self._say("Could not read the pose: %s" % error)
            traceback.print_exc()
            return
        self._pins[row] = fresh
        self._show_ghost(fresh)
        self._refresh_pins()
        self.table_pins.selectRow(self._row_of(fresh))
        self._say("Frame %d now holds the rig's pose at that frame."
                  % fresh["frame"])

    def _delete_pin(self, pin):
        row = self._row_of(pin)
        if row < 0:
            return
        core.delete_pin_previews(pin["frame"])
        frame = self._pins.pop(row)["frame"]
        self._refresh_pins()
        self._say("Removed the pin at frame %d." % frame)

    def _select_pin_cell(self, row, _column=0, _was_row=-1, _was_column=0):
        if not self._building_pins:
            self._select_pin(row)

    def _describe_pin_mode(self):
        index = self.cmb_pin_mode.currentIndex()
        if not (0 <= index < len(core.PIN_MODES)):
            return
        text = core.PIN_MODES[index][5]
        if self.cmb_pin_source.currentIndex() == 1:
            text += ("  Read from the character rig; joints it has no bone "
                     "for (jaw, eyes, finger tips) are left unpinned.")
        self.lbl_pin_mode.setText(text)

    def _clear_rig(self):
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("Set the target rig first.")
            return
        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion clear rig")
            try:
                info = core.clear_rig(target)
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Could not clear the rig: %s" % error)
            traceback.print_exc()
            return
        core.prime_references(target)
        blends = info.get("blends_restored") or []
        self._say("Cleared %d animated channels%s%s - the next retarget will "
                  "measure the rig fresh, so put it in its bind pose first."
                  % (info["channels"],
                     " and the cached rest pose" if info["cache_dropped"] else "",
                     (", put %s back to IK" % ", ".join(blends)) if blends
                     else ""))

    def _remember_take(self, result):
        # A new generation supersedes the last one: drop the previous take's
        # joints so the scene does not fill up with hidden skeletons.
        previous = self._last_take
        self._last_take = dict(result)
        self._last_take["start_frame"] = self.spin_start.value()
        if previous and previous.get("top") != result.get("top"):
            try:
                core.delete_take(previous.get("top"))
            except Exception:
                traceback.print_exc()
        self._refresh_retarget_button()

    def closeEvent(self, event):
        if self._process is not None:
            self._process.kill()
            self._process = None
        self._timer.stop()
        super(AZKimodoMotionWindow, self).closeEvent(event)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def show():
    # The tool is two files. Reloading only this one leaves the previous
    # core in place, and every function added to it since the last open is
    # missing - so pull the core forward here, where both the menu and a bare
    # `az_kimodo_gen_qt.show()` go through it.
    global _WIN, core
    import importlib
    try:
        core = importlib.reload(core)
    except Exception:
        traceback.print_exc()

    if cmds is None:
        print("Run this tool inside Maya.")
        return None
    try:
        if _WIN is not None:
            _WIN.close()
            _WIN.deleteLater()
    except Exception:
        pass
    global UI_VERSION
    UI_VERSION = getattr(core, "VERSION", "?")
    _WIN = AZKimodoMotionWindow(parent=_maya_main_window())
    _WIN.show()
    _WIN.raise_()
    print("[AZ Kimodo Motion %s] window open - core %s" % (UI_VERSION, core.__file__))
    return _WIN
