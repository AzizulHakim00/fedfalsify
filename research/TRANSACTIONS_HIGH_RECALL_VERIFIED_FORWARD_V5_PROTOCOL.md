# FedFalsify v5 Frozen Development Protocol

## High-Recall Verified Forward Search (HR-VFS)

**Status:** frozen development protocol.  
**Scientific role:** mechanism-level successor to the frozen RC-DES v4 NO-GO.  
**Protocol must exist before any v5 development seed is executed.**

## 1. Motivation from sealed v4 evidence

The v4 development matrix is closed and remains a NO-GO. Its spent seeds are `16101--16105` and must never be reused to tune v5.

Post-hoc analysis of the already-sealed 4,500-row v4 matrix classified 457 missing truth-term events across 1,140 truth-term opportunities:

- 156 truth terms were removed from the anchor by the backward audit;
- 4 accepted forward truth terms were subsequently removed by the backward audit;
- 137 truth terms never reached the candidate bank;
- 46 exposed truth terms were rejected by the selector;
- 114 exposed truth terms were rejected by the independent structural probe.

The term-specific failure pattern is especially informative:

- restricted exception `I(x3>1)*x3^2`: 51 candidate-bank misses and 28 backward removals;
- `x1^2`: 41 candidate-bank misses and 30 structural-probe rejections;
- `x1^3`: 34 selector rejections and 20 structural-probe rejections;
- `x3^2`: 39 structural-probe rejections and 32 backward removals;
- `x1`: 74 backward removals.

The no-backward v4 ablation achieved 0.6111 exact recovery versus 0.5022 for full v4, with 49 exact-only gains and zero reverse exact-only gains in the paired post-hoc comparison. However, it remained below legacy FedFalsify (0.7156), especially on `base` and `poly3`.

This evidence supports a new mechanism hypothesis rather than threshold retuning:

> Candidate generation should maximize plausible-mechanism recall, while final structural acceptance should be made only by independent held-out verification. Correlated terms that are weak one-at-a-time should be allowed a joint proposal, but every accepted member must prove conditional necessity at admission time.

The post-hoc counts above are diagnostic only. They are not confirmatory evidence for v5.

## 2. Working contribution hypothesis

**HR-VFS** combines four ideas:

1. role-conditioned and path-persistent discovery evidence;
2. a high-recall proposal-only candidate bank augmented by an aggregate score proposer;
3. discovery-only detection of highly correlated candidate pairs and joint bundle proposals;
4. selector + independent probe + leave-one-member-out necessity verification before a bundle can enter the model.

This combination is a **working contribution hypothesis**, not a universal novelty claim. Novelty wording is prohibited until a systematic prior-art review is completed.

## 3. Non-negotiable scientific boundaries

- No raw observation row may be pooled at the server.
- Candidate proposal and structural acceptance are separate roles.
- Score-only evidence may **propose** a term; it may never directly accept a term.
- The selector and structural probe must remain disjoint from discovery/proposal data.
- No backward pruning is allowed in v5.
- Truth labels may be used only for evaluation metrics and GO/NO-GO gates, never by the algorithm.
- Existing v0.6, external-validation, v1-v4, PySR-validation and final-confirmation artifacts remain immutable.
- Final-confirmation seeds `11001+` remain untouched.

## 4. Data roles

For each client, use the existing deterministic partitioning architecture:

1. **discovery/fit data**: candidate discovery, aggregate-score proposal and correlation sufficient statistics;
2. **selector data**: candidate non-degradation and validation-improvement checks;
3. **probe data**: independent structural rival and necessity tests.

No selector or probe observation may influence candidate-bank construction, score-proposer ranking, or correlation-bundle formation.

## 5. Discovery evidence

Run the same five deterministic discovery directions used by v4. Preserve:

- residual-rank evidence;
- discovery-path persistence;
- coefficient-sign information;
- client coverage;
- role-conditioned exception observability.

The v4 admitted terms form the first channel of the v5 proposal bank.

## 6. Proposal-only aggregate score channel

On **discovery/fit data only**, compute the existing federated aggregate score-only forward proposal path.

Freeze the following proposal rule:

- add every nonconstant term selected by that discovery-only score proposer to the proposal bank;
- this channel has **zero direct authority** to modify the accepted structural model;
- every score-proposed term must subsequently pass the same independent selector/probe acceptance route as any other term.

This choice is motivated by the sealed v4 comparator: score-only federated search had very high term recall but poor exact recovery and high spurious acceptance. It is therefore treated as a recall generator, not a structural decision rule.

## 7. Candidate-bank construction

The v5 candidate bank is the deterministic union of:

1. strict five-direction intersection terms (anchor terms);
2. v4 role-conditioned residual/path admitted terms;
3. discovery-only score-proposer terms;
4. eligible members of discovery-only correlated-pair bundles defined below.

Exclude the intercept `1` from the bank count.

**Maximum bank size:** 10 nonconstant terms.

If more than 10 terms are eligible, rank deterministically by:

1. anchor membership;
2. number of passed v4 evidence channels;
3. discovery-path selected-fold count;
4. best-repair fold count;
5. top-three repair fold count;
6. score-proposer selection order;
7. median absolute residual correlation;
8. coefficient-sign stability;
9. lower catalog complexity;
10. lexical term name.

No evaluation truth may break ties.

## 8. Correlated-pair discovery

Correlated bundles exist only to solve conditional-identifiability failures such as polynomial siblings.

Using **discovery/fit data only**, each client sends additive sufficient statistics for candidate-column correlation; raw feature rows are not transmitted.

For candidate terms `a` and `b`, define the federated absolute correlation from aggregated sums, sums of squares and cross-products.

A pair is eligible when all are true:

- both terms are nonconstant core terms;
- absolute federated discovery correlation is at least **0.80**;
- at least one member is already present in channels 1-3 of the candidate bank;
- the second member has at least one nonzero discovery signal: selected in any discovery direction, appears in a top-three repair set, has finite nonzero residual-correlation evidence, or is selected by the discovery-only score proposer;
- neither term is a restricted exception term;
- bundle size is exactly 2.

At most **four** pair bundles are retained, ordered by descending absolute correlation, then lower joint complexity, then lexical pair name.

The 0.80 correlation threshold, four-bundle cap, and all other values in this document are frozen before v5 development seeds are used.

## 9. Forward-only structural verification

Start from the strict intersection anchor.

### 9.1 Single-term route

For each unselected bank term in deterministic bank order:

1. refit `current + term` using fit data;
2. evaluate the existing selector admissibility safeguards on selector data;
3. if selector passes, run the independent structural rival probe on probe data;
4. accept the term only if both selector and probe pass.

No later backward deletion is permitted.

### 9.2 Pair-rescue route

A pair bundle is considered after its members have had their single-term opportunities. A pair may be proposed when neither both members are already accepted nor the pair would violate the final-size cap.

For pair `{a,b}`:

1. fit `current + {a,b}` on fit data;
2. require the same selector admissibility route applied to the joint proposal;
3. on independent probe data, require the joint proposal to improve over `current`;
4. compare against each one-member alternative `current+a` and `current+b`;
5. require **both** leave-one-member-out necessity tests to pass:
   - `current+{a,b}` must structurally beat `current+a`, establishing necessity of `b`;
   - `current+{a,b}` must structurally beat `current+b`, establishing necessity of `a`;
6. require the pair to beat the best single/rival explanation under the existing structural-probe relative-advantage and client-win safeguards;
7. accept both members atomically only when every requirement passes.

The existing structural-probe relative-advantage and client-win thresholds are not weakened for pair rescue.

This is **admission-time conditional necessity**, not backward pruning.

## 10. Restricted exception route

Restricted exceptions never enter a core correlation bundle.

For an exception term:

- retain the v4 eligible-client selector/probe denominator;
- augment proposal recall using role-conditioned discovery evidence plus the discovery-only score proposer;
- evaluate structural acceptance only on eligible gated selector/probe clients;
- require the existing role-conditioned independent probe before acceptance.

A restricted exception must never be promoted solely because it predicts well globally.

## 11. Model-size and stopping rules

- Keep the existing `max_terms = 6` interface and final-structure cap.
- No truth-dependent complexity cap is allowed.
- No backward audit is allowed.
- Stop only after the deterministic single-term and eligible pair proposal schedule is exhausted or the final-size cap is reached.
- No result-dependent restart or alternative ordering is allowed.

## 12. Frozen seeds

### Engineering smoke

`17001`

This seed is for software-path validation only and is permanently excluded from v5 evidence.

### Fresh v5 development evidence

`17101, 17102, 17103, 17104, 17105`

These seeds must not be executed until:

- protocol is committed;
- implementation tests pass;
- engineering smoke on 17001 passes;
- the evidence workflow is pinned to an exact source commit.

All earlier development/validation seeds are prohibited.

## 13. Frozen benchmark matrix

Development conditions:

- benchmarks: `base`, `nested_sine`, `trig_product`, `interaction`, `poly3`;
- scenarios: `complementary`, `spurious`, `exception`;
- noise ratios: `0.03`, `0.10`, `0.20`;
- samples per client: `120`, `300`;
- clients: `4`;
- fresh seeds: `17101--17105`.

This gives **450 matched conditions per method**.

## 14. Frozen methods

Use ten methods:

1. `legacy-certificate`;
2. `crossfit-v2-structural`;
3. `stability-superset-v3`;
4. `role-v4-no-backward`;
5. `hr-v5-full`;
6. `hr-v5-no-bundle-rescue`;
7. `hr-v5-no-score-proposer`;
8. `hr-v5-no-role-conditioning`;
9. `centralized-forward`;
10. `score-only-federated`.

Total frozen development matrix: **4,500 rows**.

## 15. Recorded endpoints

Per condition/method retain at least:

- exact structural recovery;
- term precision and recall;
- global-test NMSE;
- spurious-term acceptance;
- exception recovery;
- candidate-bank target recall;
- complete-truth candidate-bank coverage;
- bank size and nuisance count;
- selector/probe rejection stage;
- single-term accepted count;
- pair bundles attempted/accepted;
- pair necessity pass/fail for each member;
- runtime;
- serialized communication bytes;
- discovered expression and term set.

## 16. Frozen GO/NO-GO gate

**All criteria must pass. Any single failure means v5 NO-GO.**

A. Overall exact recovery of v5 full >= legacy exact recovery - 0.01.  
B. High-noise (`0.20`) `poly3` exact recovery of v5 full >= legacy + 0.05.  
C. High-noise (`0.20`) `interaction` exact recovery of v5 full >= legacy + 0.05.  
D. `base` exact recovery of v5 full >= legacy - 0.01.  
E. High-noise `poly3` candidate-bank target-term recall >= 0.95.  
F. High-noise `poly3` complete-truth candidate-bank coverage >= 0.90.  
G. Exception-term candidate-bank recall >= 0.95.  
H. Conditional exception final recovery >= 0.97.  
I. Spurious acceptance <= max(0.05, legacy spurious acceptance + 0.01).  
J. Single-term forward continuation has zero exact-recovery harms relative to its pre-activation state on diagnostic truth evaluation.  
K. Accepted pair rescue has zero exact-recovery harms relative to its pre-pair state on diagnostic truth evaluation.  
L. Mean global-test NMSE <= 1.10 x legacy mean NMSE.  
M. Median nonconstant candidate-bank size <= 10.  
N. Median runtime < 15 x legacy median runtime.  
O. Median communication < 30 x legacy median communication.

Criteria J and K are evaluation gates only; truth labels are not available to the algorithm.

## 17. Required ablation interpretation

- `hr-v5-no-bundle-rescue` tests whether joint conditional identification contributes beyond broad single-term exposure.
- `hr-v5-no-score-proposer` tests whether the proposal-only score channel improves candidate recall without controlling acceptance.
- `hr-v5-no-role-conditioning` tests restricted-domain observability handling.

No component is claimed as independently validated merely because the full method passes.

## 18. Evidence handling

The full v5 workflow must:

1. check out the exact triggering commit SHA;
2. assert the checkout SHA equals the recorded source SHA;
3. run frozen implementation tests before evidence;
4. retain exactly 4,500 rows;
5. audit ten methods x 450 matched conditions;
6. reject duplicate/missing/non-finite required results;
7. compute the frozen gate once without tuning;
8. write SHA-256 hashes for rows, summary, decision and source/protocol files;
9. upload the sealed artifact before any Git commit attempt;
10. keep PR #1 draft and unmerged.

## 19. Decision rule after development

If v5 passes every gate, proceed to a separately frozen independent validation/scalability stage. Do not immediately consume final-confirmation seeds.

If any gate fails, preserve the complete negative evidence, conduct post-hoc failure analysis, and require a new protocol plus new seeds for any successor.

## 20. Claim boundary

Until v5 passes and independent validation succeeds, the permitted statement is:

> HR-VFS is a preregistered mechanism hypothesis motivated by failure decomposition of RC-DES v4.

It is **not** yet permissible to claim that HR-VFS is superior, state of the art, universally novel, or publication-ready.
