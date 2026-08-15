"""Exception-aware correction for certificate-guided adaptive tree search.

Ordinary invariant-core genes require evidence from at least two observable
clients. A deliberately restricted gated exception may be observable on only
one client; it is therefore governed by its stricter within-observable support
threshold rather than the core minimum-observability rule.
"""

from __future__ import annotations

import numpy as np

from . import certificate_tree as _core


def _aggregate_gene_certificate(
    gene,
    evidence,
    *,
    total_clients: int,
    core_support_threshold: float,
    exception_support_threshold: float,
    sign_agreement_threshold: float,
    z_threshold: float,
    penalty_scale: float,
):
    observable = [item for item in evidence if item.observable]
    kind = "exception" if _core._contains_gate(gene) else "core"
    required_support = (
        exception_support_threshold if kind == "exception" else core_support_threshold
    )
    minimum_observable_clients = 1 if kind == "exception" else min(2, total_clients)
    supporting = [item for item in observable if abs(item.z_score) >= z_threshold]
    support_fraction = len(supporting) / len(observable) if observable else 0.0
    if supporting:
        weights = np.asarray(
            [max(item.effective_energy, 1e-12) for item in supporting],
            dtype=float,
        )
        signs = np.sign([item.coefficient for item in supporting])
        sign_agreement = float(abs(np.average(signs, weights=weights)))
        median_z = float(np.median([abs(item.z_score) for item in supporting]))
        median_coefficient = float(
            np.median([abs(item.coefficient) for item in supporting])
        )
    else:
        sign_agreement = 0.0
        median_z = 0.0
        median_coefficient = 0.0

    observability_deficit = max(
        0, minimum_observable_clients - len(observable)
    ) / max(minimum_observable_clients, 1)
    support_deficit = max(0.0, required_support - support_fraction)
    sign_deficit = max(0.0, sign_agreement_threshold - sign_agreement)
    penalty = penalty_scale * (
        2.0 * observability_deficit
        + 3.0 * support_deficit
        + 2.0 * sign_deficit
    )
    return _core.GeneCertificate(
        gene=gene.canonical(),
        recognized_term=_core.recognized_term(gene) or "",
        kind=kind,
        observable_clients=len(observable),
        supporting_clients=len(supporting),
        support_fraction=float(support_fraction),
        sign_agreement=sign_agreement,
        median_absolute_z=median_z,
        median_absolute_coefficient=median_coefficient,
        penalty=float(penalty),
    )


_core._aggregate_gene_certificate = _aggregate_gene_certificate

CertificateTreeOutput = _core.CertificateTreeOutput
GeneCertificate = _core.GeneCertificate
candidate_certificates = _core.candidate_certificates
run_certificate_tree_search = _core.run_certificate_tree_search
