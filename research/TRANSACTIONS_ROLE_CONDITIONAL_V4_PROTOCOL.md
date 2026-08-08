# Transactions role-conditioned dual-evidence v4 protocol

Status: **FROZEN BEFORE V4 EVIDENCE EXECUTION**

Working method label: **FedFalsify v4 — Role-Conditioned Dual-Evidence Search (RC-DES)**

Originality status: **contribution hypothesis only; no novelty claim until dedicated prior-art comparison is updated**

Engineering smoke seed: `16001` only

Untouched v4 development seeds: `16101--16105`

Final-confirmation seeds `11001+` remain untouched.

## 1. Why v4 exists

V3 is a frozen NO-GO. The post-hoc forensic analysis identified four mechanistic failures that cannot be repaired by changing v3 thresholds after inspection:

1. complete-mechanism candidate coverage was only `204/450 = 0.4533` even though high-noise `poly3` critical `x1^3` recall was `1.0`;
2. the true `x1^2` term was selected in fold-level discovery paths but entered the stable superset in `0/90` target conditions, showing a mismatch between path persistence and residual-rank admission;
3. the restricted exception is scientifically observable on only one of four clients, while v3's core-like global coverage condition uses all clients as the denominator;
4. 22 v3 failures contained every true term but retained nuisance terms, motivating a conservative backward necessity audit.

V4 therefore changes the **evidence architecture**. It does not lower a v3 threshold and does not rerun v3 as if fresh.

## 2. Prior-art and claim boundary

The repository already records that stability selection, forward/backward feature selection, floating search, coefficient heterogeneity, federated symbolic regression, residual feedback, and term-level search are established research families. V4 must not claim invention of those components.

The narrow contribution hypothesis to be tested is the following combination:

> Can a federated symbolic falsification system fuse two independent fold-level evidence channels—residual-rank stability and discovery-path persistence—while using role-conditioned observability for invariant versus restricted terms, then apply independent termwise forward and backward structural probes to recover complete mechanisms without admitting local shortcuts?

This is a hypothesis, not a novelty statement.

## 3. Immutable components inherited from v2/v3

The following remain unchanged unless explicitly stated below:

- raw observation rows never leave a client;
- deterministic local sample separation;
- disjoint discovery, selector, and structural-probe roles;
- aggregate normal-equation coefficient fitting;
- existing residual and coefficient certificates;
- existing exception coefficient-heterogeneity mechanism and minimum heterogeneity score `0.20`;
- selector minimum relative MSE gain `0.01`;
- selector worst-client tolerance `0.05`;
- selector client non-degradation tolerance `0.02` on at least `0.60` of clients;
- structural-probe rival advantage margin `0.01`;
- structural-probe client win fraction `0.60`;
- structural-probe sign agreement `0.60`;
- maximum final symbolic structure of six non-negligible terms including the intercept convention used by the existing implementation;
- score-only search remains a predictive comparator and may not directly determine the structural output.

No v1, v2, or v3 result file is modified.

## 4. Local data roles

V4 keeps the v3 `validation_fraction = 0.30` partition.

For each client:

1. 70% of rows form the discovery pool;
2. the discovery pool is divided into five deterministic, disjoint, exhaustive folds;
3. the held-out 30% validation pool is deterministically split into disjoint selector and structural-probe halves.

For each of five discovery directions, four discovery folds are used for aggregate fitting and one discovery fold is used for the falsification certificate. The fold-local observability floor remains:

`max(3, ceil(0.10 * held-out-fold rows))`.

No selector or structural-probe outcome is allowed to change the discovery-fold evidence statistics or ranking.

## 5. Dual evidence channels

For every inactive term `t`, V4 records two distinct channels across the five discovery directions.

### 5.1 Residual-rank channel

This is the v3 channel and remains outcome-independent with respect to selector/probe data:

- best-repair fold count `B_t`;
- top-three repair fold count `T_t`;
- median absolute residual correlation `R_t`;
- residual-sign agreement `S_t`;
- client coverage `C_t`;
- coefficient-sign stability `Q_t`.

### 5.2 Discovery-path persistence channel

V4 additionally treats actual fold-level structural recurrence as an independent candidate-generation signal:

- selected-fold count `P_t`: number of the five fold-direction final structures containing `t` after the existing coefficient pruning;
- path sign stability: existing coefficient-sign stability `Q_t` evaluated from observable fold evidence;
- path observability: number of folds for which the term has sufficient observable evidence.

The path-persistence channel is not allowed to use selector, probe, global-test, or exact-recovery outcomes.

## 6. Role-conditioned candidate admission

The term catalog already labels terms as `core` or `exception`. V4 uses that existing declared role only to define the correct observability denominator.

### 6.1 Core-term admission

A core term enters the v4 candidate pool if **either** frozen channel passes:

**Core residual-rank channel**

- `B_t >= 2`; OR
- `T_t >= 3`, `S_t >= 0.60`, and `C_t >= 0.50`.

**Core path-persistence channel**

- `P_t >= 3` (majority of five fold directions);
- `Q_t >= 0.60`;
- `S_t >= 0.60` when residual correlation is observable; and
- `C_t >= 0.50`.

The `3/5` threshold is fixed as simple fold majority, not optimized on v3 outcomes.

### 6.2 Restricted-exception admission

A declared exception term is not judged by global client coverage. Instead, each fold direction defines:

- **eligible gated clients:** clients with sufficient observed support for the declared gate;
- **eligible outside clients:** clients with an estimable source coefficient outside the gate.

An exception term is evaluable in a fold only if at least one gated and one outside client are available, matching the logic required by the existing coefficient-heterogeneity certificate.

A restricted exception enters the candidate pool when:

- it is selected in at least `3/5` discovery directions **or** is the best supported repair in at least `2/5` directions;
- at least `3/5` directions contain valid gate/outside observability;
- coefficient-sign stability is at least `0.60`; and
- every counted discovery direction satisfies the unchanged exception coefficient-heterogeneity requirement used by the legacy/v2 engine (`heterogeneity_score >= 0.20`).

No global `C_t >= 0.50` requirement is applied to a restricted exception because clients outside its declared domain are not eligible observations of the gated term.

This is a denominator change based on declared term role, not a lowering of the evidence requirement.

## 7. Frozen v4 ranking

Candidate terms are ranked without selector/probe outcomes by:

1. number of evidence channels passed (two before one);
2. selected-fold count `P_t`;
3. best-repair fold count `B_t`;
4. top-three fold count `T_t`;
5. median absolute residual correlation `R_t`;
6. coefficient-sign stability `Q_t`;
7. lower catalog complexity;
8. lexicographic term name.

At most eight inactive terms may enter the candidate pool. This remains a candidate budget, not the final-structure budget.

## 8. Termwise forward structural search

V3 mostly compared whole candidate structures against a strict-intersection primary. V4 changes this to a termwise governed continuation.

### 8.1 Anchor structure

The anchor is the five-fold strict intersection after coefficient pruning. Terms outside the dual-evidence pool may remain in the anchor only because they were independently selected in all five discovery directions; this preserves the conservative v3 safety property.

### 8.2 Sequential term proposals

For each dual-evidence candidate not already in the current structure, in the frozen ranking order:

1. fit `current + term` on discovery data using federated aggregate normal equations;
2. evaluate the existing selector admissibility gate against `current`;
3. only if selector admissibility passes, evaluate the existing independent structural probe against correlated finite-catalog rivals;
4. accept the single term only if **both** gates pass;
5. if accepted, the candidate becomes the new `current` structure before the next ranked term is tested.

No multi-term bundle can enter solely because its aggregate score is good. Every new term must earn its own selector and probe evidence.

## 9. Bidirectional necessity audit

After forward search, V4 performs one frozen backward pass in reverse admission order.

For each non-intercept term `t` in the current structure:

1. create a deletion candidate `current - t`;
2. treat the deletion candidate as the conservative primary and the current structure as the one-term continuation;
3. re-run the same existing selector admissibility gate for whether retaining `t` provides at least the frozen validation gain and safeguards;
4. if retention passes the selector gate, re-run the independent structural probe for `t` in the current context;
5. retain `t` only if both retention gates pass; otherwise accept the simpler deletion candidate.

Thus the backward stage introduces no new numerical performance threshold. It asks whether every retained term can still justify itself under the same independent evidence standard after other accepted terms are present.

The backward pass is executed once; it does not oscillate to convergence.

## 10. Final refit and outputs

After the forward and backward termwise gates, V4 refits the retained term set on each client's full training partition through aggregate normal equations. Raw rows remain local.

Every run records:

- final terms and expression;
- anchor terms;
- dual-evidence candidate pool;
- channel membership for every term;
- per-term forward selector/probe decision;
- per-term backward retention/deletion decision;
- core/exception role;
- eligible gated/outside counts for exception terms;
- exact recovery, term precision, term recall, test NMSE, train MSE;
- spurious acceptance and exception recovery;
- runtime and serialized communication bytes.

## 11. Frozen development matrix

Benchmarks:

- `base`;
- `poly3`;
- `nested_sine`;
- `trig_product`;
- `interaction`.

Scenarios:

- `complementary`;
- `spurious`;
- `exception`.

Noise ratios:

- `0.03`;
- `0.10`;
- `0.20`.

Samples per client:

- `120`;
- `300`.

Clients: `4`.

Engineering smoke seed: `16001` only; smoke is excluded from evidence.

Fresh development seeds: `16101`, `16102`, `16103`, `16104`, `16105`.

Primary/comparator methods:

1. legacy certificate;
2. cross-fit v2 structural;
3. frozen stability-superset v3;
4. **RC-DES v4 full**;
5. v4 anchor-only diagnostic;
6. v4 without role-conditioned exception handling;
7. v4 without path-persistence admission;
8. v4 without backward necessity audit;
9. centralized forward upper bound;
10. score-only federated predictive comparator.

Full matrix size: `450 conditions x 10 methods = 4,500 rows`.

All rows and failures are retained.

## 12. Primary endpoints

1. overall exact structural recovery;
2. high-noise `poly3`/`interaction` exact recovery;
3. full-target candidate-pool recall;
4. candidate-pool **complete-truth coverage**;
5. conditional exception-term candidate recall and final exception recovery;
6. test NMSE;
7. spurious `x4`/`x4^2` acceptance;
8. forward exact gains/harms relative to the v4 anchor;
9. backward deletion exact gains/harms relative to forward-only v4;
10. candidate-pool size and nuisance inclusion;
11. runtime and communication.

Single critical-term recall is retained as a diagnostic but is not sufficient for the v4 mechanism gate.

## 13. Frozen go/no-go gate

V4 advances only if **every** criterion below passes on the complete 4,500-row matrix:

1. **overall exact non-inferiority:** v4 exact recovery `>= legacy - 0.01`;
2. **high-noise structural gain:** on `noise_ratio=0.20` and (`poly3` or `interaction`), v4 exact recovery `>= legacy + 0.05`;
3. **full high-noise poly3 term recall:** mean candidate-pool target-term recall on high-noise `poly3` `>= 0.90`;
4. **complete high-noise poly3 coverage:** candidate pool contains all true `poly3` terms in at least `0.80` of high-noise `poly3` conditions;
5. **exception candidate recall:** the declared exception term enters the v4 candidate pool in at least `0.90` of true exception conditions;
6. **final exception recovery:** conditional exception-scenario exception recovery `>= 0.97`;
7. **spurious control:** v4 `x4`/`x4^2` acceptance `<= legacy + 0.01`;
8. **forward safety:** zero observed exact harms when a termwise forward continuation activates relative to the paired v4 anchor on the same condition;
9. **backward safety:** zero conditions where the backward audit converts an exact forward-only v4 structure into a non-exact structure;
10. **predictive safety:** mean v4 test NMSE `<= 1.10 x legacy`;
11. **candidate compactness:** median dual-evidence candidate-pool size `<= 6` inactive terms;
12. **runtime:** mean runtime `< 15x legacy`;
13. **communication:** mean serialized communication `< 30x legacy`.

Failure of any single criterion is a NO-GO. No threshold, ranking rule, endpoint, or role definition may be changed after v4 evidence is inspected.

## 14. Pre-evidence implementation checks

Before any development seed `16101--16105` is run, CI must verify:

- deterministic five-fold splits;
- selector/probe disjointness;
- engineering smoke seed cannot enter the evidence path;
- v3 seeds `15101--15105` cannot enter v4 evidence;
- final seeds `11001+` cannot enter v4 development;
- role-conditioned exception eligibility never counts an ineligible outside-domain client as a gated observation;
- each forward proposal adds exactly one term;
- every added term has both selector and probe records;
- the backward pass removes at most one term per tested step and executes only once;
- score-only output cannot become the structural output;
- row counts and all numeric evidence fields are finite.

## 15. Evidence governance

The v4 implementation may be debugged only with unit tests, synthetic fixtures, and engineering smoke seed `16001` before evidence execution. If smoke touches `16001`, it is permanently excluded from evidence.

Once any seed in `16101--16105` is executed through the full evidence path:

- the v4 protocol is immutable;
- all five development seeds become spent;
- negative results are retained;
- no selective seed replacement is permitted;
- any subsequent redesign becomes v5 with a new protocol and fresh seeds.

## 16. Claim boundary after a possible pass

Even a complete v4 development pass would establish only that role-conditioned dual-evidence candidate admission plus termwise bidirectional probing improved the frozen finite-catalog synthetic development matrix.

A pass would **not** establish:

- catalog-free discovery;
- causal validity;
- formal privacy;
- universal superiority over symbolic-regression systems;
- real-world scientific discovery;
- Transactions readiness.

A pass permits only the next independent external-validation and scalability stage. PR #1 remains draft and unmerged until later evidence gates are completed.
