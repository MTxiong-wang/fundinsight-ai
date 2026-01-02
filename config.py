"""配置管理"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """应用配置"""

    # AI Provider
    AI_PROVIDER = os.getenv("AI_PROVIDER", "zhipu")
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # AI Models (可配置)
    ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4.7")  # 默认使用glm-4.7
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Scraping
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    TIMEOUT = int(os.getenv("TIMEOUT", "30000"))

    # Cache
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 24 hours
    CACHE_FILE = "data/cache.json"

    @classmethod
    def validate(cls):
        """验证配置"""
        if cls.AI_PROVIDER == "zhipu" and not cls.ZHIPU_API_KEY:
            raise ValueError("ZHIPU_API_KEY is required when using zhipu provider")
        if cls.AI_PROVIDER == "deepseek" and not cls.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is required when using deepseek provider")
        if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using openai provider")
