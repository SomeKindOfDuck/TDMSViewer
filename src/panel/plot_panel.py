import numpy as np
from PyQt6 import QtCore, QtGui

from core import debounce_binary_after_schmitt, schmitt_trigger
from core.plot import DataPlot


class AnalogPlot(DataPlot):
    REFRESH_KEY_EVENT = ["threshold", "invert_y"]
    def __init__(self, *args, **kwargs):
        self.on_lines = {}
        self.off_lines = {}
        super().__init__(*args, **kwargs)
        self.setYRange(-1, 5, padding=0)

    def set_signals(self, cols: list[str]):
        from itertools import cycle

        import pyqtgraph as pg

        for lines in list(self.on_lines.values()):
            self.removeItem(lines)
        for lines in list(self.off_lines.values()):
            self.removeItem(lines)
        self.on_lines.clear()
        self.off_lines.clear()

        super().set_signals(cols)

        for col, color in zip(self._cols, cycle(self._theme_colors)):
            qcol = QtGui.QColor(color)
            qcol_dim = QtGui.QColor(qcol)
            qcol_dim.setAlpha(90)
            on_pen = pg.mkPen(qcol_dim, width=1.75, style=QtCore.Qt.PenStyle.DotLine)
            off_pen = pg.mkPen(qcol_dim, width=1.75, style=QtCore.Qt.PenStyle.DashLine)

            on, off = self._settings.get("threshold", {}).get(col, (0., 0.))
            on_line = pg.InfiniteLine(pos=float(on), angle=0, pen=on_pen, movable=False)
            off_line = pg.InfiniteLine(pos=float(off), angle=0, pen=off_pen, movable=False)

            on_line.setZValue(50)
            off_line.setZValue(50)

            self.on_lines[col] = on_line
            self.off_lines[col] = off_line
            self.addItem(on_line)
            self.addItem(off_line)

    def _sync_signal_visibility(self, col: str):
        super()._sync_signal_visibility(col)
        sig = self.signals.get(col)
        on_line = self.on_lines.get(col)
        off_line = self.off_lines.get(col)
        if sig is None or on_line is None or off_line is None:
            return
        on_line.setVisible(sig.visible)
        off_line.setVisible(sig.visible)

    def refresh(self):
        for col in list(self.on_lines.keys()):
            sig = self.signals.get(col)
            if sig is None or not sig.visible:
                continue
            on, off = self._settings.get("threshold", {}).get(col, (0., 0.))
            self.on_lines[col].setPos(float(on))
            self.off_lines[col].setPos(float(off))
        super().refresh()

    def refresh_one(self, col: str):
        super().refresh_one(col)
        sig = self.signals.get(col)
        if sig is None or not sig.visible:
            return
        on, off = self._settings.get("threshold", {}).get(col, (0., 0.))
        self.on_lines[col].setPos(float(on))
        self.off_lines[col].setPos(float(off))

    def process_signal(self, sig: np.ndarray, col: str | None = None) -> np.ndarray:
        if self._settings.get("invert_y", {}).get(col, False):
            return -sig
        return sig

    def on_settings_changed(self, ev):
        super().on_settings_changed(ev)
        if ev.scope == "col" and (ev.key in self.REFRESH_KEY_EVENT):
            self.refresh_one(ev.col)


class BinPlot(DataPlot):
    REFRESH_KEY_EVENT = ["threshold", "debounce", "invert_y"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setYRange(0, 1, padding=0.1)

    def process_signal(self, sig: np.ndarray, col: str | None = None):
        if self._settings.get("invert_y", {}).get(col, False):
            sig = -sig
        on, off = self._settings.get("threshold", {}).get(col, (0., 0.))
        bin_sig = schmitt_trigger(sig, on, off)
        n = self._settings.get("debounce", {}).get(col, 0)
        if n and n > 0:
            bin_sig = debounce_binary_after_schmitt(bin_sig, n)
        return bin_sig

    def on_settings_changed(self, ev):
        super().on_settings_changed(ev)
        if ev.scope == "col" and ev.key in self.REFRESH_KEY_EVENT:
            self.refresh_one(ev.col)
