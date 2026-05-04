from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from .. import audit_logger, order_service
from ..auth import CurrentUser, DbSession
from ..command_parser import parse_command
from ..schemas import (
    ConfirmRequest,
    OrderPreview,
    OrderResult,
    ParsedCommand,
    ParseRequest,
)


router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("/parse", response_model=ParsedCommand)
def parse(payload: ParseRequest, user: CurrentUser, db: DbSession) -> ParsedCommand:
    parsed = parse_command(payload.text)
    audit_logger.log_event(
        db,
        user_id=user.id,
        event_type="command_parsed",
        raw_command=payload.text,
        parsed_payload=parsed.model_dump(),
        success=parsed.rejection_reason is None,
        message=parsed.rejection_reason,
    )
    return parsed


class PreviewRequest(BaseModel):
    text: str


@router.post("/preview", response_model=OrderPreview)
async def preview(payload: PreviewRequest, user: CurrentUser, db: DbSession) -> OrderPreview:
    parsed = parse_command(payload.text)
    if parsed.intent != "place_order":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Preview is only for place_order intent (got '{parsed.intent}'): "
            + (parsed.rejection_reason or "no further details"),
        )
    if parsed.rejection_reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, parsed.rejection_reason)

    try:
        _, _, preview_payload = await order_service.build_preview(db, user, parsed, payload.text)
    except order_service.OrderServiceError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return OrderPreview(**preview_payload)


@router.post("/confirm", response_model=OrderResult)
async def confirm(payload: ConfirmRequest, user: CurrentUser, db: DbSession) -> OrderResult:
    if not payload.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "confirm must be true")
    try:
        result = await order_service.confirm_and_place(
            db,
            user,
            payload.confirmation_id,
            payload.second_factor_phrase,
        )
    except order_service.OrderServiceError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return result
