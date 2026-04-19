from ninja import Router
from .client.default import router as client_default_router
from .token.default import router as token_default_router

router = Router(tags=["API"])
router.add_router("/client", client_default_router)
router.add_router("/token", token_default_router)
