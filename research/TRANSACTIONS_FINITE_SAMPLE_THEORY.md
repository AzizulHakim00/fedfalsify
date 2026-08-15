# Finite-Sample Certificate Theory for FedFalsify

## 1. Scope

This note gives finite-sample probability bounds for a statistically calibrated,
sample-split version of the FedFalsify client certificate. The results are not
claimed for arbitrary adaptive reuse of the same observations. They apply under
explicit fixed-design Gaussian assumptions and motivate a v0.7 certificate
whose discovery and validation samples are separated.

The deterministic screening propositions in
`TRANSACTIONS_THEORY_FRAMEWORK.md` remain valid for the implemented v0.5/v0.6
rules. The theorems below add a probabilistic layer for a calibrated validation
certificate.

## 2. Client-level model

Consider a candidate term after residualizing it against the currently accepted
terms on an independent validation split. For observable client `k`, let

```text
r_k = beta_k z_k + epsilon_k,
```

where:

- `z_k in R^(n_k)` is the fixed residualized candidate column;
- `S_k = ||z_k||_2^2 > 0`;
- `epsilon_k ~ N(0, sigma_k^2 I)`;
- validation noises are independent across clients;
- `sigma_k` is known or replaced by an independently justified upper bound.

Define the standardized local statistic

```text
T_k = (z_k^T r_k) / (sigma_k sqrt(S_k)).
```

Then

```text
T_k ~ N(mu_k, 1),
mu_k = beta_k sqrt(S_k) / sigma_k.
```

For a two-sided evidence threshold `a > 0`, client `k` supports the candidate
when

```text
|T_k| >= a.
```

A positive-sign invariant candidate additionally requires `T_k >= a` on enough
clients. Let `m` be the number of observable clients and let `rho in (0,1)` be
the required support fraction.

## 3. True invariant-term retention

### Theorem 1 — finite-sample retention of a same-sign invariant term

Assume an invariant term has positive standardized effect

```text
mu_k >= mu_min > 0
```

on every one of the `m` observable clients. Define

```text
p_plus  = Phi(mu_min - a),
p_minus = Phi(-a - mu_min),
```

where `Phi` is the standard-normal cumulative distribution function. If

```text
p_plus > rho,
```

then the probability that at least a `rho` fraction of clients provide
positive support and that no client provides wrong-sign support is at least

```text
1
- exp[-2 m (p_plus - rho)^2]
- m p_minus.
```

Consequently, a certificate that accepts when at least `rho m` clients satisfy
`T_k >= a` and rejects any candidate with observed wrong-sign support retains
the true invariant term with at least this probability.

#### Proof

Let

```text
X_k = 1{T_k >= a}.
```

Because `T_k ~ N(mu_k,1)` and `mu_k >= mu_min`,

```text
P(X_k = 1)
= P[T_k >= a]
= Phi(mu_k - a)
>= Phi(mu_min - a)
= p_plus.
```

The `X_k` are independent across clients. A Hoeffding lower-tail bound for
independent Bernoulli variables with mean at least `p_plus` gives

```text
P[(1/m) sum_k X_k < rho]
<= exp[-2 m (p_plus - rho)^2].
```

A wrong-sign support occurs when `T_k <= -a`. For every client,

```text
P[T_k <= -a]
= Phi(-a - mu_k)
<= Phi(-a - mu_min)
= p_minus.
```

By the union bound, the probability of at least one wrong-sign support is at
most `m p_minus`. Applying another union bound to the two failure events proves
the result. `square`

### Corollary 1 — design and sample-size requirement

Suppose

```text
|beta_k| >= beta_min,
S_k >= n_min v_min,
sigma_k <= sigma_max.
```

Then

```text
mu_min >= beta_min sqrt(n_min v_min) / sigma_max.
```

Substituting this lower bound into Theorem 1 produces an explicit sufficient
condition in client sample size, residualized term energy, effect size, noise,
number of observable clients, and support threshold.

### Interpretation

The theorem shows why increasing client count cannot rescue a term whose
per-client standardized effect is below the evidence threshold: `p_plus` must
first exceed `rho`. Once that separation exists, the support-fraction error
probability decays exponentially in the number of observable clients.

## 4. Rejection of a client-local shortcut

### Theorem 2 — finite-sample rejection of a partially local term

Suppose a candidate may have arbitrary effects on at most a fraction `q` of the
`m` observable clients, while

```text
beta_k = 0
```

on the remaining fraction `1-q`. Let

```text
p0 = 2[1 - Phi(a)]
```

be the two-sided null support probability. Define

```text
p_short = q + (1-q) p0.
```

If

```text
p_short < rho,
```

then the probability that the candidate reaches the required support fraction
is at most

```text
exp[-2 m (rho - p_short)^2].
```

Any additional sign-agreement requirement can only decrease the acceptance
probability.

#### Proof

Treat every client in the arbitrary-effect subset conservatively as supporting
the candidate with probability one. On each null client,

```text
P[|T_k| >= a] = 2[1-Phi(a)] = p0.
```

Therefore the mean support probability over all observable clients is at most

```text
q * 1 + (1-q) p0 = p_short.
```

Let `Y_k` indicate two-sided support. The `Y_k` are independent Bernoulli
variables with average mean at most `p_short`. Hoeffding's upper-tail inequality
gives

```text
P[(1/m) sum_k Y_k >= rho]
<= exp[-2m(rho-p_short)^2].
```

The sign-agreement gate is another necessary condition for acceptance, so
ignoring it gives a conservative upper bound. `square`

### Corollary 2 — deterministic locality boundary

As the evidence threshold grows, `p0` decreases. In the idealized limit
`p0 -> 0`, a term active on fraction `q` cannot pass a support threshold
`rho > q` except with exponentially small finite-sample probability.

For the default core support threshold `rho = 0.60`, a term restricted to fewer
than 60% of observable clients is therefore rejectable under adequate local
calibration. This does not address a proxy that is correlated across most
clients.

## 5. Null global false-selection control

### Corollary 3 — globally null candidate

For `q=0`, Theorem 2 gives

```text
P[global null candidate passes support]
<= exp{-2m[rho - 2(1-Phi(a))]^2},
```

provided `2(1-Phi(a)) < rho`.

For a fixed library of `M` globally null candidate terms, a union bound gives

```text
P[at least one null term passes]
<= M exp{-2m[rho - 2(1-Phi(a))]^2}.
```

This is a screening bound, not full model-selection consistency. Candidate
statistics may become dependent under adaptive search, and a sequential or
sample-splitting correction is required when repeatedly testing generated
expressions.

## 6. Exception term and single-client limitation

Let an exception term be observable only on `m_e` clients. Applying Theorem 1
with `m=m_e` gives its retention bound among observable clients. If `m_e=1`,
the bound reduces essentially to the local positive-support probability.

### Proposition 3 — single-observable-client identifiability boundary

When a gated exception is observable on exactly one client, cross-client
support evidence alone cannot distinguish a genuine restricted mechanism from
a client-specific artifact with the same conditional distribution on that
client.

#### Justification

Construct two data-generating processes that are identical on every observed
client: one labels the gated effect as a genuine mechanism, and the other labels
it as an artifact. Because the joint distribution of all observations is the
same, no statistical procedure can distinguish the labels with probability
better than chance without additional assumptions or data.

Therefore a one-client exception requires at least one of:

- a predeclared gate with scientific meaning;
- repeated environments within that client;
- temporal or experimental replication;
- an independent validation cohort;
- a prior restriction on admissible artifacts.

The adaptive implementation permits a one-observable-client exception because
the synthetic benchmark intentionally declares the gate. The manuscript must
state this assumption.

## 7. Why sample splitting is required

The Gaussian distributions above are conditional on the residualized design
being fixed independently of the validation noise. If the same observations
are used to:

1. generate candidate expressions;
2. select the current model;
3. compute validation z statistics;

then the nominal normal tail probabilities need not hold because of adaptive
selection.

A theory-aligned Transactions implementation should use one of:

- discovery/validation sample splitting within each client;
- cross-fitting;
- reusable holdout methods;
- sequential alpha spending;
- selective-inference corrections.

The simplest initial implementation is deterministic chronological or random
sample splitting fixed before search, with certificates computed only on the
validation partition.

## 8. Threshold design

The theory exposes an explicit trade-off:

- increasing `a` reduces null support `p0` and improves shortcut rejection;
- increasing `a` also lowers `p_plus` and can reduce true-term retention;
- increasing `rho` rejects more local terms but requires wider cross-client
  support;
- increasing `m` sharpens both retention and rejection once their expected
  support probabilities lie on the correct side of `rho`.

Thresholds must therefore be fixed from development data or theoretical design
before final confirmation. They must not be tuned on seeds `9001--9020` or on
the final `11001+` confirmation block.

## 9. Required theorem-validation simulation

A simulation must vary:

- `m in {3,4,8,16,32}` observable clients;
- standardized effect `mu_min` across and around threshold `a`;
- local shortcut fraction `q` across and around support threshold `rho`;
- evidence threshold `a`;
- support threshold `rho`;
- residualized energy through sample size and feature collinearity.

For each cell, estimate:

- invariant retention probability;
- wrong-sign probability;
- shortcut acceptance probability;
- globally null family-wise acceptance over `M` terms.

Overlay empirical probabilities with Theorem 1 and Theorem 2 bounds. The bounds
are sufficient and may be conservative; systematic violations indicate an
implementation or assumption mismatch.

## 10. Manuscript claim boundary

Permitted after implementation and validation:

> Under fixed-design Gaussian validation splits and minimum standardized-effect
> assumptions, the probability of retaining a same-sign invariant term and the
> probability of accepting a client-local shortcut admit explicit finite-sample
> bounds in client count, support fraction, and evidence threshold.

Not permitted:

- unrestricted consistency under adaptive reuse of the same data;
- causal identification;
- rejection of globally shared proxies;
- identification of a one-client exception without additional assumptions;
- differential privacy.
