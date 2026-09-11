from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.deps import limiter
from app.modules.assistantv2.router import api_router as assistantv2_router
from app.modules.audit.service import attach_listeners as attach_audit_listeners
from app.modules.identity.router import api_router as identity_router
from app.modules.insurance.router import api_router as insurance_router
from app.modules.ledger.service import attach_listeners as attach_ledger_listeners
from app.modules.ledger.router import api_router as ledger_router
from app.modules.audit.router import api_router as audit_router
from app.modules.poultry.router import api_router as poultry_router
from app.modules.vtc.router import api_router as vtc_router

app = FastAPI()
app.state.limiter = limiter

attach_audit_listeners()
attach_ledger_listeners()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Trop de requetes. Reessayez plus tard."},
    )


app.include_router(identity_router, prefix=settings.API_STR)
app.include_router(ledger_router, prefix=settings.API_STR)
app.include_router(audit_router, prefix=settings.API_STR)
app.include_router(insurance_router, prefix=settings.API_STR)
app.include_router(poultry_router, prefix=settings.API_STR)
app.include_router(vtc_router, prefix=settings.API_STR)
app.include_router(assistantv2_router, prefix=settings.API_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="localhost", port=8000, reload=True)