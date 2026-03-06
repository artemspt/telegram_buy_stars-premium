import re

from src.exceptions import BadRequest, ResourceNotFound
from src.fragment import fragment
from src.fragment.exceptions import FragmentBadRequest
from src.kit.utils import after_fee
from src.logging import get_logger
from src.ton_wallet import wallet

from .schemas import StarsRecipient

log = get_logger()


class StarsService:
    async def buy(
        self, quantity: int, username: str
    ) -> str:
        log.info(
            "Buy stars request",
            username=username,
            quantity=quantity,
        )

        if quantity < 50:
            raise ValueError("Stars amount should be bigger than 50")

        try:
            recipient_data = await fragment.search_stars_recipient(
                query=username, quantity=quantity
            )
        except FragmentBadRequest as exc:
            raise BadRequest(str(exc))

        buy_stars_request = await fragment.init_buy_stars_request(
            recipient=recipient_data.found.recipient, quantity=quantity
        )

        stars_ton_price = after_fee(buy_stars_request.amount)
        balance = await wallet.balance()
        if balance < stars_ton_price:
            raise BadRequest("We have insufficcient funds")

        link = await fragment.get_buy_stars_link(req_id=buy_stars_request.req_id)

        try:
            tx_hash = await wallet.transfer_from_tc(
                message=link.transaction.messages[0],
                valid_until=link.transaction.valid_until,
            )

            log.info(
                "New buy stars transaction!",
                hash=tx_hash,
                username=username,
                quantity=quantity,
            )

            return tx_hash

        except Exception as exc:
            log.exception(
                "Stars transaction failed",
                error=str(exc),
                exc_type=type(exc).__name__,
                username=username,
                quantity=quantity,
            )
            raise

    async def get_recipient(self, username: str) -> StarsRecipient:
        try:
            recipient_data = await fragment.search_stars_recipient(query=username)
        except FragmentBadRequest:
            raise ResourceNotFound("No recipient found")

        photo_match = re.search(r'src="(.*)"', recipient_data.found.photo)

        return StarsRecipient(
            recipient=recipient_data.found.recipient,
            name=recipient_data.found.name,
            photo=photo_match.group(1) if photo_match else None,
        )


stars_service = StarsService()
