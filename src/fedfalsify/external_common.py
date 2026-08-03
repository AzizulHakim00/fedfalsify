"""Shared leakage-safe utilities for external scientific studies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .basis import BasisTerm


@dataclass(frozen=True)
class ExternalClientData:
    """Arbitrary-dimensional client data accepted by the aggregate protocol."""

    client_id: str
    x: np.ndarray
    y: np.ndarray

    def __post_init__(self) -> None:
        x = np.asarray(self.x, dtype=float)
        y = np.asarray(self.y, dtype=float)
        if x.ndim != 2:
            raise ValueError("external client x must be two-dimensional")
        if y.ndim != 1 or len(y) != len(x):
            raise ValueError("external client y must match x rows")
        if len(y) < 10:
            raise ValueError("every external client needs at least 10 rows")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError("external client data must be finite")
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)


class FlexibleTermCatalog:
    """Duck-compatible finite catalog for arbitrary external feature counts."""

    def __init__(self, terms: Iterable[BasisTerm]) -> None:
        ordered = tuple(terms)
        if not ordered or ordered[0].name != "1":
            raise ValueError("catalog must begin with intercept term '1'")
        names = [term.name for term in ordered]
        if len(names) != len(set(names)):
            raise ValueError("catalog term names must be unique")
        self._terms = {term.name: term for term in ordered}

    def names(self) -> tuple[str, ...]:
        return tuple(self._terms)

    def get(self, name: str) -> BasisTerm:
        try:
            return self._terms[name]
        except KeyError as exc:
            raise KeyError(f"unknown external basis term: {name}") from exc

    def matrix(self, x: np.ndarray, names: Iterable[str]) -> np.ndarray:
        selected = tuple(names)
        if not selected:
            raise ValueError("at least one external term is required")
        return np.column_stack([self.get(name).evaluate(x) for name in selected])

    def complexity(self, names: Iterable[str]) -> int:
        return int(sum(self.get(name).complexity for name in names))


@dataclass(frozen=True)
class Standardization:
    x_mean: tuple[float, ...]
    x_scale: tuple[float, ...]
    y_mean: float
    y_scale: float

    def transform_x(self, x: np.ndarray) -> np.ndarray:
        return (np.asarray(x, dtype=float) - np.asarray(self.x_mean)) / np.asarray(
            self.x_scale
        )

    def transform_y(self, y: np.ndarray) -> np.ndarray:
        return (np.asarray(y, dtype=float) - self.y_mean) / self.y_scale

    def inverse_y(self, y: np.ndarray) -> np.ndarray:
        return np.asarray(y, dtype=float) * self.y_scale + self.y_mean


def systematic_indices(count: int, maximum: int) -> np.ndarray:
    if count < 1 or maximum < 1:
        raise ValueError("count and maximum must be positive")
    if count <= maximum:
        return np.arange(count, dtype=int)
    return np.unique(np.linspace(0, count - 1, maximum, dtype=int))


def systematic_sample(x: np.ndarray, y: np.ndarray, maximum: int) -> tuple[np.ndarray, np.ndarray]:
    indices = systematic_indices(len(y), maximum)
    return np.asarray(x, dtype=float)[indices], np.asarray(y, dtype=float)[indices]


def fit_standardization(clients: Iterable[ExternalClientData]) -> Standardization:
    """Fit stable training-only scaling from client aggregate moments.

    The implementation intentionally has no absolute magnitude floor. Scientific
    variables may legitimately live near 1e-30, so replacing their scale by 1.0
    would collapse a non-constant regression task into an apparent zero target.
    Constant columns alone receive unit scale.
    """

    materialized = tuple(clients)
    if not materialized:
        raise ValueError("at least one client is required")
    feature_count = materialized[0].x.shape[1]
    if any(client.x.shape[1] != feature_count for client in materialized):
        raise ValueError("external clients must share a feature count")
    total = sum(len(client.y) for client in materialized)
    x_sum = sum(
        (client.x.sum(axis=0) for client in materialized),
        start=np.zeros(feature_count),
    )
    y_sum = sum(float(client.y.sum()) for client in materialized)
    x_mean = x_sum / total
    y_mean = y_sum / total

    # A two-pass aggregate variance avoids catastrophic cancellation for small
    # physical quantities while retaining the station/client aggregation model.
    x_squared_deviation = sum(
        (((client.x - x_mean) ** 2).sum(axis=0) for client in materialized),
        start=np.zeros(feature_count),
    )
    y_squared_deviation = sum(
        float(((client.y - y_mean) ** 2).sum()) for client in materialized
    )
    x_var = np.maximum(x_squared_deviation / total, 0.0)
    y_var = max(y_squared_deviation / total, 0.0)
    raw_x_scale = np.sqrt(x_var)
    raw_y_scale = float(np.sqrt(y_var))
    x_scale = np.where(raw_x_scale > 0.0, raw_x_scale, 1.0)
    y_scale = raw_y_scale if raw_y_scale > 0.0 else 1.0
    return Standardization(
        tuple(float(value) for value in x_mean),
        tuple(float(value) for value in x_scale),
        float(y_mean),
        y_scale,
    )


def standardized_clients(
    clients: Iterable[ExternalClientData], scaling: Standardization
) -> list[ExternalClientData]:
    return [
        ExternalClientData(
            client.client_id,
            scaling.transform_x(client.x),
            scaling.transform_y(client.y),
        )
        for client in clients
    ]


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Return physical-unit error and scale-aware normalized MSE.

    NMSE uses the observed target variance without an absolute denominator floor.
    For an exactly constant target, perfect predictions receive zero and any
    non-zero error receives infinity because normalized error is undefined.
    """

    truth = np.asarray(y_true, dtype=float)
    prediction = np.asarray(y_pred, dtype=float)
    if truth.shape != prediction.shape:
        raise ValueError("metric arrays must have identical shapes")
    residual = truth - prediction
    mse = float(np.mean(residual * residual))
    variance = float(np.mean((truth - float(np.mean(truth))) ** 2))
    if variance > 0.0:
        nmse = float(mse / variance)
    else:
        nmse = 0.0 if mse == 0.0 else float("inf")
    return {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(mse)),
        "nmse": nmse,
    }


def cluster_bootstrap_mean(
    values: Iterable[float], *, resamples: int = 4000, seed: int = 12001
) -> dict[str, float]:
    data = np.asarray(tuple(float(value) for value in values), dtype=float)
    if data.size < 2 or not np.all(np.isfinite(data)):
        raise ValueError("cluster bootstrap requires at least two finite clients")
    rng = np.random.default_rng(seed)
    samples = rng.choice(data, size=(resamples, data.size), replace=True).mean(axis=1)
    return {
        "estimate": float(data.mean()),
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "clusters": int(data.size),
        "resamples": int(resamples),
    }
