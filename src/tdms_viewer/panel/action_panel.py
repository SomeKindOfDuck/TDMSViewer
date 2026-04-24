from pathlib import Path
from typing import Any

import numpy as np
import yaml
from nptdms import TdmsFile
from pandas import DataFrame
from PyQt6 import QtCore, QtWidgets


class TDMSActionPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(10, 4, 10, 4)
        outer.setSpacing(8)

        self.btn_load_tdms = QtWidgets.QPushButton("Load TDMS")
        self.btn_save_tdms = QtWidgets.QPushButton("Save as")
        self.btn_set_default = QtWidgets.QPushButton("Set default")
        self.btn_load_yaml = QtWidgets.QPushButton("Load yaml")
        self.btn_save_yaml = QtWidgets.QPushButton("Save yaml")

        buttons = (
            self.btn_load_tdms,
            self.btn_save_tdms,
            self.btn_set_default,
            self.btn_load_yaml,
            self.btn_save_yaml,
        )
        for btn in buttons:
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(30)

        left_col = QtWidgets.QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)
        left_col.addWidget(self.btn_load_tdms)
        left_col.addWidget(self.btn_save_tdms)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(6)
        right_col.addWidget(self.btn_set_default)

        yaml_row = QtWidgets.QHBoxLayout()
        yaml_row.setContentsMargins(0, 0, 0, 0)
        yaml_row.setSpacing(6)
        yaml_row.addWidget(self.btn_load_yaml)
        yaml_row.addWidget(self.btn_save_yaml)

        right_col.addLayout(yaml_row)

        outer.addLayout(left_col, 1)
        outer.addLayout(right_col, 1)


    @staticmethod
    def save_settings_yaml(settings_dict: dict[str, Any], path: str | Path = "./default.yaml") -> None:
        path = Path(path)

        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                settings_dict,
                f,
                allow_unicode=True,
                sort_keys=False,
            )

    @staticmethod
    def load_settings_yaml(path: str | Path) -> dict[str, Any] | None:
        path = Path(path)
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ValueError("YAMLのトップレベルはdictである必要があります。")

        return data

    @staticmethod
    def list_tdms_channels(tdms: TdmsFile) -> list[str]:
        channel_names = []
        for group in tdms.groups():
            for ch in group.channels():
                channel_names.append(f"{group.name}/{ch.name}")
        return channel_names

    # @staticmethod
    # def tdms_to_dataframe(tdms: TdmsFile, selected_channels: list[str]) -> DataFrame:
    #     data = {}

    #     for full_name in selected_channels:
    #         group_name, channel_name = full_name.split("/", 1)
    #         ch = tdms[group_name][channel_name]
    #         data[channel_name] = ch[:]

    #     return DataFrame(data)

    @staticmethod
    def tdms_to_dataframe(
        tdms: TdmsFile,
        selected_channels: list[str],
        max_length_diff: int = 1,
    ) -> DataFrame:
        channels = [
            tdms[group][channel]
            for group, channel in (name.split("/", 1) for name in selected_channels)
        ]

        arrays = [ch[:] for ch in channels]
        lengths = [len(x) for x in arrays]

        min_len = min(lengths)
        max_len = max(lengths)

        if max_len - min_len > max_length_diff:
            raise ValueError(
                f"Channel length mismatch is too large: min={min_len}, max={max_len}"
            )

        return DataFrame({
            ch.name: arr[:min_len]
            for ch, arr in zip(channels, arrays)
        })
