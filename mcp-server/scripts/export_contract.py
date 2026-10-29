"""Exporta el contrato para revisar cambios de herramientas antes del despliegue."""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bank_mcp.server import create_app


async def main():
    tools = await create_app().state.mcp.list_tools()
    payload = (
        json.dumps(
            [tool.model_dump(by_alias=True, exclude_none=True) for tool in tools],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    target = Path("docs/tool-contract.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    Path("docs/tool-contract.sha256").write_text(
        hashlib.sha256(payload.encode()).hexdigest() + "\n"
    )
    print("Contrato exportado. Revise el diff antes de aprobar cambios.")


if __name__ == "__main__":
    asyncio.run(main())
