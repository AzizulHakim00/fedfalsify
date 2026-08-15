# RCSA spent-seed diagnostic authorization

Status: **AUTHORIZED AFTER ENGINEERING SMOKE AND FULL REGRESSION PASS**.

This record authorizes one post-independent Role-Conditional Set Augmentation (RCSA) mechanism diagnostic on already-spent independent seeds only. It is not fresh v7 evidence and cannot convert the prior SCSV-Cert v6 independent-validation NO-GO into a GO.

## Frozen scientific boundary

- Frozen protocol: `research/TRANSACTIONS_RCSA_SPENT_DIAGNOSTIC_PROTOCOL.md`.
- Post-independent mechanism diagnosis: `research/TRANSACTIONS_SCSV_V6_POST_INDEPENDENT_FORENSICS.md`.
- RCSA implementation source commit before authorization: `697ebaccc3c962edf8978449219e1b3ac0595dee`.
- Frozen SCSV-Cert v6 anchor implementation remains unchanged and is called through `scsv_cert_method`.
- RCSA may only augment a frozen v6 structure with a banked declared exception term under the preregistered selector-only role-local information test and outside-domain non-degradation rule.
- Criteria A--K are frozen and may not be changed after diagnostic outcomes are consumed.

## Pre-diagnostic engineering gates

Dedicated RCSA engineering smoke:

- workflow run: `31324284187`;
- engineering-only seed: `21001`;
- exact source pin: PASS;
- RCSA invariant tests: PASS;
- 3-condition engineering smoke: PASS;
- smoke seed-isolation audit: PASS;
- engineering artifact upload: PASS.

Full repository regression CI:

- workflow run: `31324286270`;
- conclusion: PASS;
- core pytest: PASS;
- all retained legacy/Transactions/v3/v4 smoke checks: PASS.

No spent independent scientific seed was consumed by the RCSA engineering smoke.

## Authorized diagnostic data

The only permitted scientific diagnostic seeds are the already-spent independent seeds:

- `20101`;
- `20102`;
- `20103`;
- `20104`;
- `20105`.

The diagnostic reuses the exact frozen 590-condition independent G/S/S32 geometry and reads the sealed historical `scsv-v6-full` rows as the comparator. It emits exactly one new RCSA diagnostic row per condition.

No fresh successor seed is authorized in this stage.

## Evidence-preservation requirements

The authorized workflow must:

1. pin the exact authorization SHA;
2. rerun the frozen RCSA invariant tests;
3. verify the sealed independent reference and its SHA-256 checksums;
4. execute exactly 590 RCSA diagnostic rows;
5. verify seeds are exactly `20101--20105` and that seed `21001` is absent;
6. evaluate frozen mechanism criteria A--K without threshold modification;
7. upload the sealed artifact before any repository evidence commit;
8. preserve all prior independent, v1--v6, SRSD and Beijing artifacts unchanged.

A technical preservation recovery may use the same spent seeds only and must be explicitly labeled recovery. It is not new evidence.

## Interpretation firewall

- PASS means **RCSA-MECHANISM-SIGNAL PASS on already-spent data only** and permits only design of a separately versioned successor protocol with genuinely fresh seeds.
- NO-GO retires this RCSA formulation.
- Neither result changes the historical SCSV-Cert v6 independent-validation decision.
- This authorization does not permit retrospective SRSD confirmation.
