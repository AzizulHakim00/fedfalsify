import inspect

import numpy as np

from fedfalsify.role_localization_v12 import (
    FrozenLocalizedHypothesis,
    RoleRejection,
    discover_localized_role,
)
from fedfalsify.scsv_v10_benchmarks import LINEAR_DEV_V10, v10_catalog
from tests.phase3b_test_utils import stats_packet


SHARED = ("1", "x1")
TERMS = SHARED + (LINEAR_DEV_V10,)


def _role_packet(
    client_id: str,
    beta: float,
    *,
    seed: int,
    active_support: int = 20,
    n: int = 60,
    collinear: bool = False,
):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    if collinear:
        z = x1.copy()
        active_support = n
    else:
        z = np.zeros(n)
        z[:active_support] = rng.normal(size=active_support)
    design = np.column_stack([np.ones(n), x1, z])
    response = 0.5 + 0.8 * x1 + beta * z
    observed = (n, n, active_support)
    return stats_packet(client_id, TERMS, design, response, observed_support=observed)


def _discover(packets, *, source_term="x1", shared_terms=SHARED):
    return discover_localized_role(
        shared_terms,
        tuple(packets),
        v10_catalog(),
        term=LINEAR_DEV_V10,
        source_term=source_term,
        discovery_bank_terms=("x1", LINEAR_DEV_V10),
    )


def test_discovery_api_cannot_receive_selector_or_probe_packets():
    parameters = inspect.signature(discover_localized_role).parameters
    assert "selector_packets" not in parameters
    assert "probe_packets" not in parameters


def test_client_eligibility_guards_are_explicit():
    low = _discover(
        (
            _role_packet("c1", 2.0, seed=1, active_support=9),
            _role_packet("c2", 0.0, seed=2, active_support=9),
        )
    )
    assert isinstance(low, RoleRejection)
    assert all(item.reason == "INSUFFICIENT-ACTIVE-SUPPORT" for item in low.client_evidence)

    collinear = _discover(
        (
            _role_packet("c1", 2.0, seed=3, collinear=True),
            _role_packet("c2", 0.0, seed=4, collinear=True),
        )
    )
    assert isinstance(collinear, RoleRejection)
    assert all(item.reason == "STRUCTURAL-RANK-AMBIGUOUS" for item in collinear.client_evidence)

    rng = np.random.default_rng(5)
    high_shared = ("1", "x1", "x2", "x3", "x1^2", "x2^2", "x3^2")
    high_terms = high_shared + (LINEAR_DEV_V10,)
    packets = []
    for index in range(2):
        n = 12
        design = np.column_stack([np.ones(n)] + [rng.normal(size=n) for _ in range(7)])
        response = design[:, :7] @ np.arange(1.0, 8.0)
        packets.append(
            stats_packet(
                f"df-{index}",
                high_terms,
                design,
                response,
                observed_support=(n, n, n, n, n, n, n, 10),
            )
        )
    low_df = _discover(packets, shared_terms=high_shared)
    assert isinstance(low_df, RoleRejection)
    assert all(item.reason == "INSUFFICIENT-RESIDUAL-DF" for item in low_df.client_evidence)


def test_bh_role_uses_only_eligible_clients_and_freezes_supported_minority():
    packets = tuple(
        _role_packet(f"c{index + 1}", 2.0 if index == 3 else 0.0, seed=20 + index)
        for index in range(4)
    )
    result = _discover(packets)
    assert isinstance(result, FrozenLocalizedHypothesis)
    assert result.role_client_ids == ("c4",)
    assert result.outside_client_ids == ("c1", "c2", "c3")
    assert result.discovery_sign == 1
    assert all(item.eligible for item in result.client_evidence)
    assert all(item.bh_adjusted_value is not None for item in result.client_evidence)


def test_role_admissibility_rejects_empty_global_mixed_sign_and_missing_source():
    empty = _discover(
        tuple(_role_packet(f"c{i}", 0.0, seed=40 + i) for i in range(4))
    )
    assert isinstance(empty, RoleRejection)
    assert empty.reason == "EFFECT-ROLE-NOT-LOCALIZED"

    global_scope = _discover(
        tuple(_role_packet(f"c{i}", 2.0 if i < 3 else 0.0, seed=50 + i) for i in range(4))
    )
    assert isinstance(global_scope, RoleRejection)
    assert global_scope.reason == "GLOBAL-SCOPE-AMBIGUOUS"

    mixed = _discover(
        (
            _role_packet("c1", 2.0, seed=61),
            _role_packet("c2", -2.0, seed=62),
            _role_packet("c3", 0.0, seed=63),
            _role_packet("c4", 0.0, seed=64),
        )
    )
    assert isinstance(mixed, RoleRejection)
    assert mixed.reason == "SCOPE-SIGN-AMBIGUOUS"

    valid_packets = tuple(
        _role_packet(f"c{i + 1}", 2.0 if i == 3 else 0.0, seed=70 + i)
        for i in range(4)
    )
    orphan = _discover(valid_packets, source_term=None)
    assert isinstance(orphan, RoleRejection)
    assert orphan.reason == "SOURCE-PROVENANCE-MISSING"
