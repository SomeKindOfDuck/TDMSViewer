from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import pyqtgraph as pg
from PyQt6 import QtWidgets


@dataclass
class StackItem:
    plot: pg.PlotWidget
    stretch: int = 1


class DataPlotStack(QtWidgets.QWidget):
    def __init__(
        self,
        plots: Sequence[pg.PlotWidget] | Sequence[StackItem],
        parent=None,
        *,
        link_x: bool = True,
        master_index: int = 0,
        show_x_axis_only_bottom: bool = True,
        spacing: int = 6,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    ):
        super().__init__(parent)

        if not plots:
            raise ValueError("plots is empty")

        items: list[StackItem] = []
        for p in plots:
            if isinstance(p, StackItem):
                items.append(p)
            else:
                items.append(StackItem(plot=p, stretch=1))

        if not (0 <= master_index < len(items)):
            raise IndexError("master_index out of range")

        self._items = items
        self._master = items[master_index].plot

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(spacing)
        layout.setContentsMargins(*margins)
        self.setLayout(layout)

        for i, it in enumerate(items):
            w = it.plot
            layout.addWidget(w, stretch=it.stretch)

        if link_x:
            for it in items:
                if it.plot is not self._master:
                    it.plot.setXLink(self._master)

        if show_x_axis_only_bottom:
            for it in items[:-1]:
                ax = it.plot.getAxis("bottom")
                ax.setStyle(showValues=False)
                ax.setHeight(0)

    def master(self) -> pg.PlotWidget:
        return self._master

    def plots(self) -> list[pg.PlotWidget]:
        return [it.plot for it in self._items]

if __name__ == "__main__":
    import sys
    from time import sleep

    from PyQt6 import QtWidgets

    from core import make_dummy_df
    from core.colors import ICEBERG_DARK, apply_colorscheme
    from core.datasource import TimeData
    from core.plot import DataPlot

    app = QtWidgets.QApplication(sys.argv)
    apply_colorscheme(app, ICEBERG_DARK)

    df = make_dummy_df(N=300_000, fs=1000)
    ds = TimeData(df)

    w = QtWidgets.QMainWindow()
    w.resize(1200, 700)
    p1 = DataPlot(ds, show_x_axis=True)
    p2 = DataPlot(ds, show_x_axis=True)

    p1.set_signals(["sin_3hz", "sin_4hz"])
    p2.set_signals(["sin_4hz", "sin_6hz"])
    p1.link_signals("sin_3hz", p2, "sin_6hz")

    stack = DataPlotStack([p1, p2], link_x=True, show_x_axis_only_bottom=True)
    w.setCentralWidget(stack)
    w.show()
    sys.exit(app.exec())
