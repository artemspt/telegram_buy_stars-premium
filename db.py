import asyncpg


class Database:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            min_size=1,
            max_size=5,
        )
        await self._create_tables()

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def _create_tables(self) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    balance NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    total_stars_purchased BIGINT NOT NULL DEFAULT 0,
                    total_premium_months_purchased INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS balance NUMERIC(12, 2) NOT NULL DEFAULT 0;
                """
            )
            await conn.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS total_stars_purchased BIGINT NOT NULL DEFAULT 0;
                """
            )
            await conn.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS total_premium_months_purchased INTEGER NOT NULL DEFAULT 0;
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS star_orders (
                    id BIGSERIAL PRIMARY KEY,
                    request_id TEXT UNIQUE,
                    user_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    user_order_id INTEGER,
                    order_type TEXT NOT NULL DEFAULT 'stars',
                    stars INTEGER CHECK (stars > 0),
                    premium_months INTEGER,
                    recipient_username TEXT,
                    status TEXT NOT NULL DEFAULT 'ожидается',
                    transaction_hash TEXT,
                    error_message TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ALTER COLUMN stars DROP NOT NULL;
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS order_type TEXT NOT NULL DEFAULT 'stars';
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS request_id TEXT UNIQUE;
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS user_order_id INTEGER;
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS premium_months INTEGER;
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS recipient_username TEXT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS transaction_hash TEXT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE star_orders
                ADD COLUMN IF NOT EXISTS error_message TEXT;
                """
            )
            await conn.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'star_orders_user_order_unique'
                    ) THEN
                        ALTER TABLE star_orders
                        ADD CONSTRAINT star_orders_user_order_unique
                        UNIQUE (user_id, user_order_id);
                    END IF;
                END $$;
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id SMALLINT PRIMARY KEY CHECK (id = 1),
                    total_success_orders BIGINT NOT NULL DEFAULT 0,
                    total_stars_purchased BIGINT NOT NULL DEFAULT 0,
                    total_premium_months_purchased BIGINT NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                INSERT INTO bot_stats (
                    id,
                    total_success_orders,
                    total_stars_purchased,
                    total_premium_months_purchased,
                    updated_at
                )
                SELECT
                    1,
                    COUNT(*)::BIGINT,
                    COALESCE(SUM(stars), 0)::BIGINT,
                    COALESCE(SUM(premium_months), 0)::BIGINT,
                    NOW()
                FROM star_orders
                WHERE status = 'выполнен'
                ON CONFLICT (id) DO NOTHING;
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_invoices (
                    id BIGSERIAL PRIMARY KEY,
                    order_request_id TEXT NOT NULL REFERENCES star_orders(request_id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    provider TEXT NOT NULL,
                    network TEXT,
                    amount_nano BIGINT NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'TON',
                    pay_to_address TEXT,
                    memo TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    tx_hash TEXT UNIQUE,
                    paid_amount_nano BIGINT,
                    paid_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS network TEXT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'TON';
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS pay_to_address TEXT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS tx_hash TEXT UNIQUE;
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS paid_amount_nano BIGINT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS error_message TEXT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE payment_invoices
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_payment_invoices_user_created
                ON payment_invoices (user_id, created_at DESC);
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_payment_invoices_status_expires
                ON payment_invoices (status, expires_at);
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_payment_invoices_order_request_id
                ON payment_invoices (order_request_id);
                """
            )

    async def upsert_user(self, telegram_id: int, username: str | None) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (telegram_id, username)
                VALUES ($1, $2)
                ON CONFLICT (telegram_id)
                DO UPDATE SET username = EXCLUDED.username;
                """,
                telegram_id,
                username,
            )

    async def create_order(
        self,
        telegram_id: int,
        stars: int | None,
        premium_months: int | None,
        recipient_username: str,
        order_type: str = "stars",
        status: str = "ожидается",
        request_id: str | None = None,
    ) -> tuple[int, str]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        if order_type == "stars" and (stars is None or stars <= 0):
            raise ValueError("Stars amount must be provided for stars order")
        if order_type == "premium" and premium_months not in {3, 6, 12}:
            raise ValueError("Premium months must be 3, 6 or 12")

        async with self._pool.acquire() as conn:
            user_order_id = await conn.fetchval(
                """
                SELECT COALESCE(MAX(user_order_id), 0) + 1
                FROM star_orders
                WHERE user_id = $1;
                """,
                telegram_id,
            )
            resolved_request_id = request_id or f"order-{telegram_id}-{user_order_id}"
            row = await conn.fetchrow(
                """
                INSERT INTO star_orders (
                    request_id,
                    user_id,
                    user_order_id,
                    order_type,
                    stars,
                    premium_months,
                    recipient_username,
                    status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING user_order_id, request_id;
                """,
                resolved_request_id,
                telegram_id,
                user_order_id,
                order_type,
                stars,
                premium_months,
                recipient_username,
                status,
            )
            if row is None:
                raise RuntimeError("Failed to create order")
            return int(row["user_order_id"]), str(row["request_id"])

    async def update_order_status(self, order_id: int, status: str) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE star_orders
                SET status = $2
                WHERE id = $1;
                """,
                order_id,
                status,
            )

    async def finalize_order(
        self,
        request_id: str,
        status: str,
        transaction_hash: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                order = await conn.fetchrow(
                    """
                    SELECT
                        user_id,
                        order_type,
                        stars,
                        premium_months,
                        status
                    FROM star_orders
                    WHERE request_id = $1
                    FOR UPDATE;
                    """,
                    request_id,
                )
                if order is None:
                    raise RuntimeError("Order not found")

                await conn.execute(
                    """
                    UPDATE star_orders
                    SET
                        status = $2,
                        transaction_hash = $3,
                        error_message = $4
                    WHERE request_id = $1;
                    """,
                    request_id,
                    status,
                    transaction_hash,
                    error_message,
                )

                is_new_success = status == "выполнен" and order["status"] != "выполнен"
                if is_new_success:
                    stars_to_add = int(order["stars"] or 0)
                    premium_months_to_add = int(order["premium_months"] or 0)
                    await conn.execute(
                        """
                        UPDATE users
                        SET
                            total_stars_purchased = total_stars_purchased + $2,
                            total_premium_months_purchased = total_premium_months_purchased + $3
                        WHERE telegram_id = $1;
                        """,
                        int(order["user_id"]),
                        stars_to_add,
                        premium_months_to_add,
                    )
                    await conn.execute(
                        """
                        UPDATE bot_stats
                        SET
                            total_success_orders = total_success_orders + 1,
                            total_stars_purchased = total_stars_purchased + $1,
                            total_premium_months_purchased = total_premium_months_purchased + $2,
                            updated_at = NOW()
                        WHERE id = 1;
                        """,
                        stars_to_add,
                        premium_months_to_add,
                    )

    async def create_payment_invoice(
        self,
        order_request_id: str,
        user_id: int,
        provider: str,
        amount_nano: int,
        memo: str,
        expires_at,
        network: str | None = "ton-mainnet",
        currency: str = "TON",
        pay_to_address: str | None = None,
    ) -> asyncpg.Record:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        if amount_nano <= 0:
            raise ValueError("amount_nano must be positive")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO payment_invoices (
                    order_request_id,
                    user_id,
                    provider,
                    network,
                    amount_nano,
                    currency,
                    pay_to_address,
                    memo,
                    status,
                    expires_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9, NOW())
                RETURNING
                    id,
                    order_request_id,
                    user_id,
                    provider,
                    network,
                    amount_nano,
                    currency,
                    pay_to_address,
                    memo,
                    status,
                    tx_hash,
                    paid_amount_nano,
                    paid_at,
                    expires_at,
                    error_message,
                    created_at,
                    updated_at;
                """,
                order_request_id,
                user_id,
                provider,
                network,
                amount_nano,
                currency,
                pay_to_address,
                memo,
                expires_at,
            )
            if row is None:
                raise RuntimeError("Failed to create payment invoice")
            return row

    async def get_payment_invoice_by_memo(
        self,
        memo: str,
    ) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT
                    id,
                    order_request_id,
                    user_id,
                    provider,
                    network,
                    amount_nano,
                    currency,
                    pay_to_address,
                    memo,
                    status,
                    tx_hash,
                    paid_amount_nano,
                    paid_at,
                    expires_at,
                    error_message,
                    created_at,
                    updated_at
                FROM payment_invoices
                WHERE memo = $1;
                """,
                memo,
            )

    async def get_payment_invoice_by_order_request_id(
        self,
        order_request_id: str,
    ) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT
                    id,
                    order_request_id,
                    user_id,
                    provider,
                    network,
                    amount_nano,
                    currency,
                    pay_to_address,
                    memo,
                    status,
                    tx_hash,
                    paid_amount_nano,
                    paid_at,
                    expires_at,
                    error_message,
                    created_at,
                    updated_at
                FROM payment_invoices
                WHERE order_request_id = $1
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                order_request_id,
            )

    async def mark_payment_invoice_paid(
        self,
        invoice_id: int,
        tx_hash: str,
        paid_amount_nano: int,
    ) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        if paid_amount_nano <= 0:
            raise ValueError("paid_amount_nano must be positive")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payment_invoices
                SET
                    status = 'paid',
                    tx_hash = $2,
                    paid_amount_nano = $3,
                    paid_at = NOW(),
                    error_message = NULL,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                invoice_id,
                tx_hash,
                paid_amount_nano,
            )

    async def update_payment_invoice_status(
        self,
        invoice_id: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payment_invoices
                SET
                    status = $2,
                    error_message = $3,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                invoice_id,
                status,
                error_message,
            )

    async def expire_pending_payment_invoices(self) -> list[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetch(
                """
                UPDATE payment_invoices
                SET
                    status = 'expired',
                    updated_at = NOW()
                WHERE status = 'pending' AND expires_at < NOW()
                RETURNING id, order_request_id, memo;
                """
            )

    async def add_balance(self, telegram_id: int, amount: float) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET balance = balance + $2
                WHERE telegram_id = $1;
                """,
                telegram_id,
                amount,
            )

    async def get_profile(self, telegram_id: int) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT
                    u.telegram_id,
                    u.username,
                    u.balance,
                    u.created_at,
                    COUNT(o.id) AS orders_count,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN o.status = 'выполнен' THEN COALESCE(o.stars, 0)
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_stars_purchased,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN o.status = 'выполнен' THEN COALESCE(o.premium_months, 0)
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_premium_months_purchased
                FROM users u
                LEFT JOIN star_orders o ON o.user_id = u.telegram_id
                WHERE u.telegram_id = $1
                GROUP BY
                    u.telegram_id,
                    u.username,
                    u.balance,
                    u.created_at;
                """,
                telegram_id,
            )

    async def get_purchase_history(
        self,
        telegram_id: int,
        limit: int = 10,
    ) -> list[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT
                    id,
                    request_id,
                    user_order_id,
                    order_type,
                    stars,
                    premium_months,
                    recipient_username,
                    status,
                    created_at
                FROM star_orders
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )

    async def get_order_by_request_id(
        self,
        request_id: str,
    ) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT
                    id,
                    request_id,
                    user_id,
                    user_order_id,
                    order_type,
                    stars,
                    premium_months,
                    recipient_username,
                    status,
                    created_at
                FROM star_orders
                WHERE request_id = $1;
                """,
                request_id,
            )

    async def get_order_by_id_for_user(
        self,
        telegram_id: int,
        order_id: int,
    ) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT
                    id,
                    request_id,
                    user_id,
                    user_order_id,
                    order_type,
                    stars,
                    premium_months,
                    recipient_username,
                    status,
                    transaction_hash,
                    error_message,
                    created_at
                FROM star_orders
                WHERE id = $1 AND user_id = $2;
                """,
                order_id,
                telegram_id,
            )

    async def get_order_by_request_id_for_user(
        self,
        telegram_id: int,
        request_id: str,
    ) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT
                    id,
                    request_id,
                    user_id,
                    user_order_id,
                    order_type,
                    stars,
                    premium_months,
                    recipient_username,
                    status,
                    transaction_hash,
                    error_message,
                    created_at
                FROM star_orders
                WHERE request_id = $1 AND user_id = $2;
                """,
                request_id,
                telegram_id,
            )

    async def get_global_stats(self) -> asyncpg.Record:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    b.total_success_orders,
                    b.total_stars_purchased,
                    b.total_premium_months_purchased,
                    b.updated_at,
                    (SELECT COUNT(*) FROM users) AS total_users,
                    (SELECT COUNT(*) FROM star_orders) AS total_orders,
                    (SELECT COUNT(*) FROM star_orders WHERE status = 'ошибка') AS failed_orders
                FROM bot_stats b
                WHERE b.id = 1;
                """
            )
            if stats is None:
                raise RuntimeError("Global stats are not initialized")
            return stats
