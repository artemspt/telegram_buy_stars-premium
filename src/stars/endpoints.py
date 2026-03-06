from fastapi import Depends

from src.logging import get_logger
from src.security import require_api_key

from .schemas import BuyStars, BuyStarsResponse, StarsRecipient
from .service import stars_service

from fastapi import APIRouter

router = APIRouter(prefix="/stars", tags=["Stars"])

log = get_logger()


@router.post(
    "/buy", description="Buy stars for a user. Takes user username and stars quantity"
)
async def buy_stars(
    data: BuyStars,
    _: None = Depends(require_api_key),
) -> BuyStarsResponse:
    tx_hash = await stars_service.buy(
        quantity=data.quantity,
        username=data.username,
    )

    return BuyStarsResponse(success=True, transaction_hash=tx_hash)


@router.get("/recipient/{username}", description="Get stars recipient")
async def get_recipient(
    username: str, _: None = Depends(require_api_key)
) -> StarsRecipient:
    log.info("Search stars recipient request", username=username)

    return await stars_service.get_recipient(username=username)
