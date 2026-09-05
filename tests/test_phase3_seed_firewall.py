import pytest

from fedfalsify.phase3_engineering_runner import validate_phase3_engineering_seed


def test_phase3_engineering_seed_allows_only_29300():
    validate_phase3_engineering_seed(29300)
    for seed in (29001, 29101, 29105, 29201, 29205, 29301, 29310, 11001, 11999):
        with pytest.raises(ValueError):
            validate_phase3_engineering_seed(seed)
