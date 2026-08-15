# FedFalsify v10 paper-first successor design

## Canonical working name

**FedFalsify v10: Shared-Anchor Purity with Pooled Certification (SCSV-APPC)**

Status: **PAPER DESIGN ONLY — NO IMPLEMENTATION, NO FRESH EVIDENCE AUTHORIZED**

This document is a successor-design response to the sealed v9 DEVELOPMENT-NO-GO. It is motivated by spent-data forensics but is not validated by those spent data. V9 remains permanently frozen and must not be retuned.

## Historical boundary

- v6 independent validation: `INDEPENDENT-NO-GO`;
- v7 development: `DEVELOPMENT-NO-GO`;
- v8 development: `DEVELOPMENT-NO-GO`;
- v9 original execution: `INFRASTRUCTURE-CANCELLED / NO SCIENTIFIC VERDICT`;
- v9 sharded recovery: `DEVELOPMENT-NO-GO`;
- v9 fresh namespaces `26101--26105` and `27101--27105` are permanently spent.

No v10 result may relabel any historical result.

## Forensic motivation, not confirmation

The sealed v9 recovery evidence showed two dominant spent-data failure pathways:

1. all 44 deviation false positives came from a gated exception term already entering the shared anchor, rather than from a false v9 deviation certificate;
2. 26 of 36 true-deviation misses were caused by hard selector/probe contradiction vetoes, concentrated in high-noise, small-client, and dual-deviation settings.

V10 therefore changes the architecture of structural admission rather than weakening v9 thresholds.

## Mechanism 1 — shared-anchor purity firewall

The shared anchor is restricted to terms declared **globally shareable** by grammar metadata before any response is observed.

A term with any client-role gate, subgroup indicator, role-conditioned coefficient, or exception metadata is ineligible for the shared anchor, even if a response-driven proposer ranks it highly. Such a term may enter the final model only through the separately audited conditional-certification channel.

This creates a structural separation:

`G_shared ∩ G_conditional = empty`.

The shared anchor may contain the source term of a conditional deviation, but never the gated deviation itself.

This rule is intended to prevent a role-conditioned term from being treated as globally shared and to make null precision auditable independently of conditional certification.

## Mechanism 2 — discovery-frozen conditional candidates

Role identification remains response-free and uses only discovery-side gate occupancy. Candidate coefficients and source coefficients are fitted on discovery data only. Held-out data may not change the candidate identity, role set, source identity, or coefficient estimates.

The v9 outside-role and pair-invariant rules remain mandatory.

## Mechanism 3 — pooled held-out certification without a single-view veto

V9 treated any directional contradiction in selector or probe as an automatic veto. V10 instead makes the combined held-out sample the primary certification object after discovery has frozen the candidate.

For a fixed full/reduced pair, let selector and probe supply disjoint held-out losses `(F_s,R_s)` and `(F_p,R_p)`. Define

`F_pool = F_s + F_p`

`R_pool = R_s + R_p`

with `N_pool = N_s + N_p`.

The primary evidence statistic is computed only from this pooled held-out sample. Selector and probe remain separately reported as heterogeneity diagnostics, but neither view alone can veto a candidate solely because of sampling-direction noise.

No numeric acceptance threshold is selected in this design document from v9 spent outcomes. The final statistic and threshold must be frozen in a dedicated v10 protocol before engineering or fresh seeds are run.

## Mechanism 4 — multiplicity-controlled conditional admission

Because pooled certification may be less brittle than a hard split veto, v10 must add an explicit family-wise false-positive control across all conditional candidates evaluated in a condition.

The paper design requires a deterministic multiplicity procedure, such as Holm correction over predeclared candidate-level held-out tests, with the family-wise level frozen before fresh evidence. The exact test and level require protocol freeze and must not be selected using v9 spent rows.

This guard is intended to protect null precision while permitting pooled evidence to recover weak true effects.

## Mechanism 5 — source-disjoint multi-deviation certification

For multiple conditional deviations linked to distinct sources, v10 permits a deterministic joint candidate after each source/deviation pair has passed its own structural-integrity checks.

The joint model must:

- contain only individually predeclared source-linked deviations;
- keep unrelated anchor coefficients frozen during certification;
- preserve pair/source invariants;
- use the same pooled held-out evidence object;
- apply the frozen multiplicity rule;
- reject source-ambiguous alternatives rather than ranking them by development performance.

This is intended to address dual-role settings without adding truth-aware ranking.

## Null-safety requirement

A v10 development protocol must include at least the same null and diffuse-null stress families as v9. The primary null claim must distinguish:

1. gated terms entering through the shared anchor — required to be exactly zero by construction under the anchor-purity firewall; and
2. gated terms entering through conditional certification — controlled by the frozen multiplicity procedure.

Any bypass of this separation is a fatal integrity failure.

## Candidate future seed namespaces

A repository collision search performed after sealing the v9 NO-GO found no use of the following candidate namespace:

- engineering-only candidate seed: `28001`;
- future fresh-development candidate seeds: `28101, 28102, 28103, 28104, 28105`.

These numbers are **reserved only on paper** by this document. They must remain untouched until a separately reviewed v10 protocol freezes the benchmark matrix, exact statistical test, multiplicity level, gates, source pin, collision audit, forced-path tests, engineering smoke, and full repository regression. If any of these seeds are exposed before that freeze, the namespace must be abandoned.

## Required pre-evidence protocol work

Before any v10 scientific computation, a dedicated protocol must freeze:

1. exact globally-shareable versus conditional grammar metadata;
2. anchor-purity implementation invariant;
3. exact pooled held-out statistic;
4. exact multiplicity procedure and family-wise level;
5. deterministic multi-deviation joint-certification rule;
6. benchmark families and matrix size;
7. comparison methods and ablations;
8. development gates, including strict null precision, small-client, high-noise, and dual-role gates;
9. source-code hashes;
10. engineering-only seed namespace and fresh-development namespace;
11. forced paths for anchor contamination rejection, pooled support, false-candidate multiplicity rejection, dual acceptance, null rejection, and source ambiguity;
12. sharded execution and evidence sealing so repository-write failure cannot invalidate an already sealed artifact.

## Scientific boundary

This document does **not** authorize v10 implementation tuning against v9 rows and does **not** authorize any v10 fresh run. The next valid step is protocol specification and static/engineering validation only. Fresh `281xx` evidence remains blocked until the complete v10 firewall is green at one exact implementation SHA.
