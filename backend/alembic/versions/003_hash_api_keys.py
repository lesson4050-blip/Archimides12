"""Hash existing API keys in database."""
from alembic import op
import sqlalchemy as sa
import hashlib

revision = '003'
down_revision = '002'

def upgrade():
    conn = op.get_bind()
    # Hash all existing plaintext API keys
    result = conn.execute(sa.text("SELECT id, api_key FROM users WHERE api_key IS NOT NULL"))
    for row in result:
        if row.api_key and len(row.api_key) != 64:  # Not already hashed
            hashed = hashlib.sha256(row.api_key.encode()).hexdigest()
            conn.execute(
                sa.text("UPDATE users SET api_key = :h WHERE id = :id"),
                {"h": hashed, "id": row.id}
            )

def downgrade():
    pass  # Cannot unhash — irreversible by design
