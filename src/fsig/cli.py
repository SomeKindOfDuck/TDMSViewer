from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def add_event_segment_number(
    df: pd.DataFrame,
    base_event_name: str,
    time_col: str = "time",
    event_col: str = "event",
) -> pd.DataFrame:
    required_cols = {time_col, event_col}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()
    out = out.sort_values(time_col).reset_index(drop=True)

    onset_event = f"{base_event_name}-on"
    onset_times = out.loc[out[event_col] == onset_event, time_col].to_numpy()

    if len(onset_times) == 0:
        raise ValueError(f"No onset event found: {onset_event}")

    segment = pd.Series(
        onset_times.searchsorted(out[time_col].to_numpy(), side="right"),
        index=out.index,
        name=f"frame_idx",
    )

    out[segment.name] = segment
    return out

def build_output_path(
    input_csv: Path,
    base_event_name: str,
    no_overwrite: bool,
) -> Path:
    if not no_overwrite:
        return input_csv

    return input_csv.with_name(f"{input_csv.stem}-fsig.csv")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect '<event>-on' in a TDMSViewer long CSV and add a segment/trial number "
            "based on its onset times."
        )
    )
    parser.add_argument("csv",
        type=Path,
        nargs="+",
        help="Input CSV file(s)"
    )
    parser.add_argument(
        "event",
        type=str,
        help="Base event name without '-on' suffix (e.g. 'hoge')",
    )
    parser.add_argument(
        "--time-col",
        type=str,
        default="time",
        help="Time column name (default: time)",
    )
    parser.add_argument(
        "--event-col",
        type=str,
        default="event",
        help="Event column name (default: event)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite input file (write to a new file instead)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    for csv_path in args.csv:
        df = pd.read_csv(csv_path)

        out = add_event_segment_number(
            df,
            base_event_name=args.event,
            time_col=args.time_col,
            event_col=args.event_col,
        )

        output_path = build_output_path(
            csv_path,
            args.event,
            args.no_overwrite,
        )

        out.to_csv(output_path, index=False)
        print(f"[OK] {csv_path} -> {output_path}")
