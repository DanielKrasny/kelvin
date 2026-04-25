from ninja import Router
from .device.default import router as device_default_router

router = Router(tags=["Attendance"])
router.add_router("/device", device_default_router)
