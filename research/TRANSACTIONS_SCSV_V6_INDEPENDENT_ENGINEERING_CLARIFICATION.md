# SCSV-Cert v6 independent-validation engineering clarification

Status: **FROZEN BEFORE ANY INDEPENDENT SEED `20101--20105` WAS EXECUTED**.

The first engineering smoke on seed `20001` failed before any scientific output because the preregistered imbalanced adapter allowed a 50-row client. The unchanged v6 selector/probe implementation requires at least 20 observations in the held-out validation partition before splitting it into disjoint selector and probe halves. With the unchanged 30% validation fraction, a 50-row client supplies only about 15 held-out rows and therefore cannot enter the frozen v6 algorithm.

This is an adapter-feasibility bug, not a scientific result. No independent-validation seed was touched, no gate was evaluated, and no v6 algorithm, threshold, ranking rule, benchmark truth family, scenario, endpoint, or A--R validation gate is changed.

The independent imbalanced-size adapter is therefore clarified as follows:

- retain the frozen geometric `0.50x` to `1.50x` imbalance profile;
- retain deterministic rotation by `seed % num_clients`;
- change the engineering feasibility floor from 50 to **70 observations/client**;
- 70 observations yield at least 21 rows under the unchanged 30% held-out split, satisfying the existing minimum of 20 held-out rows;
- balanced conditions remain unchanged;
- nominal study sizes, client counts, truth mechanisms, noise levels, methods, fresh seeds, matrix size, and all A--R gates remain unchanged.

The corrected smoke must pass on seed `20001` and full repository regression CI must pass before the authorization marker `[run-scsv-v6-independent]` may be committed.
