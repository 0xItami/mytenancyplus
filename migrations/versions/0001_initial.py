"""Create the initial multi-tenant schema and isolation policies."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "properties",
    "units",
    "tenant_profiles",
    "leases",
    "invitations",
    "audit_logs",
)

membership_role = sa.Enum(
    "OWNER",
    "ADMIN",
    "MANAGER",
    "VIEWER",
    name="membershiprole",
    native_enum=False,
)
membership_status = sa.Enum(
    "ACTIVE",
    "SUSPENDED",
    name="membershipstatus",
    native_enum=False,
)
lease_status = sa.Enum(
    "DRAFT",
    "ACTIVE",
    "ENDED",
    "CANCELLED",
    name="leasestatus",
    native_enum=False,
)


def identifiers() -> tuple[sa.Column[object], sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def organization_id() -> sa.Column[object]:
    return sa.Column(
        "organization_id",
        sa.Uuid(),
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        *identifiers(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "organizations",
        *identifiers(),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "memberships",
        *identifiers(),
        organization_id(),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("status", membership_status, nullable=False),
        sa.UniqueConstraint("organization_id", "user_id"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "properties",
        *identifiers(),
        organization_id(),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("address_line", sa.String(300), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
    )
    op.create_index("ix_properties_organization_id", "properties", ["organization_id"])

    op.create_table(
        "units",
        *identifiers(),
        organization_id(),
        sa.Column(
            "property_id",
            sa.Uuid(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("monthly_rent", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("property_id", "label"),
    )
    op.create_index("ix_units_organization_id", "units", ["organization_id"])
    op.create_index("ix_units_property_id", "units", ["property_id"])

    op.create_table(
        "tenant_profiles",
        *identifiers(),
        organization_id(),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(40)),
    )
    op.create_index("ix_tenant_profiles_organization_id", "tenant_profiles", ["organization_id"])
    op.create_index("ix_tenant_profiles_email", "tenant_profiles", ["email"])

    op.create_table(
        "leases",
        *identifiers(),
        organization_id(),
        sa.Column("unit_id", sa.Uuid(), sa.ForeignKey("units.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant_profiles.id"), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date()),
        sa.Column("monthly_rent", sa.Numeric(14, 2), nullable=False),
        sa.Column("deposit", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", lease_status, nullable=False),
    )
    op.create_index("ix_leases_organization_id", "leases", ["organization_id"])
    op.create_index("ix_leases_unit_id", "leases", ["unit_id"])
    op.create_index("ix_leases_tenant_id", "leases", ["tenant_id"])

    op.create_table(
        "invitations",
        *identifiers(),
        organization_id(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_invitations_organization_id", "invitations", ["organization_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        organization_id(),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])

    op.create_table(
        "outbox_events",
        *identifiers(),
        organization_id(),
        sa.Column("topic", sa.String(160), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
    )
    op.create_index("ix_outbox_events_organization_id", "outbox_events", ["organization_id"])
    op.create_index("ix_outbox_events_topic", "outbox_events", ["topic"])

    if op.get_bind().dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(
                f'''CREATE POLICY tenant_isolation ON "{table}"
                    USING (organization_id = NULLIF(
                        current_setting('app.current_organization_id', true), ''
                    )::uuid)
                    WITH CHECK (organization_id = NULLIF(
                        current_setting('app.current_organization_id', true), ''
                    )::uuid)'''
            )


def downgrade() -> None:
    for table in (
        "outbox_events",
        "audit_logs",
        "invitations",
        "leases",
        "tenant_profiles",
        "units",
        "properties",
        "memberships",
        "organizations",
        "users",
    ):
        op.drop_table(table)
