INTENTS = {
    "create_client": {
        "label": "Creer un client",
        "example": "Creer un client Moussa Camara",
        "keywords": [
            "nouveau client",
            "nouvelle cliente",
            "creer un client",
            "creer la cliente",
            "enregistrer un client",
            "ajouter un client",
            "inscrire un client",
            "creer client",
        ],
        "required": ["client"],
        "optional": ["phone", "client_number"],
    },
    "create_contract": {
        "label": "Creer un contrat",
        "example": "Nouveau contrat pour Tagoun, matricule MAT-100, prime 100 000",
        "keywords": [
            "nouveau contrat",
            "nouvelle police",
            "creer un contrat",
            "creer la police",
            "creer contrat",
            "assurer le client",
            "assurer la cliente",
            "etablir une police",
        ],
        "required": ["client", "matricule", "premium"],
    },
    "record_payment": {
        "label": "Encaisser une prime",
        "example": "Encaisser 40 000 de Tagoun pour le contrat MAT-E2E",
        "keywords": [
            "encaisser",
            "encaissement",
            "paiement",
            "payer",
            "paye",
            "a regle",
            "regle",
            "regler",
            "verser",
            "verse",
            "recu",
            "a recu",
            "toucher",
            "touche",
            "recuperer",
            "prime payee",
            "prime encaissee",
        ],
        "required": ["contract", "amount"],
        "required_extra": ["account", "category"],
    },
    "get_balance": {
        "label": "Consulter le solde d'une caisse",
        "example": "Solde de la caisse",
        "keywords": ["solde de la caisse", "solde du compte", "combien reste t il dans", "combien reste-t-il dans", "solde"],
    },
    "get_remaining": {
        "label": "Reste a payer d'un contrat",
        "example": "Reste a payer du contrat MAT-E2E",
        "keywords": ["reste a payer", "reste du contrat", "combien doit", "reste"],
    },
    "get_client_info": {
        "label": "Consulter les infos d'un client",
        "example": "Infos du client Tagoun",
        "keywords": ["infos du client", "information du client", "donnees du client", "qui est le client"],
    },
    "get_contract_info": {
        "label": "Consulter les infos d'un contrat",
        "example": "Infos du contrat MAT-E2E",
        "keywords": ["infos du contrat", "information du contrat", "details du contrat", "detail du contrat", "etat du contrat"],
    },
    "get_dues": {
        "label": "Consulter les echeances",
        "example": "Echeances du contrat MAT-100",
        "keywords": [
            "echeances en retard",
            "prochaine echeance",
            "quelles echeances",
            "echeancier",
            "echeances a venir",
            "voir les echeances",
            "liste des echeances",
            "echeances du contrat",
            "echeances de",
        ],
    },
    "add_due": {
        "label": "Ajouter une echeance",
        "example": "Ajouter une echeance pour MAT-100 le 30/09 montant 20000",
        "keywords": [
            "ajouter une echeance",
            "nouvelle echeance",
            "creer une echeance",
            "programmer une echeance",
            "prevoir une echeance",
            "planifier une echeance",
        ],
        "required": ["contract", "due_date", "amount"],
    },
    "add_purchase": {
        "label": "Enregistrer un approvisionnement (poulailler)",
        "example": "J'ai achete 24 poulets a 120000",
        "keywords": [
            "j'ai achete",
            "jai achete",
            "achat de poulets",
            "acheter des poulets",
            "nouvel approvisionnement",
        ],
        "required": ["quantity", "amount", "account", "category"],
    },
    "add_sale": {
        "label": "Enregistrer une vente (poulailler)",
        "example": "J'ai vendu 8 poulets pour 60000",
        "keywords": [
            "j'ai vendu",
            "jai vendu",
            "vente de poulets",
            "vendre des poulets",
        ],
        "required": ["quantity", "amount", "account", "category"],
    },
    "get_stock": {
        "label": "Consulter le stock de poulets",
        "example": "Combien de poulets me reste-t-il ?",
        "keywords": [
            "combien de poulets",
            "stock de poulets",
            "poulets restants",
            "poulets disponibles",
        ],
    },
    "help": {
        "label": "Aide",
        "example": "aide",
        "keywords": ["aide", "help", "que peux tu", "que sais tu", "commandes"],
    },
}

INTENT_LABELS = {op: meta["label"] for op, meta in INTENTS.items()}

POULTRY_OPS = {"add_purchase", "add_sale", "get_stock"}
INSURANCE_OPS = {
    "create_client",
    "create_contract",
    "record_payment",
    "get_remaining",
    "get_client_info",
    "get_contract_info",
    "get_dues",
    "add_due",
}


BUSINESS_ALIASES = {
    "poulets": {"poulet", "poulailler", "poulaillers", "poules", "poule"},
    "vtc": {"voiture", "chauffeur", "taxi", "transport"},
}


def business_code_for(operation: str, requested: str | None = None) -> str:
    """Determine l'activite concernee par une operation. Les operations propres a
    un module (assurance/poulets) sont routees directement ; les operations
    transverses (get_balance, help) suivent ce que l'utilisateur a precise, avec
    'assurance' comme repli par defaut. Les alias non normalises en provenance du
    LLM (ex. « poulailler ») sont ramenes au code d'activite."""
    if operation in POULTRY_OPS:
        return "poulets"
    if operation in INSURANCE_OPS:
        return "assurance"
    if requested:
        norm = requested.strip().casefold()
        for code, aliases in BUSINESS_ALIASES.items():
            if norm == code or norm in aliases:
                return code
    return requested or "assurance"