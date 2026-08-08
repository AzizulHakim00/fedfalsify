# Transactions stability-superset v3 findings

Status: **FROZEN DEVELOPMENT NO-GO**

Primary evidence workflow: `31037754111`

Primary evidence commit: `f1f3e782a59f8b5c5f9cde99ef683879726802b5`

Evidence seeds: `15101--15105` (spent; must not be reused as fresh evidence)

Engineering smoke seed: `15001` (excluded from evidence)

## 1. Executive decision

The preregistered stability-superset v3 development study is a **NO-GO**.
The full frozen 3,150-row matrix completed successfully and the audit step
verified the intended 450 matched conditions, seven methods, untouched evidence
seeds `15101--15105`, finite numeric outputs, and evaluation of every frozen gate.

The decision is final for this v3 protocol. The thresholds, ranking rules,
benchmarks, endpoints, and spent seeds must not be changed after inspection in
order to convert the outcome into a pass.

## 2. Frozen gate outcome

| Frozen criterion | Outcome |
|---|---|
| Overall exact recovery >= legacy - 0.01 | **FAIL** |
| High-noise poly3/interaction gain >= legacy + 0.05 | **FAIL** |
| High-noise poly3/interaction gain >= v2 + 0.05 | **FAIL** |
| High-noise poly3 true-term candidate recall >= 0.85 | PASS |
| Spurious acceptance <= legacy + 0.01 | PASS |
| Exception recovery >= 0.97 | **FAIL** |
| Zero observed exact harms on continuation activation | PASS |
| Median stable-superset size <= 5 | PASS |
| Runtime < 15x legacy | PASS |
| Communication < 30x legacy | PASS |

Because the protocol requires **all** criteria to pass, four failed criteria
are sufficient for a mandatory NO-GO.

## 3. What the result establishes

The result provides useful negative and mechanism-level evidence.

First, the key candidate-generation endpoint for high-noise `poly3` passed.
Therefore, the v3 stability screen did improve the specific failure mode that
motivated the redesign: the true cubic term can be retained in the candidate
superset often enough to satisfy the preregistered recall requirement.

Second, this improvement did **not** translate into the required final exact
structural-recovery gains. Both high-noise superiority criteria failed and the
overall exact-recovery non-inferiority criterion also failed. Candidate recall
alone is therefore insufficient to justify v3 as the next algorithmic version.

Third, the continuation mechanism did not produce observed exact-recovery harms
when activated, and the stable-superset size and computational/communication
budgets remained controlled. This narrows the likely bottleneck away from simple
superset explosion or an obviously destructive continuation rule.

Fourth, exception recovery failed its 0.97 floor. This is a distinct warning
because v3 changed candidate generation while retaining the v2 selector/probe
logic. Any future redesign must explicitly investigate restricted-exception
handling rather than assuming that better global candidate recall solves it.

## 4. Mechanistic interpretation boundary

The following is a **diagnostic hypothesis**, not yet a confirmed causal
explanation of the failures:

- high-noise candidate recall appears to have improved before final selection;
- final structural discrimination still fails to convert that recall into the
  required exact recovery;
- restricted-exception handling remains insufficient under the frozen matrix;
- because zero continuation harms passed, failures may include cases where the
  correct continuation is never admitted, ranked, or activated rather than
  cases where an activated continuation damages an otherwise exact structure.

The retained row-level evidence must be stratified before assigning failure
counts to candidate absence, selector rejection, structural-probe rejection,
intersection conservatism, nuisance competition, or exception-specific logic.

## 5. Evidence-preservation incident

Workflow run `31037754111` successfully completed:

1. the frozen 3,150-row matrix;
2. the integrity audit; and
3. the GO/NO-GO evaluation.

The workflow then failed only during the repository-preservation step because
`.gitignore` contains `results/*`, while the job attempted ordinary
`git add results/stability_superset_v3`. The artifact step was placed after the
failed Git step and was consequently skipped.

This is an engineering preservation failure, not an experimental failure and
not a reason to alter the scientific decision.

A recovery workflow was launched from commit
`c4ce15b25e7e32f65af48e3dac076805a8df811d` as run `31251266048`. It executes
the **same frozen code path and the same already-spent seeds** only to recreate
and preserve the lost deterministic outputs. It is explicitly not additional
statistical evidence, does not increase effective sample size, and must not be
pooled as an independent replication.

The recovery workflow uploads the sealed artifact before the Git operation and
uses `git add -f` only for `results/stability_superset_v3`.

## 6. Required next analysis after artifact recovery

Once the recovered row-level outputs are permanently available, the next task
is a forensic failure decomposition, not parameter tuning. For every v3 error,
classify the failure into mutually interpretable stages:

1. true target term absent from the stable superset;
2. target term present but absent from the candidate path used for selection;
3. candidate passed generation but failed the validation gate;
4. candidate passed validation but failed the independent structural probe;
5. correct candidate was admissible but lost the information-score decision;
6. restricted-exception-specific recovery failure;
7. nuisance/surrogate competition;
8. exact structure missed despite acceptable predictive NMSE.

Report counts by benchmark, scenario, noise level, sample size, and seed. Also
compare v3 with legacy, v2, and the paired v3-intersection diagnostic on the
same matched conditions.

## 7. Governance consequence

Do **not** proceed to final-confirmation seeds `11001+`, do not merge PR #1 as a
successful algorithmic advance, and do not claim Transactions readiness from
v3.

Any v4 proposal must be motivated by the retained failure decomposition,
preregistered before execution, and evaluated on fresh development seeds. The
v3 evidence remains part of the permanent negative-results record.
