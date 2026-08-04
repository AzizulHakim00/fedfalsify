# Cross-fit redesign v1 evidence

This directory indexes the completed, frozen development study for the
cross-fitted certificate and governed-continuation redesign.

## Authoritative evidence

- workflow run: `30892814499`;
- artifact: `crossfit-redesign-v1-parallel-final`;
- artifact ID: `8885931902`;
- artifact digest: `sha256:fd824e995f7d10aaeaa83788ca3af86b463c167d55cd01ea0c67028c75f7fc83`;
- matched conditions: `450`;
- result rows: `2,250`;
- development seeds: `13001--13005`;
- final-confirmation seeds used: **no**.

Repository summaries:

- `summary_core.json` — aggregate metrics, paired exploratory analysis, fallback audit, and gate result;
- `manifest_core.json` — artifact identity and file hashes;
- `decision.json` — explicit NO-GO and prohibited post-hoc actions.

Full `rows.csv`, workflow-generated `summary.json`, and the original manifest are
stored in the sealed Actions artifact. The raw row CSV SHA-256 is
`c947aec8317fe84d55ccebd6db760f95255bd0d983529c2e3a5a7e1ceb26ac95`.

## Scientific decision

The redesign passed four of five frozen criteria but failed the required
high-noise `poly3`/`interaction` exact-recovery gain. Legacy and governed recovery
were both `0.35`; required improvement was `+0.05`.

Therefore this redesign is **NO-GO for final confirmation**. Do not retune or
regenerate evidence using seeds `13001--13005`.
