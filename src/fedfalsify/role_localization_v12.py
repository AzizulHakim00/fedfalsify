"""Noise-calibrated Discovery-only role localization for Phase-3B."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from .basis import TermCatalog
from .multiple_testing import bh_adjust
from .nested_tests import partial_nested_f
from .sufficient_stats import SufficientStatsPacket

ROLE_Q = 0.10
MIN_ACTIVE_SUPPORT = 10
MIN_RESIDUAL_DF = 5
MAX_ROLE_FRACTION = 0.50


@dataclass(frozen=True)
class NCEEClientEvidence:
    client_id: str
    eligible: bool
    reason: str
    active_support: int
    residual_df: int | None
    raw_p_value: float | None
    bh_adjusted_value: float | None
    candidate_coefficient: float | None
    candidate_sign: int
    raw_gain: float | None
    bh_supported: bool


@dataclass(frozen=True)
class FrozenLocalizedHypothesis:
    term: str
    source_term: str
    role_indices: tuple[int, ...]
    outside_indices: tuple[int, ...]
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    discovery_sign: int
    client_evidence: tuple[NCEEClientEvidence, ...]

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.term,
            self.source_term,
            self.role_indices,
            self.outside_indices,
            self.role_client_ids,
            self.outside_client_ids,
            self.discovery_sign,
        )


@dataclass(frozen=True)
class RoleRejection:
    term: str
    source_term: str | None
    reason: str
    client_evidence: tuple[NCEEClientEvidence, ...]
    supported_client_ids: tuple[str, ...] = ()


def _active_support(packet: SufficientStatsPacket, term: str) -> int:
    try:
        index = packet.terms.index(term)
    except ValueError:
        return 0
    return int(packet.observed_support[index])


def _client_evidence(
    packet: SufficientStatsPacket,
    shared_terms: tuple[str, ...],
    term: str,
) -> NCEEClientEvidence:
    active_support = _active_support(packet, term)
    if term not in packet.terms:
        return NCEEClientEvidence(
            str(packet.client_id), False, "STRUCTURAL-NESTING-FAIL", 0, None,
            None, None, None, 0, None, False,
        )
    if active_support < MIN_ACTIVE_SUPPORT:
        return NCEEClientEvidence(
            str(packet.client_id), False, "INSUFFICIENT-ACTIVE-SUPPORT", active_support,
            None, None, None, None, 0, None, False,
        )

    full_terms = tuple(shared_terms) + (term,)
    try:
        result = partial_nested_f(
            packet,
            tuple(shared_terms),
            full_terms,
            candidate_term=term,
        )
    except (KeyError, ValueError):
        return NCEEClientEvidence(
            str(packet.client_id), False, "STRUCTURAL-NESTING-FAIL", active_support,
            None, None, None, None, 0, None, False,
        )

    if not result.admissible:
        return NCEEClientEvidence(
            str(packet.client_id), False, result.reason, active_support,
            int(result.residual_df), None, None, None, 0, float(result.raw_gain), False,
        )
    if int(result.residual_df) < MIN_RESIDUAL_DF:
        return NCEEClientEvidence(
            str(packet.client_id), False, "INSUFFICIENT-RESIDUAL-DF", active_support,
            int(result.residual_df), None, None, result.candidate_coefficient,
            int(result.candidate_sign), float(result.raw_gain), False,
        )

    return NCEEClientEvidence(
        client_id=str(packet.client_id),
        eligible=True,
        reason="OK",
        active_support=active_support,
        residual_df=int(result.residual_df),
        raw_p_value=float(result.p_value),
        bh_adjusted_value=None,
        candidate_coefficient=float(result.candidate_coefficient),
        candidate_sign=int(result.candidate_sign),
        raw_gain=float(result.raw_gain),
        bh_supported=False,
    )


def discover_localized_role(
    shared_terms: tuple[str, ...],
    discovery_packets: Sequence[SufficientStatsPacket],
    catalog: TermCatalog,
    *,
    term: str,
    source_term: str | None,
    discovery_bank_terms: Sequence[str] = (),
) -> FrozenLocalizedHypothesis | RoleRejection:
    """Construct one frozen localized hypothesis from Discovery packets only."""
    shared_terms = tuple(shared_terms)
    packets = tuple(discovery_packets)
    if not packets:
        raise ValueError("NCEE role discovery requires at least one client")
    if "1" not in shared_terms or len(set(shared_terms)) != len(shared_terms):
        raise ValueError("shared terms must be unique and contain the intercept")
    if term in shared_terms:
        raise ValueError("localized candidate must be outside the shared structure")
    client_ids = tuple(str(packet.client_id) for packet in packets)
    if len(set(client_ids)) != len(client_ids):
        raise ValueError("Discovery client IDs must be unique")

    metadata = catalog.get(term)
    if metadata.kind != "exception":
        return RoleRejection(term, source_term, "LOCALIZED-CANDIDATE-NOT-EXCEPTION", ())

    evidence = tuple(_client_evidence(packet, shared_terms, term) for packet in packets)
    eligible = tuple(item for item in evidence if item.eligible)
    if eligible:
        bh = bh_adjust(
            tuple(item.client_id for item in eligible),
            tuple(float(item.raw_p_value) for item in eligible),
            q=ROLE_Q,
        )
        adjusted = dict(zip(bh.names, bh.adjusted_values))
        rejected = set(bh.rejected)
        evidence = tuple(
            replace(
                item,
                bh_adjusted_value=(float(adjusted[item.client_id]) if item.eligible else None),
                bh_supported=bool(item.eligible and item.client_id in rejected),
            )
            for item in evidence
        )
    else:
        rejected = set()

    role_indices = tuple(index for index, item in enumerate(evidence) if item.bh_supported)
    supported_ids = tuple(evidence[index].client_id for index in role_indices)
    if not role_indices:
        return RoleRejection(
            term, source_term, "EFFECT-ROLE-NOT-LOCALIZED", evidence, supported_ids
        )

    if (
        len(role_indices) >= len(packets)
        or len(role_indices) > MAX_ROLE_FRACTION * len(packets)
    ):
        return RoleRejection(
            term, source_term, "GLOBAL-SCOPE-AMBIGUOUS", evidence, supported_ids
        )

    signs = {int(evidence[index].candidate_sign) for index in role_indices}
    if 0 in signs or len(signs) != 1:
        return RoleRejection(
            term, source_term, "SCOPE-SIGN-AMBIGUOUS", evidence, supported_ids
        )
    discovery_sign = next(iter(signs))

    if source_term is None or not str(source_term).strip():
        return RoleRejection(
            term, source_term, "SOURCE-PROVENANCE-MISSING", evidence, supported_ids
        )
    source_term = str(source_term)
    if source_term not in set(shared_terms) and source_term not in set(discovery_bank_terms):
        return RoleRejection(
            term, source_term, "WEAK-HEREDITY-FAIL", evidence, supported_ids
        )

    role_set = set(role_indices)
    outside_indices = tuple(index for index in range(len(packets)) if index not in role_set)
    return FrozenLocalizedHypothesis(
        term=term,
        source_term=source_term,
        role_indices=role_indices,
        outside_indices=outside_indices,
        role_client_ids=tuple(client_ids[index] for index in role_indices),
        outside_client_ids=tuple(client_ids[index] for index in outside_indices),
        discovery_sign=int(discovery_sign),
        client_evidence=evidence,
    )
