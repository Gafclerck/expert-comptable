from tests.helpers import auth_headers, create_account

ASSURANCE = "assurance"


def _chat(client, actor, message, session_id=None):
    response = client.post(
        "/api/assistant/chat",
        headers=auth_headers(actor),
        json={"message": message, "session_id": session_id},
    )
    assert response.status_code == 200
    return response.json()


def _create_client_and_contract(client, root):
    client_out = client.post(
        "/api/insurance/clients",
        headers=auth_headers(root),
        json={"full_name": "Tagoun"},
    ).json()
    contract = client.post(
        f"/api/insurance/clients/{client_out['id']}/contracts",
        headers=auth_headers(root),
        json={
            "matricule": "MAT-E2E",
            "contract_type": "assurance-auto",
            "premium": "100000",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    ).json()
    return client_out, contract


def test_paiement_par_phrase(client, root, assurance):
    client_out, contract = _create_client_and_contract(client, root)

    reply = _chat(client, root, "Encaisser 40 000 de Tagoun pour le contrat MAT-E2E")
    assert reply["executed"] is True
    assert reply["intent"] == "record_payment"
    assert "40 000" in reply["text"]
    assert "60 000" in reply["text"]

    account = client.get("/api/ledger/accounts", headers=auth_headers(root)).json()[0]
    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(root)).json()
    assert float(balance["balance"]) == 40000

    remaining = client.get(f"/api/insurance/contracts/{contract['id']}", headers=auth_headers(root)).json()
    assert float(remaining["remaining_amount"]) == 60000

    logs = client.get("/api/audit/logs", headers=auth_headers(root)).json()
    assert any(log["entity_type"] == "assistant_commands" for log in logs)
    assert any(log["entity_type"] == "insurance_payments" for log in logs)


def test_caisse_par_defaut_quand_plusieurs_comptes(client, root, assurance):
    # Des qu'il y a plusieurs caisses, la Caisse Principale (compte cree a la
    # creation du business) est preselectionnee : 1 business = 1 compte par defaut.
    create_account(client, root, assurance, name="Caisse Wave")
    _create_client_and_contract(client, root)

    reply = _chat(client, root, "Encaisser 40 000 de Tagoun pour le contrat MAT-E2E")
    assert reply["executed"] is True
    assert reply["intent"] == "record_payment"
    assert "Caisse Principale" in reply["text"]

    accounts = client.get("/api/ledger/accounts", headers=auth_headers(root)).json()
    wave = next(a for a in accounts if a["name"] == "Caisse Wave")
    balance = client.get(
        f"/api/ledger/accounts/{wave['id']}/balance", headers=auth_headers(root)
    ).json()
    assert float(balance["balance"]) == 0


def test_solde_caisse_assurance_sans_clarification(client, root, assurance):
    create_account(client, root, assurance, name="Caisse Wave")
    _create_client_and_contract(client, root)
    _chat(client, root, "Encaisser 30 000 de Tagoun pour le contrat MAT-E2E")

    reply = _chat(client, root, "Solde de la caisse assurance")
    assert reply["executed"] is True
    assert reply["clarification"] is False
    assert reply["intent"] == "get_balance"
    assert "30 000" in reply["text"]
    assert "Caisse Principale" in reply["text"]


def test_solde_caisse_poulailler_fallback_vers_activite_poulets(client, root, poulets):
    # Reproduit le bug : « solde caisse poulailler » demandait « Sur quelle caisse ? »
    # en boucle car le business etait pilote vers l'assurance. Le fallback doit
    # resoudre la caisse de l'activite poulets (meme nom « Caisse Poulets » distinct
    # de « Caisse Assurance »).
    acc = client.get(
        "/api/ledger/accounts?business_id=" + str(poulets.id),
        headers=auth_headers(root),
    ).json()
    assert acc, "la caisse des poulets doit etre seedee"
    poulet_account = acc[0]
    # debitons la caisse poulets d'un montant identifiable
    _chat(client, root, "J'ai achete 24 poulets a 120000")

    reply = _chat(client, root, "Solde de la caisse poulailler")
    assert reply["executed"] is True
    assert reply["clarification"] is False
    assert reply["intent"] == "get_balance"
    assert "120 000" in reply["text"]


def test_solde_caisse_poulets_avec_plusieurs_caisses(client, root, poulets, assurance):
    # Meme activite : plusieurs caisses, "poulets" doit viser la Caisse Principale
    # de l'activite poulets et non celle de l'assurance.
    create_account(client, root, assurance, name="Caisse Wave")
    _chat(client, root, "J'ai achete 10 poulets a 50000")

    reply = _chat(client, root, "Solde de la caisse poulets")
    assert reply["executed"] is True
    assert reply["clarification"] is False
    assert "50 000" in reply["text"]


def test_solde_caisse_poulailler_priorite_activite_poulets(client, root, assurance, poulets):
    # Meme quand l'assurance a plusieurs caisses, la mention « poulailler » doit
    # router la demande vers l'activite poulets (dont la caisse est vide ici).
    create_account(client, root, assurance, name="Caisse Wave")
    _create_client_and_contract(client, root)
    _chat(client, root, "Encaisser 30 000 de Tagoun pour le contrat MAT-E2E")

    reply = _chat(client, root, "Solde de la caisse poulailler")
    assert reply["executed"] is True
    assert reply["clarification"] is False
    assert "0 FCFA" in reply["text"]


def test_balance_poulailler_llm_sans_business_resout_la_bonne_caisse(client, root, poulets, monkeypatch):
    # Reproduit le bug reel remonte par l'utilisateur : le LLM appelle get_balance
    # avec account="caisse poulailler" sans renseigner business (repli assurance).
    # Le fallback doit router vers la caisse des poulets et non boucler sur
    # « Sur quelle caisse ? ».
    from app.modules.assistant.schemas import IntentCommand

    _chat(client, root, "J'ai achete 24 poulets a 120000")

    class _FakeLlm:
        def interpret(self, message):
            return IntentCommand(
                operation="get_balance",
                business="assurance",  # defaut : le LLM n'a pas precise l'activite
                params={"account": "caisse poulailler"},
                confidence="high",
            )

    monkeypatch.setattr("app.modules.assistant.service.get_interpreter", lambda: _FakeLlm())

    reply = _chat(client, root, "Solde de la caisse poulailler")
    assert reply["executed"] is True
    assert reply["clarification"] is False
    assert "120 000" in reply["text"]


def test_balance_poulailler_llm_avec_business_resout_la_bonne_caisse(client, root, poulets, monkeypatch):
    # Avec le nouveau champ business du tool get_balance, le LLM precise souvent
    # l'activite : la resolution doit tout de meme retenir la caisse poulets.
    from app.modules.assistant.schemas import IntentCommand

    _chat(client, root, "J'ai achete 24 poulets a 120000")

    class _FakeLlm:
        def interpret(self, message):
            return IntentCommand(
                operation="get_balance",
                business="poulets",
                params={"account": "caisse poulailler"},
                confidence="high",
            )

    monkeypatch.setattr("app.modules.assistant.service.get_interpreter", lambda: _FakeLlm())

    reply = _chat(client, root, "Solde de la caisse poulailler")
    assert reply["executed"] is True
    assert reply["clarification"] is False
    assert "120 000" in reply["text"]


def test_reponse_formulee_par_formulateur(client, root, assurance, monkeypatch):
    _create_client_and_contract(client, root)
    captured = {}

    class _FakeFormulator:
        def formulate(self, operation, result, user_message=""):
            captured["operation"] = operation
            captured["result"] = result
            return "La caisse Principale affiche un solde de 0 FCFA pour le moment."

    monkeypatch.setattr("app.modules.assistant.service.get_formulator", lambda: _FakeFormulator())

    reply = _chat(client, root, "Solde de la caisse")
    assert reply["executed"] is True
    assert reply["text"] == "La caisse Principale affiche un solde de 0 FCFA pour le moment."
    assert captured["operation"] == "get_balance"
    assert captured["result"]["account"] == "Caisse Principale"
    assert captured["result"]["balance"] == "0 FCFA"


def test_repli_statique_si_formulateur_echec(client, root, assurance, monkeypatch):
    _create_client_and_contract(client, root)

    class _Boom:
        def formulate(self, *args, **kwargs):
            raise RuntimeError("llm down")

    monkeypatch.setattr("app.modules.assistant.service.get_formulator", lambda: _Boom())

    reply = _chat(client, root, "Encaisser 40 000 de Tagoun pour le contrat MAT-E2E")
    assert reply["executed"] is True
    assert "40 000" in reply["text"]
    assert "Caisse Principale" in reply["text"]


def test_clarification_montant_puis_execution(client, root, assurance):
    _create_client_and_contract(client, root)

    reply = _chat(client, root, "Encaisser de Tagoun pour le contrat MAT-E2E")
    assert reply["clarification"] is True
    assert reply["missing_field"] == "amount"

    reply2 = _chat(client, root, "c'est le reste", reply["session_id"])
    assert reply2["executed"] is True
    assert "100 000" in reply2["text"]


def test_nouveau_client(client, root):
    reply = _chat(client, root, "Creer un client Moussa Camara")
    assert reply["executed"] is True
    assert reply["intent"] == "create_client"
    assert "Moussa Camara" in reply["text"]
    assert "CLI-" in reply["text"]


def test_nouveau_contrat(client, root):
    client_out = client.post(
        "/api/insurance/clients",
        headers=auth_headers(root),
        json={"full_name": "Adama"},
    ).json()
    reply = _chat(
        client,
        root,
        "Nouveau contrat pour Adama, matricule MAT-900, prime 150 000",
    )
    assert reply["executed"] is True
    assert "MAT-900" in reply["text"]
    contracts = client.get("/api/insurance/clients", headers=auth_headers(root)).json()
    assert contracts


def test_matricule_active_refusee(client, root, assurance):
    _create_client_and_contract(client, root)
    reply = _chat(client, root, "Nouveau contrat pour Tagoun, matricule MAT-E2E, prime 50 000")
    assert reply["executed"] is True
    assert "Erreur" in reply["text"] and "deja active" in reply["text"]


def test_solde_caisse(client, root, assurance):
    _create_client_and_contract(client, root)
    _chat(client, root, "Encaisser 30 000 de Tagoun pour le contrat MAT-E2E")

    reply = _chat(client, root, "Solde de la caisse")
    assert reply["executed"] is True
    assert "30 000" in reply["text"]


def test_reste_a_payer(client, root, assurance):
    _create_client_and_contract(client, root)

    reply = _chat(client, root, "Quel est le reste a payer du contrat MAT-E2E ?")
    assert reply["executed"] is True
    assert "100 000" in reply["text"]


def test_echeance_par_phrase(client, root, assurance):
    _create_client_and_contract(client, root)

    reply = _chat(client, root, "Ajouter une echeance pour MAT-E2E le 30/09/2026 montant 20000")
    assert reply["executed"] is True
    assert reply["intent"] == "add_due"
    assert "20 000" in reply["text"]
    assert "30/09/2026" in reply["text"]

    reply2 = _chat(client, root, "Echeances du contrat MAT-E2E")
    assert reply2["executed"] is True
    assert reply2["intent"] == "get_dues"
    assert "20 000" in reply2["text"]
    assert "pending" in reply2["text"]


def test_achat_et_vente_poulets_par_phrase(client, root, poulets):
    # La caisse (Caisse Principale) et les categories par defaut sont seedees par
    # init_db a la creation du business : le test s'appuie dessus (1 business = 1 compte).
    reply = _chat(client, root, "J'ai achete 24 poulets a 120000")
    assert reply["executed"] is True
    assert reply["intent"] == "add_purchase"
    assert "24" in reply["text"]

    reply2 = _chat(client, root, "Stock de poulets")
    assert reply2["executed"] is True
    assert reply2["intent"] == "get_stock"
    assert "24" in reply2["text"]

    reply3 = _chat(client, root, "J'ai vendu 8 poulets pour 60000")
    assert reply3["executed"] is True
    assert reply3["intent"] == "add_sale"

    reply4 = _chat(client, root, "Stock de poulets")
    assert "16" in reply4["text"]


def test_creation_refusee_hors_assurance(client, co_owner):
    reply = _chat(client, co_owner, "Creer un client Moussa")
    assert reply["executed"] is True
    assert "Erreur" in reply["text"]
    assert "Acces refuse" in reply["text"]


def test_aide(client, root):
    reply = _chat(client, root, "aide")
    assert reply["executed"] is False
    assert reply["intent"] == "help"
    assert "Encaisser" in reply["text"]


def test_sessions_listing(client, root):
    reply = client.get("/api/assistant/intents", headers=auth_headers(root))
    assert reply.status_code == 200
    operations = {item["operation"] for item in reply.json()}
    assert {"create_client", "create_contract", "record_payment", "get_balance"}.issubset(operations)