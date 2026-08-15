# FedFalsify v9 / SCSV-RCEF novelty audit

## Purpose

This is a pre-evidence novelty boundary for the proposed FedFalsify v9 successor. It prevents broad claims that are already covered by prior work and does not constitute a scientific result.

## Prior art that must NOT be claimed as v9 novelty

### Multi-level symbolic regression

Fong and Motani, *Multi-Level Symbolic Regression: Function Structure Learning for Multi-Level Data*, AISTATS 2024, learns a shared symbolic function structure while allowing group-specific parameter values. Therefore v9 must not claim that shared symbolic structure plus group-specific coefficients is itself new.

Primary source: https://proceedings.mlr.press/v238/sen-fong24a.html

### Privacy-preserving symbolic regression

Fong and Motani, *Explainable and Privacy-Preserving Machine Learning via Domain-Aware Symbolic Regression*, CHIL 2024, combines symbolic regression with homomorphic encryption. Therefore privacy-preserving SR, encrypted SR, or privacy alone cannot be claimed as the novelty.

Primary source: https://proceedings.mlr.press/v248/fong24a.html

### Multiple-split / aggregated statistical evidence

Repeated sample splitting and aggregation are established statistical ideas. Guo and Shah, *Rank-transformed subsampling: inference for multiple data splitting and exchangeable p-values*, JRSS-B 2025, explicitly studies aggregation across randomized data splits and shows why aggregation can improve power and stability while requiring careful calibration.

Primary source: https://doi.org/10.1093/jrsssb/qkae091

E-value/p-value merging is also established. Generic evidence averaging, p-value merging, or 'multi-split aggregation' cannot be claimed as v9 novelty.

### Symbolic-regression benchmarking and complexity trade-offs

Modern SR literature already studies explicit prediction/complexity trade-offs and attainable Pareto fronts. V9 cannot claim generic complexity-aware SR selection as novel.

Primary source: https://proceedings.mlr.press/v267/fong25b.html

## Narrow claim boundary permitted for v9

If future fresh and independent evidence supports the method, the potentially defensible contribution is the **specific composition** of the following mechanisms for federated symbolic structural recovery:

1. a response-free, client-level role-contrast proposal channel over a frozen finite symbolic grammar;
2. source-linked qualification that can recover a gated deviation even when the deviation is absent from the response-driven bank, while requiring the source to be present in the bank;
3. a fixed source/deviation pair whose unrelated shared coefficients cannot move during certification;
4. disjoint held-out selector/probe views combined by a preregistered pooled structural evidence score, while explicit directional contradiction in either view vetoes acceptance;
5. an optional source-necessity certificate, evaluated only on outside-role clients, before operationally adding a source term that was banked but absent from the frozen anchor;
6. all of the above implemented from federated sufficient statistics with explicit null-role, diffuse-null, weak-source, and dual-deviation falsification panels.

The claim must be phrased as a narrowly defined *federated symbolic role-deviation certification mechanism*. It must not be generalized to 'first personalized symbolic regression', 'first multi-level symbolic regression', 'first privacy-preserving symbolic regression', or 'first evidence aggregation method'.

## Evidence boundary

The sealed v8 fresh development result remains `DEVELOPMENT-NO-GO`. Seeds `25101--25105` are permanently spent.

The v9 engineering seed namespace `26001` and prospective fresh-development namespace `26101--26105` were searched in the repository before this file was created and showed no pre-existing collision. They remain unused at this point.

No novelty claim is promoted by this audit. Publication language remains conditional on fresh development, independent validation, and external benchmarking.