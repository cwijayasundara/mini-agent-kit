"""Run `mini-agent run` and save the trace under traces/ for the maintain loop.

Usage: uv run python tools/traced_run.py --script s.json "question"
Then:  uv run python tools/maintain.py traces
"""

import sys
import time
from pathlib import Path

from mini_agent_kit.cli import main

if __name__ == "__main__":
    traces = Path("traces")
    traces.mkdir(exist_ok=True)
    out = traces / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    code = main(["run", *sys.argv[1:], "--trace", str(out)])
    print(f"trace: {out}")
    sys.exit(code)
