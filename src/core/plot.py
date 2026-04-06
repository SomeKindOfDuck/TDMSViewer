from dataclasses import dataclass
from types import FunctionType
from typing import Callable

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtGui

from core.colors import ICEBERG_DARK_SERIES
from core.components import ParameterSettings, SecondsAxis, TrackpadXPanViewBox
from core.datasource import TimeData


@dataclass
class Signal:
    link: list[Callable[[bool], None]]
    pen: QtGui.QPen
    visible: bool = True


class DataPlot(pg.PlotWidget):
    def __init__(
        self,
        ds: TimeData,
        parent=None,
        fs: int = 1000,
        settings = ParameterSettings(),
        show_x_axis=True,
        show_legend=True,
        colors=ICEBERG_DARK_SERIES,
    ):
        self.ds = ds
        self._settings = settings
        self._settings.changed.connect(self._on_settings_changed)
        self.axis_bottom = SecondsAxis(lambda: self._settings.get("fs"), orientation="bottom")
        vb = TrackpadXPanViewBox()
        super().__init__(axisItems={"bottom": self.axis_bottom}, viewBox=vb, parent=parent)
        self.getViewBox().enableAutoRange(y=False)

        self._cols: list[str] = []
        self.signals: dict[str, Signal] = {}
        self._show_all = True
        self._win_onset = 0
        self._win_offset = 10_000
        self._min_sample = 10_000
        self._min_window = 100
        self._max_window = self.ds.nrow
        self._xpad = 0.01
        self._show_legend = True
        self._legend: pg.LegendItem | None = None
        self._legend_rows: dict[str, tuple[pg.ItemSample, pg.LabelItem]] = {}
        self._legend_all_row: tuple[pg.ItemSample, pg.LabelItem] | None = None
        self._theme_colors = ICEBERG_DARK_SERIES


        self._curves: dict[str, pg.PlotDataItem] = {}

        self.showGrid(x=True, y=True, alpha=0.1)
        self.setClipToView(True)
        self.getAxis("left").setWidth(70)

        if not show_x_axis:
            self.getAxis("bottom").setStyle(showValues=False)
            self.getAxis("bottom").hide()

        self._ignore_xrange = False

        self._buf_on = self._win_onset
        self._buf_off = self._win_onset + self._win_offset

        self.getViewBox().sigXRangeChanged.connect(self._on_xrange_changed)
        self.set_window(self._win_onset, self._win_offset, move_view=True)

    @property
    def columns(self) -> list[str]:
        return self._cols

    @property
    def colors(self) -> list[str]:
        return [self.signals[col].pen.color().name() for col in self.columns]

    def process_signal(self, sig: np.ndarray, col: str | None = None) -> np.ndarray:
        return sig

    def set_signals(self, cols: list[str]):
        from itertools import cycle

        self._cols = list(cols)

        self.clear()
        self._curves.clear()
        if self._legend is not None:
            self._legend.scene().removeItem(self._legend)
            self._legend = None
        self._legend_rows.clear()
        self._legend_all_row = None
        self._legend_all_proxy = None

        for col, color in zip(self._cols, cycle(self._theme_colors)):
            pen = pg.mkPen(color, width=1.3)
            self.signals[col] = Signal(link=[], pen=pen, visible=True)
            curve = self.plot([], [], name=col, pen=pen)
            self._curves[col] = curve


        if self._show_legend:
            self._legend = pg.LegendItem(offset=(10, 10), labelTextColor="w")
            self._legend.setParentItem(self.getViewBox())

            all_proxy = self.plot([], [], pen=pg.mkPen("#c6c8d1", width=1.3))
            self._legend.addItem(all_proxy, "All")

            all_sample, all_label = self._legend.items[-1]
            self._legend_all_row = (all_sample, all_label)

            def _all_click_handler(ev):
                self.toggle_all_visible()
                ev.accept()

            all_label.mousePressEvent = _all_click_handler
            all_sample.mousePressEvent = _all_click_handler

            for col, curve in self._curves.items():
                self._legend.addItem(curve, col)
                sample, label = self._legend.items[-1]
                self._legend_rows[col] = (sample, label)

                def _make_click_handler(_col: str):
                    def _handler(ev):
                        self.toggle_signal_visible(_col)
                        ev.accept()
                    return _handler

                label.mousePressEvent = _make_click_handler(col)
                sample.mousePressEvent = _make_click_handler(col)

            for col in self._cols:
                self._sync_signal_visibility(col)
            self._sync_all_legend_visibility()
        self.refresh()
        self.set_window(self._win_onset, self._win_offset)
        self._set_legend_bg()

    ################################
    #### Legend 関連のメソッド #####
    ################################
    def _sync_signal_visibility(self, col: str):
        """Signal.visible / curve / legend見た目 を同期する"""
        sig = self.signals.get(col)
        curve = self._curves.get(col)
        if sig is None or curve is None:
            return

        curve.setVisible(bool(sig.visible))

        row = self._legend_rows.get(col)
        if row is not None:
            sample, label = row
            sample.setOpacity(1.0 if sig.visible else 0.25)
            if sig.visible:
                color = sig.pen.color().name() if sig.pen is not None else "#FFFFFF"
                label.setText(f"<span style='color:{color}'>{col}</span>")
            else:
                label.setText(f"<span style='color:#777777'>{col}</span>")

        self._sync_all_legend_visibility()

    def _sync_all_legend_visibility(self):
        row = self._legend_all_row
        if row is None:
            return

        sample, label = row
        n_vis = sum(bool(sig.visible) for sig in self.signals.values())
        n_all = len(self.signals)

        if n_all == 0:
            sample.setOpacity(0.25)
            label.setText("<span style='color:#777777'>All</span>")
            return

        if n_vis == 0:
            sample.setOpacity(0.25)
            label.setText("<span style='color:#777777'>All</span>")
        elif n_vis == n_all:
            sample.setOpacity(1.0)
            label.setText("<span style='color:#c6c8d1'>All</span>")
        else:
            sample.setOpacity(0.7)
            label.setText("<span style='color:#c6c8d1'>All*</span>")

    def set_signal_visible(
            self,
            col: str,
            visible: bool,
            propagate = True
        ):
        signal = self.signals.get(col)
        if signal is None:
            raise KeyError(f"Unknown signal: col={col}")

        if visible == signal.visible:
            return
        signal.visible = visible

        self._sync_signal_visibility(col)

        if propagate:
            for fn in list(signal.link):
                fn(visible)

    def toggle_signal_visible(self, col: str) -> bool:
        signal = self.signals.get(col)
        if signal is None:
            raise KeyError(f"Unknown signal: col={col}")
        new_vis = not signal.visible
        self.set_signal_visible(col, new_vis, propagate=True)
        return new_vis

    def toggle_all_visible(self):
        no_vis = (sum([signal.visible for signal in self.signals.values()]) == 0)
        all_vis = (sum([not signal.visible for signal in self.signals.values()]) == 0)
        if no_vis:
            new_vis = True
        elif all_vis:
            new_vis = False
        else:
            new_vis = not self._show_all

        for col in self._cols:
            signal = self.signals.get(col)
            if signal is None:
                raise KeyError(f"Unknown signal: col={col}")
            self.set_signal_visible(col, new_vis, propagate=True)
        self._show_all = new_vis

    def get_signal_visible(self, col: str, ) -> bool:
        if col not in self.signals:
            raise KeyError(f"Unknown signal: col={col}")
        return bool(self.signals[col].visible)

    def link_signals(
        self,
        src_col: str,
        dst_plot: "DataPlot",
        dst_col: str,
        src_source: str | None = None,
        dst_source: str | None = None,
        bidirectional: bool = True,
    ) -> None:
        src_sig = self.signals[src_col]
        dst_sig = dst_plot.signals[dst_col]

        def _push_to_dst(v: bool) -> None:
            dst_plot.set_signal_visible(dst_col, v, propagate=False)

        src_sig.link.append(_push_to_dst)

        if bidirectional:
            def _push_to_src(v: bool) -> None:
                self.set_signal_visible(src_col, v, propagate=False)

            dst_sig.link.append(_push_to_src)

    def _set_legend_bg(self, border_width = 1, pad = 4, radius = 6):
        from core.colors import ICEBERG_DARK
        if self._legend is None:
            return
        try:
            self._legend.updateSize()
        except Exception:
            pass

        if not hasattr(self._legend, "_bg_path"):
            from PyQt6 import QtWidgets
            path_item = QtWidgets.QGraphicsPathItem(self._legend)
            path_item.setZValue(-10)
            path_item.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
            self._legend._bg_path = path_item

        path_item = self._legend._bg_path
        r = self._legend.boundingRect().adjusted(-pad, -pad, pad, pad)

        path = QtGui.QPainterPath()
        path.addRoundedRect(r, radius, radius)

        path_item.setPath(path)
        path_item.setBrush(pg.mkBrush(ICEBERG_DARK["bg"]))
        path_item.setPen(pg.mkPen(ICEBERG_DARK["fg_dim"], width=border_width))

    ###################################
    #### x軸の操作に関するメソッド ####
    ###################################
    def _clamp_xrange(self, x_on: float, x_off: float) -> tuple[float, float]:
        if x_off < x_on:
            x_on, x_off = x_off, x_on

        span0 = x_off - x_on
        min_span = float(self._min_window)
        max_span = float(self._max_window)

        span = max(min_span, span0)
        span = min(max_span, span)

        if abs(span - span0) > 1e-2:
            cx = 0.5 * (x_on + x_off)
            x_on = cx - 0.5 * span
            x_off = cx + 0.5 * span

        if x_on < 0.0:
            x_on = 0.0
            x_off = x_on + span
        if x_off > self.ds.nrow:
            x_off = self.ds.nrow
            x_on = x_off - span

        if x_on < 0.0:
            x_on = 0.0
        if x_off > self.ds.nrow:
            x_off = self.ds.nrow

        return x_on, x_off

    def _on_xrange_changed(self, vb, xr):
        if self._ignore_xrange:
            return

        x_on, x_off = float(xr[0]), float(xr[1])
        clp_x_on, clp_x_off = self._clamp_xrange(x_on, x_off)


        if (abs(clp_x_on - x_on) > 1e-2) or (abs(clp_x_off - x_off) > 1e-2):
            self._ignore_xrange = True
            try:
                vb.setXRange(clp_x_on, clp_x_off, padding=self._xpad)
            finally:
                self._ignore_xrange = False

        span = clp_x_off - clp_x_on
        pad = span * self._xpad
        self._ensure_in_buffer(clp_x_on - pad, clp_x_off + pad)

    def _ensure_in_buffer(self, x_on: float, x_off: float):
        x_on = max(0.0, x_on)
        x_off = min(float(self.ds.nrow), x_off)

        is_view_in_buf = (self._buf_on <= x_on) and (self._buf_off >= x_off)
        nsamples = max(self._min_sample, int(round(x_off - x_on)))

        is_zoomed_in = is_view_in_buf and (nsamples < int(self._win_offset * 0.7))

        if (not is_view_in_buf) or is_zoomed_in:
            self._buf_on = int(np.floor(x_on))
            self._buf_off = self._buf_on + nsamples
            self.set_window(self._buf_on, nsamples)

    ####################################################
    #### ウィンドウの位置変化＆更新に関するメソッド ####
    ####################################################
    def _apply_window_to_view(self):
        x0 = float(self._win_onset)
        x1 = float(self._win_onset + self._win_offset)
        x0, x1 = self._clamp_xrange(x0, x1)

        self._ignore_xrange = True
        try:
            self.getViewBox().setXRange(x0, x1, padding=self._xpad)
        finally:
            self._ignore_xrange = False

    def set_window(self, start: int, window: int, move_view = False):
        self._win_onset = int(start)
        self._win_offset = int(window)

        self.refresh()
        if move_view:
            self._apply_window_to_view()

    def refresh(self):
        x, chunk = self.ds.get_chunk(
            self._cols,
            self._win_onset,
            self._win_offset,
        )


        for col in self._cols:
            y = chunk.get(col)
            if y is None:
                y = np.empty((0,), dtype=np.float32)
            y = self.process_signal(y, col)
            self._curves[col].setData(x, y)


    def refresh_one(self, col: str):
        x, chunk = self.ds.get_chunk(
            self._cols,
            self._win_onset,
            self._win_offset,
        )
        y = chunk.get(col)
        if y is None:
            y = np.empty((0,), dtype=np.float32)
        y = self.process_signal(y, col)
        self._curves[col].setData(x, y)

    ##################################
    #### GUISetting関連のメソッド ####
    ##################################
    def set_settings(self, settings):
        if self._settings is settings:
            return
        if self._settings is not None:
            try:
                self._settings.changed.disconnect(self._on_settings_changed)
            except Exception:
                pass

        self._settings = settings

        if self._settings is not None:
            self._settings.changed.connect(self._on_settings_changed)

    @property
    def settings(self):
        return self._settings

    def _on_settings_changed(self, ev):
        self.on_settings_changed(ev)

    def on_settings_changed(self, ev):
        if ev.scope == "global" and ev.key == "fs":
            x_on, x_off = self.getViewBox().viewRange()[0]
            self.axis_bottom.setRange(x_on, x_off)
        if ev.scope == "col" and ev.key == "visible":
            self.set_signal_visible(ev.col, ev.value, propagate=False)

if __name__ == "__main__":
    import sys
    from time import sleep

    from PyQt6 import QtWidgets

    from core import make_dummy_df
    from core.colors import ICEBERG_DARK, apply_colorscheme

    app = QtWidgets.QApplication(sys.argv)
    apply_colorscheme(app, ICEBERG_DARK)

    df = make_dummy_df(N=300_000, fs=1000)
    ds = TimeData(df)

    w = QtWidgets.QMainWindow()
    plot = DataPlot(ds)
    w.setCentralWidget(plot)
    w.resize(1200, 700)
    w.setWindowTitle("DataPlot demo")

    plot.set_signals(["sin_3hz", "sin_4hz"])

    w.show()
    sys.exit(app.exec())
