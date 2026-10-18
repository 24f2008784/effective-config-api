# Effective Configuration API

FastAPI service implementing precedence:
defaults -> config.<environment>.yaml -> .env -> OS APP_* variables -> repeated ?set=key=value overrides.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Test:
`http://127.0.0.1:8000/effective-config?set=port=9000&set=debug=true`

Set `APP_ENV` to select another YAML file, e.g. `config.production.yaml`.
CORS is enabled for all origins (without credentials) for browser-based grading.
The API key is always returned as `****`.
