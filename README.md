# FedFalsify

**Research prototype for federated, counterexample-guided mechanism discovery.**

FedFalsify studies whether institutions can test and refine an interpretable
hypothesis without sharing observation rows. Clients return aggregate
falsification certificates; the server uses cross-client evidence to add,
reject, or gate symbolic terms.

> **Scientific status:** experimental software. The repository does not claim
> that counterexample-guided symbolic regression, falsification-driven
> discovery, federated symbolic regression, or coefficient heterogeneity are
> generally new. The candidate contribution is narrower and is documented in
> [`research/PRIOR_ART_AND_ORIGINALITY.md`](research/PRIOR_ART_AND_ORIGINALITY.md).

## Version 0.4

Version 0.4 adds a **cross-client coefficient-heterogeneity certificate** for
restricted-domain exceptions.

For every non-intercept grammar term, each client computes an aggregate local
coefficient adjustment after conditioning on the current candidate model. For a
gated exception, the server compares the source-term adjustment between clients
that observe the gate and clients outside it.

Current gated example:

```text
invariant source term: x3^2
restricted exception: I(x3 > 1) * x3^2
```

The exception is prioritized only when the coefficient contrast is large
relative to local uncertainty. Final coefficients are pruned using both
magnitude and an approximate significance threshold. The search may temporarily
use one slack term so a surrogate can disappear after the correct mechanism is
added.

## Controlled milestones

The repository contains synthetic tests for:

1. complementary-domain mechanism recovery;
2. rejection of a single-client spurious shortcut;
3. invariant-core and restricted-exception separation;
4. low-sample surrogate trapping;
5. v0.3 versus v0.4 coefficient-heterogeneity ablation;
6. multi-seed CSV experiment logging.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run

Base demonstration:

```bash
fedfalsify-demo --benchmark base --samples 700 --noise 0.02 --seed 2026
```

Preregistered v0.3 pilot runner:

```bash
fedfalsify-pilot --smoke --output results/pilot_smoke.csv
```

v0.4 coefficient-heterogeneity development study:

```bash
fedfalsify-heterogeneity --smoke \
  --output results/v04_heterogeneity_smoke.csv
```

Full fixed v0.4 development matrix:

```bash
fedfalsify-heterogeneity \
  --output results/v04_heterogeneity.csv
```

Tests:

```bash
pytest
```

## v0.4 development evidence

The fixed 100-run development matrix compared v0.4 with the same method after
disabling the coefficient-heterogeneity certificate.

| Method | Exact recovery | Global NMSE | Exception recovery |
|---|---:|---:|---:|
| Without heterogeneity certificate | 0.580 | 0.03249 | 0.600 |
| v0.4 | **0.940** | **0.00021** | **1.000** |

These are development results, not confirmatory publication claims. All three
remaining v0.4 exact-recovery failures are documented in
[`research/V0_4_DEVELOPMENT_FINDINGS.md`](research/V0_4_DEVELOPMENT_FINDINGS.md).
The permitted claim language is mapped to executable evidence in
[`research/V0_4_CLAIM_TO_EVIDENCE.md`](research/V0_4_CLAIM_TO_EVIDENCE.md).

## Protocol

```text
Server broadcasts a candidate symbolic structure
        ↓
Clients evaluate it on private local observations
        ↓
Clients return aggregate fit, residual, and coefficient-shift evidence
        ↓
Core terms require support across observing clients
        ↓
Gated exceptions require an uncertainty-normalized coefficient contrast
        ↓
The server refits and significance-prunes temporary surrogate terms
```

## Candidate contribution

The current narrow research hypothesis is:

> Can structured aggregate certificates separate cross-client invariant terms,
> client-local shortcuts, and restricted-domain exceptions during iterative
> federated symbolic repair?

This remains a candidate contribution until compared against published
federated symbolic regression, centralized symbolic regression, and
counterexample-guided symbolic regression methods.

## Privacy and scientific boundaries

The prototype does not send raw observation rows, but aggregate normal
equations, residual statistics, coefficient adjustments, and uncertainty
estimates may leak information. Therefore there is currently:

- no differential-privacy guarantee;
- no cryptographic-security guarantee;
- no causal-discovery claim;
- no clinical-discovery claim;
- no guarantee that a non-falsified equation is scientifically true.

## Repository layout

```text
src/fedfalsify/       algorithm, baselines, and benchmark runners
tests/                recovery, shortcut, exception, and ablation tests
research/             protocols, prior art, findings, and citation records
.github/workflows/    continuous integration
```

## Citation and attribution

Software citation metadata is provided in [`CITATION.cff`](CITATION.cff).
Relevant literature is listed in
[`research/REFERENCES.bib`](research/REFERENCES.bib). Citing this repository
does not replace citing the original methods.

## License

MIT
