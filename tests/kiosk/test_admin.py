"""관리 페이지: 이용실적 기록·합계·CSV, 만들어진 이미지 보기·지우기."""
import datetime
import time

import pytest

import hub
from fakes import FakeRunner, content, wait
from kiosk.jobs import JobQueue
from kiosk.server import create_app
from kiosk.usage import UsageLog, summarize

TOML = '''
title = "스도쿠"
seed_prefix = "S"
[[mode]]
id = "new"
label = "새 판"
'''


def make_root(tmp_path):
    folder = tmp_path / "root" / "sudoku"
    folder.mkdir(parents=True)
    (folder / "content.toml").write_text(TOML, encoding="utf-8")
    (folder / "sudoku.py").write_text("", encoding="utf-8")
    out = folder / "output"
    out.mkdir()
    for name in ["20261115_101500_SM111111.png", "20261117_090000_SM222222.png", "20261117_093000.png"]:
        (out / name).write_bytes(b"\x89PNG fake")
    (out / "notes.txt").write_text("x", encoding="utf-8")
    return tmp_path / "root"


@pytest.fixture
def admin(tmp_path):
    runner = FakeRunner()
    app = create_app(queue=JobQueue(runner=runner), pin="1234", root=make_root(tmp_path),
                     usage_path=tmp_path / "usage.csv")
    c = app.test_client()
    c.usage_path = tmp_path / "usage.csv"
    return c


def login(c):
    assert c.post("/api/admin/login", json={"pin": "1234"}).status_code == 200


def poll(c, job_id, state):
    deadline = time.time() + 3
    while time.time() < deadline:
        job = c.get(f"/api/jobs/{job_id}").get_json()
        if job["state"] == state:
            return job
        time.sleep(0.01)
    raise AssertionError(job)


def test_admin_page_and_apis_need_staff(admin):
    assert admin.get("/admin").status_code == 200
    assert admin.get("/api/admin/me").get_json()["role"] == "visitor"
    for url in ["/api/admin/stats", "/api/admin/usage.csv", "/api/admin/images",
                "/api/admin/images/sudoku/20261117_090000_SM222222.png"]:
        assert admin.get(url).status_code == 403
    assert admin.delete("/api/admin/images/sudoku/20261117_090000_SM222222.png").status_code == 403
    login(admin)
    assert admin.get("/api/admin/me").get_json()["role"] == "staff"


def test_finished_print_is_recorded_and_summed(admin):
    job = admin.post("/api/print", json={"content": "sudoku", "mode": "new", "values": {}, "sheets": 2}).get_json()
    poll(admin, job["id"], "done")
    deadline = time.time() + 3
    while not admin.usage_path.exists() and time.time() < deadline:
        time.sleep(0.01)
    login(admin)
    stats = admin.get("/api/admin/stats").get_json()
    assert stats["total"] == {"jobs": 1, "sheets": 2, "visitor_sheets": 2, "staff_sheets": 0, "failed": 0}
    assert stats["by_content"][0]["name"] == "sudoku" and stats["by_content"][0]["title"] == "스도쿠"
    assert len(stats["by_date"]) == 30 and stats["by_date"][-1]["sheets"] == 2
    csv = admin.get("/api/admin/usage.csv")
    text = csv.data.decode("utf-8")
    assert text.startswith("﻿시각,콘텐츠") and "sudoku,스도쿠,new,visitor,2,2,done" in text
    assert "attachment" in csv.headers["Content-Disposition"]


def test_stats_period_is_checked(admin):
    login(admin)
    assert admin.get("/api/admin/stats?from=2026-11-01&to=2026-11-03").get_json()["by_date"][0]["date"] == "2026-11-01"
    for bad in ["from=2026-11-05&to=2026-11-01", "from=어제", "to=2026-13-01", "from=2000-01-01&to=2026-01-01"]:
        assert admin.get("/api/admin/stats?" + bad).status_code == 400


def test_images_list_view_filter_and_delete(admin):
    login(admin)
    d = admin.get("/api/admin/images").get_json()
    assert d["total"] == 3 and [i["file"] for i in d["images"]][0] == "20261117_093000.png"
    assert d["images"][1]["tag"] == "SM222222" and d["images"][1]["time"] == "2026-11-17 09:00:00"
    assert {"name": "sudoku", "title": "스도쿠", "count": 3} in d["contents"]
    assert admin.get("/api/admin/images?date=2026-11-15").get_json()["total"] == 1
    assert admin.get("/api/admin/images?content=nope").get_json()["total"] == 0
    assert admin.get("/api/admin/images?offset=2").get_json()["images"][0]["file"] == "20261115_101500_SM111111.png"
    r = admin.get("/api/admin/images/sudoku/20261117_090000_SM222222.png")
    assert r.status_code == 200 and r.data.startswith(b"\x89PNG")
    r.close()   # Windows에서는 열린 파일을 지울 수 없다
    for bad in ["sudoku/notes.txt", "nope/20261117_090000_SM222222.png", "sudoku/..%2Fsudoku.py"]:
        assert admin.get("/api/admin/images/" + bad).status_code == 404
    assert admin.delete("/api/admin/images/sudoku/20261117_090000_SM222222.png").status_code == 200
    assert admin.get("/api/admin/images").get_json()["total"] == 2
    assert admin.delete("/api/admin/images/sudoku/20261117_090000_SM222222.png").status_code == 404


def test_queue_records_failures_and_cancelled_jobs(tmp_path):
    log = UsageLog(tmp_path / "u.csv")
    runner = FakeRunner(results=[(False, "프린터 연결을 확인해 주세요.")], gate=True)
    q = JobQueue(runner=runner, on_finish=log.record)
    first = q.submit(content(), [], 1, hub.STAFF, mode="new")
    second = q.submit(content(), [], 3, hub.STAFF, mode="new")
    deadline = time.time() + 3
    while first.state != "running" and time.time() < deadline:
        time.sleep(0.01)
    q.cancel_all()
    runner.gate.set()
    wait(first, "failed")
    deadline = time.time() + 3
    while len(log.rows()) < 2 and time.time() < deadline:
        time.sleep(0.01)
    rows = log.rows()
    assert sorted(r["state"] for r in rows) == ["cancelled", "failed"]
    assert all(r["role"] == "staff" and r["mode"] == "new" for r in rows)
    assert second.state == "cancelled"


def test_a_broken_log_does_not_stop_the_queue():
    def boom(job):
        raise OSError("disk full")
    q = JobQueue(runner=FakeRunner(), on_finish=boom)
    wait(q.submit(content(), [], 1, hub.VISITOR), "done")
    wait(q.submit(content(), [], 1, hub.VISITOR), "done")


def test_summarize_fills_empty_days_and_skips_broken_lines(tmp_path):
    path = tmp_path / "u.csv"
    path.write_text("﻿머리\n2026-11-02 10:00:00,a,가,new,visitor,2,2,done,,\n깨진 줄\n"
                    "2026-11-02 11:00:00,a,가,new,staff,5,1,failed,,오류\n", encoding="utf-8")
    rows = UsageLog(path).rows()
    s = summarize(rows, datetime.date(2026, 11, 1), datetime.date(2026, 11, 3))
    assert s["total"] == {"jobs": 2, "sheets": 3, "visitor_sheets": 2, "staff_sheets": 1, "failed": 1}
    assert [d["sheets"] for d in s["by_date"]] == [0, 3, 0]
