from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""   # only needed for real document uploads; not required for test cases
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
