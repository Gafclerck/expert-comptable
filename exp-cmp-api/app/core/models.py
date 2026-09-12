"""Agregateur des modeles SQLAlchemy.

Ce module importe tous les modeles des modules livres afin de remplir
completerement `Base.metadata`: il sert de cible pour les migrations Alembic
(`env.py`) et garantit l'equivalence exacte avec `Base.metadata.create_all`
utilise par les tests (voir `tests/conftest.py`).
"""

from app.core.base import Base
import app.modules.identity.models  # noqa: F401
import app.modules.ledger.models  # noqa: F401
import app.modules.audit.models  # noqa: F401
import app.modules.insurance.models  # noqa: F401
import app.modules.poultry.models  # noqa: F401
import app.modules.vtc.models  # noqa: F401
import app.modules.assistantv2.telegram.models  # noqa: F401

__all__ = ["Base"]
