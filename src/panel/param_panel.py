from pathlib import Path
from typing import Any

from PyQt6 import QtCore, QtWidgets

from core.components import ParameterSettings, SettingEvent


class TDMSSettings(ParameterSettings):
    def __init__(self, cols: list[str] | None = None, parent=None):
        super().__init__(parent)

        if cols is None:
            cols = []
        self._d["visible"] = {col: True for col in cols}
        self._d["invert_y"] = {col: False for col in cols}
        self._d["single"] = {col: False for col in cols}
        self._d["threshold"] = {col: (0.1, 0.1) for col in cols}
        self._d["debounce"] = {col: 0 for col in cols}

    def add_col(self, col: str) -> None:
        self._d["visible"].setdefault(col, True)
        self._d["invert_y"].setdefault(col, False)
        self._d["single"].setdefault(col, False)
        self._d["threshold"].setdefault(col, (0.1, 0.1))
        self._d["debounce"].setdefault(col, 0)

        self.changed.emit(
            SettingEvent(key="__add_col__", scope="col", col=col)
        )

    def remove_col(self, col: str) -> None:
        for key in ("visible", "invert_y", "single", "threshold", "debounce"):
            d = self._d.get(key)
            if isinstance(d, dict):
                d.pop(col, None)

        self.changed.emit(
            SettingEvent(key="__remove_col__", scope="col", col=col)
        )

    def format_for_yaml(self) -> dict[str, Any]:
        out = {}

        data = self.as_dict()
        for key, value in data.items():
            if key == "threshold" and isinstance(value, dict):
                out[key] = {}
                for col, v in value.items():
                    out[key][col] = v
            elif isinstance(value, dict):
                out[key] = value
            else:
                out[key] = value

        return out

    def apply_settings_dict(self, data: dict):
        if not data:
            return

        if "fs" in data:
            self.set("fs", data["fs"])

        for key in ("visible", "invert_y", "single", "threshold", "debounce"):
            if key not in data:
                continue

            for col, val in data[key].items():
                self.add_col(col)
                self.set_for_col(key, col, val)


class TDMSSettingPanel(QtWidgets.QWidget):
    COL_CHANNEL = 0
    COL_INVERT = 1
    COL_SINGLE = 2
    COL_ONSET = 3
    COL_OFFSET = 4
    COL_DEBOUNCE = 5

    def __init__(self, settings: TDMSSettings, cols: list[str], colors: list[str], parent = None):
        super().__init__(parent)
        self._settings = settings
        self._settings.changed.connect(self._on_settings_changed)

        self.setMinimumWidth(300)
        self.setObjectName("SettingPanel")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        glbset_lab = QtWidgets.QLabel("Global setting")
        glbset_lab.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        glbset_lab.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(glbset_lab)

        layout.addSpacing(5)
        sr_box = self._build_sr_box()
        layout.addWidget(sr_box)

        solo_box = self._build_solo_box()
        layout.addWidget(solo_box)

        layout.addSpacing(10)
        varset_lab = QtWidgets.QLabel("Variable settings")
        varset_lab.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(varset_lab)
        layout.addSpacing(10)

        self.lab_style_on = {}
        self.lab_style_off = {}

        self.labels = {}
        self.single_checks = {}
        self.invert_checks = {}
        self.inverted = {}
        self.offthr_boxes = {}
        self.onthr_boxes = {}
        self.debounce_boxes = {}

        varset_rows = self.build_threshold_panel(cols, colors)
        layout.addWidget(varset_rows, 0)
        layout.addSpacing(10)

        self.count_btn = self._build_count_btn()
        layout.addWidget(self.count_btn)

        counts_lab = QtWidgets.QLabel("Event counts")
        counts_lab.setStyleSheet("font-weight: bold; font-size: 16px")
        layout.addWidget(counts_lab)
        layout.addSpacing(10)
        layout.addWidget(self._build_count_panel(cols, colors), 0)

        layout.addStretch(1)

    #########################################
    #### Global setting 設定関連メソッド ####
    #########################################
    def _build_sr_box(self) -> QtWidgets.QWidget:
        sr_row = QtWidgets.QWidget()
        sr_lay = QtWidgets.QHBoxLayout(sr_row)
        sr_lay.setContentsMargins(0, 0, 0, 6)
        sr_lay.setSpacing(6)
        sr_label = QtWidgets.QLabel("Sampling rate")
        sr_label.setStyleSheet("opacity: 0.85;")

        self.sr_box = QtWidgets.QSpinBox()
        self.sr_box.setRange(100, 100_000)
        self.sr_box.setSingleStep(100)
        self.sr_box.setValue(1000)
        self.sr_box.valueChanged.connect(self._on_sampling_rate_changed)
        self.sr_box.setSuffix(" Hz")
        self.sr_box.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.sr_box.setFixedWidth(100)

        sr_lay.addWidget(sr_label)
        sr_lay.addStretch(0)
        sr_lay.addWidget(self.sr_box)

        return sr_row

    def _on_sampling_rate_changed(self, fs_new: int):
        self._settings.set("fs", fs_new)

    def _build_solo_box(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 6)
        lay.setSpacing(6)

        label = QtWidgets.QLabel("Single view")
        label.setStyleSheet("opacity: 0.85;")

        self.solo_mode_check = QtWidgets.QCheckBox()
        self.solo_mode_check.setChecked(False)
        self.solo_mode_check.setToolTip("Show only one channel at a time")
        self.solo_mode_check.stateChanged.connect(self._on_solo_mode_changed)

        lay.addWidget(label)
        lay.addStretch(0)
        lay.addWidget(self.solo_mode_check)

        return row

    def _on_solo_mode_changed(self, _state):
        solo = self.solo_mode_check.isChecked()
        self._settings.set("solo_mode", solo)

        if not solo:
            return

        cols = list(self.labels.keys())
        if not cols:
            return

        visible_cols = [
            col for col in cols
            if self._settings.get_for_col("visible", col, True)
        ]

        if len(visible_cols) == 1:
            return

        keep = visible_cols[0] if len(visible_cols) > 0 else cols[0]

        for col in cols:
            self._settings.set_for_col("visible", col, col == keep)

    ####################################
    #### 変数ごとの設定関連メソッド ####
    ####################################
    def build_threshold_panel(self, cols: list[str], colors: list[str]) -> QtWidgets.QWidget:
        from core.components import ClickableLabel

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll_area.setMinimumHeight(100)

        thr_inner = QtWidgets.QWidget()
        thr_layer = QtWidgets.QGridLayout(thr_inner)
        thr_layer.setContentsMargins(0, 0, 0, 6)
        thr_layer.setRowStretch(999, 1)
        scroll_area.setWidget(thr_inner)

        channel_header = ClickableLabel("Channel")
        channel_header.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        channel_header.clicked.connect(self._on_channel_header_clicked)

        invert_header = ClickableLabel("Invert")
        invert_header.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        invert_header.clicked.connect(self._on_invert_header_clicked)

        single_header = ClickableLabel("Single")
        single_header.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        single_header.clicked.connect(self._on_single_header_clicked)

        thr_layer.addWidget(channel_header,               0, self.COL_CHANNEL)
        thr_layer.addWidget(invert_header,                0, self.COL_INVERT)
        thr_layer.addWidget(single_header,                0, self.COL_SINGLE)
        thr_layer.addWidget(QtWidgets.QLabel("On"),       0, self.COL_ONSET)
        thr_layer.addWidget(QtWidgets.QLabel("Off"),      0, self.COL_OFFSET)
        thr_layer.addWidget(QtWidgets.QLabel("Debounce"), 0, self.COL_DEBOUNCE)

        for row, (col, color) in enumerate(zip(cols, colors), start=1):
            self._set_col(thr_layer, row, col, color)

        return scroll_area

    def _set_col(self, layout: QtWidgets.QGridLayout, row: int, col: str, color: str):
        from core.components import ClickableLabel
        lab = ClickableLabel(col)
        lab.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        lab.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        lab.clicked.connect(lambda c=col: self._toggle_visible(c))

        style_on = f"padding-left: 6px; border-left: 6px solid {color};"
        style_off = "padding-left: 6px; border-left: 6px solid #666; color: #777;"
        lab.setStyleSheet(style_on)

        self.labels[col] = lab
        self.lab_style_on[col] = style_on
        self.lab_style_off[col] = style_off

        layout.addWidget(lab, row, self.COL_CHANNEL)

        inv = QtWidgets.QCheckBox()
        inv.setToolTip("Invert Y (multiply by -1 for display)")
        inv.setChecked(False)
        inv.stateChanged.connect(lambda _st, c=col: self._on_invert_changed(c))
        self.invert_checks[col] = inv
        layout.addWidget(inv, row, self.COL_INVERT)

        chk = QtWidgets.QCheckBox()
        chk.setToolTip("Single threshold: upper follows off threshold (disable Upper)")
        chk.setChecked(False)
        chk.stateChanged.connect(lambda _st, c=col: self._on_single_changed(c))
        self.single_checks[col] = chk
        layout.addWidget(chk, row, self.COL_SINGLE)

        offthr = QtWidgets.QDoubleSpinBox()
        onthr = QtWidgets.QDoubleSpinBox()
        for sb in (offthr, onthr):
            sb.setDecimals(3)
            sb.setRange(-10, 10)
            sb.setSingleStep(0.05)
            sb.setKeyboardTracking(False)
            sb.setAccelerated(True)
            sb.setFixedWidth(70)

        offthr.setValue(0.1)
        onthr.setValue(0.1)
        offthr.setEnabled(True)

        onthr.valueChanged.connect(lambda v, c=col: self._on_threshold_changed(c, which="on", val=v))
        offthr.valueChanged.connect(lambda v, c=col: self._on_threshold_changed(c, which="off", val=v))

        self.offthr_boxes[col] = offthr
        self.onthr_boxes[col] = onthr

        layout.addWidget(onthr, row, self.COL_ONSET)
        layout.addWidget(offthr, row, self.COL_OFFSET)

        deb = QtWidgets.QDoubleSpinBox()
        deb.setDecimals(0)
        deb.setRange(0, 9999)
        deb.setSingleStep(1)
        deb.setKeyboardTracking(False)
        deb.setAccelerated(True)
        deb.setFixedWidth(60)
        deb.valueChanged.connect(lambda v, c=col: self._on_debounce_changed(c, v))
        self.debounce_boxes[col] = deb
        layout.addWidget(deb, row, self.COL_DEBOUNCE)

    def _toggle_visible(self, col: str):
        solo_mode = bool(self._settings.get("solo_mode", False))

        if solo_mode:
            for c in self.labels.keys():
                self._settings.set_for_col("visible", c, c == col)
            return

        new_vis = not self._settings.get_for_col("visible", col)
        if new_vis:
            self.labels[col].setStyleSheet(self.lab_style_on[col])
        else:
            self.labels[col].setStyleSheet(self.lab_style_off[col])
        self._settings.set_for_col("visible", col, new_vis)

    def _on_channel_header_clicked(self):
        cols = list(self.labels.keys())
        if not cols:
            return

        all_visible = all(
            self._settings.get_for_col("visible", col, True)
            for col in cols
        )
        new_visible = not all_visible

        for col in cols:
            self._settings.set_for_col("visible", col, new_visible)

    def _on_invert_changed(self, col):
        new_invert = not self._settings.get_for_col("invert_y", col)
        self._settings.set_for_col("invert_y", col, new_invert)

    def _on_invert_header_clicked(self):
        cols = list(self.labels.keys())
        if not cols:
            return

        all_invert = all(
            self._settings.get_for_col("invert_y", col, True)
            for col in cols
        )
        new_invert = not all_invert

        for col in cols:
            self._settings.set_for_col("invert_y", col, new_invert)

    def _on_single_changed(self, col):
        new_single = self.single_checks[col].isChecked()
        self._settings.set_for_col("single", col, new_single)

        on_box = self.onthr_boxes[col]
        off_box = self.offthr_boxes[col]

        if new_single:
            v = float(on_box.value())
            off_box.blockSignals(True)
            off_box.setValue(v)
            off_box.setEnabled(False)
            off_box.blockSignals(False)
            self._settings.set_for_col("threshold", col, (v, v))
        else:
            off_box.setEnabled(True)
            on = float(on_box.value())
            off = float(off_box.value())
            if off > on:
                off_box.blockSignals(True)
                off_box.setValue(on)
                off_box.blockSignals(False)
                off = on
            self._settings.set_for_col("threshold", col, (on, off))

    def _on_single_header_clicked(self):
        cols = list(self.labels.keys())
        if not cols:
            return

        all_single = all(
            self._settings.get_for_col("single", col, True)
            for col in cols
        )
        new_single = not all_single

        for col in cols:
            self._settings.set_for_col("single", col, new_single)

    def _on_threshold_changed(self, col: str, val: float, which: str):
        on_box = self.onthr_boxes[col]
        off_box = self.offthr_boxes[col]
        on = float(on_box.value())
        off = float(off_box.value())
        single = bool(self.single_checks[col].isChecked())

        if single:
            if which == "off":
                off_box.setValue(on)
                return

            if single:
                on_box.setValue(val)
                off_box.setValue(val)
                self._settings.set_for_col("threshold", col, (on, on))
                return

        if which == "on":
            if float(val) < off:
                on_box.setValue(off)
                on = off
            else:
                on = float(val)
        else:

            if float(val) > on:
                off_box.setValue(on)
                off = on
            else:
                off = float(val)

        self._settings.set_for_col("threshold", col, (on, off))

    def _on_debounce_changed(self, col: str, val: float):
        self._settings.set_for_col("debounce", col, val)

    ##################################
    #### Count button関連メソッド ####
    ##################################
    def _build_count_btn(self) -> QtWidgets.QWidget:
        count_btn = QtWidgets.QPushButton("Apply (count events)")
        count_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.apply_event_count = lambda: None
        count_btn.clicked.connect(self.apply_event_count)
        return count_btn

    def _build_count_panel(self, cols: list[str], colors: list[str]):
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        counts_inner = QtWidgets.QWidget()
        counts_layout = QtWidgets.QGridLayout(counts_inner)
        counts_layout.setContentsMargins(0, 0, 0, 0)
        counts_layout.setHorizontalSpacing(12)
        counts_layout.setVerticalSpacing(6)
        scroll_area.setWidget(counts_inner)

        self.count_value_labels = {}
        for row, (col, color) in enumerate(zip(cols, colors)):
            name = QtWidgets.QLabel(col)
            name.setStyleSheet(f"padding-left: 6px; border-left: 6px solid {color};")

            val = QtWidgets.QLabel("—")
            val.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            val.setMinimumWidth(80)

            counts_layout.addWidget(name, row, 0)
            counts_layout.addWidget(val,  row, 1)
            self.count_value_labels[col] = val
        return scroll_area

    ################################################
    #### yamlファイルの読み込み時のUIの更新処理 ####
    ################################################
    def _set_checkbox_safely(self, cb: QtWidgets.QCheckBox, checked: bool):
        old = cb.blockSignals(True)
        cb.setChecked(bool(checked))
        cb.blockSignals(old)

    def _set_spinbox_safely(self, sb: QtWidgets.QAbstractSpinBox, value):
        old = sb.blockSignals(True)
        if isinstance(sb, QtWidgets.QSpinBox):
            sb.setValue(int(value))
        else:
            sb.setValue(float(value))
        sb.blockSignals(old)

    def _apply_visible_ui(self, col: str, visible: bool):
        lab = self.labels.get(col)
        if lab is None:
            return
        if visible:
            lab.setStyleSheet(self.lab_style_on[col])
        else:
            lab.setStyleSheet(self.lab_style_off[col])

    def _apply_single_ui(self, col: str, single: bool):
        off_box = self.offthr_boxes.get(col)
        if off_box is None:
            return
        off_box.setEnabled(not single)

    def _on_settings_changed(self, ev):
        if ev.scope == "global" and ev.key == "fs":
            self._set_spinbox_safely(self.sr_box, ev.value)
            return

        if ev.scope == "global" and ev.key == "solo_mode":
            self._set_checkbox_safely(self.solo_mode_check, ev.value)
            return

        if ev.scope != "col" or ev.col is None:
            return

        col = ev.col
        if col not in self.labels:
            return

        if ev.key == "visible":
            self._apply_visible_ui(col, bool(ev.value))
            return

        if ev.key == "invert_y":
            cb = self.invert_checks.get(col)
            if cb is not None:
                self._set_checkbox_safely(cb, ev.value)
            return

        if ev.key == "single":
            cb = self.single_checks.get(col)
            if cb is not None:
                self._set_checkbox_safely(cb, ev.value)
            self._apply_single_ui(col, bool(ev.value))
            return

        if ev.key == "threshold":
            on_box = self.onthr_boxes.get(col)
            off_box = self.offthr_boxes.get(col)
            if on_box is None or off_box is None:
                return
            on, off = ev.value
            self._set_spinbox_safely(on_box, on)
            self._set_spinbox_safely(off_box, off)
            return

        if ev.key == "debounce":
            box = self.debounce_boxes.get(col)
            if box is not None:
                self._set_spinbox_safely(box, ev.value)
            return

    def sync_all_from_settings(self):
        self._set_spinbox_safely(self.sr_box, self._settings.get("fs", 1000))
        self._set_checkbox_safely(
            self.solo_mode_check,
            self._settings.get("solo_mode", False)
        )

        for col in self.labels.keys():
            self._apply_visible_ui(col, self._settings.get_for_col("visible", col, True))

            inv = self.invert_checks.get(col)
            if inv is not None:
                self._set_checkbox_safely(inv, self._settings.get_for_col("invert_y", col, False))

            single = self._settings.get_for_col("single", col, False)
            chk = self.single_checks.get(col)
            if chk is not None:
                self._set_checkbox_safely(chk, single)
            self._apply_single_ui(col, single)

            on, off = self._settings.get_for_col("threshold", col, (0.0, 0.0))
            if col in self.onthr_boxes:
                self._set_spinbox_safely(self.onthr_boxes[col], on)
            if col in self.offthr_boxes:
                self._set_spinbox_safely(self.offthr_boxes[col], off)

            if col in self.debounce_boxes:
                self._set_spinbox_safely(
                    self.debounce_boxes[col],
                    self._settings.get_for_col("debounce", col, 0)
                )
