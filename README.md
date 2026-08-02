# FedFalsify

**Research prototype for federated, counterexample-guided mechanism discovery.**

FedFalsify studies whether institutions can test and refine an interpretable
hypothesis without sharing observation rows. Clients return aggregate residual
certificates; the server uses cross-client evidence to add or reject symbolic
terms.

> **Scientific status:** experimental software. The repository does not claim
> that the general idea of counterexample-guided symbolic regression,
> falsification-driven discovery, or federated symbolic regression is new.
> Closest prior work is documented in
> [`research/PRIOR_ART_AND_ORIGINALITY.md`](research/PRIOR_ART_AND_ORIGINALITY.md).

## Version 0.2 research milestones

Version 0.2 implements three controlled synthetic studies:

1. **Complementary-domain recovery**
   - hidden mechanism: `2*x1 + sin(x2) + 0.5*x3^2`;
   - clients observe different input regions;
   - the federation recovers the common mechanism.
2. **Spurious-correlation rejection**
   - `x3` is strongly correlated with the outcome at only one client;
   - core terms require agreement from a declared fraction of observing clients;
   - the local shortcut is rejected.
3. **Invariant core plus restricted exception**
   - common mechanism: `2*x1 + sin(x2)`;
   - an additional `0.75*x3^2` term applies only when `x3 > 1`;
   - clients outside that domain are treated as unable to falsify the exception;
   - the output separates the invariant core from the provisional exception.

The implementation also prunes terms whose final fitted coefficients are
negligible, preventing temporary repair terms from being reported as discoveries.

## Install and run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Base experiment:

```bash
fedfalsify-demo --benchmark base --samples 700 --noise 0.02 --seed 2026
```

Spurious-correlation benchmark:

```bash
fedfalsify-demo --benchmark spurious --samples 800 --noise 0.02 --seed 191
```

Invariant-core/exception benchmark:

```bash
fedfalsify-demo --benchmark exception --samples 900 --noise 0.015 --seed 229
```

Tests:

```bash
pytest
```

## Protocol implemented here

```text
Server broadcasts a candidate symbolic structure
        ↓
Clients fit and evaluate it on private local observations
        ↓
Clients return aggregate fit summaries and term-level residual certificates
        ↓
Core terms require cross-client support among clients that observe the term
        ↓
Domain-gated terms may be retained as provisional exceptions
        ↓
The server refits, prunes negligible terms, and repeats
```

## What is potentially distinctive

The current research hypothesis is narrow:

> Can structured aggregate certificates be used to separate cross-client
> invariant symbolic terms, single-client shortcuts, and domain-restricted
> exceptions in one federated repair protocol?

This is a **candidate contribution**, not an established novelty claim. Prior
art already covers federated genetic-programming symbolic regression,
privacy-preserving symbolic regression, counterexample-driven symbolic
regression, falsification-based experiment planning, federated invariant
learning, and granular feedback for equation search. Any paper must compare
against those families and must not use phrases such as "the first" until a
systematic review supports them.

## Privacy and scientific boundaries

The prototype does not send raw observation rows, but it sends aggregate normal
equations and residual summaries. These may leak information. Therefore:

- no differential-privacy claim;
- no cryptographic-security claim;
- no causal-discovery claim;
- no clinical-discovery claim;
- no guarantee that a non-falsified equation is scientifically true.

See the technical specification and originality protocol in `research/`.

## Repository layout

```text
src/fedfalsify/       algorithm and benchmark implementation
tests/                recovery, rejection, and exception tests
research/             technical specification, prior art, and citation records
.github/workflows/    continuous integration
```

## Citation and attribution

Software citation metadata is provided in [`CITATION.cff`](CITATION.cff).
Literature used to define the research boundary is listed in
[`research/REFERENCES.bib`](research/REFERENCES.bib). Citing this repository does
not replace citing the original methods on which the research context depends.

## License

MIT
