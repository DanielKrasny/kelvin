from ninja import Router
from .default import router as default_router
from .class_session.default import router as class_session_default_router
from .device.default import router as device_default_router

router = Router(tags=["Attendance"])
router.add_router("", default_router)
router.add_router("/class-session", class_session_default_router)
router.add_router("/device", device_default_router)
