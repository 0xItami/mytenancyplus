import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

ADMIN_DATABASE_URL = os.getenv("MTP_INTEGRATION_ADMIN_DATABASE_URL")
APP_DATABASE_URL = os.getenv("MTP_INTEGRATION_APP_DATABASE_URL")

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not ADMIN_DATABASE_URL or not APP_DATABASE_URL,
    reason="PostgreSQL integration database URLs are not configured",
)
async def test_postgres_row_level_security_enforces_tenant_context() -> None:
    assert ADMIN_DATABASE_URL is not None
    assert APP_DATABASE_URL is not None
    admin_engine = create_async_engine(ADMIN_DATABASE_URL)
    app_engine = create_async_engine(APP_DATABASE_URL)
    user_id = uuid4()
    first_organization_id = uuid4()
    second_organization_id = uuid4()
    first_property_id = uuid4()
    second_property_id = uuid4()
    now = datetime.now(UTC)

    try:
        async with admin_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    DO $block$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mytenancyplus') THEN
                            CREATE ROLE mytenancyplus LOGIN PASSWORD 'mytenancyplus'
                                NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
                        END IF;
                    END
                    $block$;
                    """
                )
            )
            await connection.execute(text("GRANT USAGE ON SCHEMA public TO mytenancyplus"))
            await connection.execute(
                text(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                    "TO mytenancyplus"
                )
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO users
                        (id, created_at, updated_at, email, full_name, password_hash, is_active)
                    VALUES (:id, :now, :now, :email, 'RLS Test User', 'not-used', true)
                    """
                ),
                {"id": user_id, "now": now, "email": f"rls-{user_id}@example.com"},
            )
            for organization_id, name in (
                (first_organization_id, "First isolated workspace"),
                (second_organization_id, "Second isolated workspace"),
            ):
                await connection.execute(
                    text(
                        """
                        INSERT INTO organizations
                            (id, created_at, updated_at, name, slug, created_by_id)
                        VALUES (:id, :now, :now, :name, :slug, :user_id)
                        """
                    ),
                    {
                        "id": organization_id,
                        "now": now,
                        "name": name,
                        "slug": str(organization_id),
                        "user_id": user_id,
                    },
                )

        async with app_engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.current_organization_id', :id, true)"),
                {"id": str(first_organization_id)},
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO properties
                        (id, created_at, updated_at, organization_id, name,
                         address_line, city, country_code)
                    VALUES (:id, :now, :now, :organization_id, 'First House',
                            '1 Isolation Way', 'Lagos', 'NG')
                    """
                ),
                {
                    "id": first_property_id,
                    "now": now,
                    "organization_id": first_organization_id,
                },
            )

        async with app_engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.current_organization_id', :id, true)"),
                {"id": str(second_organization_id)},
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO properties
                        (id, created_at, updated_at, organization_id, name,
                         address_line, city, country_code)
                    VALUES (:id, :now, :now, :organization_id, 'Second House',
                            '2 Isolation Way', 'Abuja', 'NG')
                    """
                ),
                {
                    "id": second_property_id,
                    "now": now,
                    "organization_id": second_organization_id,
                },
            )

        async with app_engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.current_organization_id', :id, true)"),
                {"id": str(first_organization_id)},
            )
            visible_names = list(
                (await connection.execute(text("SELECT name FROM properties"))).scalars()
            )
            assert visible_names == ["First House"]

        with pytest.raises(DBAPIError):
            async with app_engine.begin() as connection:
                await connection.execute(
                    text("SELECT set_config('app.current_organization_id', :id, true)"),
                    {"id": str(first_organization_id)},
                )
                await connection.execute(
                    text(
                        """
                        INSERT INTO properties
                            (id, created_at, updated_at, organization_id, name,
                             address_line, city, country_code)
                        VALUES (:id, :now, :now, :organization_id, 'Forbidden House',
                                '3 Isolation Way', 'Lagos', 'NG')
                        """
                    ),
                    {
                        "id": uuid4(),
                        "now": now,
                        "organization_id": second_organization_id,
                    },
                )

        async with app_engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.current_organization_id', '', true)")
            )
            assert await connection.scalar(text("SELECT count(*) FROM properties")) == 0
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
