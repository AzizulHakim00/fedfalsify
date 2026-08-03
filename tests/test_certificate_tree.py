from __future__ import annotations

import numpy as np

from fedfalsify.benchmarks import generate_benchmark
from fedfalsify.certificate_tree import (
    candidate_certificates,
    run_certificate_tree_search,
)
from fedfalsify.expression_tree import Expr


def test_local_spurious_gene_receives_larger_certificate_penalty() -> None:
    generated = generate_benchmark(
        "base",
        scenario="spurious",
        samples_per_client=300,
        noise_ratio=0.03,
        seed=10011,
        num_clients=4,
    )
    invariant, _ = candidate_certificates(
        generated.clients,
        (Expr.variable(0),),
    )
    shortcut, _ = candidate_certificates(
        generated.clients,
        (Expr.variable(3),),
    )
    assert invariant[0].kind == "core"
    assert shortcut[0].kind == "core"
    assert invariant[0].support_fraction >= shortcut[0].support_fraction
    assert shortcut[0].penalty > invariant[0].penalty


def test_true_gated_exception_is_classified_explicitly() -> None:
    generated = generate_benchmark(
        "base",
        scenario="exception",
        samples_per_client=300,
        noise_ratio=0.03,
        seed=10012,
        num_clients=4,
    )
    gated = Expr.unary("gate_x3_gt1", Expr.unary("square", Expr.variable(2)))
    certificates, communication = candidate_certificates(
        generated.clients,
        (gated,),
    )
    certificate = certificates[0]
    assert certificate.kind == "exception"
    assert certificate.observable_clients >= 2
    assert certificate.supporting_clients >= 1
    assert communication > 0


def test_certificate_tree_search_runs_without_named_term_catalog() -> None:
    generated = generate_benchmark(
        "interaction",
        scenario="spurious",
        samples_per_client=60,
        noise_ratio=0.03,
        seed=10013,
        num_clients=4,
    )
    output = run_certificate_tree_search(
        generated.clients,
        seed=10013,
        population_size=8,
        generations=1,
        max_genes=2,
        max_complexity=5,
    )
    assert output.method == "certificate-guided-federated-tree"
    assert output.evaluations > 0
    assert output.communication_bytes > 0
    assert output.runtime_seconds > 0
    assert np.isfinite(output.global_mse)
    assert np.isfinite(output.worst_client_mse)
    canonical = [gene.canonical() for gene in output.model.genes]
    assert len(canonical) == len(set(canonical))
    assert len(output.certificates) == len(output.model.genes)


def test_search_is_deterministic_in_structure_for_fixed_seed() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=50,
        noise_ratio=0.03,
        seed=10014,
        num_clients=4,
    )
    first = run_certificate_tree_search(
        generated.clients,
        seed=10014,
        population_size=8,
        generations=1,
        max_genes=2,
        max_complexity=3,
    )
    second = run_certificate_tree_search(
        generated.clients,
        seed=10014,
        population_size=8,
        generations=1,
        max_genes=2,
        max_complexity=3,
    )
    assert [gene.canonical() for gene in first.model.genes] == [
        gene.canonical() for gene in second.model.genes
    ]
    np.testing.assert_allclose(first.model.coefficients, second.model.coefficients)
