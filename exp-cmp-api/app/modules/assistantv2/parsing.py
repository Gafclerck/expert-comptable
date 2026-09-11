"""Extraction de valeurs depuis du texte libre (montants, matricules, dates,
quantites, noms). Portee depuis `assistant/interpreter.py` (v1) : ce sont des
fonctions pures, deja eprouvees, reutilisees ici pour remplir un champ apres
une question de clarification (voir orchestrator.py::_fill_field).

Dupliquee plutot qu'importee depuis le module v1 pour que assistantv2 reste
autonome (l'idee etant, a terme, de retirer `assistant` une fois la bascule
faite). Si les deux modules coexistent longtemps, cette duplication sera a
factoriser dans un module partage.
"""
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

_AMOUNT_RE = re.compile(
    r"(?<![A-Za-z0-9-])(\d{1,3}(?:[\s\u00A0.]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?![A-Za-z0-9])"
)
_MATRICULE_KEYWORD_RE = re.compile(r"\bmatricule\s+?(?:num[eé]ro\s+)?([A-Z]{2,5})[-_ ]?([A-Z0-9]+)\b", re.IGNORECASE)
_MATRICULE_PLAIN_RE = re.compile(r"\b([A-Za-z]{2,5})[-_]([A-Za-z0-9]+)\b")
_CLIENT_NUMBER_RE = re.compile(r"\bCLI[-_ ]?\d+\b", re.IGNORECASE)
_QUANTITY_RE = re.compile(r"\b(\d+)\s*poulets?\b", re.IGNORECASE)

_NAME_STOPWORDS = {
    "svp", "merci", "telephone", "numero", "matricule", "prime", "contrat",
    "paiement", "encaisser", "compte", "caisse", "categorie", "sur", "avec",
    "pour", "de", "du", "et", "le", "la", "les", "un", "une",
}

_MONTHS_FR = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}
_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b")
_DATE_TEXT_RE = re.compile(
    r"\b(\d{1,2})\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)(?:\s+(\d{4}))?\b"
)
_CLEAN_NAME_PATTERN = re.compile(r"([a-z][a-z' -]{0,60}?)(?=\s+(?:svp|merci|telephone|numero)|[,;.!?]|$)")


def normalize(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(ch) != "Mn"
    ).strip()


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


def parse_quantity(text: str) -> int | None:
    match = _QUANTITY_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


def parse_quantity_and_amount(text: str) -> tuple[int | None, Decimal | None]:
    match = _QUANTITY_RE.search(text)
    if not match:
        return None, parse_amount(text)
    quantity = int(match.group(1))
    amount = parse_amount(text[match.end():]) or parse_amount(text[: match.start()])
    return quantity, amount


def parse_due_date(text: str) -> date | None:
    norm = normalize(text)
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


def _clean_name(value: str) -> str | None:
    cleaned = _CLEAN_NAME_PATTERN.match(normalize(value))
    if not cleaned:
        return None
    name = cleaned.group(1).strip()
    tokens = [t for t in name.split() if t not in _NAME_STOPWORDS]
    return " ".join(tokens) if tokens else None


def extract_client_name(text: str, pour: bool = False) -> str | None:
    quoted = re.search(r"[\"']([^\"']+)[\"']", text)
    if quoted:
        return _clean_name(quoted.group(1))
    norm = normalize(text)
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


def parse_period(text: str) -> tuple[date, date, str] | None:
    """Reconnait une expression de periode en langage naturel et renvoie
    (debut, fin, libelle), les deux dates incluses. None si rien de reconnu :
    a l'appelant de choisir un defaut (get_period_summary utilise "ce mois").

    Semaine calee sur lundi (convention ISO/francophone). Les bornes sont des
    dates calendaires locales : le deploiement actuel est a Dakar (UTC+0,
    sans heure d'ete), donc equivalent a UTC, ce qui est ce que utilise
    compute_period_totals pour construire ses bornes de requete.
    """
    norm = normalize(text)
    today = date.today()
    if "aujourdhui" in norm or "aujourd'hui" in norm:
        return today, today, "aujourd'hui"
    if "hier" in norm:
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday, "hier"
    if "semaine derniere" in norm or "semaine passee" in norm:
        start_this_week = today - timedelta(days=today.weekday())
        start = start_this_week - timedelta(days=7)
        end = start_this_week - timedelta(days=1)
        return start, end, "la semaine derniere"
    if "semaine" in norm:
        start = today - timedelta(days=today.weekday())
        return start, today, "cette semaine"
    if "mois dernier" in norm or "mois passe" in norm:
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end, "le mois dernier"
    if "mois" in norm:
        return today.replace(day=1), today, "ce mois"
    if "annee" in norm:
        return today.replace(month=1, day=1), today, "cette annee"
    return None


def clean_free_text(message: str) -> str | None:
    cleaned = normalize(message).strip(".,;!? ")
    return cleaned or None


def coerce_params(raw: dict) -> dict:
    """Convertit un dict de valeurs brutes (JSON : str/int/float/bool/None)
    vers les types internes attendus par les outils (Decimal pour les
    montants, date pour due_date, int pour quantity, str pour le reste).

    Utilisee a deux endroits : sur les arguments bruts renvoyes par le LLM
    (orchestrator.py), et sur les params d'un PlanStep relu depuis Redis
    (plan.py) puisque le JSON ne connait ni Decimal ni date - le round-trip
    passe donc par des chaines de caracteres et repasse par cette fonction
    pour retrouver les bons types.
    """
    params: dict = {}
    for key, value in raw.items():
        if value in (None, "None", ""):
            continue
        if key == "_confirmed":
            params[key] = bool(value)
        elif key in ("amount", "premium"):
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
