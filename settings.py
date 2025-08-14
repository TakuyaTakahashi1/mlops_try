cat > settings.py <<'PY'
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    db_url: str = ""   # mypyが読む時点のダミー値
    api_key: str = ""  # 実行時は .env で上書きされる

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
PY

