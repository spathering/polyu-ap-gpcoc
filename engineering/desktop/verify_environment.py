"""Read the shared dependency lock; no duplicate dependency version list."""
import importlib
import importlib.metadata
import json
import re
import struct
import sys
from pathlib import Path

def verify(config_path, project_root):
    settings = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    expected = settings["python"]["version"]
    actual = ".".join(map(str, sys.version_info[:3]))
    if actual != expected or struct.calcsize("P") != 8:
        raise RuntimeError(f"Python must be {expected} x64; got {actual}")
    lock = Path(project_root) / settings["dependencies"]["lockFile"]
    count = 0
    for line in lock.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)\s+--hash=sha256:[0-9a-f]{64}$", line)
        if not match:
            raise RuntimeError("Unsupported dependency lock line: " + line)
        name, version = match.groups()
        if importlib.metadata.version(name) != version:
            raise RuntimeError("Dependency version mismatch: " + name)
        count += 1
    if not count:
        raise RuntimeError("Dependency lock is empty")
    for module in settings["dependencies"]["probeModules"]:
        importlib.import_module(module)
    print(f"DEPENDENCIES_OK {count}", flush=True)

if __name__ == "__main__":
    verify(sys.argv[1], sys.argv[2])
