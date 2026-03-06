import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    admin_username: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment")

    admin_id_raw = os.getenv("ADMIN_ID", "").strip()
    if not admin_id_raw:
        raise RuntimeError("ADMIN_ID is not set in environment")

    db_name = os.getenv("DB_NAME", "").strip()
    if not db_name:
        raise RuntimeError("DB_NAME is not set in environment")

    db_user = os.getenv("DB_USER", "").strip()
    if not db_user:
        raise RuntimeError("DB_USER is not set in environment")

    db_password = os.getenv("DB_PASSWORD", "").strip()
    if not db_password:
        raise RuntimeError("DB_PASSWORD is not set in environment")

    return Settings(
        bot_token=token,
        admin_id=int(admin_id_raw),
        admin_username=os.getenv("ADMIN_USERNAME", "sptsupport").strip().lstrip("@"),
        db_host=os.getenv("DB_HOST", "localhost").strip(),
        db_port=int(os.getenv("DB_PORT", "5432").strip()),
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    )
