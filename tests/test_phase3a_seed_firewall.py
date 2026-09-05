import pytest

from fedfalsify.scsv_v11_study import DEVELOPMENT_SEEDS, SMOKE_SEED

PHASE3A_ALLOWED_SEEDS = {29001}
PHASE1_SPENT = {29101, 29102, 29103, 29104, 29105}
PHASE2_SPENT = {29201, 29202, 29203, 29204, 29205}
PHASE3_ENGINEERING_RESERVED = {29300}
PHASE3_FRESH_RESERVED = set(range(29301, 29311))
FINAL_RESERVED = set(range(11001, 12000))


def validate_phase3a_seed(seed: int) -> None:
    if int(seed) not in PHASE3A_ALLOWED_SEEDS:
        raise ValueError("Phase 3A permits engineering seed 29001 only")


def test_phase3a_seed_namespace_is_disjoint_from_all_scientific_blocks():
    assert SMOKE_SEED == 29001
    assert set(DEVELOPMENT_SEEDS) == PHASE1_SPENT
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE1_SPENT)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE2_SPENT)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE3_ENGINEERING_RESERVED)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE3_FRESH_RESERVED)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(FINAL_RESERVED)


def test_phase3a_rejects_every_non_29001_namespace():
    for seed in (29101, 29201, 29300, 29301, 11001):
        with pytest.raises(ValueError, match="29001 only"):
            validate_phase3a_seed(seed)
