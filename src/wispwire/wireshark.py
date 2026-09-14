"""Safe Wireshark tool discovery."""

import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

VERSION_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)+)")


@dataclass(frozen=True)
class ToolStatus:
    """External tool availability check result."""

    name: str
    path: Path | None
    version: str | None
    error: str | None


def inspect_tool(
    name: str,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ToolStatus:
    """Check tool availability and detect its version without raising exceptions."""
    tool_path = which(name)
    if tool_path is None:
        return ToolStatus(name, None, None, "tool not found in PATH")

    path = Path(tool_path)
    try:
        result = run(
            [tool_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return ToolStatus(name, path, None, "tool response timed out")
    except OSError as error:
        return ToolStatus(name, path, None, f"could not start tool: {error}")

    if result.returncode != 0:
        return ToolStatus(
            name,
            path,
            None,
            f"tool exited with code {result.returncode}",
        )

    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    version_match = VERSION_PATTERN.search(first_line)
    if version_match is None:
        return ToolStatus(name, path, None, "could not detect tool version")

    return ToolStatus(name, path, version_match.group(1), None)
