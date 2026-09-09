import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.modules.assistant.intents import INTENTS, business_code_for
from app.modules.assistant.schemas import IntentCommand

_AMOUNT_RE = re.compile(
    r"(?<![A-Za-z0-9-])(\d{1,3}(?:[\s\u00A0.]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?![A-Za-z0-9])"
)
_MATRICULE_KEYWORD_RE = re.compile(r"\bmatricule\s+?(?:num[eé]ro\s+)?([A-Z]{2,5})[-_ ]?([A-Z0-9]+)\b", re.IGNORECASE)
_MATRICULE_PLAIN_RE = re.compile(r"\b([A-Za-z]{2,5})[-_]([A-Za-z0-9]+)\b")
_CLIENT_NUMBER_RE = re.compile(r"\bCLI[-_ ]?\d+\b", re.IGNORECASE)
_NAME_STOPWORDS = {
    "svp",
    "merci",
    "telephone",
    "numero",
    "matricule",
    "prime",
    "contrat",
    "paiement",
    "encaisser",
    "compte",
    "caisse",
    "categorie",
    "sur",
    "avec",
    "pour",
    "de",
    "du",
    "et",
    "le",
    "la",
    "les",
    "un",
    "une",
}


def _normalize(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(ch) != "Mn"
    ).strip()


def _keyword_hit(norm: str, keyword: str) -> bool:
    if keyword in norm:
        return True
    for suffix in ("er", "re", "ir"):
        if keyword.endswith(suffix) and keyword[: -len(suffix)] in norm:
            return True
    return False


def parse_amount(text: str) -> Decimal | None:
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    raw = match.group(1).replace("\u00a0", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(",", ".")
    elif "." in raw:
        parts = raw.split(".")
        if len(parts) >= 2 and parts[-1] and len(parts[-1]) == 3 and len(parts[-2]) == 3:
            raw = raw.replace(".", "")
    return Decimal(raw or "0")


def parse_matricule(text: str) -> str | None:
    match = _MATRICULE_KEYWORD_RE.search(text)
    if match:
        return f"{match.group(1).upper()}-{match.group(2).upper()}"
    match = _MATRICULE_PLAIN_RE.search(text)
    if not match or match.group(1).upper() == "CLI":
        return None
    return f"{match.group(1).upper()}-{match.group(2).upper()}"


def parse_client_number(text: str) -> str | None:
    match = _CLIENT_NUMBER_RE.search(text)
    if not match:
        return None
    return re.sub(r"[\s_]", "-", match.group(0)).upper()


_MONTHS_FR = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}
_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b")
_DATE_TEXT_RE = re.compile(
    r"\b(\d{1,2})\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)(?:\s+(\d{4}))?\b"
)
_QUANTITY_RE = re.compile(r"\b(\d+)\s*poulets?\b", re.IGNORECASE)


def parse_quantity(text: str) -> int | None:
    match = _QUANTITY_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


def parse_quantity_and_amount(text: str) -> tuple[int | None, Decimal | None]:
    """Extrait '24 poulets ... 120000' : la quantite est ancree au mot 'poulet(s)',
    le montant est cherche apres (puis avant, en repli) pour ne jamais reprendre
    le chiffre de la quantite elle-meme comme montant.
    """
    match = _QUANTITY_RE.search(text)
    if not match:
        return None, parse_amount(text)
    quantity = int(match.group(1))
    amount = parse_amount(text[match.end():]) or parse_amount(text[: match.start()])
    return quantity, amount


def parse_due_date(text: str) -> date | None:
    norm = _normalize(text)
    match = _DATE_TEXT_RE.search(norm)
    if match:
        day = int(match.group(1))
        month = _MONTHS_FR[match.group(2)]
        year = int(match.group(3)) if match.group(3) else date.today().year
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = _DATE_NUMERIC_RE.search(text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year_raw = match.group(3)
        year = int(year_raw) if year_raw else date.today().year
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


_CLEAN_NAME_PATTERN = re.compile(r"([a-z][a-z' -]{0,60}?)(?=\s+(?:svp|merci|telephone|numero)|[,;.!?]|$)")


def _clean_name(value: str) -> str | None:
    cleaned = _CLEAN_NAME_PATTERN.match(_normalize(value))
    if not cleaned:
        return None
    name = cleaned.group(1).strip()
    tokens = [t for t in name.split() if t not in _NAME_STOPWORDS]
    return " ".join(tokens) if tokens else None


def extract_client_name(text: str, pour: bool = False) -> str | None:
    quoted = re.search(r"[\"']([^\"']+)[\"']", text)
    if quoted:
        return _clean_name(quoted.group(1))
    norm = _normalize(text)
    prefixes = ("pour le client", "pour la cliente", "du client", "de la part de", "au client", "a la cliente")
    if pour:
        prefixes = prefixes + ("pour",)
    for prefix in prefixes:
        idx = norm.find(prefix)
        if idx >= 0:
            return _clean_name(norm[idx + len(prefix):])
    for prefix in ("client", "cliente"):
        idx = norm.find(prefix)
        if idx >= 0:
            return _clean_name(norm[idx + len(prefix):])
    return None


def extract_contract_ref(text: str) -> str | None:
    matricule = parse_matricule(text)
    if matricule:
        return matricule
    number = parse_client_number(text)
    if number:
        return number
    return extract_client_name(text)


def detect_operation(norm: str) -> str | None:
    for operation in (
        "get_balance", "get_stock", "get_remaining", "get_client_info", "get_contract_info",
        "get_dues", "help",
    ):
        if any(_keyword_hit(norm, kw) for kw in INTENTS[operation]["keywords"]):
            return operation
    for operation in ("create_contract", "create_client", "record_payment", "add_due", "add_purchase", "add_sale"):
        if any(_keyword_hit(norm, kw) for kw in INTENTS[operation]["keywords"]):
            return operation
    return None


class IntentInterpreter(Protocol):
    def interpret(self, message: str) -> IntentCommand:
        ...


class RuleInterpreter:
    def interpret(self, message: str) -> IntentCommand:
        norm = _normalize(message)
        operation = detect_operation(norm)
        if operation is None:
            return IntentCommand(operation="unknown", params={}, confidence="low")
        params: dict = {}
        if _keyword_hit(norm, "assurance"):
            params["business"] = "assurance"
        elif _keyword_hit(norm, "poulet") or _keyword_hit(norm, "poulailler"):
            params["business"] = "poulets"
        if operation == "create_client":
            personnel = extract_client_name(message)
            if personnel:
                params["client"] = personnel
            number = parse_client_number(message)
            if number:
                params["client_number"] = number
        elif operation == "create_contract":
            personnel = extract_client_name(message, pour=True)
            if personnel:
                params["client"] = personnel
            matricule = parse_matricule(message)
            if matricule:
                params["matricule"] = matricule
            amount = parse_amount(message)
            if amount:
                params["premium"] = amount
        elif operation == "record_payment":
            ref = extract_contract_ref(message)
            if ref:
                params["contract"] = ref
            amount = parse_amount(message)
            if amount:
                params["amount"] = amount
        elif operation in ("get_remaining", "get_contract_info", "get_dues"):
            ref = extract_contract_ref(message)
            if ref:
                params["contract"] = ref
        elif operation == "add_due":
            ref = extract_contract_ref(message)
            if ref:
                params["contract"] = ref
            due_date = parse_due_date(message)
            if due_date:
                params["due_date"] = due_date
            date_match = _DATE_NUMERIC_RE.search(message)
            amount_source = (
                message[: date_match.start()] + " " + message[date_match.end():] if date_match else message
            )
            amount = parse_amount(amount_source)
            if amount:
                params["amount"] = amount
        elif operation in ("add_purchase", "add_sale"):
            quantity, amount = parse_quantity_and_amount(message)
            if quantity:
                params["quantity"] = quantity
            if amount:
                params["amount"] = amount
        elif operation in ("get_balance", "get_stock"):
            pass
        elif operation in ("get_client_info", "create_client"):
            personnel = extract_client_name(message)
            if personnel:
                params["client"] = personnel
        business = params.get("business") or "assurance"
        params.pop("business", None)
        confidence = "high" if params or operation in ("get_balance", "help") else "medium"
        return IntentCommand(operation=operation, business=business, params=params, confidence=confidence)


_TOOL_PARAM_SCHEMAS: dict[str, dict] = {
    "create_client": {
        "properties": {
            "client": {"type": "string", "description": "Nom complet du client"},
            "phone": {"type": "string", "description": "Numero de telephone (optionnel)"},
            "client_number": {"type": "string", "description": "Numero de client existant (optionnel)"},
        },
        "required": ["client"],
    },
    "create_contract": {
        "properties": {
            "client": {"type": "string", "description": "Nom du client"},
            "matricule": {"type": "string", "description": "Matricule du contrat, ex. MAT-100"},
            "premium": {"type": "number", "description": "Montant total de la prime"},
        },
        "required": ["client", "matricule", "premium"],
    },
    "record_payment": {
        "properties": {
            "contract": {"type": "string", "description": "Matricule du contrat ou nom du client"},
            "amount": {
                "type": "number",
                "description": "Montant encaisse. A omettre si le client paie tout ce qui reste (le systeme le deduira lui-meme).",
            },
            "account": {"type": "string", "description": "Nom de la caisse (optionnel s'il n'y en a qu'une)"},
            "category": {"type": "string", "description": "Categorie (optionnel s'il n'y en a qu'une)"},
        },
        "required": ["contract"],
    },
    "get_balance": {
        "properties": {
            "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
            "business": {
                "type": "string",
                "enum": ["assurance", "poulets", "vtc"],
                "description": "Activite concernee (optionnel, ex. assurance, poulets, vtc, poulailler)",
            },
        },
        "required": [],
    },
    "get_remaining": {
        "properties": {"contract": {"type": "string", "description": "Matricule du contrat ou nom du client"}},
        "required": ["contract"],
    },
    "get_client_info": {
        "properties": {"client": {"type": "string", "description": "Nom du client"}},
        "required": ["client"],
    },
    "get_contract_info": {
        "properties": {"contract": {"type": "string", "description": "Matricule du contrat ou nom du client"}},
        "required": ["contract"],
    },
    "get_dues": {
        "properties": {"contract": {"type": "string", "description": "Matricule du contrat ou nom du client"}},
        "required": ["contract"],
    },
    "add_due": {
        "properties": {
            "contract": {"type": "string", "description": "Matricule du contrat ou nom du client"},
            "due_date": {"type": "string", "description": "Date de l'echeance, format ISO AAAA-MM-JJ"},
            "amount": {"type": "number", "description": "Montant prevu pour cette echeance"},
        },
        "required": ["contract", "due_date", "amount"],
    },
    "add_purchase": {
        "properties": {
            "quantity": {"type": "integer", "description": "Nombre de poulets achetes"},
            "amount": {"type": "number", "description": "Montant total paye pour cet achat"},
            "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
            "category": {"type": "string", "description": "Categorie (optionnel)"},
            "note": {"type": "string", "description": "Note libre, ex. provenance (optionnel)"},
        },
        "required": ["quantity", "amount"],
    },
    "add_sale": {
        "properties": {
            "quantity": {"type": "integer", "description": "Nombre de poulets vendus"},
            "amount": {"type": "number", "description": "Montant total encaisse pour cette vente"},
            "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
            "category": {"type": "string", "description": "Categorie (optionnel)"},
        },
        "required": ["quantity", "amount"],
    },
    "get_stock": {"properties": {}, "required": []},
    "help": {"properties": {}, "required": []},
}


def _build_tool_definitions() -> list[dict]:
    """Construit les definitions d'outils (function calling) a partir du catalogue
    INTENTS et des schemas de parametres types ci-dessus.
    """
    tools = []
    for op, meta in INTENTS.items():
        schema = _TOOL_PARAM_SCHEMAS.get(op, {"properties": {}, "required": []})
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": op,
                    "description": f"{meta['label']}. Exemple : \"{meta['example']}\"",
                    "parameters": {
                        "type": "object",
                        "properties": schema["properties"],
                        "required": schema["required"],
                    },
                },
            }
        )
    return tools


def _coerce_tool_params(raw: dict) -> dict:
    """Convertit les arguments bruts (JSON) d'un appel d'outil vers les types
    internes attendus par l'executeur (Decimal pour les montants, date pour
    due_date, int pour quantity, str pour le reste).
    """
    params: dict = {}
    for key, value in raw.items():
        if value in (None, "None", "") or key == "business":
            continue
        if key in ("amount", "premium"):
            try:
                params[key] = Decimal(str(value).replace(" ", "").replace(",", "."))
            except Exception:
                continue
        elif key == "quantity":
            try:
                params[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif key == "due_date":
            try:
                params[key] = date.fromisoformat(str(value)[:10])
            except ValueError:
                continue
        else:
            params[key] = str(value)
    return params


class LlmiInterpreter:
    """Interprete via une API compatible OpenAI (/v1/chat/completions) en utilisant
    le tool-calling natif : le LLM choisit un outil parmi INTENTS et remplit ses
    arguments selon un schema JSON type, plutot que de deviner un format JSON libre.
    Repli sur RuleInterpreter en cas d'echec ou si aucun outil n'est appele.
    """

    def __init__(self, api_url: str, api_key: str, model: str):
        self._api_url = api_url
        self._api_key = api_key
        self._model = model
        self._fallback = RuleInterpreter()
        self._tools = _build_tool_definitions()

    def interpret(self, message: str) -> IntentCommand:
        try:
            import httpx

            url = f"{self._api_url.rstrip('/')}/chat/completions"
            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es l'assistant d'une application de gestion financiere (assurance et "
                            "poulailler). Appelle l'outil qui correspond a la demande de l'utilisateur, avec "
                            "les parametres que tu peux extraire du message. N'invente jamais une valeur : "
                            "omets un parametre si tu ne le connais pas avec certitude plutot que de deviner. "
                            "Si la demande ne correspond a aucun outil, n'appelle aucun outil."
                        ),
                    },
                    {"role": "user", "content": message[:1000]},
                ],
                "tools": self._tools,
                "tool_choice": "auto",
                "temperature": 0,
            }
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            body = response.json()
            message_out = body["choices"][0]["message"]
            tool_calls = message_out.get("tool_calls") or []
            if not tool_calls:
                return IntentCommand(operation="unknown", params={}, confidence="low")

            call = tool_calls[0]["function"]
            operation = call["name"]
            if operation not in INTENTS:
                return IntentCommand(operation="unknown", params={}, confidence="low")

            import json

            raw_args = json.loads(call.get("arguments") or "{}")
            params = _coerce_tool_params(raw_args)
            business = business_code_for(operation, raw_args.get("business"))
            return IntentCommand(operation=operation, business=business, params=params, confidence="high")
        except Exception:
            import logging

            logging.getLogger(__name__).warning("LLM assistant indisponible, repli sur les regles", exc_info=True)
            return self._fallback.interpret(message)


def get_interpreter():
    from app.core.config import settings

    if settings.ASSISTANT_LLM_API_KEY:
        return LlmiInterpreter(
            settings.ASSISTANT_LLM_API_URL or "https://api.openai.com/v1",
            settings.ASSISTANT_LLM_API_KEY,
            settings.ASSISTANT_LLM_MODEL,
        )
    return RuleInterpreter()