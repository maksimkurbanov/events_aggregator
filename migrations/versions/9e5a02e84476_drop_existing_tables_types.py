"""drop existing tables, types

Revision ID: 9e5a02e84476
Revises: 4474e8a34eb4
Create Date: 2026-03-18 18:25:07.457035

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "9e5a02e84476"
down_revision: Union[str, Sequence[str], None] = "a2478a380803"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Step 2: Drop all user tables
    # Get all table names from the public schema (adjust schema if needed)
    conn = op.get_bind()
    result = conn.execute(
        text("""
             SELECT tablename
             FROM pg_tables
             WHERE schemaname = 'public'
             """)
    )
    tables = [row[0] for row in result]

    # Drop tables in reverse order to handle foreign key dependencies
    # (simple approach: drop with CASCADE)
    for table in tables:
        op.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))

    # Step 3: Drop custom ENUM types
    result = conn.execute(
        text("""
             SELECT typname
             FROM pg_type
             WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
               AND typtype = 'e'
             """)
    )
    enum_types = [row[0] for row in result]
    for enum in enum_types:
        op.execute(text(f"DROP TYPE IF EXISTS {enum} CASCADE;"))

    # Optional: If you also want to drop sequences, indexes, etc., they are automatically
    # removed when their owning tables are dropped with CASCADE. However, if you have
    # standalone sequences, you can drop them similarly:
    # result = conn.execute(text("SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'"))
    # for seq in result:
    #     op.execute(text(f"DROP SEQUENCE IF EXISTS {seq[0]} CASCADE;"))


def downgrade() -> None:
    """Downgrade schema."""
    pass
