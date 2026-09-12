"""Router Telegram (liaison REST du compte applicatif) : tokens jetables,
etat du lien, debranchement, listing root. Le worker de polling consulte les
memes tables en base sans passer par ce router (process dedie)."""
from fastapi import APIRouter, HTTPException, Response

from app.core.deps import CurrentUser, RequireRoot, SessionDep
from app.modules.assistantv2.telegram import service as telegram_service
from app.modules.assistantv2.telegram.schemas import (
    BindingAdminOut,
    BindingMeOut,
    BindingTokenOut,
)

telegram_router = APIRouter(prefix="/telegram", tags=["telegram"])


@telegram_router.post("/bindings/token", response_model=BindingTokenOut, status_code=201)
def create_link_token(db: SessionDep, current_user: CurrentUser) -> BindingTokenOut:
    record = telegram_service.create_link_token(db, current_user)
    return BindingTokenOut(
        token=record.token,
        expires_at=record.expires_at,
        instruction=(
            "Ouvre le bot Telegram et envoie la commande /start <TOKEN> "
            "pour lier ton compte."
        ),
    )


@telegram_router.get("/bindings/me", response_model=BindingMeOut)
def binding_me(db: SessionDep, current_user: CurrentUser) -> dict:
    binding = telegram_service.get_binding_for_user(db, current_user.id)
    return telegram_service.binding_to_me(binding)


@telegram_router.delete("/bindings/me", status_code=204)
def unbind_me(db: SessionDep, current_user: CurrentUser) -> Response:
    binding = telegram_service.get_binding_for_user(db, current_user.id)
    if binding is None:
        raise HTTPException(status_code=404, detail="Aucun lien Telegram pour ce compte")
    telegram_service.deactivate_binding(db, binding, current_user)
    return Response(status_code=204)


@telegram_router.get("/bindings", response_model=list[BindingAdminOut])
def list_bindings(db: SessionDep, _: RequireRoot) -> list[dict]:
    return [telegram_service.binding_to_admin(b) for b in telegram_service.list_bindings(db)]


api_router = APIRouter()
api_router.include_router(telegram_router)