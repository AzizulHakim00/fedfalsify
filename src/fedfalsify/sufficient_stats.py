"""Additive sufficient-statistic primitives for Phase-3 engineering parity.

This module is intentionally additive. It does not alter the frozen v11 path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .basis import TermCatalog


@dataclass(frozen=True)
class SufficientStatsPacket:
    client_id: str
    support: int
    terms: tuple[str, ...]
    gram: np.ndarray
    target: np.ndarray
    target_energy: float
    observed_support: tuple[int, ...]


def _term_indices(all_terms: tuple[str, ...], selected_terms: tuple[str, ...]) -> np.ndarray:
    mapping = {term: index for index, term in enumerate(all_terms)}
    if len(mapping) != len(all_terms):
        raise ValueError("packet terms must be unique")
    missing = [term for term in selected_terms if term not in mapping]
    if missing:
        raise KeyError(f"selected terms not present in packet: {missing}")
    if len(set(selected_terms)) != len(selected_terms):
        raise ValueError("selected terms must be unique")
    return np.asarray([mapping[term] for term in selected_terms], dtype=int)


def packet_from_dataset(
    dataset,
    catalog: TermCatalog,
    terms: tuple[str, ...],
) -> SufficientStatsPacket:
    terms = tuple(terms)
    if not terms:
        raise ValueError("packet requires at least one term")
    if len(set(terms)) != len(terms):
        raise ValueError("packet terms must be unique")

    design = catalog.matrix(dataset.x, terms)
    response = np.asarray(dataset.y, dtype=float)
    gram = np.asarray(design.T @ design, dtype=float)
    target = np.asarray(design.T @ response, dtype=float)
    target_energy = float(response @ response)
    observed_support = tuple(
        int(np.count_nonzero(np.abs(catalog.get(term).evaluate(dataset.x)) > 1e-12))
        for term in terms
    )
    return SufficientStatsPacket(
        client_id=str(dataset.client_id),
        support=int(len(response)),
        terms=terms,
        gram=gram,
        target=target,
        target_energy=target_energy,
        observed_support=observed_support,
    )


def aggregate_packets(packets: Sequence[SufficientStatsPacket]) -> SufficientStatsPacket:
    packets = tuple(packets)
    if not packets:
        raise ValueError("cannot aggregate an empty packet sequence")
    terms = packets[0].terms
    if any(packet.terms != terms for packet in packets):
        raise ValueError("all packets must use the same ordered terms")

    width = len(terms)
    gram = sum(
        (np.asarray(packet.gram, dtype=float) for packet in packets),
        start=np.zeros((width, width), dtype=float),
    )
    target = sum(
        (np.asarray(packet.target, dtype=float) for packet in packets),
        start=np.zeros(width, dtype=float),
    )
    observed_support = tuple(
        int(sum(packet.observed_support[index] for packet in packets))
        for index in range(width)
    )
    return SufficientStatsPacket(
        client_id="aggregate",
        support=int(sum(packet.support for packet in packets)),
        terms=terms,
        gram=np.asarray(gram, dtype=float),
        target=np.asarray(target, dtype=float),
        target_energy=float(sum(packet.target_energy for packet in packets)),
        observed_support=observed_support,
    )


def subset_packet(
    packet: SufficientStatsPacket,
    selected_terms: tuple[str, ...],
) -> SufficientStatsPacket:
    selected_terms = tuple(selected_terms)
    indices = _term_indices(packet.terms, selected_terms)
    return SufficientStatsPacket(
        client_id=packet.client_id,
        support=packet.support,
        terms=selected_terms,
        gram=np.asarray(packet.gram[np.ix_(indices, indices)], dtype=float),
        target=np.asarray(packet.target[indices], dtype=float),
        target_energy=float(packet.target_energy),
        observed_support=tuple(packet.observed_support[index] for index in indices),
    )


def sse_from_packet(
    packet: SufficientStatsPacket,
    terms: tuple[str, ...],
    coefficients: Sequence[float],
) -> float:
    terms = tuple(terms)
    beta = np.asarray(tuple(coefficients), dtype=float)
    if beta.shape != (len(terms),):
        raise ValueError("coefficient count must match selected terms")
    selected = subset_packet(packet, terms)
    sse = (
        float(selected.target_energy)
        - 2.0 * float(beta @ selected.target)
        + float(beta @ selected.gram @ beta)
    )
    return float(max(sse, 0.0))
