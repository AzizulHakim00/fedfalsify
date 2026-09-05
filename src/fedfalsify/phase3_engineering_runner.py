"""Phase-3 engineering runner shell.

Only the seed firewall is implemented in Batch A. Scientific execution is added
in a later reviewed task after SCR/NCEE integration is verified.
"""

from __future__ import annotations

ENGINEERING_SEED = 29300


def validate_phase3_engineering_seed(seed: int) -> None:
    if int(seed) != ENGINEERING_SEED:
        raise ValueError("Phase-3 engineering permits seed 29300 only")


def main() -> None:
    raise SystemExit("Phase-3 engineering execution is not implemented in Batch A")
