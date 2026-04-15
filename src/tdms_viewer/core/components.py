from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, ev: QtGui.QMouseEvent | None):
        if not ev is None:
            if ev.button() == QtCore.Qt.MouseButton.LeftButton:
                self.clicked.emit()


class SecondsAxis(pg.AxisItem):
    """内部x=sample index を、表示だけ秒に変換するAxis"""
    def __init__(self, fs_getter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fs_getter = fs_getter

    def tickStrings(self, values, scale, spacing):
        fs = float(self._fs_getter())
        if fs <= 0:
            return [""] * len(values)
        return [f"{v / fs:.2f}" for v in values]


class TrackpadXPanViewBox(pg.ViewBox):
    """
    仕様:
      - x軸上のスクロール: いまのまま (Axis側/pg標準に任せる)
      - y軸上のスクロール: いまのまま (Axis側/pg標準に任せる)
      - プロットエリア内:
          * 横スクロール -> x pan
          * 縦スクロール -> x zoom only（yズーム禁止）
    """

    def __init__(self, *args, pan_frac_per_notch=0.10, zoom_base=0.9, **kwargs):
        super().__init__(*args, **kwargs)
        self._pan_frac_per_notch = float(pan_frac_per_notch)
        self._zoom_base = float(zoom_base)

    def wheelEvent(self, ev, axis=None):
        if axis is not None:
            super().wheelEvent(ev, axis)
            return

        orient = None
        delta = 0

        if hasattr(ev, "orientation") and hasattr(ev, "delta"):
            try:
                orient = ev.orientation()
            except Exception:
                orient = None
            try:
                delta = ev.delta()
            except Exception:
                delta = 0

        if delta == 0 and hasattr(ev, "angleDelta"):
            ad = ev.angleDelta()
            ax = ad.x()
            ay = ad.y()
            if abs(ax) > abs(ay):
                orient = QtCore.Qt.Orientation.Horizontal
                delta = ax
            else:
                orient = QtCore.Qt.Orientation.Vertical
                delta = ay

        if delta == 0:
            super().wheelEvent(ev, axis)
            return

        (x0, x1), _ = self.viewRange()
        span = float(x1 - x0)
        if not (span > 0):
            super().wheelEvent(ev, axis)
            return

        if orient == QtCore.Qt.Orientation.Horizontal:
            ev.accept()

            frac = (delta / 120.0) * self._pan_frac_per_notch
            shift = span * frac

            self.setXRange(x0 - shift, x1 - shift, padding=0)
            return

        ev.accept()

        center_x = self.mapSceneToView(ev.scenePos()).x()
        if center_x < x0:
            center_x = x0
        elif center_x > x1:
            center_x = x1

        steps = delta / 120.0

        factor = self._zoom_base ** steps
        new_span = span * factor

        frac = (center_x - x0) / span if span > 0 else 0.5
        new_x0 = center_x - new_span * frac
        new_x1 = new_x0 + new_span

        self.setXRange(new_x0, new_x1, padding=0)
        return


@dataclass(frozen=True)
class SettingEvent:
    key: str
    scope: str
    col: str | None = None
    value: Any = None

class ParameterSettings(QtCore.QObject):
    """
    GUI 全体で共有する設定オブジェクト。
    UI はこのオブジェクトを書き換え、Plot 側は changed を購読する。
    """
    changed = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._d: dict[str, Any] = {}
        self._d["fs"] = 1000
        self._d["single_view"] = False

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._d[key] = value
        self.changed.emit(
            SettingEvent(key=key, scope="global", value=value)
        )

    def get_for_col(self, key: str, col: str, default: Any = None) -> Any:
        m = self._d.get(key)
        if not isinstance(m, dict):
            return default
        return m.get(col, default)

    def set_for_col(self, key: str, col: str, value: Any) -> None:
        m = self._d.get(key)
        if not isinstance(m, dict):
            m = {}
            self._d[key] = m

        m[col] = value
        self.changed.emit(
            SettingEvent(key=key, scope="col", col=col, value=value)
        )

    def as_dict(self) -> dict[str, Any]:
        """保存・デバッグ用（直接書き換えないこと）"""
        return self._d
