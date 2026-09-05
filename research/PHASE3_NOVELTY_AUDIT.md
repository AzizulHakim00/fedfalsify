# Phase 3 Novelty Audit

**Status:** Pre-implementation audit, not a final systematic-review claim  
**Date:** 2026-09-06  
**Method under audit:** FedFalsify v12 / SCSV-NCSC  
**Purpose:** determine what can and cannot be claimed as novel before implementation and fresh development.

## 1. Candidate contribution under audit

The candidate contribution is:

> Federated set-conditional symbolic discovery that separates a shared symbolic core from sparse client-localized structural deviations using a sequential Discovery -> Selector -> Probe protocol, noise-calibrated partial nested-model evidence, multiplicity-controlled structural certification, and additive sufficient statistics.

This audit does **not** authorize a "first" claim.

## 2. Search scope

The audit targeted recent and adjacent work in:

- federated symbolic regression;
- distributed genetic programming for symbolic regression;
- Bayesian federated symbolic regression;
- federated symbolic system identification / KAN-based equation discovery;
- multitask symbolic regression with shared and task-specific representations;
- noise-robust symbolic regression;
- uncertainty-aware symbolic regression;
- probabilistic/Bayesian symbolic structure uncertainty;
- formal/multiplicity-controlled structural inference in symbolic regression.

Primary search concepts included:

- `federated symbolic regression`
- `distributed symbolic regression`
- `Bayesian federated symbolic regression`
- `heterogeneous federated symbolic regression`
- `personalized federated symbolic regression`
- `multitask symbolic regression shared task-specific`
- `noise resilient symbolic regression`
- `symbolic regression uncertainty quantification`
- `structural uncertainty symbolic regression`
- `symbolic regression false discovery`

This is a focused novelty audit, not a PRISMA-style systematic review. It must be refreshed before manuscript submission.

## 3. Closest federated symbolic-regression work

### 3.1 Dong et al. — Federated Genetic Programming / FSL-GEP

**Paper:** Junlan Dong, Jinghui Zhong, Wei-Neng Chen, Jun Zhang, *An Efficient Federated Genetic Programming Framework for Symbolic Regression*, IEEE Transactions on Emerging Topics in Computational Intelligence, 2023, 7(3):858-871. DOI: `10.1109/TETCI.2022.3201299`.

**Evidence found:** establishes an explicit federated genetic-programming framework for symbolic regression and removes the need to centralize raw data.

**Overlap with SCSV-NCSC:**

- federated/distributed symbolic regression: yes;
- explicit mathematical expressions: yes;
- raw-data centralization avoided: yes.

**Material distinction under audit:** FSL-GEP is not framed as recovery of one shared symbolic core plus certified sparse client-localized deviations, and the reviewed description does not provide our sequential scope-certification/error-control construction.

**Novelty consequence:** we must not claim to introduce federated symbolic regression itself.

Source: `https://doi.org/10.1109/TETCI.2022.3201299`.

### 3.2 Billa et al. — Bayesian Federated Symbolic Regression (BFSR)

**Paper:** Mattia Billa, Veronica Guidetti, Luca La Rocca, Federica Mandreoli, *Mining Trustworthy Symbolic Regression Models in Federated Settings*, IEEE ICDM 2025, pp. 1055-1064. DOI: `10.1109/ICDM65498.2025.00114`.

**Evidence found:** BFSR formulates horizontal federated symbolic regression through Bayesian model selection and distributed posterior inference. The authors emphasize predictive accuracy, model interpretability, and uncertainty quantification under heterogeneous client settings.

**Overlap:**

- horizontal federated SR: yes;
- heterogeneous clients: yes;
- uncertainty-aware model selection: yes;
- distributed inference without centralizing data: yes.

**Material distinction under audit:** BFSR's reviewed formulation targets federated model selection/posterior inference. The current audit did not find an explicit shared-core + sparse localized-deviation decomposition with client-role certification and family-wise structural error control equivalent to SCSV-NCSC.

**Novelty consequence:** uncertainty alone is not novel. Our contribution must be tied to *scope-specific structural decomposition and certification*, not generic trustworthiness or Bayesian UQ.

Sources:

- `https://doi.org/10.1109/ICDM65498.2025.00114`
- `https://www3.cs.stonybrook.edu/~icdm2025/acceptedpapers.html`

### 3.3 Giuseppi et al. — FedKANs

**Paper:** Alessandro Giuseppi, D. Menegatti, A. Pietrabissa, *Learning symbolic models of dynamical systems through Kolmogorov-Arnold Networks (KANs) in centralized and distributed settings*, Journal of Automation and Intelligence, 2026, 5(2):155-165. DOI: `10.1016/j.jai.2025.11.005`.

**Evidence found:** extends symbolic dynamical-system identification to a federated/distributed setting; agents may observe similar but non-identical systems and cooperate without exchanging process data.

**Overlap:**

- distributed/federated symbolic identification: yes;
- non-identical local systems: yes;
- interpretable symbolic model goal: yes.

**Material distinction under audit:** the reviewed FedKANs formulation is KAN-based system identification and does not appear to provide the SCSV-NCSC shared-vs-localized structural hypothesis-testing framework or sequential family-wise certification.

**Novelty consequence:** "similar but non-identical clients" is not by itself novel.

Source: `https://doi.org/10.1016/j.jai.2025.11.005`.

## 4. Closest multitask/shared-specific symbolic-regression work

### 4.1 Arslan — shared and task-specific representations

**Paper:** Sibel Arslan, *A Multitask Multi-Gene Genetic Programming Approach for Symbolic Regression with Shared and Task-Specific Representations*, IDAP 2025. DOI: `10.1109/IDAP68205.2025.11222385`.

**Overlap:** explicitly addresses shared and task-specific symbolic representations across tasks.

**Material distinction under audit:** this is multitask GP, not the federated hypothesis-certification setting under audit. Shared/task-specific representation therefore cannot be claimed as a concept invented by FedFalsify.

### 4.2 Liang et al. — IRMTGP

**Paper:** Jing Liang, Wenjing Li, Yahui Jia, Ying Bi, *A Multitask Genetic Programming Approach with ANew Individual Representation to Symbolic Regression*, ICEAAI 2025. DOI: `10.1109/ICEAAI64185.2025.10956846`.

**Evidence found:** each task solution contains a shared tree and an unshared tree, explicitly separating common and task-specific knowledge.

**Novelty consequence:** our contribution must not be described merely as "shared + local symbolic structure." The stronger distinction is federated set-conditional *scope certification* from disjoint evidence with multiplicity/error-control and outside-role safety.

### 4.3 Li et al. — MTGP-BS

**Paper:** Xinyue Li, Wang Hu, Yu Zhang, *Post-Hoc Refinement for Multitask Symbolic Regression via Consensus-Accelerated Shapley Analysis*, AAAI 2026, 40(43):37054-37062. DOI: `10.1609/aaai.v40i43.41034`.

**Evidence found:** multitask symbolic regression with post-hoc synthesis/refinement and consensus-based knowledge extraction across multiple models.

**Novelty consequence:** consensus and cross-task knowledge sharing are active areas. FedFalsify should be framed around statistically certified structural scope rather than general consensus transfer.

## 5. Noise-robust symbolic regression

### Sun et al. — NRSR

**Paper:** Chenglu Sun, Shuo Shen, Wenzhi Tao, Deyi Xue, Zixia Zhou, *Noise-Resilient Symbolic Regression with Dynamic Gating Reinforcement Learning*, AAAI 2025, 39(19):20690-20698. DOI: `10.1609/aaai.v39i19.34280`.

**Evidence found:** explicitly targets exact symbolic recovery under high noise using a noise-resilient gating module and reinforcement learning.

**Overlap:** high-noise structural recovery is a direct shared objective.

**Material distinction under audit:** NRSR is a centralized RL/search approach, not a federated shared/localized structural certification method.

**Novelty consequence:** "noise robust symbolic regression" is not novel. Our contribution must be the *federated, scope-aware, sufficient-statistic certification mechanism*.

Source: `https://doi.org/10.1609/aaai.v39i19.34280`.

## 6. Uncertainty-aware and Bayesian symbolic regression

### 6.1 ERRLESS

**Paper:** Oussama Boussif et al., *Bayesian Symbolic Regression with Entropic Reinforcement Learning*, UAI 2026, PMLR 337.

**Evidence found:** samples from a posterior over symbolic expressions and emphasizes epistemic uncertainty over expression structure.

Source: `https://proceedings.mlr.press/v337/boussif26a.html`.

### 6.2 VaSST

**Paper:** Somjit Roy, Pritam Dey, Bani Mallick, *VaSST: Variational Inference for Symbolic Regression using Soft Symbolic Trees*, UAI 2026, PMLR 337.

**Evidence found:** posterior distributions over symbolic structures and uncertainty-aware symbolic model selection.

Source: `https://proceedings.mlr.press/v337/roy26a.html`.

### 6.3 UQ survey

**Work:** Julia Reuter, Fabricio Olivetti de França, *Are you sure? A Comprehensive and Comprehensible Survey of Uncertainty Quantification in Symbolic Regression*, 2026, arXiv:2606.06567.

**Evidence found:** uncertainty quantification in symbolic regression remains underexplored but spans frequentist, Bayesian, and model-selection approaches.

**Novelty consequence:** structural uncertainty/UQ is not itself novel. A defensible claim must identify the specific frequentist federated scope-certificate construction.

## 7. Contemporary survey evidence

Palakonda et al., *A Comprehensive Survey on Symbolic Regression: State-of-the-Art Approaches, Key Applications, Benchmark Evaluations, and Future Research Directions*, Archives of Computational Methods in Engineering, 2026, DOI `10.1007/s11831-026-10681-w`, identifies robustness, uncertainty/trustworthiness, theoretical foundations, benchmarking, and federated-learning settings as active/open directions.

This supports timeliness but is not evidence of novelty by itself.

## 8. Current overlap matrix

| Method/work | Federated | Shared/task-specific structure | Client-localized scope | Noise-specific mechanism | Structural uncertainty/error control | Disjoint final certificate | Additive sufficient-statistic test |
|---|---:|---:|---:|---:|---:|---:|---:|
| FSL-GEP | Yes | No explicit audited decomposition | No audited certificate | No | No audited formal control | No audited equivalent | Not the audited contribution |
| BFSR | Yes | Not the audited core framing | Heterogeneity, but not audited role certificate | Bayesian noise/UQ | Bayesian model uncertainty | Bayesian sequential inference | Different formulation |
| FedKANs | Yes | Similar/non-identical systems | No audited discrete role certificate | Not primary | No audited Holm-style structural control | No audited equivalent | Different KAN formulation |
| Arslan 2025 | No federated setting in audited description | Yes | Task-specific | No | No audited formal control | No | No |
| IRMTGP | No federated setting in audited description | Yes | Task-specific | No | No audited formal control | No | No |
| NRSR | No | No | No | Yes | No audited FWER structure certificate | No | No |
| ERRLESS / VaSST | No | No federated scope decomposition | No | Uncertainty-aware | Bayesian/variational structural uncertainty | Different | No |
| **SCSV-NCSC candidate** | **Yes** | **Yes** | **Yes, explicit client role** | **Yes, noise-scaled partial tests** | **Holm FWER for shared + Probe deviations** | **Yes, Selector/Probe separation** | **Yes** |

`No audited ...` means this focused audit did not identify the feature in the reviewed descriptions. It must not be interpreted as proof that no version of the literature contains it.

## 9. Defensible novelty position now

The strongest current claim is:

> SCSV-NCSC investigates a federated set-conditional symbolic-discovery problem in which ordinary shared structure and sparse client-localized deviations are treated as distinct structural scopes, with candidate scope constructed from data-local sufficient statistics and final localized structure certified on an untouched Probe split under family-wise multiplicity control and outside-role safety.

This is more defensible than any of the following claims, which are prohibited:

- "first federated symbolic regression";
- "first shared/task-specific symbolic regression";
- "first noise-robust symbolic regression";
- "first uncertainty-aware symbolic regression";
- "first federated learning for non-identical symbolic systems".

## 10. Remaining novelty risks

Before manuscript submission, search must be repeated specifically for:

1. personalized federated symbolic regression;
2. federated multitask genetic programming;
3. client-specific symbolic deviations in federated system identification;
4. hierarchical/mixed-effects symbolic regression;
5. symbolic regression with confirmatory sample splitting;
6. selective inference for symbolic regression;
7. FWER/FDR-controlled symbolic feature discovery;
8. distributed sufficient-statistic hypothesis testing for equation discovery.

If a close method appears, the contribution statement must be narrowed rather than defended rhetorically.

## 11. Baselines implied by the audit

A later external-validation protocol should consider, where implementation and problem geometry are compatible:

- frozen v11/SCSV-ELRC;
- FSL-GEP;
- BFSR;
- local-only symbolic regression;
- centralized pooled symbolic regression;
- a strong general SR system such as PySR or Operon;
- a noise-robust SR baseline such as NRSR;
- a multitask/shared-specific SR baseline where task geometry is compatible;
- FedKANs only for a genuinely comparable system-identification experiment.

No baseline should be forced into an incompatible setting merely to enlarge a table.

## 12. Audit decision

**Proceed with the SCSV-NCSC design direction, but do not use a priority/"first" claim.**

The current literature supports the following strategic conclusion:

- federated SR already exists;
- shared/task-specific SR already exists;
- noise-robust SR already exists;
- structural UQ already exists;
- the candidate contribution is the specific combination of **federated set-conditional scope decomposition + sequential independent structural certification + multiplicity control + sufficient-statistic equivalence + outside-role safety**.

This position must be re-audited immediately before paper submission.
