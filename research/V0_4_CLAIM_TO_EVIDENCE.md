# FedFalsify v0.4 Claim-to-Evidence Map

This file links each currently permitted statement to executable evidence and
records what remains unsupported.

| Candidate statement | Current evidence | Status |
|---|---|---|
| Clients exchange aggregate certificates rather than raw rows | Certificate serialization tests and protocol dataclasses | Implemented, not a privacy guarantee |
| Cross-client support rejects a declared single-client shortcut | `test_rejects_a_single_client_spurious_shortcut` | Supported in the synthetic benchmark |
| The output separates core and gated exception terms | Candidate term metadata and exception benchmark | Supported in the finite grammar |
| Conditional coefficient-shift evidence improves exception recovery over the disabled-certificate ablation | Fixed 100-run v0.4 development matrix | Exploratory development support |
| v0.4 is generally superior to symbolic regression | No published SR comparison yet | Unsupported |
| Certificates preserve privacy | No threat model, attack study, DP, or secure aggregation | Unsupported |
| Recovered equations are causal or scientific laws | Synthetic predictive benchmarks only | Unsupported |
| The exact combination is first or novel | Systematic review and direct closest-method comparison incomplete | Novelty hypothesis only |

## Executable evidence

- `tests/test_discovery.py`
- `tests/test_heterogeneity.py`
- `fedfalsify-heterogeneity --smoke`
- `fedfalsify-heterogeneity --output results/v04_heterogeneity.csv`

## Documentation evidence

- `V0_4_DEVELOPMENT_PROTOCOL.md`
- `V0_4_DEVELOPMENT_FINDINGS.md`
- `PRIOR_ART_AND_ORIGINALITY.md`
- `REFERENCES.bib`

## Next claim gate

No stronger performance or novelty wording should be used until a confirmatory
study with disjoint seeds and published symbolic-regression baselines is
complete.
