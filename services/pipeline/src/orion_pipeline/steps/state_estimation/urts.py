from dataclasses import dataclass

import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.state import THETA, wrap_angle
from orion_pipeline.steps.state_estimation.ukf_step import Tick


@dataclass(frozen=True)
class SmoothedTick:
    """The smoothed state at one tick."""

    time: pd.Timestamp
    x: np.ndarray
    P: np.ndarray


def smooth(ticks: list[Tick]) -> list[SmoothedTick]:
    """Unscented Rauch-Tung-Striebel backward pass over time-ordered ticks.

    Each tick is pulled toward what the later ticks learned. A tick with no
    prediction (x_pred, P_pred, C are None) started the filter, so nothing links
    it to the tick before it: the tick before it keeps its filtered values.
    The last tick is never changed. Needs the whole run in memory.
    """
    smoothed = [SmoothedTick(t.time, t.x.copy(), t.P.copy()) for t in ticks]

    for k in range(len(ticks) - 2, -1, -1):
        nxt = ticks[k + 1]
        if nxt.x_pred is None or nxt.P_pred is None or nxt.C is None:
            continue

        # Smoother gain G = C @ inv(P_pred). P_pred is symmetric.
        G = np.linalg.solve(nxt.P_pred, nxt.C.T).T

        dx = smoothed[k + 1].x - nxt.x_pred
        dx[THETA] = wrap_angle(dx[THETA])
        dP = smoothed[k + 1].P - nxt.P_pred

        x = ticks[k].x + G @ dx
        x[THETA] = wrap_angle(x[THETA])
        P = ticks[k].P + G @ dP @ G.T
        smoothed[k] = SmoothedTick(ticks[k].time, x, (P + P.T) / 2)

    return smoothed