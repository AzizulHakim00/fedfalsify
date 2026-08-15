# FedFalsify v0.6 Smoke Findings

## Scope

This note records the GitHub Actions smoke run for the v0.6 confirmatory
pipeline. It validates software execution only. It is not a confirmatory study
and must not be copied into a paper as performance evidence.

## Smoke configuration

```text
benchmark: base
scenarios: complementary and exception
noise ratio: 0.03
samples/client: 60
clients: 4
seed: 5001
controlled GP population: 12
generations: 2
maximum genes: 3
matched conditions: 2
```

The search budget was intentionally tiny to keep continuous integration fast.

## Diagnostic aggregate output

| Method | Runs | Exact | Precision | Recall | NMSE | Spurious accepted | Exception recovered | Mean runtime (s) | Mean communication (bytes) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FedFalsify v0.5 | 2 | 1.000 | 1.000 | 1.000 | 0.0000085 | 0.000 | 1.000 | 0.239 | 271,467 |
| Controlled centralized tree GP | 2 | 0.000 | 0.333 | 0.292 | 0.09117 | 1.000 | 0.500 | 0.307 | 0 |
| Controlled federated tree-GP-style | 2 | 0.000 | 0.333 | 0.292 | 0.09117 | 1.000 | 0.500 | 0.426 | 291,072 |
| Controlled residual-counterexample GP | 2 | 0.000 | 0.333 | 0.292 | 0.09117 | 1.000 | 0.500 | 0.366 | 0 |

## Why this is not performance evidence

1. Only two matched condition-seed pairs were run.
2. The GP budget used two generations and a population of twelve.
3. FedFalsify's named finite catalog contains the relevant benchmark terms,
   while the tree methods must search generated structures.
4. The exception scenario provides FedFalsify with a declared gate constructor.
5. McNemar's exact p-value was `0.5`, reflecting the tiny number of discordant
   pairs.
6. No official PySR run was executed in default CI.

Therefore the smoke result supports only this statement:

> The v0.6 matched runner, metrics, paired statistics, communication accounting,
> and output serialization execute successfully on a small diagnostic matrix.

It does not support:

- statistical superiority;
- state-of-the-art performance;
- superiority over official PySR or published federated GP;
- a privacy claim; or
- a general symbolic-discovery claim.

## Privacy smoke

The certificate-noise smoke used one complementary-domain run at multipliers
`0.0` and `0.25`. Both recovered the exact mechanism with NMSE approximately
`1.5e-5`.

This is also a pipeline check only. One run cannot establish robustness to
noise, and the current wrapper perturbs certificates while leaving aggregate fit
summaries unperturbed.
