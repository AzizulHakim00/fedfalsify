# FedFalsify v0.6 Claim-to-Evidence Map

## Purpose

This table prevents a manuscript claim from becoming broader than the code and
experiments that support it.

| Candidate statement | Required evidence | Current status |
|---|---|---|
| The repository supports expression-tree comparisons. | `expression_tree.py`, `expression_baselines.py`, tests, CI smoke. | Implemented and smoke-tested. |
| The controlled federated baseline uses aggregate client statistics. | Aggregate Gram/target fitting and serialized communication ledger. | Implemented; not an author reproduction. |
| The controlled counterexample baseline focuses search on high-error observations. | Residual reweighting between generations. | Implemented; not formal-verification CDSR. |
| Exact-recovery comparisons are paired. | Common condition-seed key and exact McNemar test. | Implemented. |
| Multiple primary comparisons are corrected. | Holm-adjusted report generated from raw summary. | Implemented; must be used for the primary run. |
| NMSE/runtime differences have uncertainty intervals. | Paired percentile-bootstrap intervals. | Implemented. |
| Communication is compared. | Serialized byte estimates for aggregate methods. | Implemented estimates; network overhead not measured. |
| Certificate releases can change when one record changes. | Leave-one-out sensitivity probe. | Implemented as a leakage proxy. |
| The algorithm tolerates controlled certificate perturbation. | Multi-seed certificate-noise utility matrix. | Runner implemented; full matrix not yet executed. |
| FedFalsify outperforms controlled tree baselines. | Frozen 2,400-run primary matrix, corrected paired tests, effect sizes. | Not established. Smoke output is insufficient. |
| FedFalsify outperforms official PySR. | Official PySR 1.5.x runs under archived configurations. | Adapter implemented; official runs not yet executed. |
| FedFalsify outperforms published federated GP or BFSR. | Faithful author implementation or audited reproduction with comparable budget. | Not established. |
| FedFalsify is differentially private. | Full clipping, sensitivity, accountant, epsilon/delta and composition. | Not implemented and must not be claimed. |
| FedFalsify discovers causal/scientific laws. | Identification assumptions, interventions or prospective validation. | Not established. |

## Permitted software statement

> Version 0.6 provides an auditable matched-comparison framework with controlled
> expression-tree baselines, paired statistical analysis, communication
> estimates, certificate sensitivity probes, and certificate-noise utility
> ablations.

## Permitted smoke statement

> The complete v0.6 software pipeline passed continuous integration on a small
> diagnostic matrix.

## Statements requiring the frozen primary study

The following cannot appear before executing and archiving the registered
primary matrix:

- “FedFalsify significantly improves exact recovery.”
- “FedFalsify is more robust to noise.”
- “FedFalsify is communication efficient.”
- “FedFalsify outperforms genetic programming.”

## Statements not supported by v0.6

- “FedFalsify is privacy preserving.”
- “The noise multiplier is a DP budget.”
- “The controlled federated tree-GP-style baseline reproduces Dong et al.”
- “The residual-counterexample baseline reproduces formal counterexample GP.”
- “The method is state of the art.”
- “The method discovers new scientific laws.”
