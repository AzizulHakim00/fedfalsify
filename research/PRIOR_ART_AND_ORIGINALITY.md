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
use violated mathematical truths to generate corrective examples. Therefore,
FedFalsify must not claim that using counterexamples to improve symbolic
regression is new.

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

## Narrow candidate contribution

The repository currently tests the following combination:

1. clients send structured **aggregate term certificates**, not raw rows;
2. ordinary terms require support across clients that can observe them;
3. a term observable everywhere but supported at one client is treated as a
   shortcut and rejected;
4. a gated term observable in only a restricted domain can be reported as a
   provisional exception rather than forced into the invariant core; and
5. the output explicitly separates the invariant symbolic core from
   domain-restricted exceptions.

This combination is a **novelty hypothesis**. It becomes a defensible research
contribution only after systematic search and direct experiments against the
closest methods.

## Independent implementation record

The repository implementation is written specifically for this project using
NumPy and Python standard-library components. No external SR source code has
been copied into the repository. General ideas such as least-squares normal
equations, residual correlations, CEGIS-style iteration, and symbolic basis
functions are established techniques and are cited as background rather than
claimed as inventions.

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

## Pre-submission audit

Before submission:

1. update the literature search through the submission date;
2. compare the proposed algorithm line by line with the closest five methods;
3. run iThenticate or the publisher-approved similarity system on the manuscript;
4. manually inspect every highlighted phrase rather than optimizing only for a
   similarity percentage;
5. confirm that all borrowed datasets, code, equations, and definitions satisfy
   their licenses and citation requirements;
6. archive code, seeds, configurations, and a claim-to-evidence table;
7. remove "first", "novel", and "discovery" claims that are not directly
   supported by the completed comparison.

## Claim language

Safe before full comparison:

> We investigate a federated certificate protocol for separating invariant
> symbolic terms, local shortcuts, and restricted-domain exceptions.

Unsafe at the current stage:

> We present the first federated falsification algorithm and discover a new
> scientific law.

See `REFERENCES.bib` for the sources defining this research boundary.
