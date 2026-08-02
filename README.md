# FedFalsify

**Research prototype for certificate-guided federated symbolic mechanism discovery.**

FedFalsify studies whether institutions can refine an interpretable symbolic
hypothesis without sharing observation rows. Clients return aggregate fit,
residual, coefficient-shift, and replacement evidence; the server uses that
evidence to add, reject, gate, or conservatively replace symbolic terms.

> **Scientific status:** experimental finite-grammar software. The repository
> does not claim that federated symbolic regression, counterexample guidance,
> coefficient heterogeneity, or sequential replacement are generally new.
> Closest prior art and permitted claim language are documented in
> [`research/PRIOR_ART_AND_ORIGINALITY.md`](research/PRIOR_ART_AND_ORIGINALITY.md).

## Version 0.5

Version 0.5 preserves the v0.4 coefficient-heterogeneity certificate and adds a
**federated post-search core-surrogate replacement stage**.

After ordinary discovery finishes, the replacement stage evaluates conservative
one-for-one and two-for-one core-term swaps. A proposed swap is accepted only
when it:

1. improves a prespecified objective combining pooled and worst-client error;
2. improves at least a declared fraction of clients;
3. does not materially worsen most clients;
4. receives cross-client coefficient support for the incoming term;
5. remains significant after federated refitting; and
6. does not increase reported symbolic complexity.

Every accepted replacement is recorded in a machine-readable ledger. The v0.4
method remains executable as the direct ablation.

## Version history

- **v0.2:** complementary-domain recovery, shortcut rejection, and explicit
  invariant-core/exception output.
- **v0.3:** frozen pilot protocol, controlled baselines, five mechanisms,
  multi-seed CSV runner, and originality safeguards.
- **v0.4:** uncertainty-normalized cross-client coefficient contrast for a
  declared gated exception.
- **v0.5:** client-validated post-search replacement of correlated core
  surrogates.

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

Preregistered v0.3 pilot smoke test:

```bash
fedfalsify-pilot --smoke --output results/pilot_smoke.csv
```

v0.4 coefficient-heterogeneity ablation:

```bash
fedfalsify-heterogeneity --smoke --output results/v04_smoke.csv
```

v0.5 core-replacement smoke test:

```bash
fedfalsify-core-replacement --smoke --output results/v05_smoke.csv
```

Fixed v0.5 disjoint-seed development matrix:

```bash
fedfalsify-core-replacement --output results/v05_core_replacement.csv
```

Tests:

```bash
pytest
```

## Controlled development evidence

### v0.4 exception certificate

| Method | Exact recovery | Global NMSE | Exception recovery |
|---|---:|---:|---:|
| Without heterogeneity certificate | 0.580 | 0.03249 | 0.600 |
| v0.4 | **0.940** | **0.00021** | **1.000** |

### v0.5 disjoint-seed replacement study

The fixed v0.5 matrix contains five mechanisms, two sample sizes, ten seeds
disjoint from v0.4 development, and two methods: 200 method-runs total.

| Method | Exact recovery | Term precision | Term recall | Global NMSE | Exception recovery |
|---|---:|---:|---:|---:|---:|
| v0.4 | 0.920 | 0.982 | 0.985 | 0.00022 | 1.000 |
| v0.5 | **0.960** | **0.994** | **0.993** | **0.00014** | **1.000** |

The 95% Wilson intervals for exact recovery overlap, so these development
results do not establish statistically significant superiority. Four v0.5
failures remain and are documented rather than removed.

See:

- [`research/V0_4_DEVELOPMENT_FINDINGS.md`](research/V0_4_DEVELOPMENT_FINDINGS.md)
- [`research/V0_5_DEVELOPMENT_PROTOCOL.md`](research/V0_5_DEVELOPMENT_PROTOCOL.md)
- [`research/V0_5_DEVELOPMENT_FINDINGS.md`](research/V0_5_DEVELOPMENT_FINDINGS.md)
- [`research/V0_5_CLAIM_TO_EVIDENCE.md`](research/V0_5_CLAIM_TO_EVIDENCE.md)

## Protocol

```text
Server broadcasts a symbolic candidate
        ↓
Clients return aggregate fit, residual, and coefficient evidence
        ↓
Cross-client support rejects declared local shortcuts
        ↓
Coefficient contrast prioritizes restricted-domain exceptions
        ↓
The server refits and significance-prunes temporary terms
        ↓
A conservative post-search stage tests client-validated core swaps
        ↓
Final output separates invariant core, exceptions, and replacement ledger
```

## Candidate contribution

The current narrow hypothesis is:

> Can structured aggregate certificates combine residual support,
> cross-client coefficient shifts, and client-validated structural replacement
> to separate invariant terms, local shortcuts, restricted exceptions, and
> correlated core surrogates during federated symbolic repair?

This remains a candidate contribution until compared directly with published
centralized and federated symbolic-regression methods.

## Privacy and scientific boundaries

The prototype does not send raw rows, but aggregate normal equations, residual
statistics, coefficient adjustments, and repeated structural queries may leak
information. Therefore there is currently:

- no differential-privacy guarantee;
- no cryptographic-security guarantee;
- no causal-discovery claim;
- no clinical-discovery claim;
- no guarantee that a non-falsified equation is scientifically true;
- no claim of superiority over published symbolic-regression systems.

## Repository layout

```text
src/fedfalsify/       algorithm, replacement stage, baselines, and runners
tests/                recovery, shortcut, exception, replacement, and ablations
research/             protocols, findings, prior art, and claim maps
.github/workflows/    reproducibility and regression checks
```

## Citation and attribution

Software citation metadata is provided in [`CITATION.cff`](CITATION.cff).
Relevant literature is listed in
[`research/REFERENCES.bib`](research/REFERENCES.bib). Citing this repository
does not replace citing the original methods.

## License

MIT
