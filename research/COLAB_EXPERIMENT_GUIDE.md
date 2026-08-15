# FedFalsify Colab Experiment Guide

## Purpose

The notebook `colab/FedFalsify_v06_Confirmatory_Colab.ipynb` runs the frozen
v0.6 primary confirmatory experiment from GitHub while keeping two independent
copies of every completed result:

1. a Git-tracked copy under `results/colab/`; and
2. a mirrored copy in mounted Google Drive.

The primary matrix contains:

```text
5 mechanisms × 3 scenarios × 2 noise levels × 20 seeds × 4 methods
= 2,400 method-runs
```

The run is divided into four deterministic seed chunks so that a Colab
disconnection does not destroy the whole experiment.

## Open the notebook

Open the notebook on GitHub and select **Open in Colab**, or use:

```text
https://colab.research.google.com/github/AzizulHakim00/fedfalsify/blob/feat/fedfalsify-mvi/colab/FedFalsify_v06_Confirmatory_Colab.ipynb
```

A GPU is unnecessary. A CPU or high-RAM Colab runtime is appropriate.

## GitHub authentication

The public repository can be cloned without a token. A token is required only
for committing and pushing result files.

Recommended setup:

1. Create a fine-grained GitHub personal access token.
2. Limit repository access to `AzizulHakim00/fedfalsify`.
3. Grant **Contents: Read and write** permission.
4. In Colab, open the key/secrets panel.
5. Create a secret named `GITHUB_TOKEN`.
6. Enable notebook access for that secret.

Never paste a token into a notebook cell, Git remote URL, committed file, or
Drive result file. The notebook uses a temporary `GIT_ASKPASS` helper and
deletes it after pushing.

Fill in `GIT_USER_EMAIL` in the configuration cell before enabling GitHub push.
A GitHub no-reply email can be used.

## Google Drive layout

The default Drive destination is:

```text
/content/drive/MyDrive/FedFalsify/results
```

The primary run will appear at:

```text
MyDrive/FedFalsify/results/v06-primary-confirmatory/
```

The Git working-tree copy will appear at:

```text
results/colab/v06-primary-confirmatory/
```

## Required execution sequence

### Step 1: technical dry run

Use:

```text
MODE = dry_run
CHUNK_INDEX = 0
TOTAL_CHUNKS = 4
```

Run every notebook cell. The dry run uses a separate run ID ending in
`-dry-run`; it does not count as confirmatory evidence. GitHub push is disabled
for the dry run by default.

### Step 2: primary chunk 0

Use:

```text
MODE = primary_chunk
CHUNK_INDEX = 0
TOTAL_CHUNKS = 4
```

Run the notebook. This executes seeds `9001–9005` and creates:

```text
chunk-01-of-04/
```

### Step 3: remaining primary chunks

Repeat with:

```text
CHUNK_INDEX = 1  # seeds 9006–9010
CHUNK_INDEX = 2  # seeds 9011–9015
CHUNK_INDEX = 3  # seeds 9016–9020
```

The same Colab session is not required. Every completed chunk is mirrored to
Drive, and the notebook can restore Drive outputs in a later session.

Do not change any of the following between chunks:

- benchmark list;
- scenarios;
- noise levels;
- samples per client;
- client count;
- seed list;
- method list;
- GP population or generations;
- term limits;
- algorithm thresholds.

### Step 4: merge and validate

After all four chunk directories exist, set:

```text
MODE = merge
TOTAL_CHUNKS = 4
```

Merge mode:

1. restores Drive chunks into the Git working tree;
2. requires four completed manifests;
3. rejects duplicate method-condition rows;
4. requires exactly 2,400 rows;
5. recomputes the final raw summary;
6. applies Holm correction;
7. writes a final manifest with SHA-256 file hashes; and
8. creates a `COMPLETE` marker.

Final outputs:

```text
results/colab/v06-primary-confirmatory/final/v06_confirmatory.csv
results/colab/v06-primary-confirmatory/final/v06_confirmatory_raw.json
results/colab/v06-primary-confirmatory/final/v06_confirmatory_holm.json
results/colab/v06-primary-confirmatory/final/manifest.json
results/colab/v06-primary-confirmatory/COMPLETE
```

The same files are mirrored under the configured Drive root.

## Resume behavior

A chunk whose manifest has `status: completed` is not rerun unless the
`--force` option is explicitly supplied outside the notebook. This prevents
accidental replacement of completed confirmatory results.

If Colab disconnects before a manifest changes to `completed`, rerun the same
chunk index. Do not replace the seed or remove the failed attempt from the
research record.

## Git workflow

The notebook defaults to pushing result commits to:

```text
feat/fedfalsify-mvi
```

Before pushing it:

1. stages only the active run directory;
2. commits the new outputs;
3. pulls/rebases the current remote branch; and
4. pushes with the temporary token helper.

If two Colab sessions run concurrently, push conflicts are still possible.
Sequential chunk execution is recommended. Drive remains the independent backup
if a push fails.

## Manifest contents

Each chunk manifest records:

- run ID and chunk number;
- exact selected seeds;
- complete experiment configuration;
- FedFalsify version;
- Git commit at execution time;
- Python and platform information;
- expected and produced row counts;
- completion time;
- file sizes; and
- SHA-256 hashes.

This makes it possible to verify that GitHub and Drive contain identical
scientific outputs.

## Research-integrity rules

- Do not tune against seeds `9001–9020` after observing results.
- Do not delete algorithmic failures.
- Do not substitute new seeds for weak or failed results.
- Repair only deterministic software defects, document the defect, and rerun the
  complete affected matrix.
- Do not call the certificate-noise ablation differential privacy.
- Do not claim superiority over official PySR from the tiny PySR smoke run.
- Preserve the Git history, Drive backup, manifests, and final hashes.
