"""키오스크 서버: 메뉴를 내려주고, 인쇄 요청을 검사해 대기열에 넣는다."""
import os
import time

import pytest

import hub
from fakes import FakeRunner
from kiosk.jobs import JobQueue
from kiosk.server import cleanup_outputs, create_app


def make_client(pin="1234", gate=False):
    runner = FakeRunner(gate=gate)
    app = create_app(queue=JobQueue(runner=runner), pin=pin)
    client = app.test_client()
    client.runner = runner
    return client


@pytest.fixture(autouse=True)
def usage_in_tmp(tmp_path, monkeypatch):
    """테스트가 진짜 이용실적 파일(kiosk/data/usage.csv)에 쓰지 않게 한다."""
    path = tmp_path / "usage.csv"
    monkeypatch.setattr("kiosk.server.USAGE_PATH", path)
    return path


@pytest.fixture
def client():
    return make_client()


def poll(client, job_id, state, seconds=3):
    deadline = time.time() + seconds
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").get_json()
        if job["state"] == state:
            return job
        time.sleep(0.01)
    raise AssertionError(job)


def all_items(menu):
    for item in menu:
        yield from (all_items(item["items"]) if item["kind"] == "group" else [item])


def test_index_and_fonts(client):
    assert client.get("/").status_code == 200
    font = client.get("/fonts/Galmuri11.ttf")
    assert font.status_code == 200 and len(font.data) > 10000
    assert client.get("/fonts/LICENSE.txt").status_code == 404
    assert client.get("/fonts/../hub.py").status_code == 404


def test_catalog_for_visitor(client):
    d = client.get("/api/catalog").get_json()
    assert d["role"] == "visitor" and d["max_sheets"] == 4 and d["admin_enabled"] is True
    items = {i["name"]: i for i in all_items(d["menu"])}
    assert "text" not in items and len(items) == 17
    assert [m["id"] for m in items["bingo"]["modes"]] == ["new"]
    pick = items["ladder"]["modes"][0]["fields"][0]
    assert pick["type"] == "pick" and len(pick["options"]) == 20 and "호랑이" in pick["options"]


def test_print_and_poll(client):
    r = client.post("/api/print", json={"content": "sudoku", "mode": "new", "values": {"level": "hard"}, "sheets": 2})
    assert r.status_code == 202
    job = poll(client, r.get_json()["id"], "done")
    assert job["done"] == 2 and job["title"] == "스도쿠"
    script, args, _ = client.runner.calls[0]
    assert script.name == "sudoku.py" and args == ["--level", "hard"]
    assert client.get("/api/jobs/nope").status_code == 404


def test_visitor_picks_nicknames_for_ladder(client):
    body = {"content": "ladder", "mode": "new", "values": {"names": ["호랑이", "토끼", "곰"]}, "sheets": 1}
    r = client.post("/api/print", json=body)
    assert r.status_code == 202
    poll(client, r.get_json()["id"], "done")
    assert client.runner.calls[0][1] == ["--names", "호랑이,토끼,곰", "--wins", "1"]


@pytest.mark.parametrize("body", [
    {"content": "sudoku", "mode": "new", "values": {}, "sheets": 5},                  # 방문자는 4장까지
    {"content": "bingo", "mode": "blank", "values": {}, "sheets": 1},                # 운영자 전용 모드
    {"content": "text", "mode": "new", "values": {}, "sheets": 1},                   # 키오스크에 없는 콘텐츠
    {"content": "nope", "mode": "new", "values": {}, "sheets": 1},
    {"content": "tarot", "mode": "again", "values": {"seed": "안녕하세요"}, "sheets": 1},
    {"content": "ladder", "mode": "new", "values": {"names": ["민수", "지아"]}, "sheets": 1},
    {"content": "sudoku", "mode": "new", "values": "x", "sheets": 1},
    {"content": "sudoku", "mode": "new"},
    {"content": ["sudoku"], "mode": "new", "values": {}, "sheets": 1},
    [1, 2, 3],
])
def test_visitor_requests_are_refused(client, body):
    r = client.post("/api/print", json=body)
    assert r.status_code == 400 and r.get_json()["error"]
    assert client.runner.calls == []


def test_not_json_is_refused(client):
    r = client.post("/api/print", data="hello", content_type="text/plain")
    assert r.status_code == 400 and r.get_json()["error"]


def test_busy_gives_409():
    c = make_client(gate=True)
    body = {"content": "tarot", "mode": "new", "values": {}, "sheets": 1}
    assert c.post("/api/print", json=body).status_code == 202
    r = c.post("/api/print", json=body)
    assert r.status_code == 409 and "다른 인쇄" in r.get_json()["error"]
    c.runner.gate.set()


def test_admin_login_unlocks_staff(client):
    assert client.post("/api/admin/login", json={"pin": "0000"}).status_code == 403
    assert client.get("/api/admin/jobs").status_code == 403
    assert client.post("/api/admin/cancel").status_code == 403
    assert client.post("/api/admin/login", json={"pin": "1234"}).status_code == 200
    d = client.get("/api/catalog").get_json()
    assert d["role"] == "staff" and d["max_sheets"] == 20
    assert "blank" in [m["id"] for i in all_items(d["menu"]) if i["name"] == "bingo" for m in i["modes"]]
    r = client.post("/api/print", json={"content": "bingo", "mode": "blank", "values": {}, "sheets": 20})
    assert r.status_code == 202
    assert r.get_json()["id"] in [j["id"] for j in client.get("/api/admin/jobs").get_json()]
    assert "cancelled" in client.post("/api/admin/cancel").get_json()
    client.post("/api/admin/logout")
    assert client.get("/api/catalog").get_json()["role"] == "visitor"
    assert client.get("/api/admin/jobs").status_code == 403


def test_staff_session_expires_after_five_idle_minutes(client, monkeypatch):
    import kiosk.server as server
    client.post("/api/admin/login", json={"pin": "1234"})
    now = time.time()
    monkeypatch.setattr(server.time, "time", lambda: now + 4 * 60)
    assert client.get("/api/catalog").get_json()["role"] == "staff"      # 쓰는 동안은 연장된다
    monkeypatch.setattr(server.time, "time", lambda: now + 8 * 60)
    assert client.get("/api/catalog").get_json()["role"] == "staff"
    monkeypatch.setattr(server.time, "time", lambda: now + 14 * 60)
    assert client.get("/api/catalog").get_json()["role"] == "visitor"


def test_five_wrong_pins_lock_login(client):
    for _ in range(5):
        assert client.post("/api/admin/login", json={"pin": "0000"}).status_code == 403
    assert client.post("/api/admin/login", json={"pin": "1234"}).status_code == 429


def test_admin_disabled_without_pin():
    c = make_client(pin=None)
    assert c.get("/api/catalog").get_json()["admin_enabled"] is False
    assert c.post("/api/admin/login", json={"pin": ""}).status_code == 403
    assert c.post("/api/admin/login", json={}).status_code == 403


def test_cleanup_outputs(tmp_path):
    old = tmp_path / "games/sudoku/output/a.png"
    new = tmp_path / "games/sudoku/output/b.png"
    keep = tmp_path / "games/sudoku/pic.png"
    for p in (old, new, keep):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    past = time.time() - 8 * 86400
    os.utime(old, (past, past))
    os.utime(keep, (past, past))
    assert cleanup_outputs(tmp_path, 7) == 1
    assert not old.exists() and new.exists() and keep.exists()


def test_theme_css_and_kiosk_name_come_from_theme_file(client):
    css = client.get("/theme.css")
    assert css.status_code == 200 and css.mimetype == "text/css"
    text = css.get_data(as_text=True)
    assert "--board: #FFD400;" in text and "--accent: #E4002B;" in text and "--font-display:" in text
    assert client.get("/api/catalog").get_json()["name"] == "영수증 뽑기"


def test_custom_theme_overrides_and_unsafe_values_fall_back(tmp_path):
    theme = tmp_path / "theme.toml"
    theme.write_text('name = "나름 뽑기"\n[colors]\nboard = "#00ff00"\naccent = "red; } body { display:none"\n'
                     '[fonts]\ndisplay = "Gugi; } * { color: red"\n', encoding="utf-8")
    c = create_app(queue=JobQueue(runner=FakeRunner()), pin=None, theme_path=theme).test_client()
    text = c.get("/theme.css").get_data(as_text=True)
    assert "--board: #00ff00;" in text
    assert "--accent: #E4002B;" in text and "display:none" not in text and "color: red" not in text
    assert c.get("/api/catalog").get_json()["name"] == "나름 뽑기"


def test_missing_or_broken_theme_file_uses_defaults(tmp_path):
    broken = tmp_path / "theme.toml"
    broken.write_text("name = [", encoding="utf-8")
    for path in (broken, tmp_path / "none.toml"):
        c = create_app(queue=JobQueue(runner=FakeRunner()), pin=None, theme_path=path).test_client()
        assert "--board: #FFD400;" in c.get("/theme.css").get_data(as_text=True)
        assert c.get("/api/catalog").get_json()["name"] == "영수증 뽑기"


def test_error_says_which_field(client):
    r = client.post("/api/print", json={"content": "sudoku", "mode": "answer", "values": {"number": "안녕"}, "sheets": 1})
    assert r.status_code == 400 and r.get_json()["field"] == "number"
    r = client.post("/api/print", json={"content": "sudoku", "mode": "new", "values": {}, "sheets": 9})
    assert r.status_code == 400 and r.get_json()["field"] is None


def test_staff_see_why_a_content_was_dropped_and_visitors_do_not(tmp_path):
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    for folder in (good, bad):
        folder.mkdir()
        (folder / f"{folder.name}.py").write_text("", encoding="utf-8")
    (good / "content.toml").write_text('title = "좋은 것"\n[[mode]]\nid = "new"\nlabel = "새 판"\n', encoding="utf-8")
    (bad / "content.toml").write_text('title = "나쁜 것"\nkoisk = true\n', encoding="utf-8")
    c = create_app(queue=JobQueue(runner=FakeRunner()), pin="1234", root=tmp_path).test_client()
    visitor = c.get("/api/catalog").get_json()
    assert [i["name"] for i in visitor["menu"]] == ["good"] and "errors" not in visitor
    c.post("/api/admin/login", json={"pin": "1234"})
    staff = c.get("/api/catalog").get_json()
    assert len(staff["errors"]) == 1 and "bad" in staff["errors"][0] and "koisk" in staff["errors"][0]


def test_catalog_version_changes_when_the_server_restarts(client):
    first = client.get("/api/catalog").get_json()["version"]
    assert first and client.get("/api/catalog").get_json()["version"] == first
    assert make_client().get("/api/catalog").get_json()["version"] != first


# ---------------------------------------------------------------- 같은 문제 여러 장

def test_same_print_runs_once_with_copies(client):
    r = client.post("/api/print", json={"content": "sudoku", "mode": "new", "values": {}, "sheets": 3, "same": True})
    assert r.status_code == 202 and r.get_json()["same"] is True
    job = poll(client, r.get_json()["id"], "done")
    assert job["done"] == 3 and len(client.runner.calls) == 1
    assert client.runner.calls[0][1] == ["--level", "medium", "--copies", "3"]


def test_same_with_one_sheet_is_an_ordinary_job(client):
    r = client.post("/api/print", json={"content": "sudoku", "mode": "new", "values": {}, "sheets": 1, "same": True})
    assert r.status_code == 202 and r.get_json()["same"] is False
    poll(client, r.get_json()["id"], "done")
    assert client.runner.calls[0][1] == ["--level", "medium"]


@pytest.mark.parametrize("body", [
    {"content": "tarot", "mode": "new", "values": {}, "sheets": 2, "same": True},      # 받지 않는 모드
    {"content": "sudoku", "mode": "new", "values": {}, "sheets": 5, "same": True},     # 방문자는 4장까지
    {"content": "sudoku", "mode": "new", "values": {}, "sheets": 2, "same": "yes"},
    {"content": "sudoku", "mode": "new", "values": {}, "sheets": 2, "same": 1},
])
def test_bad_same_requests_are_refused(client, body):
    r = client.post("/api/print", json=body)
    assert r.status_code == 400 and r.get_json()["error"]
    assert client.runner.calls == []


def test_catalog_marks_same_sheets_modes(client):
    items = {i["name"]: i for i in all_items(client.get("/api/catalog").get_json()["menu"])}
    assert [m["same_sheets"] for m in items["sudoku"]["modes"]] == [True, False]
    assert not any(m["same_sheets"] for m in items["tarot"]["modes"])
