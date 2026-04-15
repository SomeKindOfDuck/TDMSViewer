import argparse
from pathlib import Path

import pandas as pd
from nptdms import TdmsFile

from tdms_viewer.core import as_binary_dataframe, load_settings_yaml
from tdms_viewer.core.datasource import TimeData
from tdms_viewer.panel.action_panel import TDMSActionPanel
from tdms_viewer.panel.param_panel import TDMSSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect '<event>-on' in a TDMSViewer long CSV and add a segment/trial number "
            "based on its onset times."
        )
    )
    parser.add_argument("tdms",
        type=Path,
        nargs="+",
        help="Input TDMS file(s)"
    )
    parser.add_argument("yaml",
                        type=Path,
                        default=Path("./default.yaml"),
                        help="Parameter setting for analyze TDMS file(s)")
    return parser.parse_args()


def main() -> None:

    args = parse_args()

    for tdms_path in args.tdms:
        tdms_data = TdmsFile.read(tdms_path)
        all_channels = TDMSActionPanel.list_tdms_channels(tdms_data)
        df = TDMSActionPanel.tdms_to_dataframe(tdms_data, all_channels)

        ds = TimeData(df)

        param_dict = load_settings_yaml(args.yaml)
        if param_dict is None:
            raise ValueError(f"{args.yaml} must be specified!")
        setting = TDMSSettings()
        setting.apply_settings_dict(param_dict)

        binary_data = as_binary_dataframe(ds, ds.cols, setting)
        output_path = tdms_path.with_name(tdms_path.stem + "_binary.csv")

        binary_data.to_csv(output_path, index=False)
        print(f"[OK] {tdms_path} -> {output_path}")
