# FedFalsify

**Research prototype for certificate-guided federated symbolic mechanism discovery.**

FedFalsify studies whether institutions can refine an interpretable symbolic
hypothesis without sharing observation rows. Clients return aggregate fit,
residual, coefficient-shift, and replacement evidence; the server uses that
evidence to add, reject, gate, or conservatively replace symbolic terms.

> **Scientific status:** experimental research software. The repository does
> not claim that federated symbolic regression, counterexample guidance,
> coefficient heterogeneity, genetic programming, or sequential replacement are
> generally new. Closest prior art and permitted claim language are documented
> in [`research/PRIOR_ART_AND_ORIGINALITY.md`](research/PRIOR_ART_AND_ORIGINALITY.md).

## Version 0.6

Version 0.6 preserves the frozen v0.5 FedFalsify algorithm and adds a
publication-facing comparison and research-integrity framework:

- a deterministic expression-tree grammar;
- controlled centralized tree-GP search;
- controlled federated aggregate-fitness tree-GP-style search;
- controlled residual-counterexample tree-GP search;
- an optional adapter for the official PySR package;
- exact McNemar tests, Wilson intervals, paired bootstrap intervals, and Holm
  correction;
- runtime, candidate-evaluation, and serialized-communication accounting;
- leave-one-out certificate sensitivity probes; and
- a certificate-only Gaussian-noise utility ablation.

The controlled GP methods are independent project baselines, not faithful
reproductions of named published systems. See
[`research/V0_6_BASELINE_PROVENANCE.md`](research/V0_6_BASELINE_PROVENANCE.md).

## Version history

- **v0.2:** complementary-domain recovery, shortcut rejection, and explicit
  invariant-core/exception output.
- **v0.3:** frozen pilot protocol, controlled finite-catalog baselines, five
  mechanisms, multi-seed CSV runner, and originality safeguards.
- **v0.4:** uncertainty-normalized cross-client coefficient contrast for a
  declared gated exception.
- **v0.5:** client-validated post-search replacement of correlated core
  surrogates.
- **v0.6:** expression-tree comparison framework, matched statistics, optional
  official PySR adapter, communication accounting, and leakage/noise probes.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Optional official PySR baseline:

```bash
python -m pip install -e ".[sr]"
```

The optional dependency is pinned to stable PySR 1.5.x. It is not installed in
default CI because it requires a Julia-backed runtime.

## Run

Base demonstration:

```bash
fedfalsify-demo --benchmark base --samples 700 --noise 0.02 --seed 2026
```

v0.4 coefficient-heterogeneity smoke test:

```bash
fedfalsify-heterogeneity --smoke --output results/v04_smoke.csv
```

v0.5 core-replacement smoke test:

```bash
fedfalsify-core-replacement --smoke --output results/v05_smoke.csv
```

v0.6 matched comparison smoke test:

```bash
fedfalsify-confirmatory --smoke \
  --output results/v06_confirmatory_smoke.csv \
  --summary results/v06_confirmatory_smoke.json
```

v0.6 certificate-noise and sensitivity smoke test:

```bash
fedfalsify-privacy-study --smoke \
  --output results/v06_privacy_smoke.csv
```

Publication-facing primary command and frozen seeds are specified in
[`research/V0_6_CONFIRMATORY_PROTOCOL.md`](research/V0_6_CONFIRMATORY_PROTOCOL.md).

Tests:

```bash
pytest
```

## Development evidence

### v0.4 exception certificate

| Method | Exact recovery | Global NMSE | Exception recovery |
|---|---:|---:|---:|
| Without heterogeneity certificate | 0.580 | 0.03249 | 0.600 |
| v0.4 | **0.940** | **0.00021** | **1.000** |

### v0.5 disjoint-seed replacement study

| Method | Exact recovery | Term precision | Term recall | Global NMSE | Exception recovery |
|---|---:|---:|---:|---:|---:|
| v0.4 | 0.920 | 0.982 | 0.985 | 0.00022 | 1.000 |
| v0.5 | **0.960** | **0.994** | **0.993** | **0.00014** | **1.000** |

The v0.5 Wilson intervals overlap. These are development results, not a
statistically confirmed superiority claim.

### v0.6 smoke status

The CI smoke matrix verifies the comparison pipeline on only two matched
conditions with a tiny two-generation GP budget. FedFalsify recovered both
conditions, while the controlled GP methods did not. That output is explicitly
not paper evidence because the sample of conditions and search budget are too
small. Full diagnostic numbers and the reasons they cannot support a superiority
claim are recorded in
[`research/V0_6_SMOKE_FINDINGS.md`](research/V0_6_SMOKE_FINDINGS.md).

## Confirmatory analysis

The matched runner reports:

- exact symbolic recovery;
- term precision and recall;
- global-test NMSE;
- shortcut acceptance;
- exception recovery;
- runtime;
- candidate evaluations;
- serialized communication bytes;
- exact McNemar tests;
- Wilson intervals;
- paired bootstrap differences.

The registered protocol requires Holm correction across primary exact-recovery
comparisons and completely fresh seeds `9001`--`9020`.

## Privacy and leakage scope

The prototype does not send raw rows, but aggregate normal equations, residual
statistics, coefficient adjustments, and repeated structural queries may leak
information.

Version 0.6 adds:

- leave-one-out certificate sensitivity;
- controlled certificate perturbation;
- utility measurements under certificate noise.

It still provides:

- no differential-privacy guarantee;
- no epsilon/delta accountant;
- no cryptographic-security guarantee;
- no membership-inference protection claim.

Fit summaries remain unperturbed in the current noise ablation. See
[`research/V0_6_PRIVACY_SCOPE.md`](research/V0_6_PRIVACY_SCOPE.md).

## Candidate contribution

The current narrow hypothesis is:

> Can structured aggregate certificates combine residual support,
> cross-client coefficient shifts, and client-validated structural replacement
> to separate invariant terms, local shortcuts, restricted exceptions, and
> correlated core surrogates during federated symbolic repair?

This remains a candidate contribution until the frozen confirmatory study and
published-system comparisons are complete.

## Scientific boundaries

There is currently:

- no causal-discovery claim;
- no clinical-discovery claim;
- no guarantee that a non-falsified equation is scientifically true;
- no claim of general superiority over PySR, genetic programming, or published
  federated symbolic-regression systems;
- no claim that the controlled baselines reproduce author implementations.

## Repository layout

```text
src/fedfalsify/       algorithm, tree baselines, statistics, privacy probes
tests/                recovery, shortcut, exception, replacement, runner tests
research/             protocols, findings, prior art, provenance, claim maps
.github/workflows/    reproducibility and regression checks
```

## Citation and attribution

Software citation metadata is provided in [`CITATION.cff`](CITATION.cff).
Relevant literature is listed in
[`research/REFERENCES.bib`](research/REFERENCES.bib). Citing this repository
does not replace citing the original methods.

## License

MIT
