# FedFalsify v0.6 Baseline Provenance

## Why this document exists

A method name can accidentally imply that an implementation is official or
faithfully reproduces a published algorithm. This file records exactly what the
v0.6 baselines are and are not.

## `centralized-tree-gp`

### What it is

An independent project implementation of a multi-gene expression-tree
evolutionary search. A candidate consists of several expression genes whose
coefficients are estimated by pooled least squares. Selection balances pooled
error, worst-client error, and expression complexity.

### What it is not

- not PySR;
- not SymbolicRegression.jl;
- not DEAP GP;
- not an author implementation from a published paper;
- not intended to reproduce a published benchmark number.

Its role is to provide a transparent expression-tree baseline under the same
synthetic data and a frozen search budget.

## `federated-tree-gp-style`

### What it is

The same expression candidates as `centralized-tree-gp`, fitted from aggregate
client Gram matrices and target vectors. Candidate quality includes pooled and
worst-client losses. Serialized aggregate traffic is estimated for each
candidate evaluation.

### What it is not

- not the author implementation of Dong et al.'s federated GP framework;
- not BFSR;
- not a faithful reproduction of another federated SR paper;
- not cryptographically secure or differentially private.

The suffix `-style` is mandatory in paper tables and figure labels.

## `centralized-residual-counterexample-gp`

### What it is

A pooled expression-tree search that identifies the largest residuals after a
generation and increases their weights in the following generation. It is a
controlled residual-counterexample ablation.

### What it is not

- not the formal-verification counterexample system of Błądek and Krawiec;
- not an SMT-based verifier;
- not a reproduction of Logic-Guided Genetic Algorithms;
- not evidence that formal counterexamples are ineffective.

The baseline tests whether simple residual-focused refinement explains the
FedFalsify improvement.

## `official-pysr`

### What it is

An optional adapter around the installed official `pysr` Python package. The
repository pins the optional dependency to stable PySR 1.5.x rather than a 2.0
prerelease.

### Reproducibility requirements

For every PySR run archive:

- exact PySR and Julia versions;
- random seed;
- operators and constraints;
- population size, populations, iterations, maximum size, and model-selection
  rule;
- hall-of-fame equations;
- machine and runtime metadata.

### Scope limitation

The registered `I(x3>1)` gate is not part of the generic operator set. Official
PySR should therefore be evaluated on complementary and spurious scenarios by
default. Adding a custom gate after seeing results is prohibited.

## Fair-label rules

Use these table labels:

| Repository method | Required manuscript label |
|---|---|
| `centralized-tree-gp` | Controlled centralized tree-GP baseline |
| `federated-tree-gp-style` | Controlled federated tree-GP-style baseline |
| `centralized-residual-counterexample-gp` | Controlled residual-counterexample GP baseline |
| `official-pysr` | Official PySR package baseline |

Do not use:

- “Dong et al. implementation”;
- “BFSR implementation”;
- “CDSR implementation”;
- “state-of-the-art GP”;
- “official federated GP baseline.”

## Independent implementation statement

The controlled baselines were written for this repository using NumPy and the
Python standard library. Published source code was not copied. Standard concepts
such as genetic programming, linear scaling, residual reweighting, federated
normal equations, complexity penalties, and tournament-like elite evolution
remain prior art and must be cited rather than claimed as inventions.
