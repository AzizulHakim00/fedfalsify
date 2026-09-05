from __future__ import annotations

import numpy as np

from fedfalsify.sufficient_stats import SufficientStatsPacket


def stats_packet(
    client_id: str,
    terms: tuple[str, ...],
    design: np.ndarray,
    response: np.ndarray,
    *,
    observed_support: tuple[int, ...] | None = None,
) -> SufficientStatsPacket:
    design = np.asarray(design, dtype=float)
    response = np.asarray(response, dtype=float)
    if design.ndim != 2 or design.shape[0] != response.shape[0]:
        raise ValueError("invalid synthetic packet dimensions")
    if design.shape[1] != len(terms):
        raise ValueError("term/design width mismatch")
    if observed_support is None:
        observed_support = tuple(
            int(np.count_nonzero(np.abs(design[:, index]) > 1e-12))
            for index in range(design.shape[1])
        )
    return SufficientStatsPacket(
        client_id=client_id,
        support=int(design.shape[0]),
        terms=tuple(terms),
        gram=np.asarray(design.T @ design, dtype=float),
        target=np.asarray(design.T @ response, dtype=float),
        target_energy=float(response @ response),
        observed_support=tuple(int(value) for value in observed_support),
    )
