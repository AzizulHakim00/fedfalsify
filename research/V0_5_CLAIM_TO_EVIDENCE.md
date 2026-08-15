# FedFalsify v0.5 Claim-to-Evidence Map

| Candidate statement | Evidence | Status |
|---|---|---|
| The post-search stage evaluates one- and two-term core replacements without raw rows | `replacement.py` and serialization path | Implemented; not a privacy guarantee |
| Accepted swaps require objective gain, client-level non-degradation, and incoming coefficient support | `ReplacementCertificate` fields and replacement tests | Implemented |
| The stage corrects the declared two-surrogate base trap | `test_two_for_one_replacement_removes_correlated_base_surrogates` | Supported in the controlled test |
| The stage leaves an already correct structure unchanged | `test_exact_structure_is_not_replaced_without_evidence` | Supported in the controlled test |
| v0.5 improves exact recovery over v0.4 in the disjoint-seed development matrix | 96/100 versus 92/100 | Descriptive development evidence |
| v0.5 is statistically superior to v0.4 | No paired confirmatory test yet | Unsupported |
| v0.5 outperforms established symbolic-regression systems | Published baselines not yet run | Unsupported |
| Repeated certificates are private | No threat model, DP, secure aggregation, or leakage attack | Unsupported |
| Recovered structures are causal mechanisms or scientific laws | Synthetic predictive benchmarks only | Unsupported |
| Sequential replacement itself is new | Floating and replacement feature-search methods are established | Explicitly not claimed |

## Executable evidence

- `src/fedfalsify/replacement.py`
- `src/fedfalsify/core_replacement_study.py`
- `tests/test_core_replacement.py`
- `fedfalsify-core-replacement --smoke`
- `fedfalsify-core-replacement --output results/v05_core_replacement.csv`

## Research documents

- `V0_5_DEVELOPMENT_PROTOCOL.md`
- `V0_5_DEVELOPMENT_FINDINGS.md`
- `PRIOR_ART_AND_ORIGINALITY.md`
- `REFERENCES.bib`

## Safe wording

> We evaluate a federated post-search certificate that accepts a core-term swap
> only when aggregate fit, client-level non-degradation, and incoming coefficient
> support jointly favor the replacement.

## Unsafe wording

> We invented sequential replacement and proved universal symbolic discovery.
