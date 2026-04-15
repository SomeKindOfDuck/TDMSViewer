import numpy as np
import pandas as pd

_MAX_SAMPLES = 20_000


class TimeData(pd.DataFrame):
    def __init__(self, df: pd.DataFrame, max_samples: int = _MAX_SAMPLES, *args, **kwargs):
        super().__init__(df, *args, **kwargs)
        self.max_points = max_samples
        self.nrow = len(self)

    @property
    def cols(self) -> list[str]:
        return self.columns.to_list()

    def _make_indices(self, start: int, end: int) -> np.ndarray:
        n = end - start
        m = self.max_points

        if m <= 0 or n <= 0:
            return np.empty((0,), dtype=np.int64)

        if n <= m:
            return np.arange(start, end, dtype=np.int64)

        return np.linspace(start, end - 1, num=m, dtype=np.int64)

    def get_chunk(
        self,
        cols: list[str],
        start: int,
        window: int,
        dtype=np.float32,
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        start = int(start)
        window = int(window)
        if window < 0:
            window = 0

        start = max(0, min(start, self.nrow))
        end = max(start, min(start + window, self.nrow))

        idx = self._make_indices(start, end)

        out: dict[str, np.ndarray] = {}
        for c in cols:
            if c not in self.columns:
                out[c] = np.empty((0,), dtype=dtype)
                continue

            a = self[c].to_numpy()
            out[c] = a[idx].astype(dtype, copy=False)

        return idx, out
    
    def get_col(self, col, dtype=np.float32):
        return self[col].to_numpy(dtype, copy=False)
