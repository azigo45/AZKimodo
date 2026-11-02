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

import copy
import os
import re
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
    import maya.api.OpenMaya as om2
except Exception:
    cmds = None
    omui = None
    om2 = None

from azkimodo import az_kimodo_gen as core

UI_VERSION = getattr(core, "VERSION", "?")
WORDMARK = "AZ KIMODO MOTION"
TAGLINE = "TEXT-TO-MOTION FOR YOUR CHARACTER"
AUTHOR = "Alexander Antonov"
WINDOW_OBJECT_NAME = "AZ_KimodoMotion_Qt"
LIMBS_OPTVAR = "azKimodoBakeLimbs"

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


def _progress_bar():
    bar = QtWidgets.QProgressBar()
    bar.setFixedHeight(14)
    bar.setVisible(False)
    bar.setAlignment(QtCore.Qt.AlignCenter)
    bar.setStyleSheet(
        "QProgressBar { background:#232529; border:1px solid #202225;"
        " border-radius:3px; color:#d7dae0; font-size:9px; }"
        "QProgressBar::chunk { background:#4f8a4b; border-radius:2px; }")
    return bar


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
            "<p>Generates a character animation from an English text prompt. "
            "When the window opens it finds the character in the scene - or "
            "imports it from the rig file in CHARACTER - records its bind pose "
            "and measures the retarget reference. Type a prompt, press "
            "GENERATE MOTION, and the take is baked onto the character's "
            "controls as it arrives. The solve runs in an external process, so "
            "Maya stays responsive.</p>"
            "<h3 style='color:#9ec2f0'>Changing poses</h3>"
            "<p>Press ANALYZE POSES: the animation is read at the chosen step, "
            "the frames are marked on the timeline and the pose list opens. "
            "Click a pose to go to it, adjust it with the FK controls and press "
            "Update (limbs baked to IK are posed with their IK controls). Drag "
            "Main to place the character: on the ground it goes there and stays; "
            "up, it jumps on that pose and comes back down, unless Main stays at "
            "this height is on. Turn Main and it faces that way from that pose on, "
            "with the rest of its path swinging round. New pose keeps the pose on "
            "the current frame; "
            "Delete "
            "removes the selected one. When the list is ready press RECALCULATE: "
            "the take is solved through these poses with the same prompt and "
            "seed, and baked onto the controls. Pose accuracy, above that button, "
            "sets how closely the poses you edited are followed. Orange marks are "
            "poses you edited, blue are poses read from the animation.</p>"
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
# Pose list
# --------------------------------------------------------------------------- #

class _PoseDialog(QtWidgets.QDialog):
    """The poses on the timeline: pick one, then edit or delete it."""

    def __init__(self, tool):
        super(_PoseDialog, self).__init__(tool)
        self.tool = tool
        self._time_callback = None
        self.setWindowTitle("AZ Kimodo Motion - poses")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setMinimumWidth(300)
        self.resize(320, 460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.list_poses = QtWidgets.QListWidget()
        self.list_poses.setToolTip("Click a pose to go to its frame.")
        self.list_poses.itemClicked.connect(self._picked)
        layout.addWidget(self.list_poses, 1)

        self.btn_update = _btn(
            "Update", "accent",
            "Replace the selected pose with what the character is doing now",
            self._update)
        self.btn_delete = _btn("Delete", "danger", "Remove the selected pose",
                               self._delete)
        layout.addWidget(_row(
            _btn("New pose here", "sm",
                 "Keep the character's pose on the current timeline frame",
                 self.tool._new_pose),
            self.btn_update, self.btn_delete))

        self.chk_main_stays = _check(
            "Main stays at this height", False,
            "For a step up: the character rises to Main's height by this pose and\n"
            "stays there. Off, a lifted Main is a jump: the model solves it and the\n"
            "character comes back down by the next pose. Applies when you press\n"
            "Update or New pose here.")
        layout.addWidget(self.chk_main_stays)

        self.spin_pose_accuracy = _spin(
            self.tool._pose_accuracy, 0.0, 100.0, 10.0, 0,
            "How closely RECALCULATE follows the poses you edited, in percent.\n"
            "100 hits them exactly, easing in and out half a second around\n"
            "each one. 0 leaves what the model made by itself. Lower it if the\n"
            "motion looks forced around a pose. Press RECALCULATE to apply.")
        self.spin_pose_accuracy.setSuffix(" %")
        self.spin_pose_accuracy.valueChanged.connect(self.tool._pose_accuracy_changed)
        layout.addWidget(_labeled("Pose accuracy", self.spin_pose_accuracy))

        self.btn_recalculate = _btn(
            "RECALCULATE", "primary",
            "Solve the take through these poses, with the same prompt and seed,\n"
            "and bake the result onto the controls.", self.tool._recalculate)
        layout.addWidget(self.btn_recalculate)

        self.btn_cancel = _btn("Cancel", "danger", "Stop the running solve",
                               self.tool._cancel)
        self.btn_cancel.setVisible(False)
        layout.addWidget(self.btn_cancel)

        self.progress = _progress_bar()
        layout.addWidget(self.progress)

        self.lbl_status = _label("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color:#7d828c;font-size:9px;")
        layout.addWidget(self.lbl_status)

    def showEvent(self, event):
        super().showEvent(event)
        self._watch_time()
        self.follow_timeline()

    def hideEvent(self, event):
        self._stop_watching_time()
        super().hideEvent(event)

    def _watch_time(self):
        if om2 is None or self._time_callback is not None:
            return
        # The event, not MDGMessage's time callback: that one fires before the
        # time has changed and would report the frame just left.
        self._time_callback = om2.MEventMessage.addEventCallback(
            "timeChanged", self._time_changed)

    def _stop_watching_time(self):
        callback, self._time_callback = self._time_callback, None
        if callback is not None:
            om2.MMessage.removeCallback(callback)

    def _time_changed(self, *_args):
        # Maya calls this on every frame change, and an error here would repeat
        # on each one, so a window that has gone away just stops listening.
        try:
            self.follow_timeline()
        except RuntimeError:
            self._stop_watching_time()

    def follow_timeline(self):
        """Select the pose on the current frame, or nothing if it has none."""
        start = self.tool._solve["start_frame"] if self.tool._solve else 1
        now = int(round(cmds.currentTime(query=True)))
        found = None
        for row in range(self.list_poses.count()):
            item = self.list_poses.item(row)
            frame = item.data(QtCore.Qt.UserRole)
            if core.take_frame_to_scene(frame, start) == now:
                found = item
                break
        if found is self.list_poses.currentItem():
            return
        if found is None:
            self.list_poses.setCurrentRow(-1)
            self.list_poses.clearSelection()
        else:
            self.list_poses.setCurrentItem(found)
            self.list_poses.scrollToItem(found)
        self._sync_buttons()

    def _selected(self):
        item = self.list_poses.currentItem()
        return item.data(QtCore.Qt.UserRole) if item else None

    def refresh(self):
        start = self.tool._solve["start_frame"] if self.tool._solve else 1
        self.list_poses.clear()
        for frame, pin in sorted(self.tool._poses.items()):
            text = "Frame %d" % core.take_frame_to_scene(frame, start)
            if frame in self.tool._unapplied:
                text += "  -  edited, not recalculated"
            elif pin.get("edited", True):
                text += "  -  edited"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, frame)
            self.list_poses.addItem(item)
        self.follow_timeline()
        self._sync_buttons()

    def _sync_buttons(self):
        frame = self._selected()
        chosen = frame is not None
        self.btn_update.setEnabled(chosen)
        self.btn_delete.setEnabled(chosen)
        self.chk_main_stays.setChecked(
            bool(chosen and self.tool._poses.get(frame, {}).get("main_hold")))

    def set_running(self, running):
        self.btn_recalculate.setEnabled(self.tool._install["ok"] and not running)
        self.btn_cancel.setVisible(running)
        self.btn_cancel.setEnabled(running)

    def _picked(self, item):
        self._sync_buttons()
        self.tool._open_pose(item.data(QtCore.Qt.UserRole))

    def _update(self):
        frame = self._selected()
        if frame is not None:
            self.tool._update_pose(frame)

    def _delete(self):
        frame = self._selected()
        if frame is not None:
            self.tool._delete_pose(frame)


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
        self._solve = None
        self._poses = {}
        self._unapplied = set()
        self._released = set()
        self._poses_changed = False
        self._pose_dialog = None
        self._pose_accuracy = 100.0
        self._pending = None
        self._inflight = None
        self._cancelling = False
        self._stored = ""
        self._baked = None
        self._armed = None
        self._undo_callbacks = []
        self._embed_prompt = ""
        self._install = core.probe()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addWidget(self._build_header())
        root.addWidget(self._build_body(), 1)

        # Under the scrolling body, so a long solve can be stopped from anywhere.
        root.addWidget(self.btn_cancel)
        self.progress = _progress_bar()
        root.addWidget(self.progress)

        self.lbl_status = _label("")
        self.lbl_status.setStyleSheet("color:#7d828c;font-size:9px;")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        self._add_segment()
        self._report_install()
        # After the window is on screen, so a 20 MB rig import is seen as
        # "looking for the character" rather than as a window that will not
        # open.
        QtCore.QTimer.singleShot(0, self._auto_character)

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

        # The everyday path stays on screen: who, what, generate, adjust.
        # Everything else waits behind one button.
        layout.addWidget(self._build_character_group())
        layout.addWidget(self._build_prompt_group())
        layout.addWidget(self._build_action_group())
        layout.addWidget(self._build_edit_group())

        advanced = QtWidgets.QWidget()
        advanced_layout = QtWidgets.QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)
        advanced_layout.addWidget(self._build_model_group())
        advanced_layout.addWidget(self._build_solver_group())
        advanced_layout.addWidget(self._build_scene_group())
        advanced_layout.addWidget(self._build_pins_group())
        advanced_layout.addWidget(self._build_retarget_group())
        advanced_layout.addWidget(_btn(
            "Import existing take...", "accent",
            "Pick a folder that already holds root_positions.f32",
            self._import_folder))
        advanced.setVisible(False)

        toggle = _btn("Advanced settings", "sm",
                      "Model, solver, scene, manual pose pins, retarget options")
        toggle.setCheckable(True)
        toggle.toggled.connect(advanced.setVisible)
        layout.addWidget(toggle)
        layout.addWidget(advanced)
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
        # The selector is out of sight now, so the default has to be a model
        # the character can actually use.
        for index, model in enumerate(self._install["models"]):
            if model["skeleton_key"] == core.SOMA30["key"]:
                self.cmb_model.setCurrentIndex(index)
                break
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
        self.cmb_pin_source.setCurrentIndex(1)
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

    def _build_character_group(self):
        # The rig the animation lands on. It arrives by itself when the window
        # opens - found in the scene or imported from the file below - so this
        # group mostly reports; the buttons are for the unusual case.
        box, layout = _group("CHARACTER")

        self.lbl_target = _label("Looking for the character...")
        self.lbl_target.setWordWrap(True)
        self.lbl_target.setStyleSheet("font-size:11px;")
        layout.addWidget(self.lbl_target)

        self.btn_change_character = _btn(
            "Change...", "sm", "Use a different rig or rig file")
        self.btn_change_character.setCheckable(True)
        layout.addWidget(_row(
            _btn("Frame", "sm", "Fit the view to the character",
                 self._frame_character),
            self.btn_change_character,
            None))

        self.char_tools = QtWidgets.QWidget()
        tools = QtWidgets.QVBoxLayout(self.char_tools)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(5)
        self.char_tools.setVisible(False)
        self.btn_change_character.toggled.connect(self.char_tools.setVisible)
        layout.addWidget(self.char_tools)

        self.line_target = QtWidgets.QLineEdit("")
        self.line_target.setReadOnly(True)
        self.line_target.setPlaceholderText("rig root")
        self.line_target.setToolTip("The node the animation is written under. "
                                    "Set by itself; Use selected overrides it.")
        self.line_target.setStyleSheet("color:#7d828c;font-size:9px;")
        tools.addWidget(self.line_target)

        tools.addWidget(_row(
            _btn("Use selected", "sm",
                 "Drive the selected rig instead - its top node or root joint",
                 self._pick_target),
            _btn("Import FBX...", "sm",
                 "Bring in a different skeleton to drive", self._import_target),
            None))

        self.line_character = QtWidgets.QLineEdit(core.character_file())
        self.line_character.setPlaceholderText("rig file (.ma, .mb or .fbx)")
        self.line_character.setToolTip(
            "The rig file loaded when the scene holds no character.\n"
            "Remembered between sessions.")
        tools.addWidget(_row(
            self.line_character,
            _btn("...", "sm", "Pick the rig file", self._browse_character),
            _btn("Load", "sm",
                 "Import the rig file now, even if a character is already in "
                 "the scene", self._load_character)))
        return box

    def _build_retarget_group(self):
        box, layout = _group("RETARGET")

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
            "Retarget after generate", True,
            "Put the take on the character as soon as it is solved. Off,\n"
            "the generated skeleton stays in the scene and RETARGET LAST\n"
            "TAKE does it by hand.")
        self.chk_hide_source = _check(
            "Delete source skeleton", True,
            "Remove the generated joints once the motion is on the target,\n"
            "so takes do not pile up in the scene")
        self.chk_lock_feet = _check(
            "Lock planted feet", True,
            "Shift the body along the ground so a foot that is standing does\n"
            "not slide. The path changes slightly; edited frames stay where\n"
            "they were posed.")
        self.chk_keep_path = _check(
            "Keep poses on path", True,
            "Fit a pose to the animation on its frame: where the character\n"
            "is, which way it faces, and how high its feet are.")
        self.chk_arms_out = _check(
            "Keep arms out of the body", True,
            "Swing elbows and forearms out when the bake puts them inside the\n"
            "character, using its measured thickness. The hand keeps its\n"
            "orientation.")
        self.spin_arm_clearance = _spin(
            core.ARM_CLEARANCE_DEFAULT, 0.0, 30.0, 0.5, 1,
            "Air to keep between the arm and the body, in scene units.")
        layout.addWidget(self.chk_arms_out)
        layout.addWidget(_labeled("Arm clearance", self.spin_arm_clearance))
        layout.addWidget(self.chk_keep_path)
        layout.addWidget(self.chk_align)
        layout.addWidget(self.chk_lock_feet)
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

        layout.addWidget(_row(
            _btn("Remember bind pose", "sm",
                 "Record the rig's current pose as the reference every\n"
                 "retarget and pin is measured against. Done by itself when\n"
                 "the character arrives; press it only for a rig that came in\n"
                 "another way - and only while it stands at bind.",
                 self._remember_bind_pose),
            _btn("Clear rig animation", "danger",
                 "Wipe the baked keys and the cached reference pose.\n"
                 "Use this if the first retarget ran on a rig that was not in\n"
                 "its bind pose - that wrong reference is reused by every\n"
                 "later take.",
                 self._clear_rig)))
        return box

    def _build_action_group(self):
        box, layout = _group("ACTIONS")
        self.cmb_limbs = _combo(
            [choice[0] for choice in core.IK_LIMB_CHOICES],
            "Which controls drive the arms and legs. Bakes onto IK from the FK\n"
            "animation, which is kept, so changing this does not need a new\n"
            "generation.")
        self.cmb_limbs.setCurrentIndex(
            cmds.optionVar(query=LIMBS_OPTVAR)
            if cmds and cmds.optionVar(exists=LIMBS_OPTVAR) else 0)
        self.cmb_limbs.currentIndexChanged.connect(self._limbs_changed)
        layout.addWidget(_labeled("Bake limbs to", self.cmb_limbs))
        self.btn_generate = _btn("GENERATE MOTION", "primary",
                                 "Solve the prompt and import the result",
                                 self._generate)
        layout.addWidget(self.btn_generate)

        self.btn_cancel = _btn("Cancel", "danger", "Stop the running solve",
                               self._cancel)
        self.btn_cancel.setVisible(False)
        return box

    def _build_edit_group(self):
        box, layout = _group("POSES")
        self.spin_pose_step = _ispin(
            core.POSE_STEP_DEFAULT, 1, 200,
            "Timeline frames between poses. Fewer poses leave the model more\n"
            "room to change the motion; more poses keep it closer to what it is.")
        layout.addWidget(_row(
            _label("Every"), self.spin_pose_step, _label("frames"),
            _btn("ANALYZE POSES", "primary",
                 "Read the animation at this step, mark those frames on the\n"
                 "timeline and open the pose list. Poses you edited are kept.",
                 self._analyze_poses)))
        self.btn_pose_list = _btn("Open pose list", "sm",
                                  "Show the pose list again", self._show_pose_dialog)
        layout.addWidget(self.btn_pose_list)
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
        if self._pose_dialog is not None:
            self._pose_dialog.lbl_status.setText(message)

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

        self._inflight = {
            "solve": None if len(segments) > 1 else {
                "prompt": segments[0]["prompt"],
                "frames": segments[0]["frames"],
                "seed": self.spin_seed.value(),
                "steps": self.spin_steps.value(),
                "model": model["path"],
                "start_frame": self.spin_start.value()},
            "poses": {},
            "edited_frame": None}
        self._embed_prompt = segments[0]["prompt"] if use_pins else ""

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
        self._launch(argv)

    def _launch(self, argv):
        environment = QtCore.QProcessEnvironment.systemEnvironment()
        for key, value in core.child_environment(argv[0]).items():
            environment.insert(key, value)
        environment.insert("KIMODO_PROGRESS", "1")

        self._process = QtCore.QProcess(self)
        self._process.setWorkingDirectory(self._install["root"])
        self._process.setProcessEnvironment(environment)
        self._process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.readyReadStandardOutput.connect(self._read_progress)

        self._solver_log = []
        self._solver_partial = ""
        self._solver_step = (0, 0)
        self._solver_stepped_at = 0.0
        # Several prompt segments solve one after another, restarting the steps.
        self._solver_pass = 0
        self._solver_passes = 1 if self._inflight and self._inflight["edited_frame"] is not None \
            else max(1, len(self._segments))
        self._show_progress(None, "Loading the model...")

        self._started_at = time.time()
        self._timer.start()
        self._cancelling = False
        self._set_running(True)
        self._say("Solving...")
        self._process.start(argv[0], argv[1:])

    def _bars(self):
        bars = [self.progress]
        if self._pose_dialog is not None:
            bars.append(self._pose_dialog.progress)
        return bars

    def _show_progress(self, percent, text):
        """Drive the bar. `percent` None means working, with no way to say how far."""
        for bar in self._bars():
            if percent is None:
                bar.setRange(0, 0)
            else:
                bar.setRange(0, 100)
                bar.setValue(int(percent))
            bar.setFormat(text)
            bar.setVisible(True)

    def _hide_progress(self):
        for bar in self._bars():
            bar.setVisible(False)

    def _read_progress(self):
        if self._process is None:
            return
        text = self._solver_partial + bytes(
            self._process.readAllStandardOutput()).decode("utf-8", "replace")
        lines = text.split("\n")
        self._solver_partial = lines.pop()
        for line in lines:
            match = re.match(r"\s*kimodo-step (\d+) (\d+)", line)
            if not match:
                self._solver_log.append(line)
                continue
            step, steps = int(match.group(1)), int(match.group(2))
            if step <= self._solver_step[0]:
                self._solver_pass += 1
            self._solver_step = (step, steps)
            if step == 1:
                self._solver_stepped_at = time.time()
        self._update_progress()

    def _update_progress(self):
        step, steps = self._solver_step
        if not steps or self._cancelling:
            return
        passes = max(self._solver_passes, self._solver_pass + 1)
        done = (self._solver_pass + float(step) / steps) / passes
        left = ""
        if step > 1:
            per_step = (time.time() - self._solver_stepped_at) / (step - 1)
            remaining = per_step * ((passes - self._solver_pass) * steps - step)
            left = " - about %ds left" % max(1, int(remaining + 0.5))
        self._show_progress(min(99.0, done * 100.0),
                            "Step %d of %d%s" % (step, steps, left))

    def _tick(self):
        elapsed = int(time.time() - self._started_at)
        self._say("Solving... %ds elapsed" % elapsed)
        self._update_progress()

    def _cancel(self):
        if self._process is None:
            return
        self._cancelling = True
        # The timer and the solver's own output would write over this.
        self._timer.stop()
        self.btn_cancel.setEnabled(False)
        if self._pose_dialog is not None:
            self._pose_dialog.btn_cancel.setEnabled(False)
        self._show_progress(None, "Cancelling...")
        self._say("Cancelling...")
        self._process.kill()

    def _set_running(self, running):
        self.btn_generate.setEnabled(self._install["ok"] and not running)
        self.btn_cancel.setVisible(running)
        self.btn_cancel.setEnabled(running)
        self.cmb_limbs.setEnabled(not running)
        self._refresh_retarget_button()
        if self._pose_dialog is not None:
            self._pose_dialog.set_running(running)

    def _teardown_process(self):
        self._timer.stop()
        process, self._process = self._process, None
        self._set_running(False)
        return process

    def _on_error(self, error):
        # Only a failed start ends here: a process that dies, killed or crashed,
        # goes on to report finished, with its exit code and its log.
        if self._process is None or error != QtCore.QProcess.FailedToStart:
            return
        self._teardown_process()
        self._hide_progress()
        self._inflight = None
        self._say("Generator failed to run (%s). Check that the build and its "
                  "ggml DLLs are in place." % error)

    def _on_finished(self, exit_code, exit_status):
        self._read_progress()
        process = self._teardown_process()
        if process is None:
            return
        process.deleteLater()
        cancelled, self._cancelling = self._cancelling, False
        try:
            if cancelled:
                self._inflight = None
                core.discard_unfinished_take(self._take_dir)
                self._say("Cancelled. The animation is unchanged.")
                return
            # Importing and baking block Maya for a moment, so say so before that.
            if exit_code == 0 and exit_status != QtCore.QProcess.CrashExit:
                self._show_progress(100, "Baking onto the character...")
                # Paint only: a click let through here would start another solve
                # over the one about to be baked.
                QtWidgets.QApplication.processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)
            self._finish_solve(exit_code, exit_status)
        finally:
            self._hide_progress()

    def _finish_solve(self, exit_code, exit_status):
        log = "\n".join(self._solver_log + [self._solver_partial])
        if log.strip():
            print(log.strip())

        if exit_code != 0 or exit_status == QtCore.QProcess.CrashExit:
            self._inflight = None
            self._say("Generator stopped unexpectedly (exit code %d) - see the "
                      "Script Editor." % exit_code)
            return

        elapsed = int(time.time() - self._started_at)
        # File the embedding this run produced, so the next run of the same
        # prompt skips loading the text model.
        if self._embed_prompt:
            try:
                core.keep_embedding(self._take_dir, self._embed_prompt,
                                    self._install["root"])
            except Exception:
                traceback.print_exc()

        # One undo step, whatever it takes to get the solve onto the rig.
        cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion solve")
        try:
            self._bake_solved(elapsed)
        finally:
            cmds.undoInfo(closeChunk=True)

    def _bake_solved(self, elapsed):
        inflight = self._inflight or {}
        target = self.line_target.text().strip()
        if (inflight.get("edited_frame") is not None and target
                and cmds.objExists(target)
                and core.solve_text(target) != inflight.get("stored")):
            self._inflight = None
            self._say("The poses changed during the solve, so it was not baked. "
                      "Press RECALCULATE again.")
            return
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
            self._inflight = None
            self._say("Solved, but the import failed: %s" % error)
            traceback.print_exc()
            return

        self._pending, self._inflight = self._inflight, None
        cmds.select(result["top"], replace=True)
        self._remember_take(result)
        self._say("Done in %ds - %d frames, %d joints (%s)"
                  % (elapsed, result["frames"], result["joint_count"],
                     result["skeleton"]))

        edited = self._pending["edited_frame"] if self._pending else None
        target = self.line_target.text().strip()
        if not target or not (edited is not None
                              or self.chk_auto_retarget.isChecked()):
            return
        # An edit always replaces: appending it would play the take twice.
        if not self._retarget(mode="replace" if edited is not None else None):
            return
        if edited is not None:
            cmds.currentTime(core.take_frame_to_scene(
                edited, self._solve["start_frame"]), edit=True)
            self._after_recalculate(target, edited)
            self._say("Recalculated in %ds. The poses are on the character "
                      "and its controls." % elapsed)

    def _import_folder(self):
        picked = cmds.fileDialog2(fileMode=3, okCaption="Import",
                                  caption="Pick a kimodo take folder",
                                  startingDirectory=self._install["root"])
        if not picked:
            return
        with core.undo_chunk("import take"):
            self._import_picked(picked)

    def _import_picked(self, picked):
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
        self._pending = {"solve": None, "poses": {}, "edited_frame": None}
        self._say("Imported %d frames, %d joints (%s)"
                  % (result["frames"], result["joint_count"], result["skeleton"]))
        if self.chk_auto_retarget.isChecked() and self.line_target.text().strip():
            self._retarget()

    # -- retarget --------------------------------------------------------- #

    # -- character -------------------------------------------------------- #

    def _auto_character(self):
        """Find or load the character and make it the target. Runs on open."""
        if cmds is None:
            return
        self.lbl_target.setText("Looking for the character...")
        self._say("Looking for the character...")
        try:
            info = core.ensure_character(
                self.line_character.text().strip() or None)
        except Exception as error:
            self.lbl_target.setText("No character: %s" % error)
            self.btn_change_character.setChecked(True)
            self._say("Could not bring the character in - pick its rig file "
                      "below and press Load.")
            traceback.print_exc()
            return
        if not info["root"]:
            self.lbl_target.setText(
                "No character. Pick its rig file below and press Load, or "
                "select a rig and press Use selected.")
            self.btn_change_character.setChecked(True)
            self._say("; ".join(info["notes"]))
            return

        self._set_target(info["root"], quiet=True)
        if info["loaded"]:
            try:
                core.frame_character(info["root"])
            except Exception:
                traceback.print_exc()
        how = ("loaded from %s" % os.path.basename(info["path"])
               if info["loaded"] else "already in the scene")
        self._say("Character ready - %s, %s%s. Type a prompt and press "
                  "GENERATE MOTION."
                  % (info["label"], how,
                     ("; " + "; ".join(info["notes"])) if info["notes"] else ""))

    def _browse_character(self):
        picked = cmds.fileDialog2(
            fileMode=1, okCaption="Use", caption="Pick the character rig file",
            fileFilter="Maya scene or FBX (*.ma *.mb *.fbx *.FBX)")
        if not picked:
            return
        path = picked[0].replace("\\", "/")
        self.line_character.setText(path)
        core.remember_character_file(path)
        self._say("Character file set. Press Load to bring it in now; from "
                  "the next open it comes in by itself when the scene has no "
                  "character.")

    def _load_character(self):
        path = self.line_character.text().strip()
        if not path:
            self._say("Pick the character rig file first.")
            return
        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion load character")
            try:
                root, _key = core.load_character(path)
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Could not load the character: %s" % error)
            traceback.print_exc()
            return
        core.remember_character_file(path)
        self._set_target(root)
        try:
            core.frame_character(root)
        except Exception:
            traceback.print_exc()

    def _frame_character(self):
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("No character in the scene to frame.")
            return
        core.frame_character(target)

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

    def _set_target(self, root, quiet=False):
        self.line_target.setText(root)
        note = ""
        try:
            key = core.identify_target(root)
            self.lbl_target.setText(
                "%s  -  %s" % (root.split("|")[-1].split(":")[-1],
                               core.TARGET_LABELS.get(key, key)) if key
                else core.describe_target(root).capitalize())
            # A rig opened from a file has no recorded bind pose. Taking it
            # now is safe while nothing is animated; once it is, only the
            # animator knows which pose is bind.
            if key and not core.has_bind_pose(root):
                if core.is_animated(root, target_key=key):
                    note = (" - the rig is animated and has no recorded bind "
                            "pose; put it at bind and press Remember bind pose")
                else:
                    with core.undo_chunk("measure rig"):
                        core.capture_bind_pose(root)
                        primed = core.prime_references(root)
                    note = (" - bind pose recorded"
                            + (" and reference measured" if primed else ""))
        except Exception as error:
            self.lbl_target.setText("Cannot read that hierarchy: %s" % error)
        self._refresh_retarget_button()
        try:
            self._load_poses(root)
        except Exception:
            self._solve, self._poses = None, {}
            traceback.print_exc()
        self._refresh_poses()
        if note and not quiet:
            self._say(self.lbl_target.text() + note)

    def _remember_bind_pose(self):
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("Set the target rig first.")
            return
        with core.undo_chunk("measure rig"):
            try:
                pose = core.capture_bind_pose(target)
            except Exception as error:
                self._say("Could not record the bind pose: %s" % error)
                traceback.print_exc()
                return
            primed = core.prime_references(target)
            try:
                core.measure_body(target)
            except Exception:
                traceback.print_exc()
        self._say("Recorded the bind pose of %s (%d nodes)%s. Every retarget "
                  "and pin is measured from it, so re-record it only if the "
                  "rig's bind pose really changes."
                  % (target.split("|")[-1], len(pose),
                     " and measured the reference" if primed else ""))

    def _refresh_retarget_button(self):
        self.btn_retarget.setEnabled(
            bool(self._last_take and self.line_target.text().strip()
                 and self._process is None))

    def _retarget(self, _checked=False, mode=None):
        cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion retarget")
        try:
            return self._retarget_take(mode)
        finally:
            cmds.undoInfo(closeChunk=True)

    def _retarget_take(self, mode):
        if self._process is not None:
            self._say("A solve is already running.")
            return False
        if not self._last_take:
            self._say("Generate or import a take first.")
            return False
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("Target root joint not found in the scene.")
            return False

        take = self._last_take
        poses = (self._pending or {}).get("poses", {})
        # The same take baked again keeps what its poses say about Main.
        if self._pending is None and self._baked and self._baked[0] is take:
            poses = self._baked[1]["poses"]
        try:
            info = core.retarget(
                take["joints"], take["skeleton"], target,
                start_frame=take["start_frame"],
                frames=take["frames"],
                align_rest=self.chk_align.isChecked(),
                neck_damping=self.spin_neck.value(),
                foot_lock=self.chk_lock_feet.isChecked(),
                ik_limbs=self._ik_limbs(),
                main_poses=poses,
                pose_accuracy=self._pose_accuracy / 100.0,
                arm_clearance=(self.spin_arm_clearance.value()
                               if self.chk_arms_out.isChecked() else None),
                keep_frames=[core.take_frame_to_scene(frame,
                                                      take["start_frame"])
                             for frame, pin in poses.items()
                             if pin.get("edited", True)],
                mode=mode or ("replace" if self.cmb_mode.currentIndex() == 0
                              else "append"))
        except Exception as error:
            self._say("Retarget failed: %s" % error)
            traceback.print_exc()
            return False

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

        # Recorded here rather than where the solve ends, so a take baked by
        # hand later is remembered the same way as one baked automatically.
        pending, self._pending = self._pending, None
        if pending:
            self._baked = [take, copy.deepcopy(pending), None]
            self._solve, self._poses = pending["solve"], pending["poses"]
            if pending["edited_frame"] is None:
                # A new take: nothing from the old one applies.
                self._unapplied = set()
                self._released = set()
                self._poses_changed = False
            self._store_poses()
            # Undoing back past this point brings the take back as not yet baked.
            self._baked[2] = self._stored
            self._refresh_poses()
        return True

    # -- limbs ------------------------------------------------------------ #

    def _ik_limbs(self):
        return core.IK_LIMB_CHOICES[self.cmb_limbs.currentIndex()][1]

    def _limbs_changed(self, index):
        """Apply the choice to the animation already on the rig."""
        cmds.optionVar(intValue=(LIMBS_OPTVAR, index))
        target = self.line_target.text().strip()
        if not (self._solve and target and cmds.objExists(target)):
            return
        if self._process is not None:
            self._say("A solve is already running.")
            return
        solve = self._solve
        which = self._ik_limbs()
        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion limbs")
            try:
                core.clear_ik_keys(target)
                core.set_limb_mode(target, ())
                core.bake_ik(target, core.take_frame_to_scene(0, solve["start_frame"]),
                             core.take_frame_to_scene(solve["frames"] - 1,
                                                      solve["start_frame"]), which)
                self._store_poses()
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Could not change the limbs: %s" % error)
            traceback.print_exc()
            return
        self._say("Limbs baked to: %s." % core.IK_LIMB_CHOICES[index][0])

    # -- pose analyzer ---------------------------------------------------- #

    def _timeline_take_frame(self, start_frame):
        scene = cmds.currentTime(query=True)
        return int(round((scene - start_frame) * core.MODEL_FPS
                         / core.scene_fps()))

    def _pose_context(self):
        """(target, solve) when poses can be worked on, else None after saying why."""
        if self._process is not None:
            self._say("A solve is already running.")
            return None
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("No character in the scene - load one in CHARACTER.")
            return None
        if not self._solve:
            self._say("Generate an animation from one prompt first - this rig "
                      "has no record of a prompt to solve again.")
            return None
        return target, self._solve

    def _analyze_poses(self):
        context = self._pose_context()
        if not context:
            return
        target, solve = context
        kept = dict((frame, pin) for frame, pin in self._poses.items()
                    if pin.get("edited", True))
        frames = [frame for frame in core.pose_frames(
                      solve["frames"], solve["start_frame"],
                      self.spin_pose_step.value())
                  if frame not in kept]
        try:
            poses = core.analyze_poses(target, frames, solve["start_frame"])
        except Exception as error:
            self._say("Could not read the animation: %s" % error)
            traceback.print_exc()
            return
        poses.update(kept)
        self._poses = poses
        self._store_poses()
        self._refresh_poses()
        self._show_pose_dialog()
        self._say("%d poses on the timeline. Click one to go to it." % len(poses))

    def _store_poses(self):
        target = self.line_target.text().strip()
        if target and cmds.objExists(target):
            core.remember_solve(target, self._solve, self._poses, self._unapplied,
                                self._released, self._poses_changed,
                                self.cmb_limbs.currentIndex())
            self._stored = core.solve_text(target)

    def _load_poses(self, target):
        self._solve, self._poses = core.read_solve(target)
        core.settle_old_poses(target, self._solve, self._poses)
        self._unapplied, self._released, self._poses_changed, limbs = \
            core.read_pose_state(target)
        self._stored = core.solve_text(target)
        if limbs is not None and limbs != self.cmb_limbs.currentIndex():
            # The rig already is this way, so nothing is to be baked.
            self.cmb_limbs.blockSignals(True)
            self.cmb_limbs.setCurrentIndex(limbs)
            self.cmb_limbs.blockSignals(False)
            cmds.optionVar(intValue=(LIMBS_OPTVAR, limbs))

    def _refresh_poses(self):
        """Bring the timeline marks and the pose list in line with the poses."""
        start = self._solve["start_frame"] if self._solve else 1
        try:
            if self._poses:
                core.set_pose_marks(
                    [(core.take_frame_to_scene(frame, start),
                      pin.get("edited", True))
                     for frame, pin in sorted(self._poses.items())])
            else:
                core.clear_pose_marks()
        except Exception:
            # The marks only show what the list already says.
            traceback.print_exc()
        self.btn_pose_list.setEnabled(bool(self._poses))
        if self._pose_dialog is not None:
            self._pose_dialog.refresh()

    def _show_pose_dialog(self):
        if self._pose_dialog is None:
            self._pose_dialog = _PoseDialog(self)
            self._pose_dialog.set_running(self._process is not None)
        self._pose_dialog.refresh()
        self._pose_dialog.show()
        self._pose_dialog.raise_()

    def _capture_pose(self, target, solve, frame):
        # The box describes the selected row, and reading the take below hops the
        # timeline, which moves the selection and the box with it. So this first.
        old = self._poses.get(frame, {})
        dialog = self._pose_dialog
        if (dialog is not None and dialog.isVisible()
                and dialog._selected() in (frame, None)):
            holds = dialog.chk_main_stays.isChecked()
        else:
            holds = bool(old.get("main_hold"))
        with core.quietly():
            pin = core.capture_pose_from_rig(target, frame, "full")
            pin["main_above"] = core.pose_main_above(
                target, self._poses, frame, solve["start_frame"])
            # Read before the fit, which moves the timeline to see the curves.
            drag, placed = core.main_place(target)
            if self.chk_keep_path.isChecked():
                if placed:
                    # The drag is handed over separately, not as part of the pose.
                    core.drop_main_drag(pin, drag)
                turn_drag, facing = core.main_turn(target)
                anchor = core.take_pose_at(target, frame)
                # As with height below: a solved pose keeps the way it was asked
                # to face, not the way the model got round to.
                turn_short = 0.0
                if old.get("edited"):
                    turn_short = (old.get("turn_short", 0.0)
                                  if frame in self._unapplied
                                  else core.heading_gap(old, anchor))
                pin = core.fit_pose_to_take(pin, anchor,
                                            turn_more=turn_drag + turn_short)
                # Updating a solved pose keeps what was asked, not what the model
                # reached. Updating it again before the solve adds the same amount.
                if old.get("edited"):
                    extra = (old.get("short_by", 0.0) if frame in self._unapplied
                             else old["root"][1] - old.get("reached", old["root"][1]))
                    root = list(pin["root"])
                    root[1] += extra
                    pin["root"] = root
                    pin["short_by"] = extra
                if placed:
                    pin["main_target"] = placed
                    pin["main_hold"] = holds
                    pin["main_turn"] = facing
                    pin["turn_short"] = turn_short
                    if abs(turn_drag) > 0.1:
                        pin["place_turn"] = turn_drag
                    if pin.get("scene_root"):
                        pin["scene_root"] = [v + d for v, d in zip(pin["scene_root"], drag)]
                    if any(abs(value) > 0.01 for value in drag):
                        pin["place"] = drag
            elif placed and holds:
                pin["main_target"] = placed
                pin["main_hold"] = True
        pin["edited"] = True
        # RECALCULATE reads an un-keyed pose again in case it was changed after
        # Update. If it was not, the pose and the undo queue stay as they are.
        if frame in self._unapplied and core.same_pose(pin, old):
            return
        self._poses[frame] = pin
        self._unapplied.add(frame)
        self._poses_changed = True
        self._store_poses()
        self._refresh_poses()

    def _new_pose(self):
        context = self._pose_context()
        if not context:
            return
        target, solve = context
        frame = self._timeline_take_frame(solve["start_frame"])
        if not 0 <= frame < solve["frames"]:
            self._say("The timeline is outside the take, which runs from "
                      "frame %d to %d."
                      % (core.take_frame_to_scene(0, solve["start_frame"]),
                         core.take_frame_to_scene(solve["frames"] - 1,
                                                  solve["start_frame"])))
            return
        try:
            self._capture_pose(target, solve, frame)
        except Exception as error:
            self._say("Could not read the pose: %s" % error)
            traceback.print_exc()
            return
        self._say("Pose kept on this frame. Go on to the next, or press "
                  "RECALCULATE.")

    def _update_pose(self, frame):
        context = self._pose_context()
        if not context:
            return
        target, solve = context
        if self._timeline_take_frame(solve["start_frame"]) != frame:
            self._say("The timeline has moved off this pose. Click the pose, "
                      "adjust it, then press Update.")
            return
        try:
            self._capture_pose(target, solve, frame)
        except Exception as error:
            self._say("Could not read the pose: %s" % error)
            traceback.print_exc()
            return
        self._say("Pose updated. Press RECALCULATE when the poses are ready.")

    def _open_pose(self, frame):
        """Go to a pose and show it on the character and its controls."""
        start = self._solve["start_frame"] if self._solve else 1
        cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion go to pose")
        try:
            cmds.currentTime(core.take_frame_to_scene(frame, start), edit=True)
            if frame in self._unapplied:
                try:
                    core.load_pose_on_rig(self.line_target.text().strip(),
                                          self._poses[frame])
                except Exception as error:
                    self._say("Could not show the pose: %s" % error)
                    traceback.print_exc()
                    return
        finally:
            cmds.undoInfo(closeChunk=True)
        self._say("Adjust it with the controls and press Update, or Delete.")

    def _delete_pose(self, frame):
        if self._process is not None:
            self._say("A solve is already running.")
            return
        pin = self._poses.pop(frame, None)
        if pin is None:
            return
        if frame in self._unapplied:
            self._unapplied.discard(frame)
            # It may still be on the controls, unkeyed, and Recalculate would
            # take it for a new pose.
            with core.quietly():
                now = cmds.currentTime(query=True)
                cmds.currentTime(now + 1, edit=True)
                cmds.currentTime(now, edit=True)
        elif pin.get("edited", True):
            self._released.add(frame)
        self._poses_changed = True
        self._store_poses()
        self._refresh_poses()
        self._say("Pose deleted. Press RECALCULATE when the poses are ready.")

    def _pose_accuracy_changed(self, value):
        self._pose_accuracy = value
        # The poses are the same, but what the bake does with them is not.
        if self._poses:
            self._poses_changed = True

    def _recalculate(self):
        context = self._pose_context()
        if not context:
            return
        target, solve = context
        try:
            # A pose made but not kept is still on the controls. Read it first:
            # nothing below may move the timeline before it is safe.
            if core.has_unkeyed_pose(target):
                frame = self._timeline_take_frame(solve["start_frame"])
                if 0 <= frame < solve["frames"]:
                    self._capture_pose(target, solve, frame)
            if not self._poses_changed:
                self._say("No pose has changed, so there is nothing to "
                          "recalculate.")
                return
            placed = core.warp_pose_roots(self._poses, target, solve["start_frame"],
                                          self._released)
            pins = core.pose_pins(placed, self._released)
            if not pins:
                self._say("No poses left. Press ANALYZE POSES, or GENERATE "
                          "MOTION for a fresh take.")
                return
            self._take_dir = core.new_take_dir(self._install["root"])
            hard = any(pin.get("mode") in core.PIN_MODES_NEEDING_HARD
                       for pin in pins)
            argv = core.build_constrain_command(
                solve["model"], self._take_dir, solve["prompt"],
                solve["frames"], solve["steps"], solve["seed"], pins,
                self._install["root"], pin_weight=core.EDIT_PIN_WEIGHT,
                hard=hard)
        except Exception as error:
            self._say("Could not recalculate: %s" % error)
            traceback.print_exc()
            return

        self.spin_start.setValue(solve["start_frame"])
        back_to = self._timeline_take_frame(solve["start_frame"])
        self._inflight = {"solve": solve, "poses": placed,
                          "edited_frame": back_to, "stored": self._stored}
        self._embed_prompt = solve["prompt"]
        self._launch(argv)

    def _after_recalculate(self, target, frame):
        """The animation changed, so the poses that describe it are read again."""
        solve = self._solve
        self._unapplied = set()
        self._released = set()
        self._poses_changed = False
        fresh = [f for f, pin in self._poses.items() if not pin.get("edited", True)]
        edited = [f for f in self._poses if f not in fresh]
        try:
            self._poses.update(core.analyze_poses(target, fresh,
                                                  solve["start_frame"]))
            # Soft pins fall a little short. Remembered for the next Update of
            # the pose, since auto key can change the curves before then.
            reached = core.analyze_poses(target, edited, solve["start_frame"])
            for f in edited:
                self._poses[f]["reached"] = reached[f]["root"][1]
        except Exception:
            traceback.print_exc()
        self._store_poses()
        self._refresh_poses()
        cmds.currentTime(core.take_frame_to_scene(frame, solve["start_frame"]),
                         edit=True)

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
                self._say("No character in the scene - load one in CHARACTER, "
                          "or read from the pose rig.")
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
                self._say("No character in the scene - load one in CHARACTER.")
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
        frame = self._timeline_take_frame(self.spin_start.value())
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
                    raise RuntimeError("no character in the scene - load one in CHARACTER")
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
        if self._process is not None:
            self._say("A solve is already running.")
            return
        target = self.line_target.text().strip()
        if not target or not cmds.objExists(target):
            self._say("Set the target rig first.")
            return
        try:
            cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion clear rig")
            try:
                info = core.clear_rig(target)
                core.prime_references(target)
            finally:
                cmds.undoInfo(closeChunk=True)
        except Exception as error:
            self._say("Could not clear the rig: %s" % error)
            traceback.print_exc()
            return
        self._stored = core.solve_text(target)
        self._solve, self._poses = None, {}
        self._unapplied = set()
        self._released = set()
        self._poses_changed = False
        self._refresh_poses()
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

    # -- undo ------------------------------------------------------------- #

    def showEvent(self, event):
        super().showEvent(event)
        if om2 is not None and not self._undo_callbacks:
            self._undo_callbacks = [
                om2.MEventMessage.addEventCallback(name, self._undo_happened, name)
                for name in ("Undo", "Redo")]

    def _stop_watching_undo(self):
        callbacks, self._undo_callbacks = self._undo_callbacks, []
        for callback in callbacks:
            om2.MMessage.removeCallback(callback)

    def _undo_happened(self, event):
        # Maya is still inside the undo here, so the marks wait until it is out.
        QtCore.QTimer.singleShot(0, lambda: self._follow_undo(event))

    def _follow_undo(self, event):
        """Undo moved the scene under the tool: take the poses back from the rig."""
        try:
            target = self.line_target.text().strip()
        except RuntimeError:
            self._stop_watching_undo()
            return
        if self._last_take and not cmds.objExists(self._last_take.get("top") or ""):
            self._last_take = None
            self._refresh_retarget_button()
        if not target or not cmds.objExists(target):
            # The character itself was undone.
            if self._solve or self._poses:
                self._solve, self._poses = None, {}
                self._unapplied, self._released = set(), set()
                self._poses_changed = False
                self._stored = ""
                self._refresh_poses()
            return
        if core.solve_text(target) == self._stored:
            return
        before = set(self._unapplied)
        baked_state = self._stored
        self._load_poses(target)
        if event == "Redo" and self._pending is self._armed:
            self._pending = None
        # An undo of the bake itself leaves its take in the scene to bake again.
        if (event == "Undo" and self._baked and not self._pending
                and baked_state == self._baked[2]):
            take, pending = self._baked[:2]
            if cmds.objExists(take.get("top") or ""):
                self._last_take, self._pending = take, copy.deepcopy(pending)
                self._armed = self._pending
                self._refresh_retarget_button()
        self._refresh_poses()
        # Whatever the status said was about the step just taken back.
        self._say("Undone." if event == "Undo" else "Redone.")
        if not self._solve:
            return
        frame = self._timeline_take_frame(self._solve["start_frame"])
        try:
            with core.quietly():
                if event == "Undo":
                    # The delete of a pose nobody baked took it off the controls,
                    # so undoing the delete puts it back on them.
                    if (frame in self._unapplied and frame not in before
                            and frame in self._poses):
                        core.load_pose_on_rig(target, self._poses[frame])
                elif frame in before and frame not in self._unapplied:
                    # Redo of that delete takes it off again. Only redo: on undo
                    # this would wipe a pose the animator is still working on.
                    now = cmds.currentTime(query=True)
                    cmds.currentTime(now + 1, edit=True)
                    cmds.currentTime(now, edit=True)
        except Exception:
            traceback.print_exc()

    def closeEvent(self, event):
        self._stop_watching_undo()
        if self._pose_dialog is not None:
            self._pose_dialog.close()
        process, self._process = self._process, None
        if process is not None:
            process.finished.disconnect(self._on_finished)
            process.errorOccurred.disconnect(self._on_error)
            process.kill()
            process.waitForFinished(3000)
            process.deleteLater()
            core.discard_unfinished_take(self._take_dir)
        self._timer.stop()
        super().closeEvent(event)


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
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() != WINDOW_OBJECT_NAME:
            continue
        # Opening the tool again must not kill a solve it is waiting for.
        if getattr(widget, "_process", None) is not None:
            _WIN = widget
            _WIN.show()
            _WIN.raise_()
            return _WIN
        widget.close()
        widget.deleteLater()
    global UI_VERSION
    UI_VERSION = getattr(core, "VERSION", "?")
    _WIN = AZKimodoMotionWindow(parent=_maya_main_window())
    _WIN.show()
    _WIN.raise_()
    print("[AZ Kimodo Motion %s] window open - core %s" % (UI_VERSION, core.__file__))
    return _WIN
