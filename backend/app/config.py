from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment.

    Nothing here has a secret as its default. DATABASE_URL is supplied by
    docker-compose locally and by a Kubernetes Secret in the cluster, so the
    same image runs in both places without a rebuild.
    """

    database_url: str = "postgresql+psycopg2://mltracker:mltracker@db:5432/mltracker"
    app_name: str = "ML Experiment Tracker"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
