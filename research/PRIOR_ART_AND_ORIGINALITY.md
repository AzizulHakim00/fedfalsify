# Prior Art, Originality, and Anti-Plagiarism Protocol

## Purpose

This document prevents two different research-integrity failures:

1. copying text, code, equations, or algorithm descriptions without attribution;
2. presenting an existing research direction as an original discovery.

A similarity checker cannot prove originality. Originality requires documented
prior-art search, independent implementation, accurate citations, and a narrow
claim that is experimentally distinguishable from existing methods.

## Closest research families

### Federated symbolic regression

Federated symbolic regression is established prior art. Dong et al. proposed a
federated genetic-programming framework for symbolic regression. Later work
studied vertical secure symbolic regression, Bayesian federated symbolic
regression, federated multi-objective SR, and federated KAN-based symbolic model
identification. FedFalsify must not claim that distributed equation discovery
without raw-data centralization is new.

### Counterexample-guided symbolic regression

Counterexample-driven symbolic regression is also prior art. Błądek and Krawiec
used formal verification to obtain counterexamples that guide genetic
programming under formal constraints. Logic-guided genetic algorithms likewise
use violated mathematical truths to generate corrective examples. Informal
counterexample-driven GP has also used error-focused observations without a
formal verifier. Therefore, FedFalsify must not claim that counterexamples,
residual-focused examples, or error reweighting in symbolic regression are new.

### Expression-tree symbolic regression and PySR

Genetic programming and expression-tree symbolic regression are established
methods. PySR and SymbolicRegression.jl provide mature evolutionary equation
search with configurable operators, complexity limits, populations, and model
selection. FedFalsify must not claim invention of expression trees,
multi-population search, genetic operators, linear scaling, Pareto selection, or
complexity-accuracy trade-offs.

The v0.6 tree-GP baselines are independent controlled implementations. They are
not PySR and are not author-code reproductions. The optional `official-pysr`
adapter must be clearly separated from the project tree baselines in every table.

### Falsification-driven scientific modeling

Model-falsification approaches have used symbolic regression to choose new
experimental regions that discriminate between candidate models. FedFalsify
must distinguish its retrospective, distributed certificate protocol from
active experimental-design falsification.

### Federated causal and invariant learning

Federated causal discovery and federated invariant/OOD learning already address
spurious relationships across clients. FedFalsify currently discovers
predictive symbolic structure and must not label it causal unless identification
assumptions and causal validation are added.

### Granular equation-search feedback

Recent equation-search work uses term-level or influence-level feedback to guide
symbolic refinement. Consequently, the presence of granular residual feedback
is not by itself a sufficient novelty claim.

### Cross-site coefficient heterogeneity

Site-specific effects, mixed models, heterogeneous meta-analysis, and
summary-statistic inference under data-sharing constraints are established
research areas. Fed-GLMM estimates federated generalized linear mixed models,
and integrative sparse-regression methods explicitly model similar but
non-identical coefficients across data sources. FedFalsify must therefore not
claim that local coefficient estimates, coefficient contrasts, or cross-site
heterogeneity are new by themselves.

The v0.4 novelty hypothesis is narrower: conditional source-term coefficient
adjustments are used as a falsification certificate to prioritize a declared
domain-gated symbolic exception over globally correlated surrogate expressions
during iterative federated repair.

### Sequential and floating replacement search

Adding, deleting, and conditionally replacing selected variables is established
feature-selection prior art. Floating search methods alternate forward and
backward steps to reconsider previously selected subsets. Therefore, v0.5 must
not claim that post-search replacement, one-for-one swaps, or two-for-one swaps
are new by themselves.

The v0.5 candidate contribution is narrower: proposed symbolic swaps are fitted
from federated aggregate normal equations and accepted only when a combined
certificate shows robust objective improvement, client-level non-degradation,
and cross-client coefficient support for the incoming term. Every accepted swap
is recorded in an auditable replacement ledger.

### Privacy and noisy statistics

Non-sharing of raw rows is not equivalent to privacy. Summary statistics,
normal equations, gradients, coefficients, and repeated adaptive queries can
leak information. Gaussian perturbation by itself is not a differential-privacy
guarantee without a neighboring-dataset definition, clipping, sensitivity,
composition, and an epsilon/delta accountant.

Version 0.6 therefore treats leave-one-out sensitivity and certificate noise as
leakage/utility probes only. It must not claim differential privacy.

## Narrow candidate contribution

The repository currently tests the following combination:

1. clients send structured **aggregate term certificates**, not raw rows;
2. ordinary terms require support across clients that can observe them;
3. a term observable everywhere but supported at one client is treated as a
   shortcut and rejected;
4. a gated term observable in only a restricted domain can be reported as a
   provisional exception rather than forced into the invariant core;
5. the output explicitly separates the invariant symbolic core from
   domain-restricted exceptions;
6. a gated exception may be prioritized when its source term exhibits a strong,
   uncertainty-normalized coefficient shift between clients inside and outside
   the declared validity domain; and
7. a post-search core replacement is accepted only when aggregate fit,
   worst-client behavior, client-level non-degradation, incoming coefficient
   support, and symbolic complexity jointly favor the replacement.

This combination is a **novelty hypothesis**. It becomes a defensible research
contribution only after systematic search and direct experiments against the
closest methods.

## Baseline naming and provenance rules

The v0.6 controlled baselines must be labeled exactly as project baselines:

- controlled centralized tree-GP baseline;
- controlled federated tree-GP-style baseline;
- controlled residual-counterexample GP baseline.

Do not rename them after a published method. Do not state that they reproduce
Dong et al., BFSR, PySR, or counterexample-driven formal GP. The only official
package adapter currently included is the optional PySR adapter.

See `V0_6_BASELINE_PROVENANCE.md` for the full boundary.

## Independent implementation record

The repository implementation is written specifically for this project using
NumPy and Python standard-library components. No external SR source code has
been copied into the repository. General ideas such as genetic programming,
least-squares normal equations, residualization, coefficient tests,
meta-analysis, floating search, sequential replacement, CEGIS-style iteration,
expression trees, residual reweighting, and symbolic basis functions are
established techniques and are cited as background rather than claimed as
inventions.

## Writing rules for the paper

- Write all prose from project notes and results; do not paraphrase line by line
  from a source.
- Put exact quotations in quotation marks and cite the source; avoid quotations
  unless necessary.
- Cite an idea in the paragraph where it is used, not only in the related-work
  section.
- Cite original papers rather than copying citations from a survey.
- Do not reuse figures, tables, pseudocode, or equations from another paper
  without permission and explicit attribution.
- Use fresh figure layouts and project-generated plots.
- Explain mathematical overlap: which components are standard and which are
  project-specific.
- Retain dated Git commits, experiment configurations, and result files as a
  provenance record.
- Distinguish official package results, project reimplementations, and reported
  literature results in every table.

## Pre-submission audit

Before submission:

1. update the literature search through the submission date;
2. compare the proposed algorithm line by line with the closest five methods;
3. run iThenticate or the publisher-approved similarity system on the manuscript;
4. manually inspect every highlighted phrase rather than optimizing only for a
   similarity percentage;
5. confirm that all borrowed datasets, code, equations, and definitions satisfy
   their licenses and citation requirements;
6. archive code, seeds, configurations, raw result tables, and a
   claim-to-evidence table;
7. verify every baseline label against `V0_6_BASELINE_PROVENANCE.md`;
8. remove "first", "novel", "privacy preserving", and "discovery" claims that
   are not directly supported by the completed comparison.

## Claim language

Safe before full comparison:

> We investigate a federated certificate protocol that combines conditional
> residual evidence, cross-client coefficient shifts, and conservative
> client-validated core replacement to separate invariant symbolic terms, local
> shortcuts, and restricted-domain exceptions.

Unsafe at the current stage:

> We present the first federated falsification algorithm and discover a new
> scientific law.

> Our Gaussian certificate mechanism guarantees privacy.

> Our controlled tree-GP baseline reproduces published federated GP.

See `REFERENCES.bib` for the sources defining this research boundary.
