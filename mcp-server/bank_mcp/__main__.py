import uvicorn
from pydantic import ValidationError

from bank_mcp.config import Settings
from bank_mcp.server import configure_logging, create_app

try:
    settings = Settings.from_env()
except (ValidationError, ValueError, OSError):
    raise SystemExit(
        "Configuración inválida. Revise README.md y docs/AZURE.md. "
        "Para iniciar la demo: python scripts/demo.py init"
    ) from None
configure_logging()
uvicorn.run(
    create_app(settings),
    host="127.0.0.1" if settings.app_env == "local" else "0.0.0.0",
    port=8000,
    access_log=False,
    log_level="warning",
    proxy_headers=False,
)
