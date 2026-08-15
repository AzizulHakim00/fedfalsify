# RC-DES v4 implementation clarification

Status: **FROZEN BEFORE ENGINEERING SMOKE AND BEFORE ANY V4 EVIDENCE SEED**

This document resolves implementation details of `TRANSACTIONS_ROLE_CONDITIONAL_V4_PROTOCOL.md`. It changes no numeric gate, benchmark, endpoint, seed, or selector/probe threshold.

## 1. Restricted-exception fold validity

For each discovery direction and each declared exception term, the implementation replays the already-generated candidate history and computes the existing legacy/v2 `_exception_heterogeneity` score. A fold counts as exception-valid when the maximum score observed in that direction is at least the unchanged `0.20` threshold.

The existing heterogeneity calculation itself returns zero unless it has at least one gated client and at least one outside client with an estimable source coefficient. Thus `exception_valid_fold_count >= 3` means at least three discovery directions contained valid gate-vs-outside evidence under the existing certificate logic.

No selector, structural-probe, exact-recovery, or global-test outcome enters this count.

## 2. Exception structural-probe denominator

The structural-probe thresholds remain unchanged:

- positive aggregate probe improvement;
- rival advantage at least `0.01`;
- client-win fraction at least `0.60`;
- selector coefficient-sign agreement at least `0.60`.

For a **core** term, these quantities use the existing all-observable-client implementation.

For a declared **exception** term, the denominator for client-win and sign agreement is the set of eligible gated clients, not every federated client. A selector/probe client pair is eligible only when the exception basis has at least

`max(3, ceil(0.10 * local held-out rows))`

non-zero-support observations in both its selector half and probe half.

Clients outside the declared exception domain remain relevant to the independent coefficient-heterogeneity certificate and selector non-degradation safeguards, but they are not counted as failed structural-probe wins merely because the gated basis is identically zero there.

This is a role-conditioned observability denominator, not a reduction of the `0.60` threshold.

## 3. Core path-persistence implementation

The path-persistence channel is a separate admission channel from residual-rank stability. A core term may pass path persistence only when:

- it occurs in at least `3/5` final fold-direction structures;
- coefficient-sign stability is at least `0.60`;
- residual-sign agreement is at least `0.60`;
- client coverage is at least `0.50`.

A term does not need to be top-three in the residual-rank channel to pass path persistence. This distinction is intentional and directly tests the v3 forensic observation that true terms can recur structurally while being suppressed by the inactive residual-rank statistic.

## 4. Backward order

The backward necessity audit executes exactly once.

Terms accepted during forward continuation are tested first in reverse forward-admission order. Any remaining anchor terms are then tested in reverse deterministic catalog order. Each step considers a single deletion. A deletion accepted at one step becomes the current model for the next step; removed terms are not reintroduced by the backward stage.

## 5. Paired diagnostics and ablations

`role-v4-anchor` and `role-v4-no-backward` are paired diagnostic outputs produced from the same full RC-DES run up to the relevant stage. They are not separately optimized searches.

The `no-role-conditioning` and `no-path-persistence` ablations run the same implementation with exactly one mechanism disabled. All selector/probe numeric thresholds and data partitions remain identical.

## 6. Evidence prohibition until verification

Only unit fixtures and engineering smoke seed `16001` may be used before the implementation checks pass. Seeds `16101--16105` must not be executed through the full study path until CI verifies the frozen invariants.
