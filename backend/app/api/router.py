"""Aggregate API router (FastAPI). Mounted under settings.API_V1_PREFIX."""
from fastapi import APIRouter

from app.api.routes import (
    auth,
    billing,
    businesses,
    compliance,
    dashboard,
    invoices,
    notifications,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
