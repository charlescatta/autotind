from dynaconf import Dynaconf, Validator

config = Dynaconf(
    envvar_prefix="TIND",
    settings_file="config.toml",
    env_file=True,
    validators=[
        Validator("DB_URL", must_exist=True, default="sqlite:///tind.db"),
        Validator("IMG_SAVE_PATH", must_exist=True, default="./images"),
    ])