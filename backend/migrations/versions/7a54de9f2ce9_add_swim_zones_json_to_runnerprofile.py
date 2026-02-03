"""Add swim_zones_json to RunnerProfile

Revision ID: 7a54de9f2ce9
Revises: ee4e0186557f
Create Date: 2026-01-28 23:12:12.223683

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a54de9f2ce9"
down_revision: Union[str, Sequence[str], None] = "ee4e0186557f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op upgrade.

    This migration was originally generated to add the ``swim_zones_json``
    column to ``RunnerProfile``. The column, however, was already created
    in a different migration (see revision ``1da6be737fa1``), so applying
    any schema changes here would be redundant.

    The revision is kept as an intentional placeholder to preserve Alembic's
    linear migration history and to avoid conflicts with existing databases.
    """


def downgrade() -> None:
    """No-op downgrade.

    Because this revision does not apply any schema changes (the relevant
    column was added in migration ``1da6be737fa1``), there is nothing to
    revert here. This function is intentionally left empty as part of a
    documented placeholder migration.
    """
