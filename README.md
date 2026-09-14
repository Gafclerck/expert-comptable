# Expert comptable multi-activités

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
git clone https://github.com/Gafclerck/expert-comptable.git
cd expert-comptable
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

| Service | Port | Rôle |
|---|---|---|
| `db` | — | PostgreSQL 17 (volume `pgdata`) |
| `redis` | 6379 | Persistance des plans d'exécution de l'assistant v2 |
| `backend` | 8000 | API FastAPI (Swagger `/docs`) |
| `telegram-bot` | — | Worker long-polling Telegram (si activé, voir plus bas) |
| `frontend` | 5173 | Vite dev (hot-reload) |

Le super admin est créé au premier démarrage
(`SUPER_USER_EMAIL` / `SUPER_USER_PASSWORD`).

Pour tout effacer : `docker compose down -v` (supprime aussi `pgdata`).

> Le service `frontend` expose le serveur de **développement** Vite. Pour la
> production, construire l'artefact statique (`pnpm build`) et le servir en
> statique devant le backend.

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

# Se connecter à l'API

Le login utilise le format **OAuth2 form** (champ `username`, pas `email`) :

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=admin@example.com&password=admin-changeme"
```

Réponse : `{ "access_token": ..., "refresh_token": ..., "token_type": "bearer" }`.
Les endpoints protégés s'appellent avec `Authorization: Bearer <access_token>`.

---

# Assistant IA

Deux moteurs coexistent : **v1** (legacy, `/api/assistant/*`) et **v2**
(recommandé, `/api/assistantv2/*`).

## Brancher un LLM (optionnel)

Sans clé, l'assistant fonctionne en mode **règles françaises** (compréhension
limitée). Pour le mode **LLM** (tool-calling OpenAI-compatible), renseigner
dans `exp-cmp-api/.env` :

```env
ASSISTANT_LLM_API_KEY=sk-...
ASSISTANT_LLM_API_URL=https://api.openai.com/v1   # optionnel (autre fournisseur)
ASSISTANT_LLM_MODEL=gpt-4o-mini                    # optionnel
```

## Via l'API HTTP (v2)

- `GET /api/assistantv2/tools` — liste les outils disponibles.
- `POST /api/assistantv2/chat` — converser (une phrase par appel) :

```bash
curl -X POST http://localhost:8000/api/assistantv2/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Combien reste-t-il dans la caisse assurance ?", "session_id": null}'
```

`session_id` persiste le plan d'exécution en cours (clarification/confirmation)
entre deux requêtes ; repasser `null` pour une nouvelle conversation.

## REPL de test manuel (v2)

Teste le vrai cache du LLM (choix des outils/arguments) en contournant HTTP.
Prérequis : `ASSISTANT_LLM_API_KEY` configurée, Redis accessible
(`docker compose up -d redis`), super admin déjà créé.

```bash
cd exp-cmp-api
uv run python -m app.modules.assistantv2.repl
```

---

# Canal Telegram

Le worker Telegram est un **front-end de l'assistant v2** : les échanges
prennent la forme de messages dans un chat Telegram adressé au bot.

## 1. Préparer un bot

Créer le bot via **@BotFather** (Telegram) puis récupérer son token. Dans
`exp-cmp-api/.env` :

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<TOKEN_DU_BOT>
```

Sans ces deux valeurs, le worker sort proprement sans poller.
## 2. Lancer le worker

Avec Docker (compose) :

```bash
docker compose up -d --build          # le service telegram-bot démarre tout seul
```

En local (backend déjà lancé + Redis) :

```bash
cd exp-cmp-api
uv run python -m app.modules.assistantv2.telegram
```

## 3. Lier ton compte applicatif au chat Telegram

Un `User` de l'app (root/owner) doit lier son compte au bot une fois :

1. Générer un token de liaison jetable (valable 10 min par défaut) :

   ```bash
   curl -X POST http://localhost:8000/api/telegram/bindings/token \
     -H "Authorization: Bearer $TOKEN"
   # → { "token": "…", "expires_at": "…", "instruction": "Ouvre le bot Telegram et envoie la commande /start <TOKEN>…" }
   ```

2. Dans Telegram, ouvrir le bot et envoyer : `/start <TOKEN>`.

Le compte est lié, la session est créée (`tg:<chat_id>`) et tu peux parler au
bot en langage naturel (ex. « Combien reste-t-il dans la caisse assurance ? »).

## 4. Vérifier / débrancher le lien

```bash
curl http://localhost:8000/api/telegram/bindings/me -H "Authorization: Bearer $TOKEN"   # état du lien
curl -X DELETE http://localhost:8000/api/telegram/bindings/me -H "Authorization: Bearer $TOKEN"   # 204 = débranché
```

Le root peut lister toutes les liaisons : `GET /api/telegram/bindings`.

> Détails d'implémentation : `docs/TELEGRAM_INTEGRATION.md`.

---

# Référence des variables d'environnement

Config applicative lue dans `exp-cmp-api/.env` (modèle : `exp-cmp-api/.env.example`).

| Variable | Défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` | Source de données (remplacée par compose en Docker) |
| `SECRET_KEY` | dev connue | Signature des JWT (obligatoire en production) |
| `ENVIRONMENT` | `development` | `production` refuse SQLite + clés par défaut + `DEBUG` |
| `DEBUG` | `false` | Logs SQL (interdite en production) |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]` | CORS (JSON, lister les domaines réels en prod) |
| `ASSISTANT_LLM_API_KEY` | *(vide)* | Active le mode LLM de l'assistant (sans clé : règles FR) |
| `ASSISTANT_LLM_API_URL` | `https://api.openai.com/v1` | Base URL compatible OpenAI |
| `ASSISTANT_LLM_MODEL` | `gpt-4o-mini` | Modèle de chat utilisé |
| `ASSISTANT_LLM_ENABLE_FORMULATION` | `true` | Réponse rédigée par le LLM (garde-fou anti-hallucination) |
| `ASSISTANTV2_REDIS_URL` | `redis://localhost:6379/0` | Plans d'exécution de l'assistant v2 |
| `ASSISTANTV2_MAX_ITERATIONS` | `4` | Multi-tool-calls max par message |
| `TELEGRAM_ENABLED` | `false` | Active le worker Telegram |
| `TELEGRAM_BOT_TOKEN` | *(vide)* | Token du bot (jamais committer) |
| `TELEGRAM_LINK_TOKEN_TTL_MINUTES` | `10` | Durée de vie du `/start <TOKEN>` |
| `TELEGRAM_POLL_TIMEOUT_SECONDS` | `30` | Timeout `getUpdates` |

---

# Tests

Aucun postgres ni Redis nécessaire : la suite tourne sur SQLite
(`tests/test_api.db`, créée via `Base.metadata.create_all`, sans migrations).

Depuis **`exp-cmp-api/`** :

```bash
uv run pytest                                   # toute la suite
uv run pytest tests/test_vtc.py                 # un fichier
uv run pytest tests/test_vtc.py::test_nom       # un test précis
```

> **Exécution séquentielle obligatoire** : la suite pose une seule base SQLite
> partagée — ne pas lancer deux `pytest` en parallèle (verrou d'écriture).
> Le venv local (`exp-cmp-api/.venv`) est câblé pour `python -m pytest` comme
> pour `uv run pytest`.

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
- **Canal Telegram** : liaison `/start <TOKEN>`, worker de polling
  (`app.modules.assistantv2.telegram`), journal d'idempotence exactly-once.

Non implémentés (cible) : financements personnels (B2), rappels (P4),
justificatifs (P3), dashboard/reporting (C1), créances/dettes génériques (C2).

Détails : `docs/ROADMAP.md`, `docs/ER_DIAGRAM.md`, `docs/CONTEXT.md`.

---