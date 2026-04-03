# Anansi Project Memory

## Project
AI-powered multimodal education for African classrooms. Named after the Akan spider deity.
- Repo: `/home/gasmyr/AI_SPACE/anansi`
- Branch convention: feature branches off `main`
- Python 3.12, managed with `uv`, source layout `src/anansi/`

## Architecture
6-node LangGraph agent + FastMCP cultural context server + Streamlit UI.
Node execution: N1 → N2 → N3 → [N4 ‖ N6] → N5

## FastMCP Server (COMPLETE — mcp-server branch)
- FastMCP 3.1.1 installed
- Server: `src/anansi/context/server.py` — `mcp = FastMCP('anansi-context')`
- Tools registered via `register_tools(mcp, repo)` in `context/tools.py`
- Repository: `src/anansi/context/repository.py` — loads all *.json at startup
- 5 country packs in `src/anansi/context/data/` (kenya, nigeria, senegal, ghana, cameroon)
- Transport: stdio (default) or http via `MCP_TRANSPORT` env var
- In-process test client: `from fastmcp import Client; async with Client(mcp) as c: ...`
- `result.structured_content` → dict; `result.data.<field>` → attribute access

## Key Models
- `CountryData` (Pydantic) at `src/anansi/core/models/context.py`
- MCP return models (NamesResult etc.) defined in `context/tools.py`
- `AnansiState` TypedDict stub at `src/anansi/agent/state.py` — NOT YET IMPLEMENTED

## Tests
- 57 tests passing (21 unit + 36 integration) as of mcp-server branch
- Run: `uv run pytest tests/unit/context/ tests/integration/test_mcp_server.py`
- All tests complete in ~1.6s (in-process, no subprocess/network)

## Remaining Work (28 stub files)
Grouped into 13 GitHub issues — see plan file for full breakdown.
Priority order: core models → state/config → llm factory → nodes (N1→N2→N3→N4‖N6→N5) → graph wiring → UI

## Next Steps
- Create 13 GitHub issues as planned
- Implement agent nodes (N1–N6) in `src/anansi/agent/nodes/`
- Implement `AnansiState` TypedDict in `src/anansi/agent/state.py`
- Implement `src/anansi/infrastructure/llm.py` config factory
- Node 2 Localizer calls MCP server via stdio subprocess
