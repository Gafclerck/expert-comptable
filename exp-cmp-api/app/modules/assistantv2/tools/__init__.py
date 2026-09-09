"""Point d'assemblage du registre d'outils : SEUL endroit a modifier pour
brancher un nouveau business sur l'assistant v2. Chaque import declenche
l'auto-enregistrement des outils du module (voir le `_register()` en bas de
chaque fichier `*_tools.py`).

Pour ajouter un business :
  1. Creer app/modules/assistantv2/tools/<business>_tools.py sur le modele de
     poultry_tools.py (outils propres a ce business) et/ou insurance_tools.py.
  2. Ajouter une ligne d'import ci-dessous.
Rien d'autre a modifier : registry.py, orchestrator.py et core_tools.py
(get_balance, help) restent inchanges.
"""
from app.modules.assistantv2.tools import core_tools  # noqa: F401
from app.modules.assistantv2.tools import insurance_tools  # noqa: F401
from app.modules.assistantv2.tools import poultry_tools  # noqa: F401
