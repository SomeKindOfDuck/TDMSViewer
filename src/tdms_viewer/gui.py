from pathlib import Path
from typing import Any

from PyQt6 import QtCore, QtWidgets

from core import load_settings_yaml, make_dummy_df
from core.colors import ICEBERG_DARK, apply_colorscheme
from core.datasource import TimeData
from core.plotstack import DataPlotStack
from panel.action_panel import TDMSActionPanel
from panel.param_panel import TDMSSettingPanel, TDMSSettings
from panel.plot_panel import AnalogPlot, BinPlot


class TDMSViewer(QtWidgets.QApplication):
    def __init__(
            self,
            ds: TimeData,
            cols: list[str],
            size: tuple[int, int] = (1600, 800),
        ):
        import sys
        super().__init__(sys.argv)
        apply_colorscheme(self, ICEBERG_DARK)
        self.window = QtWidgets.QMainWindow()
        self.window.resize(*size)

        self.settings = TDMSSettings()
        self.cols = cols
        self.ds = ds

        self.analog_plot = AnalogPlot(self.ds, settings=self.settings)
        self.bin_plot = BinPlot(self.ds, settings=self.settings)
        self.analog_plot.set_signals(cols)
        self.bin_plot.set_signals(cols)
        self.stack = DataPlotStack(
            [self.analog_plot, self.bin_plot],
            link_x=True,
            show_x_axis_only_bottom=True
        )

        colors = self.analog_plot.colors
        [self.settings.add_col(col) for col in cols]
        self.setting_panel = TDMSSettingPanel(settings=self.settings, cols=cols, colors=colors)
        if (default_settings := load_settings_yaml()) is not None:
            if (visibility := default_settings.get("visible")) is not None:
                default_cols = list(visibility.keys())
                if default_cols == cols:
                    self.settings.apply_settings_dict(default_settings)
                    self.setting_panel.sync_all_from_settings()

        self.action_panel = TDMSActionPanel()
        self.override_apply_event_count()
        self._connect_action_buttons()

        self.right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.setting_panel, 0)
        # right_layout.addStretch(1)
        right_layout.addWidget(self.action_panel, 0)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.stack)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([1150, 450])

        self.window.setCentralWidget(self.splitter)
        self.window.show()

    def override_apply_event_count(self):
        import numpy as np
        def _count_onsets_from_binary(yb: np.ndarray) -> int:
            """
            Count 0->1 onsets in a binary array.
            """
            if yb is None:
                return 0

            yb = np.asarray(yb).astype(np.int8, copy=False)

            if yb.size < 2:
                return int(yb.sum() > 0)

            return int(np.sum((yb[1:] == 1) & (yb[:-1] == 0)))

        def _apply_event_count():
            from core import debounce_binary_after_schmitt, schmitt_trigger
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            for col in self.cols:
                y = self.ds.get_col(col)
                on, off = self.settings.get_for_col("threshold", col)
                yb = schmitt_trigger(y, on, off, init=0)
                debounce = self.settings.get_for_col("debounce", col)
                yb = debounce_binary_after_schmitt(yb, debounce)
                cnt = _count_onsets_from_binary(yb)

                if col in self.setting_panel.count_value_labels:
                    self.setting_panel.count_value_labels[col].setText(str(cnt))
            QtWidgets.QApplication.restoreOverrideCursor()

        self.setting_panel.apply_event_count = _apply_event_count
        self.setting_panel.count_btn.clicked.connect(self.setting_panel.apply_event_count)

    def _connect_action_buttons(self):
        self.action_panel.btn_load_tdms.clicked.connect(self._on_load_tdms)
        self.action_panel.btn_save_tdms.clicked.connect(self._on_save_as)
        self.action_panel.btn_set_default.clicked.connect(self._on_set_default)
        self.action_panel.btn_save_yaml.clicked.connect(self._on_save_yaml)
        self.action_panel.btn_load_yaml.clicked.connect(self._on_load_yaml)

    def _on_load_tdms(self):
        from nptdms import TdmsFile

        from panel.selecter import ColumnSelectDialog

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Load TDMS",
            "./",
            "TDMS files (*.tdms);;All files (*)"
        )
        if not path:
            return
        self._tdms_path = path

        try:
            tdms = TdmsFile.read(path)

            all_channels = self.action_panel.list_tdms_channels(tdms)
            if not all_channels:
                QtWidgets.QMessageBox.warning(
                    self.window,
                    "No channels",
                    "このTDMSファイルにはチャネルがありません。"
                )
                return

            dlg = ColumnSelectDialog(all_channels, title="Select TDMS channels", parent=self.window)
            for cb in dlg.checks.values():
                cb.setChecked(True)

            if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return

            selected_channels = dlg.selected()
            if not selected_channels:
                QtWidgets.QMessageBox.warning(
                    self.window,
                    "No selection",
                    "少なくとも1つチャネルを選択してください。"
                )
                return

            df = self.action_panel.tdms_to_dataframe(tdms, selected_channels)
            self.load_dataframe(df)
            self.analog_plot._max_window = self.ds.nrow
            self.bin_plot._max_window = self.ds.nrow

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.window,
                "Load TDMS error",
                f"TDMSの読み込みに失敗しました。\n{e}"
            )

    def _on_save_as(self):
        from pathlib import Path

        import numpy as np
        import pandas as pd
        from PyQt6 import QtWidgets

        from core import (as_binary_dataframe, debounce_binary_after_schmitt,
                          schmitt_trigger)
        from panel.selecter import ColumnSelectDialog

        dlg = ColumnSelectDialog(self.cols, title="Select TDMS channels", parent=self.window)
        for cb in dlg.checks.values():
            cb.setChecked(True)

        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        selected_channels = dlg.selected()

        default_path = None
        if hasattr(self, "_tdms_path") and self._tdms_path:
            p = Path(self._tdms_path)
            default_path = p.with_name(p.stem + "_binary.csv")

        out = as_binary_dataframe(self.ds, selected_channels, self.settings)

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Save binary events CSV",
            str(default_path) if default_path else "",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        out.to_csv(path, index=False)
        QtWidgets.QMessageBox.information(self.window, "Successfully saved", f"{path} is successfully saved")

    def _on_set_default(self):
        try:
            self.action_panel.save_settings_yaml(self.settings.as_dict())
            QtWidgets.QMessageBox.information(
                self.window,
                "Saved",
                "default.yaml を保存しました。"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.window,
                "Error",
                f"default.yaml の保存に失敗しました:\n{e}"
            )

    def _on_save_yaml(self):
        try:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.window,
                "Save setting",
                "",
                "YAML file (*.yaml, *.yml)"
            )
            self.action_panel.save_settings_yaml(self.settings.as_dict(), path=path)
            QtWidgets.QMessageBox.information(
                self.window,
                "Saved",
                f"{path} を保存しました。"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.window,
                "Error",
                f"設定ファイルの保存に失敗しました:\n{e}"
            )

    def _on_load_yaml(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
        self.window,
        "Load YAML",
        "",
        "YAML files (*.yaml *.yml);;All files (*)"
        )

        if not path:
            return

        new_settings = self.action_panel.load_settings_yaml(path)

        if (visibility := new_settings.get("visible")) is not None:
            setting_cols = list(visibility.keys())
            if setting_cols == self.cols:
                self.settings.apply_settings_dict(new_settings)
                self.setting_panel.sync_all_from_settings()

    def load_dataframe(self, df):
        from core.datasource import TimeData
        from panel.param_panel import TDMSSettingPanel, TDMSSettings

        cols = list(df.columns)

        self.ds = TimeData(df)
        self.cols = cols

        self.settings = TDMSSettings()
        for col in cols:
            self.settings.add_col(col)

        self.analog_plot.ds = self.ds
        self.bin_plot.ds = self.ds

        self.analog_plot.set_settings(self.settings)
        self.bin_plot.set_settings(self.settings)

        self.analog_plot.set_signals(cols)
        self.bin_plot.set_signals(cols)

        colors = self.analog_plot.colors
        new_panel = TDMSSettingPanel(settings=self.settings, cols=cols, colors=colors)

        layout = self.right_panel.layout()
        old_panel = self.setting_panel
        layout.replaceWidget(old_panel, new_panel)
        old_panel.setParent(None)
        old_panel.deleteLater()
        self.setting_panel = new_panel

        self.override_apply_event_count()

def main():
    import sys

    df = make_dummy_df(N=300_000, fs=1000)
    ds = TimeData(df)

    tdms_viewer = TDMSViewer(ds, ["sin_3hz", "sin_4hz"])
    sys.exit(tdms_viewer.exec())
