# SCSV-RCD v7 close-prior-art novelty audit

Status: **claim-governance record; does not modify the frozen v7 scientific protocol or A--R gates**.

This audit was performed before any v7 scientific seed (`24101--24105`) was released.

## 1. Claims that are NOT safe

The final paper must not claim any of the following as inventions of FedFalsify v7:

- federated learning itself;
- personalized federated learning;
- splitting model parameters into global/shared and local/personalized components;
- hierarchical Bayesian/global-local personalization;
- mixed-effects or client-specific coefficient deviations;
- symbolic regression with a shared function structure and group-specific coefficients;
- privacy-preserving symbolic regression in general;
- using summary statistics for federated regression in general.

## 2. Closest prior art found

### Multi-Level Symbolic Regression (MSR)

Kei Sen Fong and Mehul Motani, AISTATS 2024, PMLR 238.

Primary source:
https://proceedings.mlr.press/v238/sen-fong24a.html

MSR is particularly close conceptually because it learns a shared symbolic function structure across groups while allowing parameter values to capture group-specific relationships. Therefore FedFalsify must not claim that shared symbolic structure plus group-specific coefficients is new.

### Partially Personalized Federated Learning

Konstantin Mishchenko, Rustem Islamov, Eduard Gorbunov, Samuel Horvath, 2023.

Primary source:
https://arxiv.org/abs/2305.18285

This work explicitly separates global shared parameters and individual local parameters. Therefore global/local decomposition is established prior art.

### Hierarchical Bayesian personalized federated learning

Mahendra Singh Thapa and Rui Li, ICML 2025, PMLR 267.

Primary source:
https://proceedings.mlr.press/v267/thapa25a.html

This establishes modern hierarchical global/personalized parameter modeling in federated learning.

### Federated mixed-effects regression from shared summaries

Marie Analiz April Limpoco, Christel Faes, Niel Hens, 2024.

Primary source:
https://arxiv.org/abs/2411.04002

This is relevant because it performs federated mixed-effects estimation using one-time shared summary information. FedFalsify therefore must not frame summary-statistic estimation of local deviations as generically novel.

### Vertical privacy-preserving symbolic regression

Du Nguyen Duy, Michael Affenzeller, Ramin Nikzad-Langerodi, 2023.

Primary source:
https://arxiv.org/abs/2307.11756

This establishes privacy-preserving symbolic regression using secure multiparty computation in a vertical setting.

### Domain-aware privacy-preserving symbolic regression

Kei Sen Fong and Mehul Motani, CHIL 2024, PMLR 248.

Primary source:
https://proceedings.mlr.press/v248/fong24a.html

This further shows that privacy-preserving and domain-aware symbolic regression is an active established direction.

## 3. Defensible v7 novelty hypothesis

The current defensible hypothesis is narrower:

> In horizontally federated symbolic mechanism recovery, a role-restricted symbolic term can be locally non-identifiable when it is collinear with an already shared source term inside eligible clients. SCSV-RCD treats such a term as a source-linked structural deviation, identifies the shared source and deviation jointly from cross-role discovery sufficient statistics, and accepts the deviation only after fixed-reduced one-parameter evidence is reproduced on disjoint selector and probe packets while preserving the frozen shared structure and outside-role safety.

The novelty is therefore **not** personalization or group-specific coefficients by themselves. It is the combination of:

1. high-recall federated symbolic candidate discovery;
2. set-conditional shared-structure selection;
3. explicit source-term metadata linking a restricted symbolic mechanism to a shared structural parent;
4. cross-role identification designed for the local collinearity/identifiability failure mode;
5. fixed-reduced coefficient-specific certification rather than refitting a reduced model that can re-absorb the deviation;
6. disjoint selector and independent probe certification;
7. non-destructive shared-anchor preservation and outside-role safety;
8. auditable sufficient-statistic communication rather than raw-data pooling.

## 4. Reviewer-risk statement

Even this narrower claim must remain provisional until the fresh v7 development and independent stages succeed. If fresh evidence fails, the mechanism must not be promoted as a validated algorithmic contribution.

A reviewer could still argue that SCSV-RCD is a specialized symbolic/mixed-effects construction. The paper must therefore empirically and mathematically demonstrate why ordinary pooled fitting, frozen-core residual fitting, and generic shared/local parameterization do not solve the same structural-identifiability problem. The preserved RCSA and FCRRA NO-GO diagnostics are useful negative controls for that argument.

## 5. Required paper comparisons if v7 survives fresh validation

A final literature/experimental section should explicitly compare or discuss:

- Multi-Level Symbolic Regression (shared structure/group parameters);
- centralized symbolic regression / PySR-style search;
- privacy-preserving symbolic regression methods;
- personalized/global-local federated learning;
- federated mixed-effects approaches;
- FedFalsify historical ablations: v5, v6, RCSA, FCRRA, RCCD diagnostic, and v7.

The paper should state exactly which comparators are executable under the horizontal federated finite-grammar benchmark and which are conceptual prior art only.
