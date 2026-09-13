"""Detection deterministe d'intentions d'enregistrement (fallback).

L'orchestrateur s'appuie sur le LLM pour choisir les outils. Sur une phrase
d'intention nue (ex. « nouvelle voiture »), certains modeles n'appellent aucun
outil (reflexe : « il manque des informations ») et le tour se termine sur
« Je n'ai pas compris ». Ce module est le filet de securite : il reconnait les
declarations evidentes et les re-injecte sous forme de step a parametres
vides, la boucle standard de clarification s'occupant du reste (champ par
champ : marque, modele, immatriculation, prix...).

Detection : presence conjointe d'un motif « sujet » et d'un signal de
declaration. Volontairement conservateur (pas de faux positif) : si aucun motif
ne matche, l'assistant reste muet (le LLM a deja eu sa chance).
"""
from __future__ import annotations

from app.modules.assistantv2 import parsing

# Sujets par outil de declaration (chaines normalisees : sans accents, minuscules).
_SUBJECTS: dict[str, set[str]] = {
    "create_vehicule": {"voiture", "voitures", "vehicule", "vehicules", "auto"},
    "create_chauffeur": {"chauffeur", "chauffeurs", "conducteur", "conducteurs"},
}

# Signaux forts de declaration (creation/enregistrement), communs a tous.
# « acheter » est volontairement exclu : ambigu (pourrait etre une depense,
# pas la creation d'un vehicule).
_DECL_SIGNALS = {
    "nouvelle", "nouveau", "nouvel", "nouvelles", "nouveaux",
    "enregistr", "ajouter", "ajoute", "ajout", "creer", "cree", "creons",
}

# Signaux qui annulent une declaration : requete de consultation/liste ou
# interrogation (ex. « montre moi les nouvelles voitures » = liste, pas une
# creation). La presence d'un signal de liste >> un signal de declaration.
_LIST_SIGNALS = {
    "montre", "montrer", "liste", "lister", "lister", "affiche", "afficher",
    "quels", "quelles", "quel", "quelle", "combien", "toutes", "tous",
    "historique", "etat", "solde", "reste",
}


def detect_declaration(message: str) -> str | None:
    """Retourne l'outil de declaration correspondant a la phrase, ou None.

    Ne se declenche que si la phrase contient a la fois un signal de
    declaration et un objet connu d'un outil, sans signal de consultation.
    """
    norm = parsing.normalize(message)
    if not norm:
        return None
    tokens = set(norm.split())
    if tokens & _LIST_SIGNALS:
        return None
    if not (tokens & _DECL_SIGNALS):
        return None
    for tool, subjects in _SUBJECTS.items():
        if tokens & subjects:
            return tool
    return None