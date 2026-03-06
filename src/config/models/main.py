from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .server import Server


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    ton_api_key: SecretStr
    wallet_mnemonic: list[SecretStr]
    api_key: SecretStr | None = None
    server: Server = Server()

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None

    log_level: str = "DEBUG"
    fragment_session_path: str = "fragment_api/fragment_session.json"

    def get_secret_wallet_mnemonic(self) -> list[str]:
        return [word.get_secret_value() for word in self.wallet_mnemonic]
