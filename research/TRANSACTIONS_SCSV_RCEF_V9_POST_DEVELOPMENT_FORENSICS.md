# SCSV-RCEF v9 post-development forensics

Status: **SPENT-DATA / NON-CONFIRMATORY DIAGNOSTIC ONLY**

This report analyzes only the sealed v9 sharded-recovery evidence from run `31465220024`. It does not revise the DEVELOPMENT-NO-GO verdict, does not authorize retuning v9, and must not be used as confirmatory evidence.

## Primary forensic conclusion

The v9 NO-GO is driven by two distinct failure pathways rather than by integrity or execution failure.

### 1. Null false positives originate in the shared anchor

Across `null_role_v9` and `diffuse_null_v9`, 44 of 120 full-v9 conditions contained a spurious deviation, giving null spurious-deviation acceptance `44/120 = 0.3667`. All 44 false positives were the same gated term, `I(x4>0.85)*x4^2`.

Crucially, in these 44 cases the term was already present in the frozen anchor/final structure while `accepted_deviations` was empty. Therefore the dominant null-precision failure did **not** arise from v9 role-contrast evidence fusion accepting a false certificate. It arose earlier, through the shared-anchor path admitting a role-conditioned exception term as if it were globally shared.

The pattern is strongly noise-dependent: at noise ratio `0.10`, null spurious-deviation acceptance was `0/60 = 0.000`; at noise ratio `0.30`, it was `44/60 = 0.7333`. By client count it was `0.225` for 4 clients, `0.375` for 8 clients, and `0.500` for 16 clients. Balanced and imbalanced rates were similar (`0.3833` and `0.3500`), so imbalance is not the main driver.

This single pathway also explains the low pooled deviation precision. Full-v9 produced 484 deviation true positives and 44 false positives, giving precision `484/(484+44) = 0.9167`. All 44 false positives occurred in the two null families; no deviation-bearing family contributed a deviation false positive.

### 2. True-deviation misses are dominated by held-out contradiction vetoes under difficult regimes

Full v9 had 36 deviation false negatives. Their family decomposition was:

- `dual_role_v9`: 11 missed true deviations;
- `quadratic_role_v9`: 10;
- `trig_role_v9`: 10;
- `linear_role_v9`: 5;
- `interaction_role_v9`: 0;
- `weak_source_role_v9`: 0.

Read-only inspection of the stored candidate diagnostics shows that all 36 missed true deviations reached an admissible role hypothesis. The rejection pathway was:

- 26/36: `HELDOUT-CONTRADICTION`;
- 9/36: `POOLED-NOT-SUPPORTED`;
- 1/36: `SOURCE-NOT-QUALIFIED`.

Thus the dominant recall bottleneck is not role discovery. It is the hard rule that any selector/probe directional contradiction vetoes a candidate, which becomes fragile when evidence per held-out view is noisy or small.

The aggregate recovery pattern supports this diagnosis. Main-family recovery was `1.000` at noise `0.10` but `0.875` at noise `0.30`. By client count it was `0.850` for 4 clients, `0.9375` for 8 clients, and `0.98125` for 16 clients. The failed 4-client and high-noise gates therefore point to limited held-out evidence rather than a broad role-identification failure.

### 3. Dual-deviation recovery is the main structural stress case

Dual-family both-deviation recovery was `0.75`. At noise `0.10`, both deviations were recovered in every 8-client and 16-client condition. At noise `0.30`, recovery fell to `0.20` for 8 clients and `0.80` for 16 clients.

The single exact-harm condition relative to v8-style also occurred in `dual_role_v9`: noise `0.30`, 16 clients, balanced, seed `27102`. V8-style recovered both deviations while v9 recovered only one. This reinforces that the v9 split-level veto can remove a true second deviation in difficult dual conditions even when the older mechanism happened to retain it.

### 4. Evidence fusion helped, but not enough

On all deviation-bearing conditions, selector-only and matched v8-style exact recovery were both `0.8479167`, while full v9 reached `0.8604167`. Therefore evidence fusion provided a real spent-data gain of `0.0125`, and the preregistered mechanism-superiority gate U passed. However, the required gate-F gain was `0.04`, so the improvement was insufficient to justify development success.

Overall exact recovery was `0.7883333` for v9 versus `0.7783333` for matched v8-style, satisfying overall noninferiority. Runtime and communication also remained within preregistered bounds. The NO-GO is therefore not due to cost or broad regression; it is due to precision, difficult-regime recovery, and dual-deviation reliability.

## What must not be concluded

These spent-data results do not justify selecting a new numeric threshold from `27101--27105`, weakening any v9 A--W gate, dropping hard cases from the benchmark, or rerunning v9 with a tuned veto. The data may motivate a separately versioned successor mechanism, but that successor requires a new protocol and a completely unused seed namespace before any fresh scientific evidence is generated.

## Mechanistic design requirements for a successor

Any successor should address the observed failure pathways structurally rather than by tuning v9:

1. gated/role-conditioned exception terms must not enter the globally shared anchor without a separate purity rule;
2. held-out support should not be decided by one noisy split-level directional veto when discovery has already frozen the candidate;
3. multiple source-disjoint true deviations should be certifiable jointly with explicit multiplicity control;
4. null precision must remain protected even if pooled evidence becomes less brittle;
5. all historical v6/v7/v8/v9 labels and spent seeds remain immutable.
