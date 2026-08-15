# FedFalsify v0.6 Execution Checklist

## Before execution

- [ ] Confirm the branch commit SHA.
- [ ] Confirm all GitHub Actions checks pass.
- [ ] Confirm no v0.5 thresholds changed after the v0.5 development matrix.
- [ ] Confirm controlled GP budget matches `V0_6_CONFIRMATORY_PROTOCOL.md`.
- [ ] Confirm seeds are exactly `9001`--`9020`.
- [ ] Record Python, NumPy, operating system, processor, and memory.
- [ ] For official PySR, record PySR and Julia versions and archive the output
      directory.

## Primary controlled run

```bash
fedfalsify-confirmatory \
  --benchmarks base,poly3,nested_sine,trig_product,interaction \
  --scenarios complementary,spurious,exception \
  --noise 0.03,0.10 \
  --samples 300 \
  --clients 4 \
  --seeds 9001,9002,9003,9004,9005,9006,9007,9008,9009,9010,9011,9012,9013,9014,9015,9016,9017,9018,9019,9020 \
  --population-size 48 \
  --generations 12 \
  --max-genes 4 \
  --bootstrap-resamples 10000 \
  --output results/v06_primary_confirmatory.csv \
  --summary results/v06_primary_confirmatory_summary_raw.json
```

## Multiple-comparison correction

```bash
fedfalsify-confirmatory-report \
  --input results/v06_primary_confirmatory_summary_raw.json \
  --output results/v06_primary_confirmatory_summary_holm.json
```

The corrected file, not the raw file, supplies primary exact-recovery p-values
for the manuscript.

## Certificate-noise utility study

```bash
fedfalsify-privacy-study \
  --benchmarks base,poly3,interaction \
  --scenarios complementary,spurious,exception \
  --seeds 7001,7002,7003,7004,7005,7006,7007,7008,7009,7010 \
  --multipliers 0,0.10,0.25,0.50,1.0 \
  --samples 120 \
  --noise-ratio 0.03 \
  --output results/v06_certificate_noise.csv
```

Label this a utility ablation, not differential privacy.

## Official PySR

```bash
python -m pip install -e ".[sr]"
```

Use the official adapter only after recording the configuration. Run
complementary and spurious scenarios by default. The registered exception gate
is unsupported unless a custom operator is frozen before execution.

## Archive

Archive these files together:

- repository commit SHA;
- environment manifest;
- raw CSV;
- raw JSON summary;
- Holm-corrected JSON summary;
- console log;
- official PySR hall of fame, when applicable;
- machine metadata;
- any crash log;
- a checksum manifest.

## Post-run prohibitions

After results are visible, do not:

- change seeds;
- remove failed conditions;
- increase only one baseline's budget selectively;
- add a custom operator to rescue one method;
- change the exact-recovery coefficient threshold;
- relabel a controlled implementation as an author reproduction;
- describe the certificate-noise multiplier as epsilon.

Any algorithm, grammar, or threshold change creates a new version and requires
new confirmatory seeds.
