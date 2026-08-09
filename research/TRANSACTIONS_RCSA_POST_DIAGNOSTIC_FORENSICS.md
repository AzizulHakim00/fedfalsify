# RCSA post-diagnostic forensic findings

Status: **FINAL POST-HOC FORENSIC INTERPRETATION OF THE SEALED RCSA SPENT-SEED NO-GO**.

This document analyzes only the sealed RCSA artifact produced from already-spent independent seeds. It does not reopen the SCSV-Cert v6 independent decision, does not convert RCSA into evidence, and does not authorize external confirmation.

## Evidence identity

- RCSA workflow run: `31324548797`;
- exact recovery/source SHA: `90451a24e83ac5b3d3c3ccd6fc45dd071a93228e`;
- sealed result commit: `7d2fc23c2a95b9954547bda950a445ff3d8ba06f`;
- diagnostic rows: `590`;
- spent seeds only: `20101--20105`;
- fresh successor seeds used: none;
- frozen historical independent comparator preserved at commit `25fd323c54bfa49dfcd55f36f39d9f1305195eb8`.

The RCSA workflow completed source-pin verification, frozen implementation tests, immutable-reference verification, all 590 diagnostic conditions, audit/sealing, artifact upload and repository evidence commit successfully. The scientific outcome was therefore a mechanism NO-GO, not an engineering failure.

## Frozen A--K verdict

RCSA passed candidate-bank identity, non-exception identity, preservation of already-selected exceptions, 8/16/32-client exception preservation, overall exact noninferiority, zero exact harms and no spurious worsening. It failed the two rescue criteria:

- Panel-S 4-client exception recovery remained `0.8000`, below the frozen `0.9000` requirement;
- rescued exception-selection misses: `0/13`, below the frozen `>=7/13` requirement.

The run made exactly `13` augmentation attempts and accepted `0`.

## Rejection anatomy

A direct audit of all 13 attempted rows shows a uniform pattern.

1. The declared exception term was already present in the frozen v6 candidate bank.
2. Exactly one selector client was role-eligible in every attempted condition: the final domain client (`client-4`, `client-8`, or `client-16` according to federation size).
3. The outside-domain non-degradation check was **not** the bottleneck. In all 13 attempts, the globally refit augmented model actually reduced selector SSE outside the eligible exception client.
4. The failure was entirely the role-local information criterion. For every attempted condition,
   `J(S + e) > J(S)` on the eligible selector client.
5. Consequently, all 13 augmentations were rejected before probe certification, leaving the frozen v6 operational structure unchanged.

Representative attempted cases include:

- `cubic_cross`, Panel S, 4 clients, imbalanced, seeds `20101--20105`: all five attempts rejected;
- `cubic_cross`, Panel S, 8 clients, balanced, seeds `20102` and `20105`: rejected;
- `cubic_cross`, Panel S, 16 clients, balanced seed `20104` and imbalanced seed `20105`: rejected;
- `multi_quadratic`, Panel S, 4 clients balanced seed `20104` and 8 clients imbalanced seed `20105`: rejected;
- two Panel-G misses (`nested_mixed` and `multi_quadratic`, seed `20104`): rejected.

Across these attempted rows, the augmented role-local information score was always worse even though outside selector SSE decreased.

## Mechanistic interpretation

The RCSA implementation used role-conditioned **selection** but not role-conditioned **coefficient fitting**. Both the anchor and `anchor + exception` candidates were refit from the pooled discovery sufficient-statistic packets across all clients before the role-local selector score was evaluated.

This creates a structural mismatch for restricted terms. The exception basis column is active only inside the declared eligible domain, but introducing it into a globally refit model allows the coefficients of the already-selected shared core terms to move as well. The global least-squares solution can therefore use the extra restricted degree of freedom to improve the dominant outside-domain fit while shifting the shared coefficients in a way that degrades the eligible client's held-out role-local score.

The observed pattern is exactly consistent with that failure mode: outside-domain SSE improved in every attempted case while eligible-client information score degraded in every case. This is an inference from the sealed diagnostic and the frozen RCSA implementation; it is not yet an independently validated causal claim.

## What is ruled out

The sealed RCSA result makes the following formulations poor successor candidates:

- simply relaxing the role-local information-score threshold;
- accepting a restricted term whenever it is present in the bank;
- global refitting of all shared coefficients followed by a role-local acceptance test;
- post-hoc subgroup rescue of Gate N;
- tuning against seeds `20101--20105`.

RCSA was deliberately harm-free because rejected augmentations left v6 unchanged, but that safety came with zero rescue.

## Next mechanistic hypothesis

The clean next hypothesis is **Frozen-Core Role Residual Augmentation (FCRRA)**.

For a banked restricted term missing from the frozen v6 selector structure:

1. retain the frozen v6 shared structure and its discovery-fitted shared coefficients as an immutable anchor;
2. compute residuals of that anchor only on role-eligible discovery clients;
3. estimate only the restricted-term coefficient from those eligible residuals using additive sufficient statistics;
4. leave every shared coefficient unchanged;
5. because the restricted basis is zero outside its declared role, outside-domain predictions are then identical to the anchor by construction;
6. decide admission using selector-only role-local information improvement;
7. send the resulting structure to the independent probe only after the selector decision.

This is materially different from RCSA: the new restricted term cannot pull shared coefficients toward the majority domains.

## Governance boundary

FCRRA must first be tested only as another explicitly post-hoc, spent-seed mechanism diagnostic on the already-spent `20101--20105` matrix. A positive signal would authorize design of a separately versioned successor with genuinely fresh seeds; it would not repair the historical v6 NO-GO and would not authorize retrospective SRSD confirmation.
