from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl


class Settings(BaseSettings):
    app_env: str = "local" # local|dev|stg|prod
    api_host: str = "0.0.0.0"
    api_port: int = 8000


    # Groq
    groq_api_key: str
    groq_base_url: AnyUrl = "https://api.groq.com"
    groq_model: str = "openai/gpt-oss-20b"


    # Mongo
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "npcdb"

    # faiss
    faiss_path: str = "Data/index.faiss"
    faiss_meta_path: str = "Data/index.faiss.meta.jsonl"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()