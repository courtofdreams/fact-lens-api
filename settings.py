from pydantic_settings import BaseSettings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    TWITTER_API_KEY: str
    TWITTER_API_SECRET_KEY: str
    TWITTER_ACCESS_BEARER_TOKEN: str
    TWITTER_ACCESS_TOKEN: str
    TWITTER_ACCESS_TOKEN_SECRET: str
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    MONGO_DB_URI: str
    FIRECRAWL_API_KEY: str
    
    class Config:
        env_file = ".env"


settings = Settings()
logger.info(settings.NEO4J_URI)
logger.info("Settings loaded successfully.") # type: ignore