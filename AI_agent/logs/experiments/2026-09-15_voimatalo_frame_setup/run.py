from pathlib import Path
import json,subprocess
command=json.loads(Path(__file__).with_name("command.json").read_text())
raise SystemExit(subprocess.call(command))
