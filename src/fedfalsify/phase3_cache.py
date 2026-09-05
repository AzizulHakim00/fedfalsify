"""Condition-local Phase-3A packet cache.

Engineering-only: seed 29001 is the sole permitted execution seed in Phase 3A.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .basis import TermCatalog
from .crossfit_redesign import partition_clients
from .crossfit_surrogate import split_selector_probe
from .sufficient_stats import SufficientStatsPacket, packet_from_dataset


@dataclass(frozen=True)
class Phase3PacketCache:
    seed: int
    client_ids: tuple[str, ...]
    all_terms: tuple[str, ...]
    discovery: tuple[SufficientStatsPacket, ...]
    selector: tuple[SufficientStatsPacket, ...]
    probe: tuple[SufficientStatsPacket, ...]


def build_phase3_packet_cache(
    datasets: Sequence[object],
    catalog: TermCatalog,
    all_terms: tuple[str, ...],
    *,
    seed: int,
) -> Phase3PacketCache:
    if int(seed) != 29001:
        raise ValueError("Phase-3A cache builder is engineering-only and permits seed 29001")

    all_terms = tuple(all_terms)
    partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
    selectors, probes = split_selector_probe(partitions, seed=seed)

    discovery = tuple(
        packet_from_dataset(item.discovery, catalog, all_terms)
        for item in partitions
    )
    selector = tuple(
        packet_from_dataset(item.validation, catalog, all_terms)
        for item in selectors
    )
    probe = tuple(
        packet_from_dataset(item.validation, catalog, all_terms)
        for item in probes
    )
    client_ids = tuple(packet.client_id for packet in discovery)

    if tuple(packet.client_id for packet in selector) != client_ids:
        raise RuntimeError("selector client order differs from discovery client order")
    if tuple(packet.client_id for packet in probe) != client_ids:
        raise RuntimeError("probe client order differs from discovery client order")

    return Phase3PacketCache(
        seed=int(seed),
        client_ids=client_ids,
        all_terms=all_terms,
        discovery=discovery,
        selector=selector,
        probe=probe,
    )
