"""인쇄 대기열: 한 번에 하나씩, 장마다 스크립트를 실행한다."""
import pytest

import hub
from fakes import FakeRunner, content, wait
from kiosk.jobs import Busy, JobQueue, friendly, run_script


def test_runs_each_sheet_and_finishes():
    r = FakeRunner()
    q = JobQueue(runner=r)
    job = q.submit(content(), ["--level", "hard"], 3, hub.VISITOR)
    wait(job, "done")
    assert job.done == 3 and len(r.calls) == 3
    assert r.calls[0][0].name == "thing.py" and r.calls[0][1] == ["--level", "hard"]
    assert job.to_dict() == {"id": job.id, "title": "아무거나", "state": "done", "done": 3, "sheets": 3, "message": "",
                             "same": False}
    assert q.get(job.id) is job and q.get("nope") is None


def test_preview_flag_is_appended():
    r = FakeRunner()
    q = JobQueue(runner=r, preview=True)
    wait(q.submit(content(), ["--x"], 1, hub.VISITOR), "done")
    assert r.calls[0][1] == ["--x", "--preview"]


def test_second_visitor_is_refused_while_first_is_active():
    r = FakeRunner(gate=True)
    q = JobQueue(runner=r)
    first = q.submit(content(), [], 1, hub.VISITOR)
    with pytest.raises(Busy):
        q.submit(content(), [], 1, hub.VISITOR)
    staff = q.submit(content(), [], 1, hub.STAFF)
    assert staff.state == "queued"
    r.gate.set()
    wait(first, "done")
    wait(staff, "done")
    assert q.submit(content(), [], 1, hub.VISITOR)


def test_visitor_is_refused_while_a_visitor_job_is_only_queued():
    r = FakeRunner(gate=True)
    q = JobQueue(runner=r)
    q.submit(content(), [], 1, hub.STAFF)            # 실행 중
    q.submit(content(), [], 1, hub.VISITOR)          # 대기 중
    with pytest.raises(Busy):
        q.submit(content(), [], 1, hub.VISITOR)
    r.gate.set()


def test_failure_stops_remaining_sheets_and_queue_continues():
    r = FakeRunner(results=[(True, ""), (False, "시간이 너무 오래 걸려 멈췄습니다. 다시 시도해 주세요.")])
    q = JobQueue(runner=r)
    bad = q.submit(content(), [], 4, hub.STAFF)
    nxt = q.submit(content(), [], 1, hub.STAFF)
    wait(bad, "failed")
    assert bad.done == 1 and "오래" in bad.message
    wait(nxt, "done")
    assert len(r.calls) == 3                          # 실패한 작업의 남은 두 장은 뽑지 않았다


def test_runner_crash_fails_the_job_but_not_the_queue():
    def boom(script, args, timeout):
        raise RuntimeError("boom")
    q = JobQueue(runner=boom)
    bad = q.submit(content(), [], 1, hub.STAFF)
    wait(bad, "failed")
    assert bad.message == "인쇄하지 못했습니다. 선생님께 알려 주세요."
    q.runner = FakeRunner()
    wait(q.submit(content(), [], 1, hub.STAFF), "done")


def test_cancel_all():
    r = FakeRunner(gate=True)
    q = JobQueue(runner=r)
    running = q.submit(content(), [], 5, hub.STAFF)
    queued = q.submit(content(), [], 1, hub.STAFF)
    wait(running, "running")
    assert q.cancel_all() == 2
    assert queued.state == "cancelled"
    r.gate.set()
    wait(running, "cancelled")
    assert running.done == 1 and len(r.calls) == 1    # 뽑던 장까지만 뽑고 멈춘다


def test_wait_between_applies_across_jobs():
    naps = []
    q = JobQueue(runner=FakeRunner(), sleep=naps.append)
    c = content(wait_between=5)
    q.submit(c, [], 1, hub.STAFF)
    b = q.submit(c, [], 1, hub.STAFF)
    wait(b, "done")
    assert len(naps) == 1 and 4 < naps[0] <= 5
    other = q.submit(content(wait_between=5, name="other"), [], 1, hub.STAFF)
    wait(other, "done")
    assert len(naps) == 1                             # 다른 콘텐츠는 기다리지 않는다


def test_jobs_lists_oldest_first_and_keeps_only_recent_finished():
    q = JobQueue(runner=FakeRunner())
    made = [q.submit(content(), [], 1, hub.STAFF) for _ in range(55)]
    wait(made[-1], "done")
    listed = q.jobs()
    assert len(listed) == 50 and listed[-1] is made[-1] and listed[0] is made[5]
    assert q.get(made[0].id) is None


@pytest.mark.parametrize("code,out,expected", [
    (None, "", "시간이 너무 오래 걸려 멈췄습니다. 다시 시도해 주세요."),
    (1, "Traceback (most recent call last):\n  x\nserial.serialutil.SerialException: could not open port '/dev/ttyACM0'",
     "프린터 연결을 확인해 주세요."),
    (1, "Traceback (most recent call last):\n  x\nPermissionError: [Errno 13] Permission denied: '/dev/ttyACM0'",
     "프린터 연결을 확인해 주세요."),
    (1, "Traceback (most recent call last):\n  x\nKeyError: 'x'", "인쇄하지 못했습니다. 선생님께 알려 주세요."),
    (1, "오류: 아이디 'x'을(를) 찾을 수 없습니다. 인쇄하지 않았습니다.\n",
     "오류: 아이디 'x'을(를) 찾을 수 없습니다. 인쇄하지 않았습니다."),
    (2, "usage: sudoku.py [-h] [--level {easy,medium,hard}]\nsudoku.py: error: 시드번호는 S로 시작합니다 (예: SM482913)\n",
     "시드번호는 S로 시작합니다 (예: SM482913)"),
    (2, "", "인쇄하지 못했습니다."),
])
def test_friendly(code, out, expected):
    assert friendly(code, out) == expected


def test_run_script_times_out(tmp_path):
    s = tmp_path / "slow.py"
    s.write_text("import time; time.sleep(30)", encoding="utf-8")
    ok, msg = run_script(s, [], timeout=1)
    assert ok is False and "오래" in msg


def test_run_script_reports_exit_message_and_success(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('import sys; sys.exit("없는 시드번호입니다.")', encoding="utf-8")
    assert run_script(bad, [], timeout=30) == (False, "없는 시드번호입니다.")
    good = tmp_path / "good.py"
    good.write_text('import sys; print("한글 출력", sys.argv[1:])', encoding="utf-8")
    assert run_script(good, ["--a", "가나"], timeout=30) == (True, "")


# ---------------------------------------------------------------- 같은 문제 여러 장

def test_same_job_runs_once_with_copies():
    r = FakeRunner()
    q = JobQueue(runner=r, preview=True, timeout=100)
    job = q.submit(content(), ["--level", "hard"], 4, hub.VISITOR, same=True)
    wait(job, "done")
    assert len(r.calls) == 1 and job.done == 4
    assert r.calls[0][1] == ["--level", "hard", "--copies", "4", "--preview"]
    assert r.calls[0][2] == 100 + 15 * 3              # 장 수만큼 제한 시간을 늘린다
    assert job.to_dict()["same"] is True


def test_same_job_failure_is_reported_and_queue_continues():
    r = FakeRunner(results=[(False, "프린터 연결을 확인해 주세요.")])
    q = JobQueue(runner=r)
    bad = q.submit(content(), [], 3, hub.STAFF, same=True)
    nxt = q.submit(content(), [], 1, hub.STAFF)
    wait(bad, "failed")
    assert bad.done == 0 and "프린터" in bad.message
    wait(nxt, "done")


def test_cancel_before_start_skips_a_same_job():
    r = FakeRunner(gate=True)
    q = JobQueue(runner=r)
    running = q.submit(content(), [], 1, hub.STAFF)
    same = q.submit(content(), [], 3, hub.STAFF, same=True)
    wait(running, "running")
    q.cancel_all()
    r.gate.set()
    wait(running, "done")                             # 뽑던 한 장은 끝까지 뽑는다
    assert same.state == "cancelled" and same.done == 0 and len(r.calls) == 1
