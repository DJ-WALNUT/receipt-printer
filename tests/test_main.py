"""터미널 메뉴: content.toml 로 질문을 만들고 스크립트 인자를 돌려준다."""
import sys
import types

import pytest

import hub
import main

CAT = hub.load()


def feed(monkeypatch, *answers):
    left = list(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": left.pop(0))
    return left


def test_enter_only_gives_defaults(monkeypatch):
    feed(monkeypatch, "", "")                       # 모드 Enter, 난이도 Enter
    args, mode = main.ask_content(CAT.contents["sudoku"])
    assert args == ["--level", "medium"] and mode.id == "new" and mode.sheets is True


def test_single_mode_content_skips_the_mode_question(monkeypatch):
    left = feed(monkeypatch, "", "")                # 가로 점 수 Enter, 세로 점 수 Enter
    args, mode = main.ask_content(CAT.contents["dots"])
    assert args == ["--size", "8"] and left == []


def test_choice_by_number_and_number_field(monkeypatch):
    feed(monkeypatch, "1", "3")
    assert main.ask_content(CAT.contents["sudoku"])[0] == ["--level", "hard"]
    feed(monkeypatch, "6", "12")
    assert main.ask_content(CAT.contents["dots"])[0] == ["--size", "6", "--rows", "12"]


def test_answer_mode(monkeypatch):
    feed(monkeypatch, "2", "SM482913")
    args, mode = main.ask_content(CAT.contents["sudoku"])
    assert args == ["--answer", "SM482913"] and mode.sheets is False


def test_staff_modes_and_fields_are_offered_in_terminal(monkeypatch):
    feed(monkeypatch, "2", "2", "나름,청소년")        # 낱말 찾기: 낱말 직접 넣기, 보통, 낱말
    assert main.ask_content(CAT.contents["wordsearch"])[0] == ["--level", "medium", "--words", "나름,청소년"]
    feed(monkeypatch, "1", "7")                      # 전리품: 한 장 뽑기, 레벨 7
    assert main.ask_content(CAT.contents["loot"])[0] == ["--level", "7"]


def test_typed_names_and_optional_text(monkeypatch):
    feed(monkeypatch, "1", "민수, 지아,하준", "")     # 사다리: 첫 모드, 이름, 당첨 개수 Enter
    assert main.ask_content(CAT.contents["ladder"])[0] == ["--names", "민수,지아,하준", "--wins", "1"]
    feed(monkeypatch, "1", "", "", "")               # 로또: 복권, 게임 수 Enter, 상품 Enter, 수동 번호 Enter
    assert main.ask_content(CAT.contents["lotto"])[0] == ["--games", "5"]


@pytest.mark.parametrize("answers", [("2", "안녕하세요"), ("2", ""), ("2", "q"), ("9",), ("1", "7")])
def test_bad_input_returns_none(monkeypatch, capsys, answers):
    feed(monkeypatch, *answers)
    assert main.ask_content(CAT.contents["sudoku"]) is None


def test_bad_input_explains_itself(monkeypatch, capsys):
    feed(monkeypatch, "2", "안녕하세요")
    main.ask_content(CAT.contents["sudoku"])
    assert "SM482913" in capsys.readouterr().out


def test_cli_passthrough(monkeypatch):
    seen = {}
    monkeypatch.setattr(main.subprocess, "run",
                        lambda cmd, **k: seen.update(cmd=cmd) or types.SimpleNamespace(returncode=0))
    monkeypatch.setattr(sys, "argv", ["main.py", "sudoku", "--level", "hard", "--preview"])
    with pytest.raises(SystemExit) as e:
        main.main()
    assert e.value.code == 0
    assert seen["cmd"][1].replace("\\", "/").endswith("games/sudoku/sudoku.py")
    assert seen["cmd"][2:] == ["--level", "hard", "--preview"]


def test_cli_unknown_name_lists_contents(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "nope"])
    with pytest.raises(SystemExit) as e:
        main.main()
    assert e.value.code not in (0, None) and "sudoku" in capsys.readouterr().out


def test_menu_runs_selected_content_with_sheets_and_preview(monkeypatch):
    runs = []
    monkeypatch.setattr(main, "run", lambda content, args: runs.append((content.name, args)) or 0)
    # p(미리보기) -> 2(고전게임) -> 1(스도쿠) -> 모드 Enter -> 난이도 Enter -> 2장 -> b -> q
    feed(monkeypatch, "p", "2", "1", "", "", "2", "b", "q")
    main.menu()
    assert runs == [("sudoku", ["--level", "medium", "--preview"])] * 2


def test_menu_does_not_ask_sheets_for_one_sheet_modes(monkeypatch):
    runs = []
    monkeypatch.setattr(main, "run", lambda content, args: runs.append((content.name, args)) or 0)
    feed(monkeypatch, "2", "1", "2", "SM482913", "b", "q")
    main.menu()
    assert runs == [("sudoku", ["--answer", "SM482913"])]
