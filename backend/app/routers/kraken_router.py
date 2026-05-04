from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from .. import audit_logger
from ..auth import CurrentUser, DbSession
from ..crypto_utils import decrypt_secret, encrypt_secret
from ..kraken_client import KrakenAPIError, KrakenClient
from ..models import KrakenCredential
from ..schemas import (
    BalanceItem,
    BalancesResponse,
    CancelOrderRequest,
    HistoryItem,
    HistoryResponse,
    KrakenConnectRequest,
    KrakenConnectResponse,
    OpenOrderItem,
    OpenOrdersResponse,
)


router = APIRouter(prefix="/kraken", tags=["kraken"])


def _get_creds(db, user) -> tuple[str, str]:
    cred = db.query(KrakenCredential).filter_by(user_id=user.id).first()
    if not cred:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Kraken API keys not configured. Connect them first.",
        )
    return decrypt_secret(cred.api_key_encrypted), decrypt_secret(cred.api_secret_encrypted)


@router.post("/connect", response_model=KrakenConnectResponse)
async def connect(payload: KrakenConnectRequest, user: CurrentUser, db: DbSession):
    # Validate credentials by calling a private endpoint (Balance) before persisting.
    try:
        async with KrakenClient(api_key=payload.api_key, api_secret=payload.api_secret) as kc:
            await kc.balance()
    except KrakenAPIError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Kraken rejected credentials: {e}")
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not verify credentials: {e}")

    cred = db.query(KrakenCredential).filter_by(user_id=user.id).first()
    if cred:
        cred.api_key_encrypted = encrypt_secret(payload.api_key)
        cred.api_secret_encrypted = encrypt_secret(payload.api_secret)
    else:
        cred = KrakenCredential(
            user_id=user.id,
            api_key_encrypted=encrypt_secret(payload.api_key),
            api_secret_encrypted=encrypt_secret(payload.api_secret),
        )
        db.add(cred)
    db.commit()

    audit_logger.log_event(db, user_id=user.id, event_type="kraken_connected")
    return KrakenConnectResponse(connected=True, message="Kraken credentials saved (encrypted).")


@router.get("/balances", response_model=BalancesResponse)
async def balances(user: CurrentUser, db: DbSession):
    api_key, api_secret = _get_creds(db, user)
    try:
        async with KrakenClient(api_key=api_key, api_secret=api_secret) as kc:
            data = await kc.balance()
    except KrakenAPIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kraken: {e}")
    items = [BalanceItem(asset=k, amount=float(v)) for k, v in (data or {}).items()]
    return BalancesResponse(balances=items)


@router.get("/pairs")
async def pairs(pair: str | None = None):
    try:
        async with KrakenClient() as kc:
            data = await kc.asset_pairs(pair=pair)
    except KrakenAPIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kraken: {e}")
    return {"pairs": data}


@router.get("/open-orders", response_model=OpenOrdersResponse)
async def open_orders(user: CurrentUser, db: DbSession):
    api_key, api_secret = _get_creds(db, user)
    try:
        async with KrakenClient(api_key=api_key, api_secret=api_secret) as kc:
            data = await kc.open_orders()
    except KrakenAPIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kraken: {e}")

    raw = (data or {}).get("open", {}) or {}
    items: list[OpenOrderItem] = []
    for txid, order in raw.items():
        descr = order.get("descr") or {}
        opened_ts = order.get("opentm")
        opened_at = datetime.utcfromtimestamp(float(opened_ts)) if opened_ts else None
        items.append(
            OpenOrderItem(
                txid=txid,
                pair=descr.get("pair", ""),
                side=descr.get("type", ""),
                order_type=descr.get("ordertype", ""),
                volume=float(order.get("vol", 0) or 0),
                price=float(descr.get("price", 0) or 0),
                status=order.get("status", ""),
                opened_at=opened_at,
            )
        )
    return OpenOrdersResponse(orders=items)


@router.get("/order-history", response_model=HistoryResponse)
async def order_history(user: CurrentUser, db: DbSession):
    api_key, api_secret = _get_creds(db, user)
    try:
        async with KrakenClient(api_key=api_key, api_secret=api_secret) as kc:
            data = await kc.closed_orders()
    except KrakenAPIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kraken: {e}")

    raw = (data or {}).get("closed", {}) or {}
    items: list[HistoryItem] = []
    for txid, order in raw.items():
        descr = order.get("descr") or {}
        closed_ts = order.get("closetm")
        closed_at = datetime.utcfromtimestamp(float(closed_ts)) if closed_ts else None
        items.append(
            HistoryItem(
                txid=txid,
                pair=descr.get("pair", ""),
                side=descr.get("type", ""),
                order_type=descr.get("ordertype", ""),
                volume=float(order.get("vol", 0) or 0),
                price=float(descr.get("price", 0) or 0),
                status=order.get("status", ""),
                closed_at=closed_at,
            )
        )
    return HistoryResponse(orders=items)


@router.post("/cancel-order")
async def cancel_order(payload: CancelOrderRequest, user: CurrentUser, db: DbSession):
    api_key, api_secret = _get_creds(db, user)
    try:
        async with KrakenClient(api_key=api_key, api_secret=api_secret) as kc:
            res = await kc.cancel_order(payload.txid)
    except KrakenAPIError as e:
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="cancel_failed",
            parsed_payload={"txid": payload.txid},
            success=False,
            message=str(e),
        )
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kraken: {e}")
    audit_logger.log_event(
        db,
        user_id=user.id,
        event_type="cancel_submitted",
        parsed_payload={"txid": payload.txid},
        result_payload=res,
    )
    return {"success": True, "result": res}


# ---- Direct (non-NL) order placement, kept for power users / scripts ----
from ..schemas import PlaceOrderRequest  # noqa: E402


@router.post("/place-order")
async def place_order(payload: PlaceOrderRequest, user: CurrentUser, db: DbSession):
    """Direct limit order. Still goes through the same risk checks via parsed proxy."""
    if not payload.confirm:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Direct order placement requires 'confirm: true'. Prefer /commands/preview + /commands/confirm.",
        )
    api_key, api_secret = _get_creds(db, user)
    try:
        async with KrakenClient(api_key=api_key, api_secret=api_secret) as kc:
            res = await kc.add_order(
                pair=payload.pair,
                side=payload.side,
                ordertype="limit",
                volume=payload.volume,
                price=payload.limit_price,
            )
    except KrakenAPIError as e:
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="direct_order_failed",
            parsed_payload=payload.model_dump(),
            success=False,
            message=str(e),
        )
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kraken: {e}")
    audit_logger.log_event(
        db,
        user_id=user.id,
        event_type="direct_order_submitted",
        parsed_payload=payload.model_dump(),
        result_payload=res,
    )
    return {"success": True, "result": res}
