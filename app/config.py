import os

class Settings:
    API_KEY: str = os.getenv("API_KEY", "")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "512"))

settings = Settings()
