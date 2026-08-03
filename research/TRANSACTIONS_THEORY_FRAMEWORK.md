# FedFalsify Transactions Theory Framework

## 1. Status and purpose

This document separates three different kinds of statements:

1. **deterministic algorithmic properties** that follow directly from the implemented acceptance rules;
2. **finite-sample statistical targets** that require explicit distributional assumptions and proofs;
3. **claims that are not currently justified** and must not appear as theorems.

The goal is to prevent empirical behavior from being mislabeled as theory. Deterministic screening properties below can be proved from the code. Statistical consistency, identifiability, and privacy are not yet proved.

## 2. Notation

Let:

- `K` be the number of clients;
- `j` index a candidate symbolic term;
- `O_j` be the set of clients on which term `j` has sufficient observed support and nonzero energy;
- `c_kj` be the residual correlation reported by observable client `k` for term `j`;
- `tau_e = max(0.05, min_repair_score / 2)` be the client-level evidence threshold;
- `S_j = {k in O_j : |c_kj| >= tau_e}` be the supporting-client set;
- `s_j = |S_j| / |O_j|` be the support fraction;
- `a_j = |weighted_mean(sign(c_kj), k in S_j)|` be weighted sign agreement;
- `q_j` be the symbolic complexity of term `j`;
- `rho_core` be the minimum core support fraction, currently `0.60`;
- `rho_exc` be the minimum exception support fraction, currently `0.80`;
- `eta` be the minimum repair score;
- `H_j` be the coefficient-heterogeneity score for an exception term;
- `h_min` be the minimum exception heterogeneity score, currently `0.20`.

For a core term, the implemented score has the form

```text
strength_j = 0.6 * median(|c_kj|) + 0.4 * weighted_mean(|c_kj|)
score_j = strength_j
          * (0.5 + 0.5 * a_j)
          * sqrt(s_j)
          * sqrt(|O_j| / K)
          / sqrt(q_j)
```

where medians and weighted means are taken over supporting clients.

Exception scores additionally depend on a coefficient-heterogeneity certificate and a priority comparison against the best core term.

## 3. Deterministic propositions supported by the implementation

### Proposition D1 — insufficient-support rejection

For a core term `j`, if

```text
s_j < rho_core,
```

then `j` cannot be selected in that discovery round.

For an exception term, if

```text
s_j < rho_exc,
```

then the exception cannot be selected.

#### Proof

The server returns a null repair decision before score construction whenever the measured support fraction is below the term-kind-specific threshold. Therefore selection is impossible in that round. This is an algorithmic screening property; it does not state that the measured support fraction is a statistically unbiased estimate of population support.

### Corollary D1.1 — rejection of a sufficiently local shortcut

A core candidate supported on fewer than 60% of its observable clients is deterministically rejected under the default configuration.

This corollary is conditional on observability and the implemented residual-correlation threshold. It does not imply rejection of every spurious term, because a spurious term can be correlated across many clients.

### Proposition D2 — sign-conflict rejection

If the weighted sign agreement of a candidate term satisfies

```text
a_j < 0.5,
```

then the term cannot be selected in that discovery round.

#### Proof

The server returns a null repair decision before final score construction when weighted sign agreement is below `0.5`.

### Proposition D3 — minimum-observability rejection for core terms

A core term observed on fewer than `min(2, K)` clients cannot be selected.

This prevents a single observable client from promoting an ordinary core term. It does not apply identically to restricted exception terms, whose interpretation is support-qualified.

### Proposition D4 — score-threshold rejection

Even when a term passes observability, support, and sign checks, it cannot be added unless

```text
score_j >= eta.
```

This provides a deterministic lower bound on accepted aggregate evidence, conditional on the implemented score definition.

### Proposition D5 — exception heterogeneity gate

With coefficient heterogeneity enabled, an exception term cannot be selected when

```text
H_j < h_min.
```

It must additionally satisfy the exception support threshold and be competitive with the best core candidate under the configured priority ratio.

### Proposition D6 — replacement non-degradation gate

A proposed structural replacement is rejected unless all of the following hold:

1. robust objective gain exceeds `min_objective_gain`;
2. the improved-client fraction exceeds its threshold;
3. the nonworsening-client fraction exceeds its threshold;
4. incoming-term support and sign agreement exceed their thresholds;
5. the incoming term passes its global coefficient z threshold.

Thus, under the default implementation, a replacement cannot be accepted solely because it improves pooled fit while materially worsening too many clients.

This is a deterministic property of reported client losses. It is not a population generalization theorem.

### Proposition D7 — bounded symbolic growth

The discovery loop cannot add terms after reaching

```text
max_terms + search_slack_terms.
```

The final candidate is then coefficient-pruned. Therefore the active support is deterministically bounded by the configured search complexity.

## 4. Communication-complexity accounting target

Let:

- `R` be the number of discovery rounds;
- `m_r` be the active-term count in round `r`;
- `M` be the number of catalog candidates scored in a certificate;
- `P` be the number of replacement proposals evaluated;
- `m_p` be the active-term count for proposal `p`.

A fit summary contains a Gram matrix and target vector, requiring on the order of

```text
O(m_r^2 + m_r)
```

numeric values per client per fit. A falsification certificate contains loss summaries and evidence across catalog terms, requiring approximately

```text
O(M)
```

values per client, subject to the concrete serialized schema.

A first-order communication bound is therefore

```text
O(
  K * sum_r [m_r^2 + M]
  + K * sum_p [m_p^2 + M]
).
```

With bounded active size `m` this becomes

```text
O(K * (R + P) * (m^2 + M)).
```

The paper must report both this symbolic bound and measured serialized bytes. The bound does not include transport framing, cryptographic overhead, retries, or secure aggregation.

## 5. Finite-sample theorem targets requiring new proofs

The statements in this section are research targets, not completed theorems.

### Target T1 — true invariant-term retention

Under assumptions such as:

- independent client samples conditional on client domain;
- sub-Gaussian residual noise;
- a lower bound on residualized term variance;
- a nonzero minimum partial effect for the true term;
- bounded within-client design condition number;
- sufficient observable clients;

derive a bound of the form

```text
P(true invariant term passes support and sign certificates)
>= 1 - delta(K, n_min, effect, noise, threshold).
```

A union bound may combine client-level concentration events, but dependence induced by fitting the current candidate must be handled explicitly, preferably through sample splitting or conditional analysis.

### Target T2 — spurious-term rejection probability

For a term whose client-specific partial effects are zero on most clients or have conflicting signs, derive an upper bound on the probability that it simultaneously passes:

- the client evidence threshold;
- the minimum support fraction;
- the sign-agreement threshold;
- the aggregate repair-score threshold.

The theorem must distinguish:

1. a purely local artifact;
2. a globally correlated but noncausal proxy;
3. an observationally equivalent surrogate.

Only the first class is directly controlled by support sparsity. The second and third require stronger assumptions or additional interventions/domains.

### Target T3 — restricted-exception identifiability

Assume clients differ in gate support and that the source-term coefficient shift exceeds a minimum contrast. Derive sufficient conditions for the gated exception to pass the heterogeneity certificate while the ungated core substitute does not dominate it.

Required quantities include:

- number of gate-observing clients;
- gate-support sample size;
- coefficient contrast;
- local standard errors;
- heterogeneity threshold;
- exception priority ratio.

### Target T4 — replacement safety beyond observed clients

The current non-degradation rule concerns observed client losses. A population result would require uniform or client-wise generalization bounds linking reported empirical MSE changes to expected client risk changes.

## 6. Identifiability boundary

No method using only observational finite-domain data can generally distinguish expressions that are functionally equivalent on all observed supports. The Phase 1 `poly3` failures illustrate this boundary: trigonometric surrogates can approximate polynomial terms within the training domain and diverge under extrapolation.

A valid theory section must state at least the following impossibility boundary:

> Without domain coverage that separates candidate functions, or prior restrictions that remove equivalent surrogates, structural identification is not guaranteed even when prediction error is small.

This is why the Transactions evaluation includes interpolation and extrapolation domains and why adaptive-domain acquisition is a candidate future extension.

## 7. Privacy boundary

The algorithm transmits aggregate fit summaries and falsification certificates rather than raw rows. This does not prove differential privacy, secure aggregation, resistance to reconstruction, or membership-inference protection.

No privacy theorem may be stated unless all communicated quantities are covered by a formal mechanism with neighboring-dataset definitions, clipping, sensitivity, composition, and reported `(epsilon, delta)` values.

## 8. Required proof-validation simulations

Every completed probabilistic theorem must be accompanied by simulations that vary the theorem's controlling quantities:

- client count;
- minimum samples per observable client;
- effect size;
- noise;
- support fraction;
- sign conflict;
- design collinearity;
- gate prevalence;
- coefficient contrast.

The empirical transition should be compared with the theoretical sufficient condition. A theorem should not be presented only as an isolated algebraic result.

## 9. Current theory decision

Completed and defensible now:

- deterministic support, sign, observability, score, exception, replacement, and complexity gates;
- a first-order communication-complexity bound;
- an explicit observational-identifiability limitation.

Not completed:

- finite-sample true-term retention probability;
- finite-sample false-selection control;
- exception-identifiability probability;
- population replacement safety;
- formal privacy.

The manuscript remains `NO-GO` until at least one substantial finite-sample theorem and supporting propositions are completed, or until the target venue is changed to one where a predominantly empirical contribution is appropriate.
