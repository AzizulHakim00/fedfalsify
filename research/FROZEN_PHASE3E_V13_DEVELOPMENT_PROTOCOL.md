# Frozen Phase-3E v13 Fresh-Noisy Development Protocol

**Date frozen:** 2026-09-14  
**Base implementation head:** `435a8c1af7436fac3d3b1a625e356cf6de180bb0`  
**Scientific candidate:** FedFalsify v13 / SCSV-SCC  
**Fresh development seeds:** `29401–29410`  
**Spent Phase-3C seeds:** `29301–29310` remain read-only  
**Engineering seed:** `29300` remains blocked  
**Final-confirmation seeds:** `11001–11999` remain blocked  
**Status:** prospective, pre-result specification.

## 1. Scientific objective

Test whether the already frozen v13 scope-contrast architecture retains its deterministic Phase-3D structural advantage under the complete noisy V10 heterogeneous federated benchmark. No v13 scientific rule, threshold, candidate grammar, split rule, multiplicity rule, capacity, source-provenance rule, or scope rule may change after any seed in `29401–29410` is executed.

Phase-3E is a development validation block, not final confirmation and not an architecture-tuning block.

## 2. Governed methods

Exactly four method rows are produced per condition, in fixed order:

1. `scsv-elrc-v11-full` — frozen v11 comparator;
2. `scsv-ncsc` — frozen v12/SCSV-NCSC predecessor;
3. `scope-contrast-only` — oracle/protected-shared v13 localization ablation; **not** a fair performance comparator;
4. `v13-full` — frozen SCSV-SCC v13 candidate.

The Phase-3D scientific source files remain unchanged.

## 3. Benchmark matrix

Use the frozen V10 generator and exactly the Phase-3C geometry:

- `quadratic_role_v10`, `linear_role_v10`, `trig_role_v10`, `interaction_role_v10`: K in {4,8,16}, balanced/imbalanced, single role for all K, quarter role for K in {8,16}, noise 0.10/0.30;
- `null_role_v10`, `anchor_contamination_null_v10`: K in {4,8,16}, balanced/imbalanced, role none, noise 0.10/0.30;
- `weak_source_role_v10`, `dual_role_v10`: K in {8,16}, balanced/imbalanced, quarter role, noise 0.10/0.30.

There are 120 conditions per seed, 1200 matched conditions across ten seeds, and 4800 primary rows.

## 4. Evidence separation

v11/v12 keep their frozen predecessor procedures. v13 keeps the frozen Phase-3D Discovery/Selector/Probe modulo split. Discovery may nominate scope identity/sign; Selector may only remove; Probe may only recertify frozen survivors. Benchmark truth is evaluation metadata only and must not enter `v13-full` scientific decisions.

`scope-contrast-only` intentionally uses the true shared structure and is interpreted only as a mechanism ablation.

## 5. Frozen v13 scientific constants

No changes from Phase-3D:

- Discovery role BH q = 0.10;
- Selector/Probe Holm alpha = 0.05;
- maximum role fraction = 0.50;
- outside-scope nondegradation tolerance = 1e-10;
- maximum non-intercept shared terms = 5;
- maximum localized terms = 2;
- maximum final terms including intercept = 10;
- weak source heredity preserved;
- candidate shared/localized grammar preserved exactly.

## 6. Outcomes

Primary outcome: exact full symbolic structure recovery for `v13-full` versus frozen v11 on matched conditions.

Secondary structural outcomes:

- shared precision/recall and TP/FP/FN;
- localized precision/recall and TP/FP/FN;
- exact client-scope recovery;
- mechanism-exact recovery = exact term structure AND exact client scope;
- null localized-FP and shared-FP condition rates;
- family-, client-count-, noise-, weak-source-, and dual-role stratified recovery;
- failure taxonomy and stage diagnostics;
- runtime;
- independent client-aware heldout NMSE after evaluation-only fixed-structure refit.

The heldout evaluation seed is deterministically `500000 + training_seed`. It is used only after structure is frozen and never enters discovery, selection, certification, or gates based on training evidence.

v13 Phase-3D communication accounting is not yet instrumented comparably with v11/v12. Therefore Phase-3E records communication as unavailable for v13 and makes **no communication superiority claim or communication GO/NO-GO criterion**.

## 7. Prospective paired analysis

Compare `v13-full` with `scsv-elrc-v11-full` condition-wise. Report:

- overall exact-recovery gain;
- repairs and harms;
- exact two-sided McNemar/binomial test on discordant pairs;
- seed-cluster bootstrap 95% CI for exact gain;
- exact one-sided sign-flip p-value over the ten seed-level gains;
- seed-level gain table.

A fixed analysis RNG distinct from benchmark seeds is used only for bootstrap resampling.

## 8. Prospective GO/NO-GO gate

All of the following must pass for `PHASE3E-DEVELOPMENT-GO`:

- overall exact-recovery gain vs v11 >= +0.03;
- seed-cluster bootstrap lower 95% CI bound > 0;
- pooled localized precision >= 0.99;
- pooled localized recall >= 0.94;
- pooled shared precision >= 0.975;
- pooled shared recall >= 0.98;
- null localized-FP condition rate <= 0.02;
- null shared-FP condition rate <= 0.02;
- exact harm rate vs v11 <= 0.01;
- exact client-scope recovery on non-null conditions >= 0.94;
- each ordinary role family all-true-localized recovery >= 0.92;
- K=4 >= 0.90, K=8 >= 0.93, K=16 >= 0.95 all-true-localized recovery where applicable;
- high-noise ordinary-family all-true-localized recovery >= 0.90;
- high-noise ordinary-family exact-recovery gain vs v11 >= +0.05;
- weak-source all-true-localized recovery >= 0.90;
- dual-role all-true-localized recovery >= 0.90;
- zero row-level integrity violations;
- exactly 1200 complete conditions and 4800 primary rows.

Runtime, heldout NMSE, v12 comparisons, and the oracle ablation are reported but are not hidden gates.

## 9. Persistence and visibility

A resume unit is one complete four-method condition group. A partial, duplicate, wrong-seed, wrong-method, or corrupt group is discarded and rerun. Each valid completed group is atomically persisted to Google Drive before the next condition.

Drive root:

`/content/drive/MyDrive/FedFalsify_Q1/PHASE3E_V13_FRESH_NOISY_DEVELOPMENT`

During incomplete execution, the console may show identity/progress/integrity only. Comparative performance summaries and GO/NO-GO are produced only after all 1200 conditions are complete.

## 10. Authorization firewall

Scientific execution requires:

- exact seed block `29401–29410`;
- explicit token `AUTHORIZE_PHASE3E_V13_FRESH_NOISY_DEVELOPMENT`;
- test gate PASS;
- frozen protocol SHA256 match;
- frozen predecessor and v13 scientific files diff-equivalent to base head `435a8c1af7436fac3d3b1a625e356cf6de180bb0`;
- spent `29300`, `29301–29310` and protected `11001–11999` unreachable.

The one-cell Colab wrapper defaults to NOT AUTHORIZED.

## 11. Interpretation boundary

A Phase-3E GO supports freezing v13 for external validation/final confirmation. It does not establish state-of-the-art performance, formal privacy guarantees, communication superiority, or final publication-level superiority.

A NO-GO is retained as a scientific negative result. The `29401–29410` block cannot be reused after any architectural or scientific change.
