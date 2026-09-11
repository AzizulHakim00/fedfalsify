# Phase-3C Fresh-Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, resume-safe Phase-3C fresh-development runner and one-cell Colab wrapper for the exact `29301–29310` block without altering the sealed scientific method or touching final-confirmation seeds.

**Architecture:** Reuse the sealed Phase-3B evaluator and scientific modules, but place development orchestration in a new module. The new runner owns only the legal 1200-condition matrix, seed/authorization firewall, complete-group checkpointing, paired analysis, prospective gate, and reproducibility artifacts. Scientific algorithm files remain byte-equivalent to the frozen Phase-3B source.

**Tech Stack:** Python 3.11+, NumPy, pandas, SciPy, joblib, pytest, GitHub Actions, Google Colab/Drive.

**Spec:** `research/PHASE3C_FRESH_DEVELOPMENT_PROTOCOL_DRAFT.md`

## Global Constraints

- Never execute benchmark seeds `29301–29310` during implementation or CI.
- Never touch seeds `11001–11999`.
- Frozen scientific source: `b67a07371bcf244728536028593373ca7d1990b1`.
- Frozen comparator files remain byte-identical to Phase-3A/Phase-3B seals.
- The new runner may import/reuse Phase-3B scientific code but may not alter its scientific constants or acceptance logic.
- Checkpoint only complete exact four-method groups.
- Comparative performance is hidden during partial execution.
- All writes are atomic where Phase-3B already uses atomic semantics.

---

### Task 1: Development matrix and seed firewall

**Files:**
- Create: `tests/test_phase3_development_runner.py`
- Create: `src/fedfalsify/phase3_development_runner.py`

**Interfaces:**
- Produces: `DEVELOPMENT_SEEDS`, `scientific_conditions()`, `validate_development_seed_block()`, `condition_key_string()`.

- [ ] **Step 1: Write failing tests** asserting exact seeds `29301..29310`, 120 conditions per seed, 1200 unique conditions total, legal family geometry, and rejection of engineering/final/partial seed sets.
- [ ] **Step 2: Run focused tests and verify RED** because `phase3_development_runner` does not yet exist.
- [ ] **Step 3: Implement minimal matrix/firewall code** by reproducing the already frozen legal V10 geometry, not by inspecting performance.
- [ ] **Step 4: Run focused tests and verify GREEN.**
- [ ] **Step 5: Commit.**

### Task 2: Complete-group checkpoint and authorization firewall

**Files:**
- Modify: `tests/test_phase3_development_runner.py`
- Modify: `src/fedfalsify/phase3_development_runner.py`

**Interfaces:**
- Produces: `validate_checkpoint_groups()`, `development_authorized()`, `require_development_authorization()`.

- [ ] **Step 1: Write failing tests** for four-method grouping, duplicate/partial/unauthorized row rejection, required test-gate environment variable, required explicit authorization token, and final-seed rejection.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement minimal checkpoint/authorization behavior.**
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: Commit.**

### Task 3: Evaluation rows and scope diagnostics

**Files:**
- Modify: `tests/test_phase3_development_runner.py`
- Modify: `src/fedfalsify/phase3_development_runner.py`

**Interfaces:**
- Consumes: sealed `run_scsv_v12_branches()` and V10 benchmark generator.
- Produces: `_evaluate_output()`, `_true_role_map()`, `_predicted_role_map()`, `_evaluate_condition()`.

- [ ] **Step 1: Write failing tests** using tiny fake outputs only; no fresh scientific seed execution. Assert historical term exactness remains unchanged while additive `scope_exact_recovery` and `mechanism_exact_recovery` detect a wrong client role.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement output evaluation and role-map extraction.**
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: Commit.**

### Task 4: Paired statistical analysis and prospective gate

**Files:**
- Modify: `tests/test_phase3_development_runner.py`
- Modify: `src/fedfalsify/phase3_development_runner.py`

**Interfaces:**
- Produces: `paired_analysis()`, `development_gate_metrics()`, `development_decision()`.

- [ ] **Step 1: Write failing deterministic tests** with synthetic row dictionaries for repair/harm counts, exact McNemar/binomial p-value, fixed cluster-bootstrap CI reproducibility, exact seed sign-flip p-value, and every hard gate boundary.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement analysis with fixed analysis RNG that is explicitly outside the benchmark seed namespace.**
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: Commit.**

### Task 5: Resume-safe execution and reproducibility artifacts

**Files:**
- Modify: `tests/test_phase3_development_runner.py`
- Modify: `src/fedfalsify/phase3_development_runner.py`

**Interfaces:**
- Produces: `run_development()`, artifact writers, manifest/ZIP verification, state PKL/joblib.

- [ ] **Step 1: Write failing tests** that monkeypatch `_evaluate_condition` so no scientific seed is run; verify resume skips complete groups, persists after each mocked group, refuses partial completion, suppresses comparative summary until complete, and creates expected artifact names only after complete mocked execution.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement execution/persistence by adapting Phase-3B atomic/checkpoint patterns.**
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: Commit.**

### Task 6: Frozen protocol and one-cell Colab wrapper

**Files:**
- Modify: `research/PHASE3C_FRESH_DEVELOPMENT_PROTOCOL_DRAFT.md` only after code/tests stabilize; then rename/copy to final frozen protocol name.
- Create: `tools/build_phase3_development_colab.py`
- Create: `colab/FedFalsify_Phase3_Fresh_Development_OneCell.ipynb`
- Create: `tests/test_phase3_development_colab.py`

**Interfaces:**
- Wrapper clones an exact development-harness commit, verifies the final protocol SHA, verifies frozen scientific diffs against `b67a073...`, creates an isolated environment, runs the complete test gate, mounts Drive before any scientific execution, then calls the development runner only when the explicit authorization token is present.

- [ ] **Step 1: Write failing wrapper tests** for exact source/protocol pins, Drive-first persistence, isolated environment, full pytest before runner, authorization token, blocked final seeds, and no inline copy of scientific algorithms.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement builder and generated one-cell notebook.**
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: Freeze the protocol text, compute its SHA, update wrapper literals, regenerate notebook, and rerun tests.**
- [ ] **Step 6: Commit.**

### Task 7: CI seal without scientific execution

**Files:**
- Create: `.github/workflows/phase3c_development_ci.yml`

**Interfaces:**
- CI verifies frozen scientific/comparator diffs and runs all repository tests. It must not set the authorization token and must never call `run_development()` with real scientific execution.

- [ ] **Step 1: Add workflow with branch trigger `research/phase3c-fresh-development`.**
- [ ] **Step 2: Verify comparator/scientific diff checks against frozen commits.**
- [ ] **Step 3: Run focused Phase-3C tests and full suite.**
- [ ] **Step 4: Wait for CI SUCCESS and record run ID/commit SHA in the protocol.**
- [ ] **Step 5: Final self-review for seed strings, authorization paths, artifact names, and protocol SHA.**

## Self-review

Spec coverage: matrix, seed firewall, no mid-block tuning, exact four methods, additive scope diagnostics, paired inference, prospective gate, checkpointing, Drive persistence, protocol/source pinning, and final-seed protection are all assigned to explicit tasks.

No production task authorizes execution during CI. No external baseline is added to the development decision because the protocol keeps external benchmarking as a separate post-development validation layer.
