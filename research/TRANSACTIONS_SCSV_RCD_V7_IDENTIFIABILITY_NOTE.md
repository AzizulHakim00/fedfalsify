# SCSV-RCD v7 identifiability note

Status: **pre-evidence theoretical record**. Written before release of v7 scientific seeds `24101--24105`. This note does not change the frozen algorithm, benchmark matrix, or A--R gates.

## 1. Problem

Let `phi(x)` denote a shared symbolic source term and let `g_r(x)` be a role gate. Consider

`y = f_0(x) + beta * phi(x) + delta * g_r(x) * phi(x) + epsilon`,

where `f_0` collects the remaining shared structure, `beta` is the shared source coefficient, and `delta` is a role-specific deviation.

For a role-eligible client whose observed domain satisfies `g_r(x)=1` on every locally observed row,

`y = f_0(x) + (beta + delta) * phi(x) + epsilon`.

The local design columns for `phi(x)` and `g_r(x)phi(x)` are therefore identical.

## 2. Local non-identifiability

After conditioning on `f_0`, the eligible-client design matrix for `(beta, delta)` is

`X_E = [phi_E, phi_E]`.

Its two columns are identical, so

`rank(X_E) = 1 < 2`.

Hence `beta` and `delta` are not separately identifiable from that eligible client. For any scalar `c`, the pairs

`(beta, delta)` and `(beta+c, delta-c)`

produce the same eligible-client fitted values because their sum is unchanged.

This is a structural identifiability problem, not a threshold-selection problem.

## 3. Cross-role identification

Now include at least one noneligible role for which `g_r(x)=0` while `phi(x)` is observed with nonzero variation. The stacked source/deviation design is

`X = [[phi_N, 0], [phi_E, phi_E]]`,

where `N` denotes noneligible observations and `E` eligible observations.

The two columns are no longer globally identical. If

- `phi_N` has nonzero energy;
- `phi_E` has nonzero energy;
- both role subsets have positive support;

then the stacked two-column design has rank two and `(beta, delta)` is identifiable in the ordinary linear-algebraic sense, conditional on the remaining shared structure.

This is the core reason SCSV-RCD performs joint discovery identification across roles rather than estimating the deviation coefficient from eligible-client residuals alone.

## 4. Fixed-reduced contrast

Let the discovery-only joint fit estimate coefficients `theta_hat` for the shared anchor and all source-linked deviation candidates. For a candidate deviation `e`, SCSV-RCD forms a reduced predictor by setting only `theta_hat_e` to zero and leaving every other discovery coefficient fixed.

This differs from refitting a reduced model. A refitted reduced model can move the shared source coefficient toward `beta+delta` and re-absorb the role deviation, recreating the same confounding that motivated the method.

The fixed-reduced contrast instead asks a coefficient-specific held-out question:

> Given the same jointly identified shared coefficients, does the independently fitted deviation coefficient contribute reproducible predictive evidence in its eligible role?

Selector and probe answer that question on disjoint held-out packets.

## 5. Sufficient-statistic form

For a selected term vector `z`, client `k` need only expose the aggregate statistics

- `G_k = Z_k^T Z_k`,
- `c_k = Z_k^T y_k`,
- `q_k = y_k^T y_k`,
- support counts and observed-support counts.

The pooled discovery normal equations use

`G = sum_k G_k`,

`c = sum_k c_k`.

For any frozen coefficient vector `b`, held-out SSE is recoverable from

`SSE_k(b) = q_k - 2 b^T c_k + b^T G_k b`.

Thus the structural contrast does not require centralizing row-level client observations in the study's federated abstraction.

This note does not claim that sufficient-statistic regression, mixed-effects parameterization, or global/local models are themselves novel.

## 6. Necessary limitations

The argument does not guarantee recoverability in every setting. Identifiability can still fail or become numerically weak if:

1. the source term itself is absent or nearly constant outside the eligible role;
2. the source term is not recovered into the shared anchor;
3. the deviation is not recovered into the high-recall candidate bank;
4. multiple candidate deviations remain linearly dependent after cross-role stacking;
5. role support is too small for selector/probe certification;
6. noise overwhelms the conditional deviation signal;
7. an omitted shared mechanism aliases with the candidate deviation.

These are empirical failure modes that the fresh v7 family, client-count, imbalance, high-noise, null-control, and dual-deviation gates are intended to expose.

## 7. Claim discipline

If fresh v7 development and later independent validation succeed, the theoretical claim should be framed as an identifiability rationale for the source-linked role-contrast construction, not as a universal identifiability theorem for arbitrary nonlinear symbolic regression.

A rigorous final paper can state a conditional proposition for the linear-in-parameters finite symbolic basis used by FedFalsify and separately discuss extension limits for general symbolic programs.