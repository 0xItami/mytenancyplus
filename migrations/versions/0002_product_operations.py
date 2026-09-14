"""Add sessions, billing, maintenance, documents, and notifications."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0002_product_operations"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "subscriptions",
    "work_orders",
    "work_order_comments",
    "documents",
    "notifications",
)

subscription_plan = sa.Enum(
    "STARTER", "GROWTH", "SCALE", name="subscriptionplan", native_enum=False
)
subscription_status = sa.Enum(
    "TRIALING",
    "ACTIVE",
    "PAST_DUE",
    "CANCELLED",
    name="subscriptionstatus",
    native_enum=False,
)
work_order_priority = sa.Enum(
    "LOW", "NORMAL", "HIGH", "URGENT", name="workorderpriority", native_enum=False
)
work_order_status = sa.Enum(
    "OPEN",
    "TRIAGED",
    "IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
    "CANCELLED",
    name="workorderstatus",
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
        "refresh_sessions",
        *identifiers(),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "replaced_by_id",
            sa.Uuid(),
            sa.ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("ip_address", sa.String(64)),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])

    op.create_table(
        "subscriptions",
        *identifiers(),
        organization_id(),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_customer_id", sa.String(160), unique=True),
        sa.Column("provider_subscription_id", sa.String(160), unique=True),
        sa.Column("plan", subscription_plan, nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])

    op.create_table(
        "webhook_receipts",
        *identifiers(),
        sa.Column("provider_event_id", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("processing_status", sa.String(20), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.String(500)),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_webhook_receipts_provider_event_id",
        "webhook_receipts",
        ["provider_event_id"],
        unique=True,
    )
    op.create_index("ix_webhook_receipts_organization_id", "webhook_receipts", ["organization_id"])

    op.create_table(
        "work_orders",
        *identifiers(),
        organization_id(),
        sa.Column("property_id", sa.Uuid(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("unit_id", sa.Uuid(), sa.ForeignKey("units.id")),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", work_order_priority, nullable=False),
        sa.Column("status", work_order_status, nullable=False),
        sa.Column("reported_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_work_orders_organization_id", "work_orders", ["organization_id"])
    op.create_index("ix_work_orders_property_id", "work_orders", ["property_id"])
    op.create_index("ix_work_orders_unit_id", "work_orders", ["unit_id"])
    op.create_index("ix_work_orders_assigned_to_id", "work_orders", ["assigned_to_id"])

    op.create_table(
        "work_order_comments",
        *identifiers(),
        organization_id(),
        sa.Column(
            "work_order_id",
            sa.Uuid(),
            sa.ForeignKey("work_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_work_order_comments_organization_id", "work_order_comments", ["organization_id"]
    )
    op.create_index(
        "ix_work_order_comments_work_order_id", "work_order_comments", ["work_order_id"]
    )

    op.create_table(
        "documents",
        *identifiers(),
        organization_id(),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_resource_id", "documents", ["resource_id"])

    op.create_table(
        "notifications",
        *identifiers(),
        organization_id(),
        sa.Column("recipient_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(80)),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])

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
        "notifications",
        "documents",
        "work_order_comments",
        "work_orders",
        "webhook_receipts",
        "subscriptions",
        "refresh_sessions",
    ):
        op.drop_table(table)
