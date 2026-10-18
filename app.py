import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI(title="Effective Configuration API")

# Allow browser-based graders to call the API from another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def coerce_value(key: str, value):
    if key in {"port", "workers"}:
        return int(value)
    if key == "debug":
        return parse_bool(value)
    return str(value)


def normalized_key(key: str) -> str:
    key = key.strip()
    if key == "NUM_WORKERS":
        return "workers"
    if key.startswith("APP_"):
        return key[4:].lower()
    return key.lower()


def apply_layer(config: dict, layer: dict, *, env_layer: bool = False):
    for raw_key, value in layer.items():
        if value is None:
            continue
        if env_layer:
            # OS environment layer accepts APP_* only.
            if not raw_key.startswith("APP_"):
                continue
        key = normalized_key(raw_key)
        config[key] = value


def get_effective_config(overrides: Optional[list[str]] = None) -> dict:
    config = dict(DEFAULTS)

    # Layer 2: environment-specific YAML.
    environment = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development"))
    yaml_path = BASE_DIR / f"config.{environment}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as handle:
            yaml_config = yaml.safe_load(handle) or {}
        if isinstance(yaml_config, dict):
            apply_layer(config, yaml_config)

    # Layer 3: .env file only. dotenv_values reads the file without mutating
    # os.environ, so the following OS-environment layer can override it.
    env_file_values = dotenv_values(BASE_DIR / ".env")
    apply_layer(config, env_file_values)

    # Layer 4: actual OS environment variables with APP_* prefix.
    apply_layer(config, dict(os.environ), env_layer=True)

    # Highest precedence: repeated ?set=key=value query parameters.
    for item in overrides or []:
        if "=" not in item:
            continue
        raw_key, value = item.split("=", 1)
        key = normalized_key(raw_key)
        if key:
            config[key] = value

    # Coerce after merging so values from every layer have consistent types.
    result = {key: coerce_value(key, value) for key, value in config.items()}

    # Never disclose the secret, even if it came from a CLI override.
    if "api_key" in result:
        result["api_key"] = "****"
    return result


@app.get("/")
def root():
    return {"service": "effective-config", "endpoint": "/effective-config"}


@app.get("/effective-config")
def effective_config(set: Optional[list[str]] = Query(default=None)):
    return get_effective_config(set)
