# FedFalsify v0.6 Official PySR Smoke Findings

## Scope

This note records one successful execution of the official PySR package through
the repository adapter. It verifies installation, Julia integration, model
fitting, prediction, CSV export, and workflow-artifact archiving.

It is **not** a performance comparison. The search budget was deliberately tiny
to keep the one-time GitHub Actions validation manageable.

## Environment

```text
operating system: Ubuntu 24.04 GitHub-hosted runner
Python: 3.11.15
Julia: 1.11.9
PySR: 1.5.10
SymbolicRegression.jl: 1.11.3
```

The optional dependency remains pinned to stable PySR 1.5.x.

## Smoke configuration

```text
benchmark: base
scenario: complementary domains
seed: 8001
clients: 4
samples/client: 60
noise ratio: 0.03
iterations: 5
populations: 2
population size: 20
maximum expression size: 14
binary operators: +, *
unary operators: sin, cos, square
parallelism: serial
model selection: best
```

Ground-truth mechanism:

\[
y = 2x_1 + \sin(x_2) + 0.5x_3^2 + \epsilon.
\]

## Result

PySR returned:

```text
2.0648782*x1
```

Measured values:

```text
global-test NMSE: 0.181411
model-search runtime: 10.816 seconds
exact symbolic recovery: no
missing terms: sin(x2), x3^2
```

Most workflow time was first-run Julia package installation and precompilation;
the reported model-search runtime excludes that setup cost.

## Correct interpretation

The result supports only this statement:

> The official PySR 1.5.10 adapter successfully executes on the registered data,
> exports an equation and predictions, and archives a reproducible result.

It does not support:

- a claim that PySR performs poorly;
- a claim that FedFalsify outperforms PySR;
- a fair runtime comparison;
- a state-of-the-art comparison;
- use of the smoke result in a paper performance table.

Five iterations and two small populations are intentionally insufficient for a
serious PySR benchmark. The publication-facing PySR comparison must use a frozen
larger budget, multiple fresh seeds, archived hall-of-fame equations, and the
complementary/spurious scenarios registered in the v0.6 protocol.

## Exception-condition limitation

The registered restricted exception uses:

\[
\mathbb{I}[x_3>1]x_3^2.
\]

This gate is not in the generic PySR operator set used by the adapter. Official
PySR exception results must therefore remain `unsupported` unless a custom gate
operator is frozen before execution and exposed equally to every applicable
method.

## Archived evidence

Workflow metadata:

```text
run ID: 30763089477
job ID: 91537012187
artifact ID: 8838112707
artifact SHA-256:
40bb9ac1a100aee99a95145781de639e8ca79fd6312bd7e1078129cc7127b32a
```

A machine-readable summary is stored in:

```text
research/results/V0_6_PYSR_SMOKE.json
```
