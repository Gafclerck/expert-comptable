"""Tests des garde-fous d'extensibilite eux-memes : la detection de collision
(nom d'outil, alias business, code business) et la verification a
l'enregistrement des dependances entre champs (requires_fields). Sans ces
tests, un garde-fou de securite n'est qu'une promesse non verifiee.
"""
import pytest

from app.modules.assistantv3 import registry


def _dummy_handler(db, actor, params):
    return {}, None, "dummy"


def test_collision_nom_outil_deja_enregistre():
    with pytest.raises(ValueError, match="deja enregistre"):
        registry.register(registry.ToolSpec(
            name="get_balance",  # deja pris par core_tools.py
            label="doublon",
            example="doublon",
            handler=_dummy_handler,
            parameters={"properties": {}, "required": []},
        ))


def test_collision_type_de_champ_deja_enregistre():
    with pytest.raises(ValueError, match="deja enregistre"):
        registry.register_field_type("amount", registry.BaseFieldType())


def test_collision_alias_business_deja_utilise():
    with pytest.raises(ValueError, match="deja utilise"):
        registry.register_business(registry.BusinessModule(
            code="fake_business_test",
            aliases={"poulet"},  # deja pris par poulets
        ))


def test_collision_code_business_insensible_a_la_casse():
    # Avant correctif : la comparaison code-contre-code n'etait pas
    # casefoldee, donc "POULETS" (majuscules) passait a travers.
    with pytest.raises(ValueError, match="collision"):
        registry.register_business(registry.BusinessModule(code="POULETS"))


def test_requires_fields_verifie_a_l_enregistrement():
    """payment_amount exige que 'contract' precede le champ dans order :
    un outil qui l'utilise sans respecter cet ordre doit echouer a
    l'enregistrement, pas silencieusement perdre le raccourci "reste"."""
    with pytest.raises(ValueError, match="exige que 'contract'"):
        registry.register(registry.ToolSpec(
            name="test_ordre_invalide",
            label="test",
            example="test",
            handler=_dummy_handler,
            business="assurance",
            parameters={"properties": {}, "required": []},
            order=["amount", "contract"],  # ordre invalide : amount avant contract
            field_type_overrides={"amount": "payment_amount"},
        ))
