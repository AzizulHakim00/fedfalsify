# SCSV-Cert v6 independent scalability and generalization findings

Status: **FINAL INDEPENDENT-VALIDATION NO-GO; sealed evidence retained without tuning**.

## Evidence identity and integrity

- workflow run: `31314059069` (success);
- frozen authorization/source SHA: `38416eacc3d4f2e715f2e54394946e1e4ba7ef2a`;
- sealed evidence commit: `25fd323c54bfa49dfcd55f36f39d9f1305195eb8`;
- artifact: `scsv-v6-independent-evidence`;
- artifact ID: `9039890190`;
- uploaded ZIP SHA-256: `dba6bebf7137c1bf7300ab9f94ed51e09f9f79f043bdf83552c0dd1aab8f39f3`;
- rows: `3540`;
- matched conditions: `590` (`G=300`, `S=270`, `S32=20`);
- seeds: only `20101--20105`;
- methods: exactly six frozen methods, each appearing `590` times;
- duplicate condition-method keys: `0`;
- required numeric NaN/Inf values: `0`;
- minimum generated client size: at least the frozen feasibility floor of `71`.

The workflow uploaded the sealed artifact before committing repository evidence. A local recheck of the downloaded artifact reproduced the recorded SHA-256 values:

- `rows.csv`: `6462f268775ae7c52595e3a87c0b56e70e65745aca66df1e062891678367d9af`;
- `summary.json`: `166d66eebc77e3da2f831ca7339aa77d405df010585e3dc1be32bc663da9c83b`;
- `decision.json`: `271c9508118aca6c7710aa7e294ad1ff2b500585013f16300f8d51bd271c4ff9`;
- `manifest.json`: `5a1e355a8e33107c48e851c852c295a98d65dc89330963217aea0e37789bed53`.

This was not a technical failure. Source-pin verification, frozen implementation tests, the complete 3,540-row matrix, audit/sealing, artifact upload, and evidence commit all succeeded.

## Frozen A--R gate verdict

Exactly one preregistered gate failed.

| Gate | Frozen requirement | Observed | Verdict |
|---|---|---:|---|
| A | Panel G v6 exact >= Legacy + 0.05 | `0.9367` vs `0.4333`; gap `+0.5033` | PASS |
| B | Panel G v6 exact >= v5 + 0.10 | `0.9367` vs `0.2733`; gap `+0.6633` | PASS |
| C | Panel G v6 exact >= centralized - 0.05 | `0.9367` vs `0.9733`; gap `-0.0367` | PASS |
| D | Panel G precision >= 0.95 | `0.9828` | PASS |
| E | Panel G recall >= 0.95 | `0.9819` | PASS |
| F | Panel G v6 NMSE <= Legacy NMSE | `0.0004618` vs `0.0144017` | PASS |
| G | Panel G spurious acceptance <= max(0.05, Legacy + 0.01) | `0.0000`; Legacy `0.0000`; limit `0.05` | PASS |
| H | Panel G exception recovery >= 0.90 | `0.9800` | PASS |
| I | Panel G bank target recall >= 0.98 | `0.9989` | PASS |
| J | Panel G complete-truth bank coverage >= 0.95 | `0.9967` | PASS |
| K | Panel S each 4/8/16-client v6 exact >= Legacy + 0.03 | v6 `0.7889/0.9000/0.9667`; Legacy `0.4111/0.4000/0.4444`; gaps `+0.3778/+0.5000/+0.5222` | PASS |
| L | Panel S 16-client exact >= 4-client exact - 0.03 | `0.9667` vs `0.7889`; change `+0.1778` | PASS |
| M | Panel S imbalanced exact >= balanced exact - 0.05 | `0.8741` vs `0.8963`; gap `-0.0222` | PASS |
| N | Panel S exception recovery at every client count >= 0.90 | 4 clients `0.8000`; 8 `0.9000`; 16 `0.9333` | **FAIL** |
| O | 16-client median communication/client <= 1.50x 4-client | `750606.5 / 758118.0 = 0.9901x` | PASS |
| P | 16-client median runtime <= 5.0x 4-client | `8.4418 / 2.2261 = 3.7921x` | PASS |
| Q | S32 exact >= 0.85 and exception >= 0.85 | exact `1.0000`; exception `1.0000` | PASS |
| R | all-condition v6 probe certification >= 0.70 | `0.85085` | PASS |

Because Gate N failed, the frozen rule yields **INDEPENDENT-VALIDATION NO-GO**. Threshold relaxation or subgroup rescue on seeds `20101--20105` is prohibited.

## Paired exact-recovery analysis

The following reporting analysis was computed only after the sealed artifact was frozen. It does not alter any gate.

Across all 590 matched conditions, v6 exact recovery was `0.9153`.

| Comparator | V6 wins | V6 losses | Ties | Exact-rate difference | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| Legacy certificate | 294 | 7 | 289 | `+0.4864` | `2.08e-77` |
| HR-VFS v5 | 410 | 1 | 179 | `+0.6932` | `1.56e-121` |
| Centralized forward | 30 | 39 | 521 | `-0.0153` | `0.3356` |

Condition-level bootstrap 95% CIs for the all-condition matched exact-rate difference (20,000 deterministic resamples, reporting seed `20260809`) were:

- v6 minus Legacy: `[+0.4441, +0.5288]`;
- v6 minus v5: `[+0.6542, +0.7305]`;
- v6 minus centralized: `[-0.0424, +0.0119]`.

For the preregistered primary Panel G alone (`n=300`), v6 exact recovery was `0.9367` versus Legacy `0.4333`, v5 `0.2733`, and centralized `0.9733`.

- v6 vs Legacy: `153` wins, `2` losses, `145` ties; difference `+0.5033`; exact McNemar `p=5.29e-43`; bootstrap 95% CI `[+0.4467,+0.5600]`;
- v6 vs v5: `200` wins, `1` loss, `99` ties; difference `+0.6633`; exact McNemar `p=1.26e-58`; bootstrap 95% CI `[+0.6067,+0.7167]`;
- v6 vs centralized: `6` wins, `17` losses, `277` ties; difference `-0.0367`; exact McNemar `p=0.0347`; bootstrap 95% CI `[-0.0667,-0.0067]`.

The centralized comparison remains consistent with frozen Gate C because the preregistered criterion was a `0.05` noninferiority-style tolerance, not equality or superiority.

## Scalability and imbalance findings

Panel S v6 exact recovery increased with federation size: `0.7889` at 4 clients, `0.9000` at 8, and `0.9667` at 16. The corresponding Legacy values were `0.4111`, `0.4000`, and `0.4444`.

Balanced versus imbalanced v6 exact recovery was `0.8963` versus `0.8741`, only `0.0222` lower under imbalance. Median communication per client was essentially flat from 4 to 16 clients (`758118.0` to `750606.5`, ratio `0.9901x`). Median runtime increased from `2.2261 s` to `8.4418 s` (`3.7921x`), within the frozen 5x ceiling. The targeted 32-client panel achieved exact recovery `1.0000`, exception recovery `1.0000`, and probe certification `1.0000`.

The sole NO-GO driver was the 4-client Panel S exception rate (`24/30 = 0.80`). Post-seal descriptive localization shows the strongest concentration in `cubic_cross` under the imbalanced 4-client profile (`0/5` exception recoveries); `multi_quadratic` balanced was `4/5`, while the other four 4-client family/profile cells were `5/5`. This localization is descriptive only and may not be used to rescue Gate N or tune v6 on the spent independent seeds.

## Scientific interpretation

The independent study strongly validates the score proposer and candidate-bank design: removing the score proposer reduced Panel G complete-truth bank coverage from `0.9967` to `0.4333` and exact recovery from `0.9367` to `0.4333`. Full v6 was also dramatically stronger than Legacy and v5 across the matched independent conditions, while remaining close to centralized forward selection.

However, the preregistered scalability gate required exception recovery of at least `0.90` at every tested federation size. The 4-client rate of `0.80` is a real retained failure. Therefore the independent synthetic-generalization claim must remain qualified, and the current frozen protocol does **not** authorize Layer B SRSD external execution as a confirmatory continuation.

## Correct next action

Do not rerun or tune v6 on seeds `20101--20105`, do not relax Gate N, and do not overwrite historical SRSD/Beijing/v1--v6 evidence. The appropriate next research step is a separately labeled post-independent forensic study using only spent evidence to characterize why low-client imbalanced exception discovery fails. Any algorithmic repair would constitute a new version and would require a new preregistered protocol plus genuinely fresh validation seeds before any new external-confirmatory claim.
