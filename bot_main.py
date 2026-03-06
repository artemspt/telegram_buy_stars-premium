import asyncio
import logging
import os

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import CustomEmoji, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Settings, load_settings
from db import Database

router = Router()
logger = logging.getLogger(__name__)
_settings: Settings | None = None
_db: Database | None = None


class PurchaseStates(StatesGroup):
    waiting_stars_username = State()
    waiting_stars_amount = State()
    waiting_premium_username = State()
    waiting_premium_months = State()


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def get_db() -> Database:
    if _db is None:
        raise RuntimeError("Database is not initialized")
    return _db


def get_api_config() -> tuple[str, dict[str, str]]:
    base_url = os.getenv("FRAG_API_BASE", "http://localhost:8000").rstrip("/")
    api_key = os.getenv("API_KEY", "").strip()
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return base_url, headers



async def build_order_start_link(bot: Bot, request_id: str) -> str | None:
    me = await bot.get_me()
    if not me.username:
        return None
    return f"https://t.me/{me.username}?start=order_{request_id}"


def format_order_details(order: dict) -> str:
    order_type = order["order_type"]
    if order_type == "premium":
        item = f"{order['premium_months']} мес."
        type_label = "Premium"
    else:
        item = f"{order['stars']} ⭐"
        type_label = "Stars"

    created_at = order["created_at"]
    created_text = (
        created_at.strftime("%Y-%m-%d %H:%M")
        if created_at is not None
        else "—"
    )

    recipient = order["recipient_username"] or "—"
    status = order["status"] or "—"
    request_id = order["request_id"] or "—"
    user_order_id = order["user_order_id"] or order["id"]
    tx_hash = order.get("transaction_hash") or "—"
    error_message = order.get("error_message") or "—"

    return (
        "Информация о покупке:\n"
        f"Номер: #{user_order_id}\n"
        f"Тип: {type_label}\n"
        f"Количество: {item}\n"
        f"Получатель: @{recipient}\n"
        f"Статус: {status}\n"
        f"Время: {created_text}\n"
        f"Request ID: {request_id}\n"
        f"TX Hash: {tx_hash}\n"
        f"Ошибка: {error_message}"
    )





async def execute_stars_purchase(
    message: Message,
    state: FSMContext,
    user_id: int,
    username: str | None,
    stars: int | None,
    order_request_id: str | None = None,
    user_order_id: int | None = None,
) -> None:
    if not username or stars is None:
        await message.answer("Не найдены данные заказа, начните заново")
        await state.clear()
        return

    db = get_db()
    if order_request_id is None or user_order_id is None:
        await db.upsert_user(user_id, message.from_user.username if message.from_user else None)
        user_order_id, request_id = await db.create_order(
            telegram_id=user_id,
            stars=stars,
            premium_months=None,
            recipient_username=username,
            order_type="stars",
            status="ожидается",
        )
    else:
        request_id = order_request_id

    base_url, headers = get_api_config()
    payload = {"username": username, "quantity": stars}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{base_url}/v1/stars/buy", json=payload, headers=headers)
        if resp.status_code != 200:
            error_text = f"HTTP {resp.status_code} | {resp.text}"
            await db.finalize_order(
                request_id=request_id,
                status="ошибка",
                error_message=error_text[:1000],
            )
            await message.answer(f"Ошибка API: HTTP {resp.status_code} | {resp.text}")
            await state.clear()
            return

        result = resp.json()
        tx_hash = str(result.get("transaction_hash") or "")
        await db.finalize_order(
            request_id=request_id,
            status="выполнен",
            transaction_hash=tx_hash or None,
            error_message=None,
        )
        order_link = await build_order_start_link(message.bot, request_id)
        order_ref = f"<a href=\"{order_link}\">Заказ</a>" if order_link else "Заказ"
        await message.answer(
            f"Готово. {order_ref} #{user_order_id} выполнен."
            + (f"\nTX: <code>{tx_hash}</code>" if tx_hash else "")
        )
    except Exception as exc:
        logger.exception("Stars purchase failed")
        await db.finalize_order(
            request_id=request_id,
            status="ошибка",
            error_message=str(exc)[:1000],
        )
        await message.answer(f"Ошибка запроса: {exc}")
    finally:
        await state.clear()


async def execute_premium_purchase(
    message: Message,
    state: FSMContext,
    user_id: int,
    username: str | None,
    months: int | None,
    order_request_id: str | None = None,
    user_order_id: int | None = None,
) -> None:
    if not username or months is None:
        await message.answer("Не найдены данные заказа, начните заново")
        await state.clear()
        return

    db = get_db()
    if order_request_id is None or user_order_id is None:
        await db.upsert_user(user_id, message.from_user.username if message.from_user else None)
        user_order_id, request_id = await db.create_order(
            telegram_id=user_id,
            stars=None,
            premium_months=months,
            recipient_username=username,
            order_type="premium",
            status="ожидается",
        )
    else:
        request_id = order_request_id

    base_url, headers = get_api_config()
    payload = {"username": username, "months": months}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{base_url}/v1/premium/buy", json=payload, headers=headers)
        if resp.status_code != 200:
            error_text = f"HTTP {resp.status_code} | {resp.text}"
            await db.finalize_order(
                request_id=request_id,
                status="ошибка",
                error_message=error_text[:1000],
            )
            await message.answer(f"Ошибка API: HTTP {resp.status_code} | {resp.text}")
            await state.clear()
            return

        result = resp.json()
        tx_hash = str(result.get("transaction_hash") or "")
        await db.finalize_order(
            request_id=request_id,
            status="выполнен",
            transaction_hash=tx_hash or None,
            error_message=None,
        )
        order_link = await build_order_start_link(message.bot, request_id)
        order_ref = f"<a href=\"{order_link}\">Заказ</a>" if order_link else "Заказ"
        await message.answer(
            f"Premium оформлен! {order_ref} #{user_order_id} выполнен."
            + (f"\nTX: <code>{tx_hash}</code>" if tx_hash else "")
        )
    except Exception as exc:
        logger.exception("Premium purchase failed")
        await db.finalize_order(
            request_id=request_id,
            status="ошибка",
            error_message=str(exc)[:1000],
        )
        await message.answer(f"Ошибка запроса: {exc}")
    finally:
        await state.clear()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    if message.from_user and message.text:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("order_"):
            request_id = parts[1][len("order_") :].strip()
            if request_id:
                db = get_db()
                order = await db.get_order_by_request_id_for_user(
                    message.from_user.id,
                    request_id,
                )
                if order is not None:
                    await message.answer(format_order_details(dict(order)))
                    return

    name = message.from_user.first_name if message.from_user else "друг"
    settings = get_settings()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⭐ Купить звёзды", callback_data="buy_stars")
    keyboard.button(text="Купить премиум 🎁", callback_data="buy_premium")
    keyboard.button(text="Профиль", callback_data="profile")
    keyboard.button(text="История покупок", callback_data="buys_history")
    keyboard.button(text="🆘 поддержка 🆘", callback_data="support")
    is_admin = message.from_user and message.from_user.id == settings.admin_id
    if is_admin:
        keyboard.button(text="Админ панель", callback_data="admin_panel")
        keyboard.adjust(2, 2, 1)
    else:
        keyboard.adjust(2, 2)

    text = Text(
        f"Добро пожаловать, {name} ",
        CustomEmoji("🙂", custom_emoji_id="5258079378159453410"),
    )
    await message.answer(**text.as_kwargs(), reply_markup=keyboard.as_markup())


@router.callback_query(F.data == "buy_stars")
async def buy_stars_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(PurchaseStates.waiting_stars_username)
    await callback.message.answer("Введите @username получателя звёзд")


@router.callback_query(F.data == "buy_premium")
async def buy_premium_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(PurchaseStates.waiting_premium_username)
    await callback.message.answer("Введите @username получателя Premium")


@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    db = get_db()
    await db.upsert_user(callback.from_user.id, callback.from_user.username)
    profile = await db.get_profile(callback.from_user.id)

    if profile is None:
        await callback.message.answer("Профиль не найден.")
        return

    created_at = profile["created_at"]
    created_text = (
        created_at.strftime("%Y-%m-%d %H:%M")
        if created_at is not None
        else "—"
    )
    text = (
        "<b>Ваш профиль:</b>\n"
        f"<blockquote>Заказов: {profile['orders_count']}</blockquote>\n"
        f"<blockquote>Куплено звёзд: {profile['total_stars_purchased']}</blockquote>\n"
        f"<blockquote>Куплено Premium (мес.): {profile['total_premium_months_purchased']}</blockquote>\n"
        f"<blockquote>Создан: {created_text}</blockquote>"
    )
    await callback.message.answer(text)


@router.callback_query(F.data == "buys_history")
async def buys_history_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    db = get_db()
    await db.upsert_user(callback.from_user.id, callback.from_user.username)
    orders = await db.get_purchase_history(callback.from_user.id, limit=10)

    if not orders:
        await callback.message.answer("История покупок пуста.")
        return

    keyboard = InlineKeyboardBuilder()
    for order in orders:
        order_type = order["order_type"]
        if order_type == "premium":
            item = f"{order['premium_months']} мес."
            type_label = "Premium"
        else:
            item = f"{order['stars']} ⭐"
            type_label = "Stars"

        status = order["status"] or "—"
        user_order_id = order["user_order_id"] or order["id"]
        keyboard.button(
            text=f"#{user_order_id} | {type_label} | {item} | {status}",
            callback_data=f"order_details:{order['id']}",
        )

    keyboard.adjust(1)
    await callback.message.answer(
        "Выберите покупку, чтобы посмотреть детали:",
        reply_markup=keyboard.as_markup(),
    )


@router.callback_query(F.data.startswith("order_details:"))
async def order_details_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None or callback.data is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    try:
        order_id = int(callback.data.split(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        await callback.message.answer("Некорректный идентификатор заказа.")
        return

    db = get_db()
    order = await db.get_order_by_id_for_user(callback.from_user.id, order_id)
    if order is None:
        await callback.message.answer("Заказ не найден.")
        return

    await callback.message.answer(format_order_details(dict(order)))


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    settings = get_settings()
    support_username = settings.admin_username or "sptsupport"
    await callback.message.answer(
        f"По всем вопросам и предложениям обращаться @{support_username}"
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    settings = get_settings()
    if callback.from_user.id != settings.admin_id:
        await callback.message.answer("Доступ запрещён.")
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Статистика", callback_data="admin_stats")
    keyboard.adjust(1)
    await callback.message.answer(
        "Админ панель:",
        reply_markup=keyboard.as_markup(),
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    settings = get_settings()
    if callback.from_user.id != settings.admin_id:
        await callback.message.answer("Доступ запрещён.")
        return

    db = get_db()
    stats = await db.get_global_stats()
    updated_at = stats["updated_at"]
    updated_text = (
        updated_at.strftime("%Y-%m-%d %H:%M")
        if updated_at is not None
        else "—"
    )

    text = (
        "Глобальная статистика бота:\n"
        f"Пользователей: {stats['total_users']}\n"
        f"Заказов всего: {stats['total_orders']}\n"
        f"Успешных транзакций: {stats['total_success_orders']}\n"
        f"Ошибок: {stats['failed_orders']}\n"
        f"Куплено звёзд (всего): {stats['total_stars_purchased']}\n"
        f"Куплено Premium (мес., всего): {stats['total_premium_months_purchased']}\n"
        f"Обновлено: {updated_text}"
    )
    await callback.message.answer(text)


@router.message(Command("paid"))
async def mark_paid_command(message: Message) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    settings = get_settings()
    if message.from_user.id != settings.admin_id:
        await message.answer("Доступ запрещён.")
        return

    parts = (message.text or "").strip().split()
    if len(parts) != 4:
        await message.answer("Использование: /paid <memo> <tx_hash> <amount_nano>")
        return

    _, memo, tx_hash, amount_raw = parts
    if not amount_raw.isdigit():
        await message.answer("amount_nano должен быть числом.")
        return

    amount_nano = int(amount_raw)
    db = get_db()
    invoice = await db.get_payment_invoice_by_memo(memo)
    if invoice is None:
        await message.answer("Инвойс по memo не найден.")
        return

    await db.mark_payment_invoice_paid(
        invoice_id=int(invoice["id"]),
        tx_hash=tx_hash,
        paid_amount_nano=amount_nano,
    )
    await message.answer(
        f"Оплата принята: invoice #{invoice['id']} | order {invoice['order_request_id']}"
    )


@router.message(PurchaseStates.waiting_stars_username)
async def submit_stars_username(message: Message, state: FSMContext) -> None:
    username = (message.text or "").strip().lstrip("@")
    if not username:
        await message.answer("Введите корректный username")
        return

    await state.update_data(stars_username=username)
    await state.set_state(PurchaseStates.waiting_stars_amount)
    await message.answer("Введите количество звёзд для покупки (50-1000000)")


@router.message(PurchaseStates.waiting_premium_username)
async def submit_premium_username(message: Message, state: FSMContext) -> None:
    username = (message.text or "").strip().lstrip("@")
    if not username:
        await message.answer("Введите корректный username")
        return

    await state.update_data(premium_username=username)
    await state.set_state(PurchaseStates.waiting_premium_months)
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="3 месяца", callback_data="premium_months:3")
    keyboard.button(text="6 месяцев", callback_data="premium_months:6")
    keyboard.button(text="12 месяцев", callback_data="premium_months:12")
    keyboard.adjust(3)
    await message.answer(
        "Выберите срок Premium:",
        reply_markup=keyboard.as_markup(),
    )


@router.message(PurchaseStates.waiting_stars_amount)
async def submit_stars_purchase(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        await state.clear()
        return

    raw_value = (message.text or "").strip()
    if not raw_value.isdigit():
        await message.answer("Количество звёзд должно быть числом")
        return

    stars = int(raw_value)
    if stars < 50 or stars > 1000000:
        await message.answer("Допустимый диапазон: 50-1000000")
        return

    data = await state.get_data()
    username = data.get("stars_username")
    if not username:
        await message.answer("Не найден username, начните заново")
        await state.clear()
        return

    await state.update_data(stars_amount=stars)
    await execute_stars_purchase(
        message=message,
        state=state,
        user_id=message.from_user.id,
        username=username,
        stars=stars,
        order_request_id=data.get("stars_order_request_id"),
        user_order_id=data.get("stars_user_order_id"),
    )

@router.callback_query(F.data.startswith("premium_months:"))
async def submit_premium_purchase(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.data is None:
        return
    if callback.from_user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        await state.clear()
        return

    state_value = await state.get_state()
    if state_value != PurchaseStates.waiting_premium_months.state:
        await callback.message.answer("Сначала выберите пользователя для Premium.")
        return

    try:
        months = int(callback.data.split(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        await callback.message.answer("Некорректный срок Premium.")
        return

    if months not in {3, 6, 12}:
        await callback.message.answer("Доступные варианты: 3, 6 или 12 месяцев.")
        return

    data = await state.get_data()
    username = data.get("premium_username")
    if not username:
        await callback.message.answer("Не найден username, начните заново")
        await state.clear()
        return

    await state.update_data(premium_months=months)
    await execute_premium_purchase(
        message=callback.message,
        state=state,
        user_id=callback.from_user.id,
        username=username,
        months=months,
        order_request_id=data.get("premium_order_request_id"),
        user_order_id=data.get("premium_user_order_id"),
    )





async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    global _settings, _db
    _settings = load_settings()
    _db = Database(
        host=_settings.db_host,
        port=_settings.db_port,
        user=_settings.db_user or "",
        password=_settings.db_password or "",
        database=_settings.db_name or "",
    )
    await _db.connect()

    bot = Bot(
        token=_settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        if _db is not None:
            await _db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
