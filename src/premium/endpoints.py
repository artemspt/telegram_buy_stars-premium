from fastapi import APIRouter, Depends

from src.logging import get_logger
from src.security import require_api_key

from .schemas import BuyPremium, BuyPremiumResponse, PremiumRecipient
from .service import premium_service

router = APIRouter(prefix="/premium", tags=["Premium"])

log = get_logger()


@router.post(
    "/buy",
    description="Buy premium subscription for a user. Takes user username and premium months",
)
async def buy_premium(
    data: BuyPremium,
    _: None = Depends(require_api_key),
) -> BuyPremiumResponse:
    tx_hash = await premium_service.buy(
        username=data.username,
        months=data.months,
    )

    return BuyPremiumResponse(success=True, transaction_hash=tx_hash)


@router.get("/recipient/{username}", description="Get premium recipient")
async def get_recipient(
    username: str, _: None = Depends(require_api_key)
) -> PremiumRecipient:
    log.info("Search premium recipient request", username=username)

    return await premium_service.get_recipient(username=username)
