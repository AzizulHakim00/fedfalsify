from types import SimpleNamespace

import numpy as np

from fedfalsify.scsv_v10_benchmarks import LINEAR_DEV_V10, v10_catalog
from fedfalsify.shared_recertification import certify_shared_core, nominate_shared_family
from tests.phase3b_test_utils import stats_packet


def _anchor(selector_terms, bank_terms):
    return SimpleNamespace(
        selector_structure=tuple(selector_terms),
        bank=SimpleNamespace(candidate_terms=tuple(bank_terms)),
    )


def test_nominate_shared_family_unions_selector_and_bank_without_exceptions():
    catalog = v10_catalog()
    anchor = _anchor(
        ("1", "x1", LINEAR_DEV_V10),
        ("x3^2", "sin(x2)", LINEAR_DEV_V10),
    )
    family = nominate_shared_family(anchor, catalog)
    assert family[0] == "1"
    assert set(family) == {"1", "x1", "x3^2", "sin(x2)"}
    assert all(catalog.get(term).kind != "exception" for term in family)
    assert len(family) == len(set(family))


def test_selector_joint_certification_keeps_signal_rejects_null_and_abstains_collinear():
    catalog = v10_catalog()
    terms = ("1", "x1", "x2", "x3", "x1^2")
    rng = np.random.default_rng(771)
    n = 180
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    duplicate = rng.normal(size=n)
    design = np.column_stack([np.ones(n), x1, x2, duplicate, duplicate])
    response = 0.4 + 2.2 * x1
    packet = stats_packet("selector-pooled", terms, design, response)
    anchor = _anchor(terms, ())

    result = certify_shared_core(anchor, (packet,), catalog)
    diagnostics = {item.term: item for item in result.diagnostics}

    assert result.accepted_shared_terms == ("1", "x1")
    assert diagnostics["x1"].holm_rejected is True
    assert diagnostics["x2"].holm_rejected is False
    assert diagnostics["x2"].raw_p_value >= 0.99
    assert diagnostics["x3"].reason == "STRUCTURAL-RANK-AMBIGUOUS"
    assert diagnostics["x1^2"].reason == "STRUCTURAL-RANK-AMBIGUOUS"
    assert set(result.rank_abstentions) == {"x3", "x1^2"}


def test_shared_capacity_is_intercept_plus_five_using_adjusted_p_then_catalog_order():
    catalog = v10_catalog()
    terms = ("1", "x1", "x2", "x3", "x1^2", "x2^2", "x3^2")
    rng = np.random.default_rng(772)
    n = 240
    design = np.column_stack([np.ones(n)] + [rng.normal(size=n) for _ in range(6)])
    response = design @ np.asarray([0.2, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
    packet = stats_packet("selector-pooled", terms, design, response)
    anchor = _anchor(terms, terms[1:])

    result = certify_shared_core(anchor, (packet,), catalog)

    assert result.capacity_truncated is True
    assert result.accepted_shared_terms == ("1", "x1", "x2", "x3", "x1^2", "x2^2")
    assert result.removed_by_capacity == ("x3^2",)
