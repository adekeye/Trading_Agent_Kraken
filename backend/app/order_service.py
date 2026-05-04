"""Order placement & lifecycle service.

This module mediates between parsed commands, the risk engine, and the Kraken
client. It also enforces the dry-run flag and persists results.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from . import audit_logger
from .crypto_utils import decrypt_secret
from .kraken_client import KrakenAPIError, KrakenClient, to_kraken_pair_altname
from .models import KrakenCredential, OrderRecord, PendingConfirmation, User, UserSettings
from .risk_engine import RiskDecision, RiskEngine
from .schemas import OrderResult, ParsedCommand


CONFIRMATION_TTL_SECONDS = 120


class OrderServiceError(Exception):
    pass


def _user_credentials(db: Session, user: User) -> tuple[str, str]:
    cred = db.query(KrakenCredential).filter_by(user_id=user.id).first()
    if not cred:
        raise OrderServiceError("Kraken API keys not configured for this user")
    return decrypt_secret(cred.api_key_encrypted), decrypt_secret(cred.api_secret_encrypted)


def _user_settings(db: Session, user: User) -> UserSettings:
    s = db.query(UserSettings).filter_by(user_id=user.id).first()
    if not s:
        s = UserSettings(user_id=user.id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


async def build_preview(
    db: Session,
    user: User,
    parsed: ParsedCommand,
    raw_command: str,
) -> tuple[PendingConfirmation, RiskDecision, dict[str, Any]]:
    """Run risk checks, persist a PendingConfirmation, return preview payload."""
    settings = _user_settings(db, user)

    # If 'sell all' style commands ever surface (quantity=None, intent place_order),
    # we'd resolve real balances here. For now we require explicit quantities and the
    # risk engine rejects ambiguous quantity.

    decision = await RiskEngine(settings).evaluate(parsed)

    if not decision.approved:
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="preview_rejected",
            raw_command=raw_command,
            parsed_payload=parsed.model_dump(),
            success=False,
            message=decision.reason,
        )
        raise OrderServiceError(decision.reason or "Order rejected by risk engine")

    pair = to_kraken_pair_altname(parsed.asset or "", parsed.quote_currency or settings.preferred_quote_currency)
    notional = (parsed.quantity or 0.0) * (parsed.limit_price or 0.0)

    pending = PendingConfirmation(
        id=str(uuid4()),
        user_id=user.id,
        raw_command=raw_command,
        parsed_payload=parsed.model_dump(),
        requires_two_step=decision.requires_two_step,
        expires_at=datetime.utcnow() + timedelta(seconds=CONFIRMATION_TTL_SECONDS),
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)

    audit_logger.log_event(
        db,
        user_id=user.id,
        event_type="preview_created",
        raw_command=raw_command,
        parsed_payload=parsed.model_dump(),
        result_payload={"confirmation_id": pending.id, "pair": pair, "notional": notional},
    )

    preview_payload = {
        "confirmation_id": pending.id,
        "pair": pair,
        "side": parsed.side,
        "order_type": "limit",
        "volume": parsed.quantity,
        "limit_price": parsed.limit_price,
        "notional_value": notional,
        "quote_currency": parsed.quote_currency or settings.preferred_quote_currency,
        "fees_estimate": None,
        "dry_run": settings.dry_run,
        "requires_two_step": decision.requires_two_step,
        "warnings": decision.warnings,
        "expires_at": pending.expires_at,
    }
    return pending, decision, preview_payload


async def confirm_and_place(
    db: Session,
    user: User,
    confirmation_id: str,
    second_factor_phrase: str | None,
) -> OrderResult:
    pending = db.query(PendingConfirmation).filter_by(id=confirmation_id, user_id=user.id).first()
    if not pending:
        raise OrderServiceError("Confirmation id not found")
    if pending.consumed:
        raise OrderServiceError("This confirmation has already been used")
    if datetime.utcnow() > pending.expires_at:
        raise OrderServiceError("Confirmation expired; please re-submit the command")

    if pending.requires_two_step:
        expected = "I CONFIRM"
        if (second_factor_phrase or "").strip().upper() != expected:
            raise OrderServiceError(
                f"Large order requires two-step confirmation: type the phrase '{expected}'"
            )

    parsed = ParsedCommand(**pending.parsed_payload)
    settings = _user_settings(db, user)

    # Re-run risk evaluation immediately before submission. Belt and suspenders.
    decision = await RiskEngine(settings).evaluate(parsed)
    if not decision.approved:
        pending.consumed = True
        db.commit()
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="confirm_rejected",
            raw_command=pending.raw_command,
            parsed_payload=parsed.model_dump(),
            success=False,
            message=decision.reason,
        )
        raise OrderServiceError(decision.reason or "Order rejected by risk engine on confirm")

    pair = to_kraken_pair_altname(parsed.asset or "", parsed.quote_currency or settings.preferred_quote_currency)
    notional = (parsed.quantity or 0.0) * (parsed.limit_price or 0.0)

    if settings.dry_run:
        pending.consumed = True
        record = OrderRecord(
            user_id=user.id,
            kraken_txid=None,
            pair=pair,
            side=parsed.side or "",
            order_type="limit",
            volume=parsed.quantity or 0.0,
            limit_price=parsed.limit_price or 0.0,
            notional_usd=notional,
            dry_run=True,
            status="dry_run_simulated",
            raw_command=pending.raw_command,
            response_payload={"simulated": True},
        )
        db.add(record)
        db.commit()
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="order_simulated",
            raw_command=pending.raw_command,
            parsed_payload=parsed.model_dump(),
            result_payload={"pair": pair, "volume": parsed.quantity, "price": parsed.limit_price},
        )
        return OrderResult(
            success=True,
            dry_run=True,
            kraken_txid=None,
            description=f"DRY RUN: would place {parsed.side} {parsed.quantity} {pair} @ {parsed.limit_price}",
        )

    try:
        api_key, api_secret = _user_credentials(db, user)
    except OrderServiceError:
        pending.consumed = True
        db.commit()
        raise

    try:
        async with KrakenClient(api_key=api_key, api_secret=api_secret) as kc:
            response = await kc.add_order(
                pair=pair,
                side=parsed.side or "",
                ordertype="limit",
                volume=parsed.quantity or 0.0,
                price=parsed.limit_price or 0.0,
            )
    except KrakenAPIError as ke:
        pending.consumed = True
        db.commit()
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="order_failed",
            raw_command=pending.raw_command,
            parsed_payload=parsed.model_dump(),
            success=False,
            message=str(ke),
        )
        return OrderResult(success=False, dry_run=False, error=f"Kraken: {ke}")
    except Exception as exc:  # network errors, etc.
        pending.consumed = True
        db.commit()
        audit_logger.log_event(
            db,
            user_id=user.id,
            event_type="order_failed",
            raw_command=pending.raw_command,
            parsed_payload=parsed.model_dump(),
            success=False,
            message=str(exc),
        )
        return OrderResult(success=False, dry_run=False, error=str(exc))

    txid_list = response.get("txid") or []
    txid = txid_list[0] if txid_list else None
    description = (response.get("descr") or {}).get("order")

    record = OrderRecord(
        user_id=user.id,
        kraken_txid=txid,
        pair=pair,
        side=parsed.side or "",
        order_type="limit",
        volume=parsed.quantity or 0.0,
        limit_price=parsed.limit_price or 0.0,
        notional_usd=notional,
        dry_run=False,
        status="submitted",
        raw_command=pending.raw_command,
        response_payload=response,
    )
    db.add(record)
    pending.consumed = True
    db.commit()

    audit_logger.log_event(
        db,
        user_id=user.id,
        event_type="order_submitted",
        raw_command=pending.raw_command,
        parsed_payload=parsed.model_dump(),
        result_payload={"txid": txid, "description": description},
    )
    return OrderResult(
        success=True,
        dry_run=False,
        kraken_txid=txid,
        description=description,
        raw_response=response,
    )
