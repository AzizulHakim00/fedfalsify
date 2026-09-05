import numpy as np

from fedfalsify.localized_certification import (
    certify_on_probe,
    outside_safe,
    screen_on_selector,
)
from fedfalsify.role_localization_v12 import FrozenLocalizedHypothesis
from fedfalsify.scsv_v10_benchmarks import (
    LINEAR_DEV_V10,
    QUADRATIC_DEV_V10,
    TRIG_DEV_V10,
    v10_catalog,
)
from tests.phase3b_test_utils import stats_packet


SHARED = ("1", "x1")


def _hypothesis(term, source, role_id, outside_ids, sign=1):
    all_ids = (role_id,) + tuple(outside_ids)
    return FrozenLocalizedHypothesis(
        term=term,
        source_term=source,
        role_indices=(0,),
        outside_indices=tuple(range(1, len(all_ids))),
        role_client_ids=(role_id,),
        outside_client_ids=tuple(outside_ids),
        discovery_sign=sign,
        client_evidence=(),
    )


def _pair_packets(term, *, role_beta, outside_beta=0.0, outside_active=False, collinear=False):
    packets = []
    for index, (client_id, beta, active) in enumerate(
        (("role", role_beta, True), ("outside", outside_beta, outside_active))
    ):
        rng = np.random.default_rng(100 + index)
        n = 70
        x1 = rng.normal(size=n)
        if collinear and client_id == "role":
            z = x1.copy()
        elif active:
            z = np.zeros(n)
            z[:25] = rng.normal(size=25)
        else:
            z = np.zeros(n)
        design = np.column_stack([np.ones(n), x1, z])
        response = 0.3 + 0.7 * x1 + beta * z
        packets.append(stats_packet(client_id, SHARED + (term,), design, response))
    return tuple(packets)


def test_selector_can_only_remove_and_enforces_sign_gain_outside_and_rank_safety():
    catalog = v10_catalog()
    h = _hypothesis(LINEAR_DEV_V10, "x1", "role", ("outside",), sign=1)

    good = screen_on_selector((h,), SHARED, _pair_packets(LINEAR_DEV_V10, role_beta=2.0), catalog)
    assert good.surviving_hypotheses == (h,)

    sign_bad = screen_on_selector(
        (h,), SHARED, _pair_packets(LINEAR_DEV_V10, role_beta=-2.0), catalog
    )
    assert sign_bad.surviving_hypotheses == ()
    assert sign_bad.diagnostics[0].reason == "SCOPE-SIGN-MISMATCH"

    gain_bad = screen_on_selector(
        (h,), SHARED, _pair_packets(LINEAR_DEV_V10, role_beta=0.0, outside_active=False), catalog
    )
    assert gain_bad.surviving_hypotheses == ()
    assert gain_bad.diagnostics[0].reason == "NONPOSITIVE-ROLE-GAIN"

    outside_bad = screen_on_selector(
        (h,),
        SHARED,
        _pair_packets(LINEAR_DEV_V10, role_beta=2.0, outside_beta=0.0, outside_active=True),
        catalog,
    )
    assert outside_bad.surviving_hypotheses == ()
    assert outside_bad.diagnostics[0].reason == "OUTSIDE-NONDEGRADATION-FAIL"

    rank_bad = screen_on_selector(
        (h,), SHARED, _pair_packets(LINEAR_DEV_V10, role_beta=2.0, collinear=True), catalog
    )
    assert rank_bad.surviving_hypotheses == ()
    assert rank_bad.diagnostics[0].reason == "STRUCTURAL-RANK-AMBIGUOUS"


def test_selector_structural_missing_term_is_rejected_not_rewritten():
    catalog = v10_catalog()
    h = _hypothesis(LINEAR_DEV_V10, "x1", "role", ("outside",), sign=1)
    rng = np.random.default_rng(123)
    packets = []
    for client_id in ("role", "outside"):
        n = 40
        x1 = rng.normal(size=n)
        design = np.column_stack([np.ones(n), x1])
        response = 0.2 + 0.5 * x1
        packets.append(stats_packet(client_id, SHARED, design, response))
    result = screen_on_selector((h,), SHARED, tuple(packets), catalog)
    assert result.surviving_hypotheses == ()
    assert result.diagnostics[0].reason == "STRUCTURAL-NESTING-FAIL"


def _multi_probe_packets(effects, *, collinear_term=None):
    terms = SHARED + (LINEAR_DEV_V10, QUADRATIC_DEV_V10, TRIG_DEV_V10)
    packets = []
    role_ids = ("c1", "c2", "c3")
    for client_index, client_id in enumerate(("c1", "c2", "c3", "c4")):
        rng = np.random.default_rng(200 + client_index)
        n = 80
        x1 = rng.normal(size=n)
        columns = [np.ones(n), x1]
        response = 0.4 + 0.6 * x1
        for term_index, term in enumerate(terms[2:]):
            if client_id == role_ids[term_index]:
                if term == collinear_term:
                    z = x1.copy()
                else:
                    z = np.zeros(n)
                    z[:30] = rng.normal(size=30)
                response = response + float(effects.get(term, 0.0)) * z
            else:
                z = np.zeros(n)
            columns.append(z)
        packets.append(stats_packet(client_id, terms, np.column_stack(columns), response))
    return tuple(packets)


def _three_hypotheses(*, shared_source=False):
    sources = (
        "x1",
        "x1" if shared_source else "x3^2",
        "cos(x2)",
    )
    terms = (LINEAR_DEV_V10, QUADRATIC_DEV_V10, TRIG_DEV_V10)
    ids = ("c1", "c2", "c3")
    all_ids = ("c1", "c2", "c3", "c4")
    result = []
    for term, source, role_id in zip(terms, sources, ids):
        outside = tuple(item for item in all_ids if item != role_id)
        role_index = all_ids.index(role_id)
        outside_indices = tuple(index for index, item in enumerate(all_ids) if item != role_id)
        result.append(
            FrozenLocalizedHypothesis(
                term=term,
                source_term=source,
                role_indices=(role_index,),
                outside_indices=outside_indices,
                role_client_ids=(role_id,),
                outside_client_ids=outside,
                discovery_sign=1,
                client_evidence=(),
            )
        )
    return tuple(result)


def test_probe_preserves_family_identity_and_holm_includes_rank_abstention_as_p_one():
    hypotheses = _three_hypotheses()
    snapshot = tuple(item.identity for item in hypotheses)
    packets = _multi_probe_packets(
        {LINEAR_DEV_V10: 2.0, QUADRATIC_DEV_V10: 0.0, TRIG_DEV_V10: 2.0},
        collinear_term=TRIG_DEV_V10,
    )
    result = certify_on_probe(hypotheses, SHARED, packets, v10_catalog())
    diagnostics = {item.term: item for item in result.diagnostics}

    assert result.family_identities == snapshot
    assert tuple(result.holm.names) == tuple(item.term for item in hypotheses)
    assert diagnostics[TRIG_DEV_V10].raw_p_value == 1.0
    assert diagnostics[TRIG_DEV_V10].reason == "STRUCTURAL-RANK-AMBIGUOUS"
    assert set(result.accepted_terms).issubset(set(result.holm.rejected))


def test_probe_source_ambiguity_rejects_all_linked_acceptances():
    hypotheses = _three_hypotheses(shared_source=True)[:2]
    packets = _multi_probe_packets({LINEAR_DEV_V10: 2.0, QUADRATIC_DEV_V10: 2.0})
    result = certify_on_probe(hypotheses, SHARED, packets, v10_catalog())
    assert result.source_ambiguity is True
    assert result.accepted_terms == ()


def test_probe_capacity_rejects_new_localized_set_instead_of_ranking_three_winners():
    hypotheses = _three_hypotheses()
    packets = _multi_probe_packets(
        {LINEAR_DEV_V10: 2.0, QUADRATIC_DEV_V10: 2.0, TRIG_DEV_V10: 2.0}
    )
    result = certify_on_probe(hypotheses, SHARED, packets, v10_catalog())
    assert set(result.holm.rejected) == {item.term for item in hypotheses}
    assert result.capacity_ambiguous is True
    assert result.accepted_terms == ()


def test_outside_safety_tolerance_boundary_is_exact():
    assert outside_safe(reduced_sse=1.0, full_sse=1.0 + 1e-10)
    assert not outside_safe(reduced_sse=1.0, full_sse=1.0 + 1.0001e-10)
