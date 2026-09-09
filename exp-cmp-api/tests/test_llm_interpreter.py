from decimal import Decimal

from app.modules.assistant.interpreter import LlmiInterpreter


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _tool_call_response(name: str, arguments: str) -> _FakeResponse:
    return _FakeResponse(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {"function": {"name": name, "arguments": arguments}}
                        ]
                    }
                }
            ]
        }
    )


def test_llmi_interpreter_appelle_le_bon_outil_avec_les_bons_types(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return _tool_call_response(
            "record_payment",
            '{"contract": "MAT-100", "amount": "40000"}',
        )

    monkeypatch.setattr("httpx.post", fake_post)

    interpreter = LlmiInterpreter("https://fake-llm.local/v1", "fake-key", "fake-model")
    command = interpreter.interpret("Encaisser 40000 pour MAT-100")

    assert command.operation == "record_payment"
    assert command.params["contract"] == "MAT-100"
    assert command.params["amount"] == Decimal("40000")
    # Le vrai tool-calling doit envoyer un schema d'outils, pas un prompt en texte libre.
    assert "tools" in captured["payload"]
    tool_names = {t["function"]["name"] for t in captured["payload"]["tools"]}
    assert {"record_payment", "add_purchase", "add_sale", "get_stock", "add_due"}.issubset(tool_names)


def test_llmi_interpreter_coerce_quantity_et_due_date(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _tool_call_response(
            "add_purchase",
            '{"quantity": "24", "amount": "120000"}',
        )

    monkeypatch.setattr("httpx.post", fake_post)

    interpreter = LlmiInterpreter("https://fake-llm.local/v1", "fake-key", "fake-model")
    command = interpreter.interpret("J'ai achete 24 poulets a 120000")

    assert command.operation == "add_purchase"
    assert command.params["quantity"] == 24
    assert isinstance(command.params["quantity"], int)
    assert command.params["amount"] == Decimal("120000")


def test_llmi_interpreter_aucun_outil_appele_donne_unknown(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"choices": [{"message": {"content": "Je ne comprends pas la demande."}}]})

    monkeypatch.setattr("httpx.post", fake_post)

    interpreter = LlmiInterpreter("https://fake-llm.local/v1", "fake-key", "fake-model")
    command = interpreter.interpret("bla bla incomprehensible")
    assert command.operation == "unknown"


def test_llmi_interpreter_repli_sur_regles_si_echec_reseau(monkeypatch):
    def fake_post(*args, **kwargs):
        raise RuntimeError("connexion impossible")

    monkeypatch.setattr("httpx.post", fake_post)

    interpreter = LlmiInterpreter("https://fake-llm.local/v1", "fake-key", "fake-model")
    command = interpreter.interpret("Creer un client Awa Diop")

    # Repli transparent sur le RuleInterpreter : le message est quand meme compris.
    assert command.operation == "create_client"
    assert command.params.get("client") == "awa diop"


def test_llmi_interpreter_ignore_un_outil_inconnu(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _tool_call_response("supprimer_toute_la_base", "{}")

    monkeypatch.setattr("httpx.post", fake_post)

    interpreter = LlmiInterpreter("https://fake-llm.local/v1", "fake-key", "fake-model")
    command = interpreter.interpret("fais n'importe quoi")
    assert command.operation == "unknown"
