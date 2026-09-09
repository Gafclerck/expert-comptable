import pytest

from app.modules.assistant.formulator import Formulator


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_formulator_transmet_les_faits_et_renvoie_le_contenu(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(
            {"choices": [{"message": {"content": "Caisse Principale, solde 40 000 FCFA."}}]}
        )

    monkeypatch.setattr("httpx.post", fake_post)

    formulator = Formulator("https://fake-llm.local/v1", "fake-key", "fake-model")
    text = formulator.formulate("get_balance", {"account": "Caisse Principale", "balance": "40 000 FCFA"})

    assert text == "Caisse Principale, solde 40 000 FCFA."
    assert captured["payload"]["temperature"] == 0
    facts_prompt = captured["payload"]["messages"][1]["content"]
    assert "40 000 FCFA" in facts_prompt
    assert "Caisse Principale" in facts_prompt


def test_formulator_rejette_une_reponse_qui_invente_un_montant(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(
            {"choices": [{"message": {"content": "Le solde est de 10 000 FCFA."}}]}
        )

    monkeypatch.setattr("httpx.post", fake_post)

    formulator = Formulator("https://fake-llm.local/v1", "fake-key", "fake-model")
    with pytest.raises(ValueError):
        formulator.formulate("get_balance", {"account": "Caisse Principale", "balance": "40 000 FCFA"})


def test_formulator_rejette_une_reponse_vide(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"choices": [{"message": {"content": "   "}}]})

    monkeypatch.setattr("httpx.post", fake_post)

    formulator = Formulator("https://fake-llm.local/v1", "fake-key", "fake-model")
    with pytest.raises(ValueError):
        formulator.formulate("get_stock", {"kind": "get_stock", "quantity": "8"})


def test_formulator_rejette_si_echec_reseau(monkeypatch):
    def fake_post(*args, **kwargs):
        raise RuntimeError("connexion impossible")

    monkeypatch.setattr("httpx.post", fake_post)

    formulator = Formulator("https://fake-llm.local/v1", "fake-key", "fake-model")
    with pytest.raises(RuntimeError):
        formulator.formulate("get_stock", {"kind": "get_stock", "quantity": "8"})