# SCSV-RCEF v9 hardened engineering reauthorization

This is a pre-fresh-evidence engineering reauthorization after strengthening forced-path coverage. It changes no scientific rule, benchmark condition, A--W gate, threshold, or seed namespace.

## Why repeated engineering smoke is required

The first engineering smoke passed, but its eight natural smoke conditions were already structurally exact under the frozen v6 anchor. Therefore the smoke did not naturally exercise every new v9 augmentation branch.

The firewall was strengthened to deterministically exercise:

- response-free role proposal when a deviation is absent from the response-driven bank;
- source qualification pass when a banked source is absent from the anchor;
- source qualification failure and mandatory blocking of the linked deviation;
- pooled selector/probe evidence rescuing a directional but individually underpowered selector view;
- selector contradiction veto despite strong evidence in the other view;
- same-source ambiguity rejection;
- global ambiguity rejection for more than two positive deviations.

The first hardened test run exposed two fixture-only issues before any fresh seed was touched: a mock bank unintentionally admitted a second source-linked candidate, and an ambiguity assertion compared tuple order instead of structural set equality. The fixtures were corrected without modifying the v9 algorithm, protocol, benchmark matrix, thresholds, or A--W gates.

## Authorization boundary

- engineering seed `26001` may be reused for this smoke;
- fresh seeds `26101--26105` remain untouched and unauthorized;
- v8 remains `DEVELOPMENT-NO-GO` and its evidence files are immutable;
- the frozen v9 protocol and A--W gates are unchanged;
- fresh v9 development may begin only if this corrected hardened smoke and the full repository regression pass at the resulting implementation-equivalent state.