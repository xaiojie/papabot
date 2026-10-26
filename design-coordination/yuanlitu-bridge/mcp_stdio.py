"""MCP stdio frontend; starts a loopback bridge when it isn't already running."""
import atexit
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from client import call

ROOT = Path(__file__).resolve().parent
mcp = FastMCP("yuanlitu-mac-desktop-assistant")


@mcp.tool()
def eda_health() -> dict:
    """Read project/page, requiring the user's DesktopAssistant_RevA project."""
    return call("system.health")


@mcp.tool()
def eda_list_pages() -> dict:
    """List schematic pages in the current guarded project."""
    return call("schematic.listPages")


@mcp.tool()
def eda_inspect_page(pageUuid: str, includeWires: bool = True) -> dict:
    """Read schematic components, library IDs, pins, labels and wires."""
    return call("schematic.inspectPage", {"pageUuid": pageUuid, "includeWires": includeWires})


@mcp.tool()
def eda_search_components(query: str, limit: int = 10) -> list:
    """Search the EDA device library. Verify returned symbol and footprint."""
    return call("library.searchComponents", {"query": query, "limit": limit})


@mcp.tool()
def eda_validate_operations(operations: list[dict[str, Any]]) -> dict:
    """Validate an operation batch without editing. Maximum 100 operations."""
    return call("operations.validate", {"operations": operations})


@mcp.tool()
def eda_apply_operations(sessionId: str, operations: list[dict[str, Any]]) -> dict:
    """Edit native schematic with mandatory session backup. No PCB API.

    Supported types: create_component (pageUuid, libraryUuid, deviceUuid, x,y,
    rotation, designator, addIntoBom, addIntoPcb); create_wire (pageUuid,line,net);
    connect_pins (pageUuid,from/to {componentId,pinNumber},net,horizontalFirst);
    create_net_port (pageUuid,direction,net,x,y,rotation); create_text
    (pageUuid,text,x,y,fontSize,bold); set_no_connects
    (pageUuid,componentId,pinNumbers,noConnected); move_component
    (pageUuid,componentId,x,y); set_component_attribute
    (pageUuid,componentId,key,value,keyVisible,valueVisible); rename_page
    (pageUuid,name). Other extension whitelist operations are described in the
    adapter README. Inspect before retrying any failed write; batches are not atomic.
    """
    return call("operations.apply", {"sessionId": sessionId, "operations": operations})


@mcp.tool()
def eda_run_schematic_drc(pageUuid: str) -> dict:
    """Run native schematic DRC. This is not a PCB fabrication check."""
    return call("schematic.runDrc", {"pageUuid": pageUuid})


def ensure_bridge():
    try:
        with socket.create_connection(("127.0.0.1", 49640), timeout=1):
            return
    except OSError:
        pass
    log = (ROOT / "bridge.log").open("a")
    proc = subprocess.Popen([sys.executable, str(ROOT / "bridge.py")], stdout=log, stderr=log)
    atexit.register(proc.terminate)
    for _ in range(30):
        if proc.poll() is not None:
            raise RuntimeError("Local bridge startup failed; inspect bridge.log")
        try:
            with socket.create_connection(("127.0.0.1", 49640), timeout=.2):
                return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("Local bridge did not start")


if __name__ == "__main__":
    ensure_bridge()
    mcp.run(transport="stdio")
