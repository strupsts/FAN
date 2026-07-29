"""add users and user preferences

Revision ID: d2604d482290
Revises: 798d68731784
Create Date: 2026-07-29 15:57:27.186508

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2604d482290"
down_revision: Union[str, Sequence[str], None] = "798d68731784"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEV_USER_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_preferences",
        sa.Column(
            "user_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "interface_language",
            sa.String(length=35),
            nullable=False,
        ),
        sa.Column(
            "formatting_locale",
            sa.String(length=35),
            nullable=False,
        ),
        sa.Column(
            "home_country",
            sa.String(length=2),
            nullable=False,
        ),
        sa.Column(
            "default_receipt_currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "reporting_currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "time_zone",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_preferences_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # Preserve every user identifier already referenced by existing data.
    op.execute(
        """
        INSERT INTO users (id, created_at)
        SELECT existing_users.user_id, CURRENT_TIMESTAMP
        FROM (
            SELECT user_id FROM receipts
            UNION
            SELECT user_id FROM receipt_predictions
            UNION
            SELECT user_id FROM training_samples
        ) AS existing_users
        ON CONFLICT (id) DO NOTHING
        """
    )

    # Ensure the configured local development user always exists.
    op.execute(
        f"""
        INSERT INTO users (id, created_at)
        VALUES (
            '{DEV_USER_ID}'::uuid,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    # Bootstrap local development preferences explicitly.
    op.execute(
        f"""
        INSERT INTO user_preferences (
            user_id,
            interface_language,
            formatting_locale,
            home_country,
            default_receipt_currency,
            reporting_currency,
            time_zone,
            onboarding_completed,
            updated_at
        )
        VALUES (
            '{DEV_USER_ID}'::uuid,
            'en',
            'en-CA',
            'CA',
            'CAD',
            'CAD',
            'America/Edmonton',
            FALSE,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (user_id) DO NOTHING
        """
    )

    # Foreign keys are added only after existing user IDs were migrated.
    op.create_foreign_key(
        "fk_receipt_predictions_user",
        "receipt_predictions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_receipts_user",
        "receipts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_training_samples_user",
        "training_samples",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_training_samples_user",
        "training_samples",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_receipts_user",
        "receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_receipt_predictions_user",
        "receipt_predictions",
        type_="foreignkey",
    )

    op.drop_table("user_preferences")
    op.drop_table("users")
