from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql://user:password@localhost:5436/open_sg_law"
    elitigation_base_url: str = "https://www.elitigation.sg"
    sso_base_url: str = "https://sso.agc.gov.sg"


settings = AppSettings()
