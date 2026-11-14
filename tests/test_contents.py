"""저장소의 실제 content.toml 18개가 계획대로 읽히고, 모든 모드가 실제로 실행된다."""
import pytest

import hub
from conftest import run_script

CAT = hub.load()
NICK = ["토끼", "여우", "수달", "펭귄"]
DEFAULTS = {  # 터미널 메뉴에서 Enter만 눌렀을 때와 같은 종류의 판
    "sudoku": ["--level", "medium"], "futoshiki": ["--level", "medium"], "minesweeper": ["--level", "medium"],
    "maze": ["--level", "medium"], "nonogram": ["--level", "easy"], "wordsearch": ["--level", "medium"],
    "spot": ["--count", "5"], "omok": ["--size", "15"], "dots": ["--size", "8"], "tictactoe": ["--boards", "6"],
    "bingo": ["--size", "5"], "hangman": ["--lang", "ko", "--slots", "10"], "loot": [], "lotto": ["--games", "5"],
    "tarot": [],
}
SEEDS = {"sudoku": "S", "futoshiki": "F", "minesweeper": "M", "maze": "Z", "nonogram": "N",
         "wordsearch": "W", "spot": "D", "loot": "L", "tarot": "T"}


def test_all_eighteen_load_without_errors():
    assert CAT.errors == ()
    assert len(CAT.contents) == 18


def test_menu_order():
    menu = CAT.menu()
    assert menu[0].name == "text" and menu[3].name == "maimai"
    assert menu[1][0].title == "고전게임" and menu[2][0].title == "오늘의 운세"
    assert [c.name for c in menu[1][1]] == ["sudoku", "futoshiki", "nonogram", "minesweeper", "maze", "wordsearch",
                                             "spot", "omok", "dots", "tictactoe", "bingo", "ladder", "hangman"]
    assert [c.name for c in menu[2][1]] == ["loot", "lotto", "tarot"]


def test_seed_prefixes_match_the_scripts():
    assert {c.name: c.seed_prefix for c in CAT.contents.values() if c.seed_prefix} == SEEDS
    for name, letter in SEEDS.items():
        source = CAT.contents[name].script.read_text(encoding="utf-8")
        assert f'SEED_PREFIX = "{letter}"' in source


@pytest.mark.parametrize("name,expected", DEFAULTS.items())
def test_default_args(name, expected):
    assert hub.build_args(CAT.contents[name], "new", {}, hub.VISITOR) == expected


@pytest.mark.parametrize("name,mode,values", [
    ("wordsearch", "custom", {"words": "가,나"}), ("wordsearch", "answer_custom", {"number": "WM0482913", "words": "가,나"}),
    ("bingo", "blank", {}), ("bingo", "caller", {}), ("lotto", "draw", {}), ("maimai", "all", {"handle": "a"}),
    ("ladder", "numbers", {}), ("ladder", "results", {"names": ["토끼", "여우"], "results": "a,b"}),
    ("loot", "new", {"level": 5}), ("lotto", "new", {"prize": "상품"}), ("lotto", "new", {"manual": "1 2 3 4 5 6"}),
    ("loot", "again", {"seed": "안녕"}), ("loot", "again", {"seed": "482913"}), ("tarot", "again", {"seed": "hello"}),
    ("sudoku", "answer", {"number": "ZM482913"}), ("wordsearch", "answer", {"number": "WM0482913"}),
    ("ladder", "new", {"names": ["민수", "지아"]}), ("maimai", "new", {"handle": "a" * 41}),
    ("maimai", "new", {"handle": "https://maimai.shiftpsh.com/profile/x"}), ("lotto", "new", {"games": 6}),
])
def test_visitor_is_refused(name, mode, values):
    with pytest.raises(hub.HubError):
        hub.build_args(CAT.contents[name], mode, values, hub.VISITOR, NICK)


def test_visitor_is_allowed():
    c = CAT.contents
    assert hub.build_args(c["ladder"], "new", {"names": NICK[:3]}, hub.VISITOR, NICK) == \
        ["--names", "토끼,여우,수달", "--wins", "1"]
    assert hub.build_args(c["maimai"], "new", {"handle": "gupying"}, hub.VISITOR) == ["gupying", "--top", "3"]
    assert hub.build_args(c["sudoku"], "answer", {"number": "sm482913"}, hub.VISITOR) == ["--answer", "sm482913"]
    assert hub.build_args(c["tarot"], "again", {"seed": "T482913"}, hub.VISITOR) == ["--seed", "T482913"]
    assert hub.build_args(c["wordsearch"], "new", {"theme": "animal"}, hub.VISITOR) == \
        ["--level", "medium", "--theme", "animal"]


def test_text_is_terminal_only():
    assert CAT.contents["text"].kiosk is False
    assert "text" not in [i["name"] for i in hub.describe(CAT, hub.STAFF)["menu"]]


def test_one_sheet_modes():
    one = {(c.name, m.id) for c in CAT.contents.values() for m in c.modes if not m.sheets}
    assert one == {("sudoku", "answer"), ("futoshiki", "answer"), ("minesweeper", "answer"), ("maze", "answer"),
                   ("nonogram", "answer"), ("wordsearch", "answer"), ("wordsearch", "answer_custom"),
                   ("spot", "answer"), ("ladder", "new"), ("loot", "again"), ("lotto", "draw"), ("tarot", "again"),
                   ("maimai", "new"), ("maimai", "all")}
    assert CAT.contents["maimai"].wait_between == 5


SAMPLE = {"words": "나름,청소년,광명,동아리", "results": "설거지,청소", "names": ["민수", "지아", "하준"],
          "prize": "문화상품권", "manual": "3 11 17 24 38 42"}
RUNNABLE = [(c.name, m.id) for c in CAT.contents.values() for m in c.modes if c.name != "maimai"]


@pytest.mark.slow
@pytest.mark.parametrize("name,mode", RUNNABLE)
def test_every_mode_runs_in_preview(name, mode):
    """모든 모드를 --preview로 실제 실행한다. 글자 항목에는 설정 파일의 example이나 SAMPLE을 넣는다."""
    content = CAT.contents[name]
    m = next(x for x in content.modes if x.id == mode)
    values = {f.id: SAMPLE.get(f.id) or f.example for f in m.fields if f.type in ("text", "names")}
    args = hub.build_args(content, mode, values, hub.STAFF)
    code, out, err = run_script(content.script, *args)
    assert code == 0, err
