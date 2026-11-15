# 같은 문제 여러 장 뽑기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 터미널 메뉴와 키오스크에서 퍼즐 일곱 종을 "같은 문제로 N장" 뽑을 수 있게 한다.

**Architecture:** 공통 인쇄 함수 `receipt.output()`이 `--copies N`을 받아 같은 이미지를 N번 전송한다. `content.toml`의 모드 키 `same_sheets`가 이 선택지를 보여줄 모드를 정하고, 터미널과 키오스크는 사용자가 고르면 스크립트를 장마다 실행하는 대신 한 번만 `--copies N`으로 실행한다.

**Tech Stack:** Python 3.11+, argparse, Pillow, Flask, pytest, 빌드 없는 ES2017 JavaScript.

**Spec:** `docs/superpowers/specs/2026-11-15-same-sheets-design.md`

## Global Constraints

- 기본 동작은 바뀌지 않는다: 고르지 않으면 장마다 다른 문제.
- 장 수 제한은 그대로다: 방문자 4장, 관리자 20장 (`hub.MAX_SHEETS`). `--copies`의 범위는 1~20.
- 콘텐츠 스크립트(`games/*/*.py`)는 고치지 않는다.
- 브랜치: Task 1~3은 `receipt-contents`, Task 4~5는 `kiosk`(먼저 `git merge receipt-contents`). `kiosk`에서는 `kiosk/`, `deploy/`, `tests/kiosk/` 밖의 파일을 고치지 않는다.
- `kiosk/static/app.js`는 ES2017까지만 쓴다 (`?.`, `??` 금지).
- 사용자에게 보이는 문장은 기존 말투를 따른다 (키오스크 "~요", 터미널 "~습니다/~세요").
- 테스트 실행: `.venv\Scripts\python -m pytest` (저장소 폴더에서).

## Review Focus

1. 방문자가 `same_sheets`가 아닌 모드(예: 타로)에 `same: true`를 보낸다 → 400으로 거절하고 인쇄하지 않는다. (Task 4)
2. `same: true`인데 1장이다 → 보통 작업처럼 한 번 실행하고 `--copies`를 붙이지 않는다. (Task 3, Task 4)
3. 방문자가 `same: true`로 5장을 요청한다 → 기존 장 수 제한이 그대로 거절한다. `--copies`로 제한을 돌아갈 수 없다. (Task 4)
4. 같은 문제 작업 도중 프린터가 실패한다 → 작업은 `failed`, 사유 문장이 보이고, 대기열은 다음 작업을 계속한다. (Task 4)
5. `same`에 참/거짓이 아닌 값(`"yes"`, `1`)이 온다 → 400으로 거절한다. (Task 2, Task 4)

---

### Task 1: `--copies` 인쇄 옵션

**Files:**
- Modify: `receipt.py` (`add_output_args`, `output`)
- Test: `tests/test_receipt_copies.py` (새로 만든다)

**Interfaces:**
- Produces: 모든 콘텐츠 스크립트가 `--copies N`(정수 1~20, 기본 1)을 받는다. `receipt.MAX_COPIES = 20`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
"""--copies: 같은 이미지를 여러 장 인쇄한다."""
import argparse

import pytest
from PIL import Image

import receipt


def parse(*argv):
    ap = argparse.ArgumentParser()
    receipt.add_output_args(ap)
    return ap.parse_args(list(argv))


@pytest.fixture
def sent(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(receipt, "send", lambda sheet, port, cut=True: calls.append((port, cut)))
    monkeypatch.setattr(receipt, "save_output", lambda sheet, content, tag="": receipt.ROOT / "x.png")
    return calls


SHEET = Image.new("1", (receipt.PAPER_W, 80), 1)


def test_default_is_one_copy(sent):
    receipt.output(SHEET, "games/sudoku", parse("--port", "P"))
    assert sent == [("P", True)]


def test_copies_sends_the_same_sheet_that_many_times(sent):
    message = receipt.output(SHEET, "games/sudoku", parse("--port", "P", "--copies", "3"))
    assert sent == [("P", True)] * 3 and "3장" in message


def test_preview_saves_once_and_sends_nothing(sent):
    message = receipt.output(SHEET, "games/sudoku", parse("--preview", "--copies", "4"))
    assert sent == [] and "4장" in message


@pytest.mark.parametrize("bad", ["0", "21", "-1", "two"])
def test_out_of_range_copies_is_a_usage_error(bad):
    with pytest.raises(SystemExit):
        parse("--copies", bad)


def test_args_without_copies_still_print_once(sent):
    receipt.output(SHEET, "games/sudoku", argparse.Namespace(port="P", preview=False, no_cut=False))
    assert len(sent) == 1
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv\Scripts\python -m pytest tests/test_receipt_copies.py -q`
Expected: FAIL (`unrecognized arguments: --copies`)

- [ ] **Step 3: `receipt.py`를 고친다**

- `MAX_COPIES = 20`.
- `add_output_args`에 `--copies`(metavar `장수`, 기본 1, help "같은 이미지를 여러 장 인쇄 (1~20)"). 범위 밖이나 숫자가 아니면 argparse 사용법 오류.
- `output()`은 `getattr(args, "copies", 1)`번 `send`한다. 2장 이상이면 결과 문장 끝에 ` · 같은 것 N장`을 붙인다 (미리보기 문장에도).

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add receipt.py tests/test_receipt_copies.py
git commit -m "feat: --copies 로 같은 이미지를 여러 장 인쇄한다"
```

---

### Task 2: 모드 키 `same_sheets`

**Files:**
- Modify: `hub.py` (`MODE_KEYS`, `Mode`, `_parse_mode`, `_describe_content`, 새 함수 `check_same`)
- Modify: `games/{sudoku,futoshiki,nonogram,minesweeper,maze,spot}/content.toml`의 `new` 모드, `games/wordsearch/content.toml`의 `new`와 `custom` 모드
- Modify: `README.md` ("콘텐츠 설정 파일" 절의 예시와, 터미널 사용법에 `--copies` 한 줄)
- Test: `tests/test_hub.py`, `tests/test_contents.py`

**Interfaces:**
- Produces:
  - `Mode.same_sheets: bool` (필드 순서: `sheets` 바로 뒤. `Mode(id, label, audience, sheets, same_sheets, args, fields)`).
  - `hub.check_same(mode: Mode, same) -> bool`: `same`이 `None`/`False`면 `False`. `True`이고 `mode.same_sheets`면 `True`. 그 밖(참/거짓이 아닌 값, 지원하지 않는 모드)은 `HubError("같은 문제로 뽑을 수 없는 메뉴예요.")`.
  - `hub.describe()`의 각 모드 dict에 `"same_sheets": bool`.
  - `hub.COPIES_ARG = "--copies"`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hub.py`에 (파일의 기존 도우미로 임시 폴더에 설정을 써서 읽는 방식을 그대로 쓴다):

```python
def test_same_sheets_defaults_to_false_and_is_described(...):
    # SUDOKU 설정: 두 모드 모두 same_sheets is False, describe 결과의 모드에 "same_sheets": False
    # new 모드에 same_sheets = true 를 넣은 설정: True, describe 에도 True

def test_same_sheets_on_a_one_sheet_mode_is_a_config_error(...):
    # sheets = false 와 same_sheets = true 를 함께 쓰면 catalog.errors 에 "same_sheets" 가 든 문장, 콘텐츠는 빠진다

def test_same_sheets_must_be_a_boolean(...):
    # same_sheets = "yes" -> catalog.errors

@pytest.mark.parametrize("same,expected", [(None, False), (False, False), (True, True)])
def test_check_same_on_a_supporting_mode(same, expected): ...

@pytest.mark.parametrize("same", ["yes", 1, 0, "true", []])
def test_check_same_refuses_non_booleans(same):          # Review Focus 5
    with pytest.raises(hub.HubError): ...

def test_check_same_refuses_modes_without_it():
    # same_sheets 가 False 인 모드에 True -> HubError, False/None -> False
```

`tests/test_contents.py`에:

```python
SAME = {("sudoku", "new"), ("futoshiki", "new"), ("nonogram", "new"), ("minesweeper", "new"),
        ("maze", "new"), ("wordsearch", "new"), ("wordsearch", "custom"), ("spot", "new")}

def test_same_sheets_modes():
    found = {(c.name, m.id) for c in CAT.contents.values() for m in c.modes if m.same_sheets}
    assert found == SAME

def test_copies_runs_in_preview():
    code, out, err = run_script("games/sudoku/sudoku.py", "--copies", "3")
    assert code == 0 and "3장" in out
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv\Scripts\python -m pytest tests/test_hub.py tests/test_contents.py -q`
Expected: 새 테스트 FAIL

- [ ] **Step 3: 구현한다**

`hub.py`를 Interfaces대로 고치고, `sheets = false`인 모드에 `same_sheets = true`면 `HubError(f"{where}: same_sheets는 여러 장을 뽑는 모드에서만 쓸 수 있습니다")`. 여덟 모드의 `label` 줄 아래에 `same_sheets = true`를 넣는다. README 예시의 `# sheets = false` 줄 아래에 `# same_sheets = true     # "같은 문제로 여러 장" 선택지를 보일 때 (타임어택용)`을 넣고, 퍼즐 사용법에 `python main.py sudoku --copies 4   # 같은 문제 네 장` 예를 더한다.

`tests/kiosk/fakes.py`는 `receipt-contents`에 없다. `Mode`/`Content`를 위치 인자로 만드는 다른 곳이 있는지 `grep -rn "hub.Mode(\|Mode(" --include=*.py .`로 확인해 함께 고친다.

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add hub.py games README.md tests
git commit -m "feat: same_sheets 모드 키로 같은 문제 여러 장을 고를 수 있는 모드를 표시한다"
```

---

### Task 3: 터미널 메뉴의 질문

**Files:**
- Modify: `main.py` (`run_from_menu`, 새 함수 `ask_same`)
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `Mode.same_sheets`, `hub.COPIES_ARG`.
- Produces: `main.ask_same() -> bool` ("같은 문제로 뽑을까요? (y/N) > ", `y`/`Y`/`ㅛ`만 참).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
@pytest.fixture
def runs(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run", lambda content, args: calls.append(args) or 0)
    return calls


def test_same_question_runs_once_with_copies(monkeypatch, runs):
    feed(monkeypatch, "", "", "3", "y")              # 모드, 난이도, 3장, 같은 문제
    main.run_from_menu(CAT.contents["sudoku"], preview=True)
    assert runs == [["--level", "medium", "--copies", "3", "--preview"]]


def test_declining_runs_each_sheet_separately(monkeypatch, runs):
    feed(monkeypatch, "", "", "3", "")               # Enter = 다른 문제
    main.run_from_menu(CAT.contents["sudoku"], preview=False)
    assert runs == [["--level", "medium"]] * 3


def test_one_sheet_does_not_ask(monkeypatch, runs):   # Review Focus 2
    left = feed(monkeypatch, "", "", "1")
    main.run_from_menu(CAT.contents["sudoku"], preview=False)
    assert runs == [["--level", "medium"]] and left == []


def test_modes_without_same_sheets_do_not_ask(monkeypatch, runs):
    left = feed(monkeypatch, "", "2")                # 타로: 모드 Enter, 2장 (항목 수가 다르면 그 콘텐츠의 질문 수에 맞춘다)
    main.run_from_menu(CAT.contents["tarot"], preview=False)
    assert len(runs) == 2 and left == []
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv\Scripts\python -m pytest tests/test_main.py -q`
Expected: 새 테스트 FAIL

- [ ] **Step 3: `run_from_menu`를 고친다**

장 수를 물은 뒤, 고른 모드가 `same_sheets`이고 2장 이상이면 `ask_same()`을 부른다. 참이면 `args + [hub.COPIES_ARG, str(count)]`로 한 번만 실행한다 (`--preview`는 그 뒤에 붙는다). `CUSTOM_ASK` 경로는 묻지 않는다.

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add main.py tests/test_main.py
git commit -m "feat: 터미널 메뉴에서 같은 문제로 여러 장을 뽑을 수 있다"
```

---

### Task 4: 키오스크 서버와 대기열

**Files:** (`kiosk` 브랜치. 먼저 `git merge receipt-contents`)
- Modify: `kiosk/jobs.py` (`Job`, `JobQueue.submit`, `JobQueue._run`)
- Modify: `kiosk/server.py` (`post_print`)
- Modify: `tests/kiosk/fakes.py`는 `Content`만 만들므로 그대로일 것이다. `Mode`를 위치 인자로 만드는 곳이 있으면 고친다.
- Test: `tests/kiosk/test_jobs.py`, `tests/kiosk/test_server.py`

**Interfaces:**
- Consumes: `hub.check_same(mode, same) -> bool`, `hub.COPIES_ARG`.
- Produces:
  - `JobQueue.submit(content, args, sheets, role, same=False) -> Job`.
  - `Job.same: bool`. `Job.to_dict()`에 `"same": bool`.
  - `POST /api/print` 본문의 선택 키 `same`(참/거짓).
  - `kiosk.jobs.COPY_SECONDS = 15` (같은 문제 작업에서 한 장 더 뽑을 때마다 늘리는 제한 시간).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/kiosk/test_jobs.py`:

```python
def test_same_job_runs_once_with_copies():
    r = FakeRunner()
    q = JobQueue(runner=r, preview=True, timeout=100)
    job = q.submit(content(), ["--level", "hard"], 4, hub.VISITOR, same=True)
    wait(job, "done")
    assert len(r.calls) == 1 and job.done == 4
    assert r.calls[0][1] == ["--level", "hard", "--copies", "4", "--preview"]
    assert r.calls[0][2] == 100 + 15 * 3
    assert job.to_dict()["same"] is True


def test_same_job_failure_is_reported_and_queue_continues():   # Review Focus 4
    r = FakeRunner(results=[(False, "프린터 연결을 확인해 주세요.")])
    q = JobQueue(runner=r)
    bad = q.submit(content(), [], 3, hub.STAFF, same=True)
    nxt = q.submit(content(), [], 1, hub.STAFF)
    wait(bad, "failed")
    assert bad.done == 0 and "프린터" in bad.message
    wait(nxt, "done")


def test_cancel_before_start_skips_a_same_job():
    # gate=True 인 실행기로 앞 작업을 붙잡아 두고, same 작업을 대기시킨 뒤 cancel_all -> same 작업은 cancelled, 실행 0번
```

기존 `test_runs_each_sheet_and_finishes`의 `to_dict` 비교에 `"same": False`를 더한다.

`tests/kiosk/test_server.py` (요청 본문은 기존 테스트의 모양을 따른다):

```python
def test_same_print_runs_once_with_copies(client):
    # sudoku/new, sheets 3, same True -> 202, 실행 1번, 인자 끝이 ["--copies", "3"], 작업 done 3

def test_same_with_one_sheet_is_an_ordinary_job(client):       # Review Focus 2
    # sheets 1, same True -> 202, 인자에 "--copies" 없음

def test_same_is_refused_for_modes_without_it(client):         # Review Focus 1
    # tarot/(첫 모드), same True -> 400, client.runner.calls == []

def test_same_cannot_exceed_the_visitor_limit(client):         # Review Focus 3
    # sudoku/new, sheets 5, same True -> 400

@pytest.mark.parametrize("same", ["yes", 1])
def test_same_must_be_a_boolean(client, same):                 # Review Focus 5
    # -> 400

def test_catalog_marks_same_sheets_modes(client):
    # /api/catalog 의 sudoku new 모드에 same_sheets True, answer 모드에 False
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv\Scripts\python -m pytest tests/kiosk -q`
Expected: 새 테스트 FAIL

- [ ] **Step 3: 구현한다**

- `jobs.py`: `_run`에서 `job.same`이면 취소 여부를 한 번 보고, `_pace` 뒤 `job.args + [hub.COPIES_ARG, str(job.sheets)]`(+ 미리보기 플래그)로 한 번 실행한다. 제한 시간은 `self.timeout + COPY_SECONDS * (job.sheets - 1)`. 성공하면 `job.done = job.sheets`.
- `server.py`: `check_sheets` 뒤에 `same = hub.check_same(mode, body.get("same")) and sheets > 1`. 같은 `try` 안에서 검사해 `HubError`가 400이 되게 한다. `queue.submit(content, args, sheets, who, same=same)`.
- 모듈 독스트링의 "장마다 스크립트를 새 프로세스로 실행한다"에 같은 문제 작업의 예외를 한 문장 더한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add kiosk tests/kiosk
git commit -m "feat: 키오스크 서버가 같은 문제 여러 장 인쇄를 받는다"
```

---

### Task 5: 키오스크 화면

**Files:**
- Modify: `kiosk/static/app.js` (`state`, `setMode`, `goHome`, `renderForm`, 새 함수 `renderSame`, `progressText`, `submit`)
- Modify: `kiosk/README.md` ("화면에서 할 수 있는 것" 표에 한 줄)
- Test: 자동 테스트 없음 (화면 코드에 테스트 틀이 없다). 아래 손 확인으로 대신한다.

**Interfaces:**
- Consumes: 카탈로그 모드의 `same_sheets`, `/api/print`의 `same`, 작업 dict의 `same`.

- [ ] **Step 1: 화면을 고친다**

- `state.same = false`. `setMode`에서 `keepValues`가 아니면, 그리고 `goHome`에서 `false`로 되돌린다.
- `renderForm`: `mode.sheets && mode.same_sheets`이면 "몇 장?" 바로 아래에 `renderSame()`을 넣는다. 기존 `field` / `choices choices--2` / `choice` 모양을 그대로 쓴다. 라벨 `문제`, 버튼 `장마다 다르게` / `모두 같게`, 누르면 `state.same`을 바꾸고 `renderPanel()`.
- `submit`: 본문에 `same: !!(state.mode.same_sheets && state.same && state.sheets > 1)`.
- `progressText`: `job.same && job.sheets > 1`이고 실행 중이면 `'같은 문제 ' + job.sheets + '장을 뽑는 중이에요'`.
- `kiosk/README.md` 표: `| 같은 문제 여러 장 | 퍼즐 일곱 종에서 가능 | 가능 |`.

- [ ] **Step 2: 손으로 확인한다**

```powershell
$env:KIOSK_PREVIEW = "1"; $env:KIOSK_PIN = "1234"; .venv\Scripts\python -m kiosk
```

`http://localhost:8080`에서:
1. 스도쿠 → `문제` 선택이 보이고 기본이 `장마다 다르게`다. 타로에는 보이지 않는다. 스도쿠 `정답 인쇄` 모드에도 보이지 않는다.
2. 스도쿠 3장 + `모두 같게` → `games/sudoku/output/`에 이미지가 **1개** 생긴다. 진행 문장이 "같은 문제 3장을 뽑는 중이에요"다.
3. 스도쿠 3장 + `장마다 다르게` → 이미지가 **3개** 생긴다.
4. `모두 같게`를 고른 뒤 다른 콘텐츠로 갔다 돌아오면 `장마다 다르게`로 돌아와 있다.
5. 관리자로 들어가(제목 2초 누르기) 낱말 찾기 `낱말 직접 넣기`에도 선택이 보인다.

- [ ] **Step 3: 커밋**

```bash
git add kiosk/static/app.js kiosk/README.md
git commit -m "feat: 키오스크 화면에서 같은 문제 여러 장을 고를 수 있다"
```
