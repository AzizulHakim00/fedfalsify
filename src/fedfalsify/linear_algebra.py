"""Deterministic linear-algebra primitives for Phase-3 engineering parity."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .sufficient_stats import SufficientStatsPacket, subset_packet


@dataclass(frozen=True)
class RankPolicy:
    relative_tolerance: float = 1.0

    def __post_init__(self) -> None:
        if float(self.relative_tolerance) != 1.0:
            raise ValueError("Phase-3 rank policy is fixed at machine-scale tolerance")


@dataclass(frozen=True)
class LeastSquaresFit:
    terms: tuple[str, ...]
    coefficients: tuple[float, ...]
    sse: float
    rank: int
    residual_df: int
    full_rank: bool


def _svd_tolerance(
    singular_values: np.ndarray,
    rows: int,
    cols: int,
    policy: RankPolicy,
) -> float:
    singular_values = np.asarray(singular_values, dtype=float)
    if singular_values.size == 0:
        return 0.0
    return float(
        policy.relative_tolerance
        * max(int(rows), int(cols))
        * np.finfo(float).eps
        * float(singular_values[0])
    )


def matrix_rank_svd(matrix: np.ndarray, policy: RankPolicy = RankPolicy()) -> int:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("matrix_rank_svd expects a two-dimensional matrix")
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    tolerance = _svd_tolerance(
        singular_values,
        matrix.shape[0],
        matrix.shape[1],
        policy,
    )
    return int(np.count_nonzero(singular_values > tolerance))


def fit_from_sufficient_stats(
    packet: SufficientStatsPacket,
    selected_terms: tuple[str, ...],
    policy: RankPolicy = RankPolicy(),
) -> LeastSquaresFit:
    selected_terms = tuple(selected_terms)
    if not selected_terms:
        raise ValueError("least-squares fit requires at least one selected term")

    selected = subset_packet(packet, selected_terms)
    gram = np.asarray(selected.gram, dtype=float)
    target = np.asarray(selected.target, dtype=float)
    gram = 0.5 * (gram + gram.T)

    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    eigenvalues = np.asarray(eigenvalues, dtype=float)
    eigenvectors = np.asarray(eigenvectors, dtype=float)

    # Eigenvalues of X^T X are squared singular values of X.
    clipped = np.maximum(eigenvalues, 0.0)
    singular_values = np.sqrt(clipped)
    order = np.argsort(singular_values)[::-1]
    singular_values_desc = singular_values[order]
    tolerance = _svd_tolerance(
        singular_values_desc,
        selected.support,
        len(selected_terms),
        policy,
    )
    keep = singular_values > tolerance
    rank = int(np.count_nonzero(keep))

    if rank:
        basis = eigenvectors[:, keep]
        inverse_eigenvalues = 1.0 / eigenvalues[keep]
        coefficients = basis @ (inverse_eigenvalues * (basis.T @ target))
    else:
        coefficients = np.zeros(len(selected_terms), dtype=float)

    sse = (
        float(selected.target_energy)
        - 2.0 * float(coefficients @ target)
        + float(coefficients @ gram @ coefficients)
    )
    if sse < 0.0:
        numerical_limit = 1e-10 * max(1.0, abs(float(selected.target_energy)))
        if abs(sse) <= numerical_limit:
            sse = 0.0
        else:
            raise FloatingPointError(f"negative reconstructed SSE outside numerical tolerance: {sse}")

    return LeastSquaresFit(
        terms=selected_terms,
        coefficients=tuple(float(value) for value in coefficients),
        sse=float(sse),
        rank=rank,
        residual_df=int(selected.support - rank),
        full_rank=bool(rank == len(selected_terms)),
    )
