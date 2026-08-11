# SCSV-RCEF v9 sharded recovery engineering authorization

This authorization permits **engineering-only** validation of the infrastructure-recovery implementation frozen after the v9 monolithic-run cancellation.

## Frozen scientific boundary

- v9 scientific mechanism, benchmark grammar, six methods, and A--W gates remain unchanged from the cancelled-run source `f291f05f1c0f0916b4450e9dcc8bbec4322bb110`;
- run `31435708338` remains `INFRASTRUCTURE-CANCELLED / NO SCIENTIFIC VERDICT`;
- seeds `26101--26105` remain permanently spent;
- fresh replacement seeds `27101--27105` remain untouched and unauthorized at this stage.

## Engineering-only release

Only seed `27001` is authorized for the recovery smoke.

The engineering firewall must verify:

1. exact source pin and historical-boundary integrity;
2. cancelled-run scientific source equality for v9 core, benchmark, study, protocol, and hardened v9 tests;
3. original hardened v9 forced-path tests;
4. recovery shard/aggregation firewall tests;
5. engineering smoke isolation to seed `27001` only;
6. no occurrence of `26101--26105` or `27101--27105` in smoke evidence;
7. full repository regression at the same implementation-equivalent state.

Fresh recovery development is unauthorized unless both the dedicated recovery smoke and full repository regression complete successfully.
