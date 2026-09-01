# Hackathon ISM Groupe Special

Description courte du projet.

---

# Structure du projet

```text
exp-cmp/
│
├── exp-cmp-api/        # API FastAPI (backend)
├── exp-cmp-client/     # Application cliente (vide, pas encore implementee)
├── docs/               # Documentation du projet
└── README.md
```

---

# Prérequis

- Git
- Python 3.13+
- PostgreSQL (optionnel : le backend tourne aussi sur SQLite sans config)
- uv

---

# Récupération du projet

```bash
git clone https://github.com/Gafclerck/Hackaton.git
cd Hackaton
```

---

# Lancement de l'application

## Option A : Docker Compose (backend + base de donnees)

Lance la stack : Postgres + backend. Le backend se connecte au Postgres
conteneurise et cree le super admin au demarrage.

Prerequis : Docker Desktop (ou docker engine + plugin compose).

### 1. Configurer les variables

```bash
cp .env.example .env
```

Ouvrir `.env` a la racine et remplir au minimum `SECRET_KEY`,
`SUPER_USER_EMAIL` et `SUPER_USER_PASSWORD`.

### 2. Demarrer la stack

```bash
docker compose up -d --build
```

- Swagger : http://localhost:8000/docs

La base persiste dans le volume Docker `pgdata`. Pour tout effacer :
`docker compose down -v`.

> Le service `frontend` est desactive dans `docker-compose.yml` (TODO) car
> `exp-cmp-client/` est encore vide.

---

## Option B : Installation manuelle (backend seul)

Le backend tourne **sans aucune configuration** : par defaut il utilise une
base SQLite (`./dev.db`) et des identifiants de dev connus.

```bash
cd exp-cmp-api
uv sync                       # cree .venv et installe uv.lock
uv run uvicorn app.main:app --reload
```

Le backend est accessible sur `http://localhost:8000` et Swagger sur
`http://localhost:8000/docs`.

Pour brancher PostgreSQL au lieu de SQLite, copier `exp-cmp-api/.env.example`
en `exp-cmp-api/.env` et renseigner `DATABASE_URL` + `SECRET_KEY`.

### Creer le super admin (optionnel, sinon fait au demarrage)

```bash
uv run python -m app.initial_data
```

Utilise `SUPER_USER_EMAIL` / `SUPER_USER_PASSWORD` (defauts de dev :
`admin@example.com` / `admin-changeme`).

---

# Backend purge : scope actuel

Le backend a ete reduit a une API **auth-only** + des **squelettes** d'endpoints :
- **Fonctionnel** : chaine d'authentification complete (login, refresh, me,
  change-password) + gestion des utilisateurs (creation, listing, profil).
- **Squelettes** (reponses placeholder, sans logique metier ni stockage) :
  dossier, client, agence, referentiel, historique, discussion, document, websocket.

Le stockage Cloudflare R2 et les scripts de seed ont ete supprimes.

# Tests

```bash
cd exp-cmp-api
uv run pytest
```

Les tests couvrent l'auth + le smoke test. La base de test est un SQLite
(`tests/test_api.db`) cree via `Base.metadata.create_all` (pas de migrations).

---

# Convention de commits

- `feat: add login feature`
- `fix: resolve authentication bug`
- `docs: update README`
- `refactor: simplify service layer`
- `test: add authentication tests`

No commit direct sur `main`, jamais de push non teste. Branches feature depuis
`develop`. Ne pas committer `.env`, `.venv/`, `__pycache__/`.
