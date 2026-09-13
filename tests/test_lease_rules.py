from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.property import LeaseCreate
from app.services.leases import date_ranges_overlap


@pytest.mark.parametrize(
    ("first_start", "first_end", "second_start", "second_end", "expected"),
    [
        (date(2026, 1, 1), date(2026, 1, 31), date(2026, 2, 1), None, False),
        (date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31), None, True),
        (date(2026, 1, 1), None, date(2030, 1, 1), None, True),
    ],
)
def test_date_range_overlap(
    first_start: date,
    first_end: date | None,
    second_start: date,
    second_end: date | None,
    expected: bool,
) -> None:
    assert date_ranges_overlap(first_start, first_end, second_start, second_end) is expected


def test_lease_rejects_an_end_before_its_start() -> None:
    with pytest.raises(ValidationError):
        LeaseCreate(
            unit_id=uuid4(),
            tenant_id=uuid4(),
            starts_on=date(2026, 5, 2),
            ends_on=date(2026, 5, 1),
            monthly_rent="2000",
            deposit="1000",
        )
