import json
from pathlib import Path

from bank_mcp.server import create_app


async def test_tool_contract_matches_reviewed_snapshot(settings):
    tools = await create_app(settings).state.mcp.list_tools()
    actual = [tool.model_dump(by_alias=True, exclude_none=True) for tool in tools]
    expected = json.loads(Path("docs/tool-contract.json").read_text(encoding="utf-8"))
    assert actual == expected, "Revise y apruebe los cambios de esquemas o descripciones."
