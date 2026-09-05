import pytest

from fedfalsify.phase3_engineering_runner import (
    ENGINEERING_CONDITIONS,
    ENGINEERING_SEED,
    validate_phase3_engineering_seed,
)


def test_phase3_engineering_seed_allows_only_29300():
    validate_phase3_engineering_seed(29300)
    for seed in (29001, 29101, 29105, 29201, 29205, 29301, 29310, 11001, 11999):
        with pytest.raises(ValueError):
            validate_phase3_engineering_seed(seed)


def test_phase3_engineering_matrix_contains_only_reserved_engineering_seed():
    assert ENGINEERING_SEED == 29300
    assert len(ENGINEERING_CONDITIONS) == 6
    assert {int(condition[-1]) for condition in ENGINEERING_CONDITIONS} == {29300}

    blocked = set(range(29301, 29311)) | set(range(11001, 12000))
    blocked |= {29001, 29101, 29102, 29103, 29104, 29105, 29201, 29202, 29203, 29204, 29205}
    assert not ({int(condition[-1]) for condition in ENGINEERING_CONDITIONS} & blocked)
