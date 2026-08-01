# FedFalsify

**Federated counterexample-guided mechanism discovery.**

FedFalsify explores a different objective from ordinary federated learning:
instead of averaging model weights, institutions act as private falsifiers of
an interpretable scientific hypothesis. They return structured certificates
that identify how a candidate mechanism fails; the server uses cross-client
consensus to repair the mechanism.

> Status: research prototype / minimum viable invention. It is not yet a
> privacy guarantee or a validated scientific-discovery system.

## What version 0.1 implements

- Four heterogeneous simulated clients with complementary input domains.
- A known hidden mechanism:
  `y = 2*x1 + sin(x2) + 0.5*x3^2 + noise`.
- A finite interpretable grammar of linear, quadratic, sine, and cosine terms.
- Client-side falsification certificates containing aggregated residual
  evidence and failure regions, never raw observation rows.
- Server-side consensus scoring that adds one counterexample-supported symbolic
  repair per discovery round.
- Exact coefficient refitting from federated aggregate summaries.
- Automated tests and a reproducible command-line demo.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run

```bash
fedfalsify-demo
```

or:

```bash
python -m fedfalsify.demo --samples 700 --noise 0.02 --rounds 7
```

A successful run should recover an expression close to:

```text
2*x1 + sin(x2) + 0.5*x3^2
```

Run tests:

```bash
pytest
```

## Protocol

```text
Server broadcasts candidate symbolic structure
        ↓
Clients fit/evaluate only on private local data
        ↓
Clients return aggregate fit summaries and falsification certificates
        ↓
Server ranks residual-supported missing terms
        ↓
Server repairs the hypothesis and starts the next round
```

## Important scientific boundary

Version 0.1 avoids sharing raw rows, but aggregated statistics can still leak
information. Do not describe the current prototype as differentially private,
cryptographically secure, or clinically validated. The next stages must add
privacy attacks, secure aggregation or DP, stronger baselines, expression-tree
search, theoretical guarantees, and external validation.

See [`research/TECHNICAL_SPEC.md`](research/TECHNICAL_SPEC.md) for the exact
research question, current assumptions, falsifiable claims, and next milestones.

## Repository layout

```text
src/fedfalsify/       discovery implementation
tests/                mechanism-recovery and certificate tests
research/             formal research notes
.github/workflows/    continuous integration
```

## License

MIT
