from fastapi import Depends

from ..config import Settings, get_settings
from ..services.flashalpha_service import FlashAlphaService
from ..services.ibkr_service import IBKRService
from ..services.iv_history import IVHistoryStore
from ..services.polygon_service import PolygonService

_ibkr_singleton: IBKRService | None = None
_polygon_singleton: PolygonService | None = None
_flashalpha_singleton: FlashAlphaService | None = None
_iv_store_singleton: IVHistoryStore | None = None


def get_ibkr(settings: Settings = Depends(get_settings)) -> IBKRService:
    global _ibkr_singleton
    if _ibkr_singleton is None:
        _ibkr_singleton = IBKRService(settings.ibkr_host, settings.ibkr_port, settings.ibkr_client_id)
    return _ibkr_singleton


def get_polygon(settings: Settings = Depends(get_settings)) -> PolygonService:
    global _polygon_singleton
    if _polygon_singleton is None:
        _polygon_singleton = PolygonService(settings.polygon_api_key)
    return _polygon_singleton


def get_flashalpha(settings: Settings = Depends(get_settings)) -> FlashAlphaService:
    global _flashalpha_singleton
    if _flashalpha_singleton is None:
        _flashalpha_singleton = FlashAlphaService(settings.flashalpha_api_key, settings.flashalpha_base_url)
    return _flashalpha_singleton


def get_iv_store() -> IVHistoryStore:
    global _iv_store_singleton
    if _iv_store_singleton is None:
        _iv_store_singleton = IVHistoryStore()
    return _iv_store_singleton
