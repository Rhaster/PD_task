"""Settings for application, utilizing pydantic"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl, Field

class Settings(BaseSettings):
    app_env: str = Field("local", env="APP_ENV")
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")

    # Groq
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_base_url: AnyUrl = Field("https://api.groq.com", env="GROQ_BASE_URL")
    groq_model: str = Field("openai/gpt-oss-20b", env="GROQ_MODEL")

    # Mongo
    mongo_uri: str = Field("mongodb://mongo:27017", env="MONGO_URI")
    mongo_db: str = Field("npcdb", env="MONGO_DB")

    # faiss
    faiss_path: str = Field("App/Data/index.faiss", env="FAISS_PATH")
    faiss_meta_path: str = Field("App/Data/index.faiss.meta.jsonl", env="FAISS_META_PATH")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",  
        extra="ignore"
    )

settings = Settings()
