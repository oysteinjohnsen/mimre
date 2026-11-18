import pytest

from app.schemas import validate_birthdate


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [
        (None, None, None),
        (2019, None, None),
        (None, 3, 14),
        (None, 2, 29),  # unknown year: 29 Feb is allowed
        (2020, 2, 29),
        (1980, 12, 31),
    ],
)
def test_valid(year, month, day):
    validate_birthdate(year, month, day)


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [
        (None, None, 5),  # day without month
        (2019, 2, 29),  # not a leap year
        (None, 4, 31),
        (9999, None, None),  # future
    ],
)
def test_invalid(year, month, day):
    with pytest.raises(ValueError):
        validate_birthdate(year, month, day)
