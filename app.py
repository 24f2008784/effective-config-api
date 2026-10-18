
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

BASE_DIR = Path(__file__).resolve().parent


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def normalize_key(key):
    key = key.strip()
    if key == "NUM_WORKERS":
        return "workers"
    if key.startswith("APP_"):
        return key[4:].lower()
    return key.lower()


def merge_layer(config, layer, os_layer=False):
    for key, value in layer.items():
        if value is None:
            continue
        if os_layer and not key.startswith("APP_"):
            continue
        config[normalize_key(key)] = value


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    config = DEFAULTS.copy()

    # YAML layer
    env_name = os.environ.get(
        "APP_ENV",
        os.environ.get("ENVIRONMENT", "development")
    )
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"

    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
        if isinstance(yaml_config, dict):
            merge_layer(config, yaml_config)

    # .env layer
    merge_layer(config, dotenv_values(BASE_DIR / ".env"))

    # OS environment layer
    merge_layer(config, dict(os.environ), os_layer=True)

    # CLI/query overrides (highest precedence)
    for item in set or []:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = normalize_key(key)
        if key in DEFAULTS:
            config[key] = value

    # Ensure all required keys exist and have the correct types
    result = {
        "port": int(config.get("port", 8000)),
        "workers": int(config.get("workers", 1)),
        "debug": to_bool(config.get("debug", False)),
        "log_level": str(config.get("log_level", "info")),
        "api_key": "****",
    }

    return result
