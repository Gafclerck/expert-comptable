# Hackathon ISM Groupe Special

Moteur métier financier et comptable multi-activités (assurance, poulets, VTC)
avec assistant conversationnel. Backend FastAPI **monolithe modulaire**,
frontend React, canal Telegram.

---

# Structure du projet

```text
exp-comp/
│
├── exp-cmp-api/          # Backend FastAPI (monolithe modulaire : app/modules/*)
├── exp-cmp-client/       # Frontend React 19 + Vite + TypeScript + Tailwind 4
├── docs/                 # Documentation (ER_DIAGRAM, ROADMAP, USE_CASE, CONTEXT…)
├── docker-compose.yml    # Stack complète (db + redis + backend + telegram + frontend)
└── README.md
```

> L'ancien découpage `./backend` / `./frontend` cité dans certains fichiers
> n'existe pas : les dossiers réels sont **`exp-cmp-api/`** et **`exp-cmp-client/`**.

---

# Prérequis

- Git
- Python 3.13+ et `uv` (backend)
- Node.js + `pnpm` (frontend, optionnel si Docker)
- Docker Desktop (ou docker engine + plugin compose)

---

# Récupération du projet

```bash
git clone https://github.com/Gafclerck/Hackaton.git
cd Hackaton
```

---

# Lancement de l'application

## Option A : Docker Compose (stack complète)

Lance : **Postgres + Redis + backend FastAPI + worker Telegram + frontend
Vite en mode développement (hot-reload)**.

### 1. Configurer les variables

Le `.env` **racine** ne configure que l'infra Docker (Postgres/Redis). La
configuration applicative du backend se fait dans **`exp-cmp-api/.env`**
(source unique des paramètres applicatifs, injectée via `env_file`).

```bash
cp .env.example .env
cp exp-cmp-api/.env.example exp-cmp-api/.env
```

- Racine : remplir `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- `exp-cmp-api/.env` : remplir au minimum `SECRET_KEY`, `SUPER_USER_EMAIL`,
  `SUPER_USER_PASSWORD` (des défauts de dev existent sinon). Ne pas renseigner
  `DATABASE_URL` ni `ASSISTANTV2_REDIS_URL` : elles sont injectées par compose.

### 2. Démarrer la stack

```bash
docker compose up -d --build
```

- Swagger : http://localhost:8000/docs
- Frontend (dev) : http://localhost:5173
- Canal Telegram : worker actif si `TELEGRAM_ENABLED=true` dans `exp-cmp-api/.env`.

La base persiste dans le volume Docker `pgdata`. Pour tout effacer :
`docker compose down -v`.

> Le service `frontend` expose le serveur de **développement** Vite. Pour la
> production, construire l'artefact statique (`pnpm build`) et le servir en
> statique devant le backend.

---

## Option B : Installation manuelle (backend seul)

Le backend tourne **sans aucune configuration** : par défaut il utilise une
base SQLite (`./dev.db`) et des identifiants de dev connus.

```bash
cd exp-cmp-api
uv sync                       # crée .venv et installe le lockfile
uv run uvicorn app.main:app --reload
```

Le backend est accessible sur `http://localhost:8000` et Swagger sur
`http://localhost:8000/docs`.

Pour brancher PostgreSQL au lieu de SQLite : copier `exp-cmp-api/.env.example`
en `exp-cmp-api/.env` et renseigner `DATABASE_URL` + `SECRET_KEY`.

### Créer le super admin (optionnel, sinon fait au démarrage)

```bash
uv run python -m app.initial_data
```

Utilise `SUPER_USER_EMAIL` / `SUPER_USER_PASSWORD` (défauts de dev :
`admin@example.com` / `admin-changeme`).

---

# Scope actuel

Backend FastAPI **monolithe modulaire** (`app/modules/<module>/`), routes sous
`/api`, auth JWT + Argon2, RBAC = **root global + ownership** :

- **P0 Identity & Access** : `persons`, `users`, `roles`, `businesses`,
  `business_accounts` (login, refresh, me, change-password, gestion users).
- **P1 Ledger** : caisses (`accounts`), catégories, recettes/dépenses,
  ventilation multi-activités (`transaction_allocations`), virements
  (`transfers`).
- **P2 Audit** : journal append-only via événements
  (identity / ledger / assistant, dont `assistant.command.executed`).
- **B1 Assurance** : clients, contrats (unicité partielle de la matricule),
  paiements, échéances (`insurance_dues`, statut dérivé).
- **B3 Poulets** : lots & achats, ventes (FIFO via `poultry_sale_lots`),
  marge.
- **B4 VTC** : véhicules (prix d'acquisition + acquisition au grand livre
  optionnelle), chauffeurs, affectations historisées, versements, dépenses
  véhicules unifiées, indisponibilités.
- **C3 Assistant IA (v2)** : interpréteur règles FR + plug LLM optionnel
  (tool-calling OpenAI-compatible), sessions / clarifications, fallback
  d'intention, réponse formulée par LLM avec garde-fou anti-hallucination.
- **Canal Telegram** : liaison `/start <token>`, worker de polling
  (`app.modules.assistantv2.telegram`), journal d'idempotence exactly-once.

Non implémentés (cible) : financements personnels (B2), rappels (P4),
justificatifs (P3), dashboard/reporting (C1), créances/dettes génériques (C2).

Détails : `docs/ROADMAP.md`, `docs/ER_DIAGRAM.md`, `docs/CONTEXT.md`.

---

# Tests

```bash
cd exp-cmp-api
uv run pytest
```

Les tests couvrent identity, ledger, audit, insurance, poultry, vtc,
assistant (v1/v2) et Telegram. La base de test est un SQLite
(`tests/test_api.db`) créé via `Base.metadata.create_all` (pas de migrations).

---

# Convention de commits

- `feat: add login feature`
- `fix: resolve authentication bug`
- `docs: update README`
- `refactor: simplify service layer`
- `test: add authentication tests`

No commit direct sur `main`, jamais de push non testé. Branches feature depuis
`develop`. Ne pas committer `.env`, `.venv/`, `__pycache__/`.