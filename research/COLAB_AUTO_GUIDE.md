# One-click audited Colab execution

Use the audited notebook:

```text
https://colab.research.google.com/github/AzizulHakim00/fedfalsify/blob/feat/fedfalsify-mvi/colab/FedFalsify_v06_Confirmatory_Colab_Auto.ipynb
```

## What it does

The notebook:

1. mounts Google Drive;
2. clones or refreshes the frozen GitHub branch;
3. restores any completed chunks from Drive;
4. validates the Colab pipeline and notebook syntax;
5. runs deterministic seed chunks;
6. records result hashes and a source-code fingerprint;
7. rejects mixed code versions or mixed experiment configurations;
8. verifies exact seed coverage and unique method-condition rows;
9. merges exactly 2,400 primary rows;
10. applies Holm correction;
11. creates `COMPLETE` and `VERIFIED.json` markers;
12. mirrors every completed state to Drive; and
13. optionally commits and pushes each completed chunk to GitHub.

## Required GitHub secret

Create a fine-grained personal access token limited to
`AzizulHakim00/fedfalsify` with **Contents: Read and write** permission. In
Colab, add it through the Secrets panel as:

```text
GITHUB_TOKEN
```

Allow notebook access. Do not paste the token into a code cell.

## Recommended sequence

### 1. Technical validation

Keep:

```python
MODE = "dry_run"
```

Run all cells. The dry run is stored separately and is not confirmatory evidence.

### 2. Full resumable primary experiment

Set:

```python
MODE = "run_all_and_merge"
```

Run all cells. The notebook processes four deterministic chunks:

```text
chunk 1: seeds 9001-9005
chunk 2: seeds 9006-9010
chunk 3: seeds 9011-9015
chunk 4: seeds 9016-9020
```

With `PUSH_AFTER_EACH_CHUNK = True`, each completed chunk is committed and pushed
to GitHub immediately after its Drive mirror and scientific seal are written.

If Colab disconnects, reopen the same notebook and use the same configuration.
Drive outputs are restored, completed manifests are detected, and completed
chunks are not recomputed.

### 3. Shorter sessions

Run one chunk at a time with:

```python
MODE = "run_one_chunk"
CHUNK_INDEX = 0  # then 1, 2, and 3
```

After all chunks exist, use:

```python
MODE = "merge_only"
```

## Output locations

Git working tree:

```text
results/colab/v06-primary-confirmatory/
```

Google Drive:

```text
MyDrive/FedFalsify/results/v06-primary-confirmatory/
```

Final required files:

```text
COMPLETE
VERIFIED.json
final/v06_confirmatory.csv
final/v06_confirmatory_raw.json
final/v06_confirmatory_holm.json
final/manifest.json
audit_premerge.json
```

## Integrity checks

Every sealed chunk records:

- exact selected seeds;
- frozen experiment settings;
- row count;
- SHA-256 hashes of result files;
- SHA-256 fingerprints of the source package, protocol, packaging metadata, and
  audited notebook;
- Python/platform metadata; and
- the Git commit visible during execution.

Merge fails when:

- a chunk is missing or incomplete;
- a result file changed after sealing;
- source fingerprints differ across chunks;
- protocol configurations differ;
- seeds overlap or fail to cover `9001-9020` exactly;
- duplicate method-condition rows exist; or
- the merged result does not contain exactly 2,400 rows.

## Scientific rules

- Never replace a weak or failed seed.
- Never change thresholds after examining confirmatory outputs.
- Do not delete algorithmic failures.
- A deterministic software defect must be documented and the complete affected
  matrix rerun.
- Keep the PR in draft until the final verified matrix and established-package
  comparisons are reviewed.
