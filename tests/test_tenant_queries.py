from datetime import date
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.services.leases import overlapping_lease_query


def test_overlap_query_always_scopes_the_organization() -> None:
    query = overlapping_lease_query(
        organization_id=uuid4(),
        unit_id=uuid4(),
        starts_on=date(2026, 1, 1),
        ends_on=None,
    )
    compiled = str(query.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
    assert "leases.organization_id" in compiled
