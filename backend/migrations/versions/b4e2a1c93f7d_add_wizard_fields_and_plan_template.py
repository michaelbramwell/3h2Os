"""Add wizard fields and plan template table

Revision ID: b4e2a1c93f7d
Revises: 9a4ad7fe5e8e
Create Date: 2026-02-10 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "b4e2a1c93f7d"
down_revision: Union[str, None] = "9a4ad7fe5e8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # RunnerProfile new columns
    with op.batch_alter_table("runnerprofile") as batch_op:
        batch_op.add_column(sa.Column("weight_kg", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "experience_level", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "events_completed_json",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "pain_points_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("weekly_availability", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("longest_recent_distance_m", sa.Integer(), nullable=True)
        )

    # RunnerProject new columns
    with op.batch_alter_table("runnerproject") as batch_op:
        batch_op.add_column(
            sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("target_time", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("primary_goal", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    # PlanTemplate table
    op.create_table(
        "plantemplate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sport", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("level", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("default_weeks", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("structure_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("plantemplate")

    with op.batch_alter_table("runnerproject") as batch_op:
        batch_op.drop_column("primary_goal")
        batch_op.drop_column("target_time")
        batch_op.drop_column("event_type")

    with op.batch_alter_table("runnerprofile") as batch_op:
        batch_op.drop_column("longest_recent_distance_m")
        batch_op.drop_column("weekly_availability")
        batch_op.drop_column("pain_points_json")
        batch_op.drop_column("events_completed_json")
        batch_op.drop_column("experience_level")
        batch_op.drop_column("weight_kg")
