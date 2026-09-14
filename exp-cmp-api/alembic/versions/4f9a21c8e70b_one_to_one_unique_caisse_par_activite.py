"""one-to-one : une activite = une seule caisse (unique sur accounts.business_id)

Revision ID: 4f9a21c8e70b
Revises: 0f8af265b393
Create Date: 2026-09-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f9a21c8e70b'
down_revision: Union[str, None] = '0f8af265b393'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Defense : ne jamais appliquer la contrainte sur des donnees encore
    # multi-comptes. Consolider d'abord (re-pointage transactions/transfers,
    # suppression des transferts intra-fusion et des comptes absorbes).
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT business_id, COUNT(*) AS compte FROM accounts "
            "GROUP BY business_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicates:
        details = ", ".join(f"{row.business_id} (x{row.compte})" for row in duplicates)
        raise RuntimeError(
            "Contrainte one-to-one refusee : activites encore multi-comptes -> "
            f"{details}. Consolidez les comptes avant d'appliquer la migration."
        )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("accounts") as batch_op:
            batch_op.create_unique_constraint("uq_accounts_business_id", ["business_id"])
    else:
        op.create_unique_constraint("uq_accounts_business_id", "accounts", ["business_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("accounts") as batch_op:
            batch_op.drop_constraint("uq_accounts_business_id", type_="unique")
    else:
        op.drop_constraint("uq_accounts_business_id", "accounts", type_="unique")