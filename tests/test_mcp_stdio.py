import subprocess
import sys


def test_mcp_stdio_startup_keeps_stdout_protocol_clean():
    result = subprocess.run(
        [sys.executable, "main.py", "mcp-server", "--transport", "stdio"],
        input="",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
