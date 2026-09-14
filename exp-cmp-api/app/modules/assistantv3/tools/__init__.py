"""Point d'assemblage : import de chaque module business declenche son
auto-enregistrement (tools + business module + eventuels field types
propres). Ajouter un business = un fichier ici + une ligne d'import,
rien d'autre a modifier dans le reste du package.
"""
from app.modules.assistantv3.tools import core_tools  # noqa: F401
from app.modules.assistantv3.tools import insurance_tools  # noqa: F401
from app.modules.assistantv3.tools import poultry_tools  # noqa: F401
