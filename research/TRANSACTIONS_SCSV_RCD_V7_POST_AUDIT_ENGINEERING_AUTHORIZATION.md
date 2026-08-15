# SCSV-RCD v7 post-audit engineering authorization

Status: **engineering-only**.

This authorization follows two pre-evidence audit corrections made before any scientific v7 seed was consumed:

1. Gate-B structural preservation is now audited against the explicit operational `final_structure`, rather than a coefficient-thresholded reporting view of discovered terms.
2. Dedicated v7 workflows explicitly execute both the invariant suite and the forced one-/two-deviation acceptance-path suite.

These corrections do **not** alter:

- the frozen v7 mechanism;
- any benchmark truth;
- the 580-condition matrix;
- noise levels, role profiles, or federation geometry;
- any A--R scientific threshold;
- fresh development seeds `24101--24105`.

Allowed seed in this recheck: `24001` only.

Fresh v7 development remains prohibited until both the dedicated v7 smoke and the full repository regression CI complete successfully at this exact implementation state.