# FCRRA spent-seed diagnostic authorization

Status: **AUTHORIZED FOR ONE FROZEN POST-INDEPENDENT SPENT-SEED DIAGNOSTIC RUN**.

This authorization releases only the already-spent independent seeds for the preregistered Frozen-Core Role Residual Augmentation (FCRRA) mechanism diagnostic. It is not fresh successor evidence, does not reopen the SCSV-Cert v6 independent NO-GO, and does not authorize SRSD external confirmation.

## Frozen scientific source

The governing protocol is:

- `research/TRANSACTIONS_FCRRA_SPENT_DIAGNOSTIC_PROTOCOL.md`;
- protocol freeze commit: `137c76bfa2303b94f75caa50f6218257131039cf`.

The corrected pre-authorization implementation lineage is headed by:

- `156a5a8443b9dd21a80353ce67a020d8defefdc3`.

The exact evidence source is the authorization commit containing this file and the `[run-fcrra-spent]` trigger marker. The workflow must verify `HEAD == GITHUB_SHA` before any spent-seed condition is evaluated.

## Scientific mechanism frozen

FCRRA is frozen as follows:

1. call the unchanged SCSV-Cert v6 method;
2. preserve its selected shared structure;
3. recover its selector-fit shared coefficients as the immutable admission anchor;
4. evaluate only a declared exception already present in the v6 candidate bank and absent from the v6 selector structure;
5. estimate only the exception coefficient from role-eligible discovery residual additive sufficient statistics;
6. do not refit any shared coefficient during admission;
7. use selector-only role-local information score for admission;
8. require outside-role prediction/SSE identity within `1e-10`;
9. use the independent probe only after admission and only as an audit;
10. do not alter candidate-bank rules, v6 thresholds, structure-size cap, role definition, or any historical result.

The A--M mechanism-signal criteria in the frozen protocol are immutable for this run.

## Engineering qualification

Engineering-only seed:

- `22001`.

First FCRRA smoke:

- run `31327238383`;
- result: engineering failure before any spent diagnostic data were evaluated;
- failure cause: a low-level unit test manually attempted to augment an exception already present in its synthetic anchor, while the production FCRRA path already prohibited that state;
- no `20101--20105` condition was executed;
- no scientific FCRRA result was produced.

The engineering repair added explicit helper guards against re-augmenting an already-selected exception and corrected the invariant test to construct a genuinely missing-exception anchor. The frozen FCRRA scientific rule and A--M criteria were unchanged.

Corrected FCRRA smoke:

- run `31327378386`;
- source SHA `156a5a8443b9dd21a80353ce67a020d8defefdc3`;
- exact source pin: PASS;
- FCRRA invariant tests: PASS;
- three-condition engineering smoke: PASS;
- smoke isolation audit: PASS;
- artifact upload: PASS;
- only seed `22001` used.

Full repository regression CI:

- run `31327380956`;
- source SHA `156a5a8443b9dd21a80353ce67a020d8defefdc3`;
- full pytest step: PASS;
- all legacy demos, benchmark smokes, privacy/statistical reports, audited Colab dry run, v3 smoke and v4 engineering smoke: PASS;
- final workflow conclusion: SUCCESS.

## Diagnostic data boundary

Authorized scientific diagnostic seeds are exactly:

- `20101`, `20102`, `20103`, `20104`, `20105`.

These seeds were already spent by the sealed SCSV-Cert v6 independent validation and therefore may be reused only for this explicitly post-hoc mechanism diagnostic.

Prohibited:

- any fresh successor seed;
- `22001` in the scientific diagnostic artifact;
- threshold or rule changes after this authorization;
- redefinition of the 590-condition independent geometry;
- overwriting historical independent, RCSA, SRSD, Beijing, v1--v6 artifacts;
- interpreting a FCRRA PASS as independent confirmation.

## Frozen matrix

Exactly one FCRRA row for each historical independent condition:

- Panel G: `300`;
- Panel S: `270`;
- Panel S32: `20`;
- total: `590` rows.

Historical frozen SCSV-Cert v6 rows at `results/scsv_v6_independent/rows.csv` are read-only matched comparators.

## Frozen decision criteria

All A--M criteria from the FCRRA protocol must pass for **FCRRA-MECHANISM-SIGNAL**. Any failed criterion yields **FCRRA-MECHANISM-SIGNAL NO-GO**.

No post-result threshold adjustment, coefficient shrinkage selection, subgroup rescue, repeated testing, or reinterpretation of a failed criterion is permitted.

## Evidence preservation

The guarded workflow must:

1. pin the authorization SHA exactly;
2. rerun FCRRA invariants before spent data;
3. verify the immutable historical independent reference;
4. execute exactly 590 rows using only `20101--20105`;
5. audit seeds, keys, required numeric fields, frozen-core structural containment, size cap and outside-role identity;
6. write a strict A--M decision;
7. hash source and outputs;
8. upload the sealed artifact before repository write;
9. commit the sealed diagnostic without modifying historical evidence.

## Promotion boundary

A PASS authorizes only design of a separately named successor algorithm and a genuinely fresh-seed preregistered validation protocol.

A PASS does **not** convert SCSV-Cert v6 to independent GO, erase the RCSA NO-GO, or authorize retrospective SRSD execution.

A NO-GO retires this FCRRA formulation and leaves the v6 independent NO-GO as the current scientific boundary.
