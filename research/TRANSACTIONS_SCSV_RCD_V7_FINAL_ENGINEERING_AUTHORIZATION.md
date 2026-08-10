# Final SCSV-RCD v7 engineering recheck

This commit triggers a second engineering-only smoke after adding forced acceptance-path tests.

Allowed seed: `24001` only.

The scientific protocol, benchmark matrix, truth coefficients, A--R gates, and fresh development seed set `24101--24105` are unchanged from the frozen protocol.

Formal fresh development remains prohibited until:

1. this dedicated v7 smoke passes;
2. the full repository regression CI passes at this implementation state.

No scientific result is authorized by this engineering recheck.