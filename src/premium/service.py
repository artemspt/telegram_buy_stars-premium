import re

from src.exceptions import BadRequest, ResourceNotFound
from src.fragment import fragment
from src.fragment.enums import PremiumMonths
from src.fragment.exceptions import FragmentBadRequest
from src.kit.utils import after_fee
from src.logging import get_logger
from src.premium.schemas import PremiumRecipient
from src.ton_wallet import wallet

log = get_logger()


class PremiumService:
    async def buy(
        self, username: str, months: PremiumMonths
    ) -> str:
        try:
            recipient_data = await fragment.search_premium_recipient(
                query=username, months=months
            )
        except FragmentBadRequest as exc:
            raise BadRequest(str(exc))

        buy_premium_request = await fragment.init_premium_request(
            recipient=recipient_data.found.recipient, months=months
        )

        premium_ton_price = after_fee(buy_premium_request.amount)
        balance = await wallet.balance()
        if balance < premium_ton_price:
            raise BadRequest("We have insufficcient funds")

        link = await fragment.get_premium_link(req_id=buy_premium_request.req_id)

        try:
            tx_hash = await wallet.transfer_from_tc(
                message=link.transaction.messages[0],
                valid_until=link.transaction.valid_until,
            )

            log.info(
                "New buy premium transaction!",
                hash=tx_hash,
                username=username,
                months=months,
            )

            return tx_hash

        except Exception as exc:
            log.error(
                "Failed to transfer premium",
                error=str(exc),
                username=username,
                months=months,
            )
            raise

    async def get_recipient(self, username: str) -> PremiumRecipient:
        try:
            recipient_data = await fragment.search_premium_recipient(query=username)
        except FragmentBadRequest:
            raise ResourceNotFound("No recipient found")

        photo_match = re.search(r'src="(.*)"', recipient_data.found.photo)

        return PremiumRecipient(
            recipient=recipient_data.found.recipient,
            name=recipient_data.found.name,
            photo=photo_match.group(1) if photo_match else None,
        )


premium_service = PremiumService()
