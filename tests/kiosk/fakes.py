"""키오스크 테스트용 가짜 실행기와 도우미."""
import threading
import time
from pathlib import Path

import hub


class FakeRunner:
    """스크립트를 실행하는 대신 호출을 기록한다. gate=True면 gate.set() 전까지 실행 중인 채로 멈춘다."""

    def __init__(self, results=None, gate=False):
        self.calls = []
        self.results = list(results or [])
        self.gate = threading.Event()
        if not gate:
            self.gate.set()

    def __call__(self, script, args, timeout):
        self.calls.append((script, list(args), timeout))
        self.gate.wait(5)
        return self.results.pop(0) if self.results else (True, "")


def content(wait_between=0, name="thing", title="아무거나"):
    return hub.Content(name, title, 10, None, Path(f"{name}.py"), True, wait_between, None, ())


def wait(job, state, seconds=3):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if job.state == state:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job is {job.state!r}, expected {state!r} ({job.message})")
