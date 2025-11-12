from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 既存
    db_url: str | None = None
    api_key: str | None = None

    # A17: Playwright用の設定を追加
    playwright_login_url: str | None = None
    playwright_username: str | None = None
    playwright_password: str | None = None
    playwright_target_url: str | None = None

    # 共通設定
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ← .envに知らないキーがあっても落ちないようにする
        case_sensitive=False,  # ← PLAYWRIGHT_... の大文字小文字をゆるく
    )


settings = Settings()  # .env から読み込み
