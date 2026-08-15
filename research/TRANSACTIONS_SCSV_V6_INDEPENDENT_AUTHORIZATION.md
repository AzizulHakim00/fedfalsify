# SCSV-Cert v6 independent-validation authorization

Status: **AUTHORIZED ONCE AFTER PRE-EVIDENCE ENGINEERING GATES PASSED**.

## Frozen scientific object

The operational SCSV-Cert v6 implementation remains byte-identical to the sealed v6 development GO version: `src/fedfalsify/scsv_v6.py` has Git blob SHA `4351e250b88c2ebc18fd9c08f25296ca2fffddbd` both at development evidence source `aee24a7b1eeb809d058e9623becddd6f4f31b867` and immediately before this authorization.

No v6 algorithm, threshold, bank rule, selector score, role-conditioning rule, score-proposer rule, probe semantics, final structure cap, development gate, or independent-validation gate has been changed for this stage.

## Independent protocol

Frozen protocol:

- `research/TRANSACTIONS_SCSV_V6_INDEPENDENT_VALIDATION_PROTOCOL.md`
- engineering clarification: `research/TRANSACTIONS_SCSV_V6_INDEPENDENT_ENGINEERING_CLARIFICATION.md`

The two earlier engineering-smoke failures were pre-evidence adapter-feasibility failures only. They touched smoke seed `20001` only, produced no independent scientific verdict, and are preserved in the clarification. The final adapter uses the mathematically minimal 71-row client floor required by the unchanged v6 30% held-out split and five discovery folds.

## Pre-authorization verification

Pre-authorization source commit: `0fc53c72ee306a6b0757cd6c4e68750a2ea2ba72`.

- independent engineering smoke: GitHub Actions run `31313955403` — **PASS**;
- smoke seed isolation: **PASS**, only `20001`;
- independent gate evaluation during smoke: **DISABLED**;
- full repository regression CI: GitHub Actions run `31313957436` — **PASS**;
- frozen v6 implementation blob identity versus sealed development source: **MATCH**.

## Fresh independent evidence

Fresh independent seeds:

`20101, 20102, 20103, 20104, 20105`

Matrix:

- Panel G: 300 matched unseen-combination conditions;
- Panel S: 270 matched scalability/imbalance conditions;
- Panel S32: 20 matched 32-client stress conditions;
- total: **590 matched conditions**;
- methods per condition: **6**;
- expected artifact: **3,540 rows**.

Frozen methods:

1. `legacy-certificate`;
2. `hr-v5-full`;
3. `scsv-v6-full`;
4. `scsv-v6-no-score-proposer`;
5. `centralized-forward`;
6. `score-only-federated`.

Independent-validation criteria **A--R** from the protocol are final. All must pass for `INDEPENDENT-GO`; any failure is `INDEPENDENT-NO-GO`. No threshold relaxation, benchmark deletion, subgroup rescue, seed replacement, or post-result algorithm change is permitted.

## Evidence boundary

The commit containing this authorization and marker `[run-scsv-v6-independent]` is the exact source commit for the one-time fresh independent-validation workflow. Once the workflow begins evaluating any of seeds `20101--20105`, all five are considered spent.

The workflow must preserve exact source pinning, verify frozen tests, execute exactly 3,540 rows, audit 590 conditions and six methods, seal hashes, upload the artifact before repository write, and only then commit the evidence.

A technical workflow/preservation failure may be deterministically recovered on the same spent seeds only if explicitly labeled recovery. It is not new evidence.

A synthetic `INDEPENDENT-GO` authorizes Layer B external SRSD validation; it does not itself establish real-world validity.
