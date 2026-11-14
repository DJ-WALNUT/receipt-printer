"""인쇄 대기열. 작업을 한 번에 하나씩 꺼내, 장마다 콘텐츠 스크립트를 새 프로세스로 실행한다.

프린터가 한 대라서 작업자 스레드도 하나다. 방문자 작업은 한 번에 하나만 받고(나머지는 Busy),
운영자 작업은 뒤에 쌓인다.
"""
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import hub

KEEP_FINISHED = 50
ACTIVE = ("queued", "running")

MSG_TIMEOUT = "시간이 너무 오래 걸려 멈췄습니다. 다시 시도해 주세요."
MSG_PRINTER = "프린터 연결을 확인해 주세요."
MSG_CRASH = "인쇄하지 못했습니다. 선생님께 알려 주세요."
MSG_UNKNOWN = "인쇄하지 못했습니다."
PRINTER_SIGNS = ("SerialException", "could not open port", "PermissionError")


class Busy(Exception):
    """방문자 작업이 이미 대기 중이거나 인쇄 중이다."""


@dataclass(eq=False)
class Job:
    id: str
    title: str
    role: str
    sheets: int
    done: int = 0
    state: str = "queued"   # queued | running | done | failed | cancelled
    message: str = ""
    content: object = field(default=None, repr=False)
    args: list = field(default_factory=list, repr=False)
    cancel: bool = field(default=False, repr=False)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "state": self.state,
                "done": self.done, "sheets": self.sheets, "message": self.message}


def friendly(returncode, output):
    """스크립트의 실패를 화면에 보여줄 한 문장으로 바꾼다. returncode가 None이면 시간 초과."""
    if returncode is None:
        return MSG_TIMEOUT
    if any(sign in output for sign in PRINTER_SIGNS):
        return MSG_PRINTER
    if "Traceback" in output:
        return MSG_CRASH
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return MSG_UNKNOWN
    return re.sub(r"^\S+\.py: error: ", "", lines[-1])  # argparse의 "sudoku.py: error: ..." 머리를 뗀다


def run_script(script: Path, args: list, timeout: float):
    """스크립트를 실행한다. (성공 여부, 실패했을 때 보여줄 문장)"""
    try:
        r = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, cwd=hub.ROOT,
                           env={**os.environ, "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired:
        return False, friendly(None, "")
    if r.returncode == 0:
        return True, ""
    return False, friendly(r.returncode, r.stderr)


class JobQueue:
    def __init__(self, runner=run_script, preview=False, timeout=180, sleep=time.sleep):
        self.runner = runner
        self.preview = preview
        self.timeout = timeout
        self.sleep = sleep
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._queue = deque()
        self._jobs = {}            # id -> Job, 만든 순서대로
        self._last_start = {}      # 콘텐츠 이름 -> 마지막으로 실행을 시작한 시각
        self._closed = False
        threading.Thread(target=self._work, name="print-queue", daemon=True).start()

    # ---- 바깥에서 부르는 것

    def submit(self, content, args, sheets, role):
        with self._wake:
            if role != hub.STAFF and any(j.role != hub.STAFF and j.state in ACTIVE for j in self._jobs.values()):
                raise Busy()
            job = Job(uuid.uuid4().hex[:12], content.title, role, sheets, content=content, args=list(args))
            self._jobs[job.id] = job
            self._queue.append(job)
            self._wake.notify()
            return job

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def jobs(self):
        with self._lock:
            return list(self._jobs.values())

    def cancel_all(self):
        """대기 작업은 바로 취소하고, 인쇄 중인 작업은 지금 장까지만 뽑고 멈춘다. 손댄 작업 수를 돌려준다."""
        with self._lock:
            touched = 0
            for job in self._jobs.values():
                if job.state == "queued":
                    job.state = "cancelled"
                    touched += 1
                elif job.state == "running" and not job.cancel:
                    job.cancel = True
                    touched += 1
            self._queue.clear()
            return touched

    def close(self):
        with self._wake:
            self._closed = True
            self._wake.notify()

    # ---- 작업자 스레드

    def _work(self):
        while True:
            with self._wake:
                while not self._queue and not self._closed:
                    self._wake.wait()
                if self._closed:
                    return
                job = self._queue.popleft()
                job.state = "running"
            try:
                state, message = self._run(job)
            except Exception:  # 대기열은 어떤 작업 때문에도 멈추면 안 된다
                state, message = "failed", MSG_CRASH
            with self._lock:
                job.state, job.message = state, message
                self._prune()

    def _run(self, job):
        content = job.content
        args = job.args + (["--preview"] if self.preview else [])
        for _ in range(job.sheets):
            if job.cancel:
                return "cancelled", ""
            self._pace(content)
            ok, message = self.runner(content.script, args, self.timeout)
            if not ok:
                return "failed", message or MSG_UNKNOWN
            with self._lock:
                job.done += 1
        return "done", ""

    def _pace(self, content):
        """같은 콘텐츠를 연달아 실행할 때 wait_between 만큼 간격을 둔다 (작업이 달라도)."""
        last = self._last_start.get(content.name)
        if content.wait_between and last is not None:
            remaining = content.wait_between - (time.monotonic() - last)
            if remaining > 0:
                self.sleep(remaining)
        self._last_start[content.name] = time.monotonic()

    def _prune(self):
        finished = [j for j in self._jobs.values() if j.state not in ACTIVE]
        for job in finished[:-KEEP_FINISHED]:
            del self._jobs[job.id]
