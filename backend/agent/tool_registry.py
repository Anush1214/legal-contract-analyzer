import logging
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field
from backend.agent.tools import (
    search_contract,
    get_clause,
    search_statutes,
    search_cases,
    compare_contracts_tool
)

logger = logging.getLogger("agent.registry")

# Whitelist of allowed tool functions
TOOL_REGISTRY: Dict[str, Callable] = {
    "search_contract": search_contract,
    "get_clause": get_clause,
    "search_statutes": search_statutes,
    "search_cases": search_cases,
    "compare_contracts": compare_contracts_tool
}

def is_tool_allowed(name: str) -> bool:
    """Validate tool name against whitelist to prevent arbitrary function execution."""
    return name in TOOL_REGISTRY

def get_whitelisted_tools() -> list:
    """Return the list of callable functions for the Google GenAI client."""
    return [
        search_contract,
        get_clause,
        search_statutes,
        search_cases,
        compare_contracts_tool
    ]

def execute_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered tool safely with argument forwarding and error capture."""
    if not is_tool_allowed(tool_name):
        error_msg = f"SECURITY ALERT: Rejected unauthorized or unknown tool call '{tool_name}'."
        logger.warning(error_msg)
        return {"error": error_msg}

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        return tool_fn(**args)
    except TypeError as te:
        error_msg = f"Invalid arguments passed to tool '{tool_name}': {te}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error executing tool '{tool_name}': {e}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}
