import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run_script(script, *args, preview=True):
    """콘텐츠 스크립트를 실제로 실행한다. (returncode, stdout, stderr)"""
    cmd = [sys.executable, str(ROOT / script), *args] + (["--preview"] if preview else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1"}, timeout=300, cwd=ROOT)
    return r.returncode, r.stdout, r.stderr
