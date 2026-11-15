"""허브: 설정 파일을 읽고, 입력값을 검사해 스크립트 인자로 바꾼다."""
import json

import pytest

import hub

SUDOKU = r'''
title = "스도쿠"
order = 10
seed_prefix = "S"

[[mode]]
id = "new"
label = "새 판"
[[mode.field]]
id = "level"
type = "choice"
label = "난이도"
arg = "--level"
choices = [["쉬움", "easy"], ["보통", "medium"], ["어려움", "hard"]]
default = "medium"

[[mode]]
id = "answer"
label = "정답 인쇄"
sheets = false
[[mode.field]]
id = "number"
type = "text"
label = "시드번호"
arg = "--answer"
pattern = '[Ss][EMHemh]\d{6}'
example = "SM482913"
'''

FREE_TEXT = '''
title = "자유 글"
[[mode]]
id = "m"
label = "m"
[[mode.field]]
id = "words"
type = "text"
label = "낱말"
arg = "--words"
max_length = 100
audience = "staff"
'''

STAFF_PARTS = '''
title = "전리품"
[[mode]]
id = "new"
label = "한 장 뽑기"
[[mode.field]]
id = "level"
type = "number"
label = "아이템 레벨"
arg = "--level"
min = 1
max = 30
audience = "staff"

[[mode]]
id = "draw"
label = "추첨"
audience = "staff"
args = ["--draw"]
'''

DOTS = '''
title = "점과 상자"
[[mode]]
id = "m"
label = "m"
[[mode.field]]
id = "size"
type = "number"
label = "가로 점 수"
arg = "--size"
min = 4
max = 12
default = 8
[[mode.field]]
id = "rows"
type = "number"
label = "세로 점 수"
arg = "--rows"
min = 4
max = 30
'''

LADDER = '''
title = "사다리"
[[mode]]
id = "m"
label = "m"
[[mode.field]]
id = "names"
type = "names"
label = "참가자"
arg = "--names"
min = 2
max = 8
'''

MAIMAI_ALL = r'''
title = "maimai"
[[mode]]
id = "all"
label = "전부 찍기"
args = ["--all"]
[[mode.field]]
id = "top"
type = "choice"
label = "곡 수"
arg = "--top"
choices = [["3곡", "3"], ["전부", ""]]
default = "3"
[[mode.field]]
id = "handle"
type = "text"
label = "아이디"
arg = ""
pattern = '[A-Za-z0-9_.\-]{1,40}'
'''


def make(root, rel, toml_text):
    """rel/content.toml 과 rel/<폴더 이름>.py 를 만든다."""
    folder = root / rel
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "content.toml").write_text(toml_text, encoding="utf-8")
    (folder / f"{folder.name}.py").write_text("", encoding="utf-8")


def one(tmp_path, toml_text, name="thing"):
    make(tmp_path, name, toml_text)
    cat = hub.load(tmp_path)
    assert cat.errors == ()
    return cat.contents[name]


@pytest.fixture
def sudoku(tmp_path):
    return one(tmp_path, SUDOKU, "sudoku")


def test_finds_grouped_and_top_level(tmp_path):
    (tmp_path / "games").mkdir()
    (tmp_path / "games/group.toml").write_text('title = "고전게임"\norder = 20', encoding="utf-8")
    make(tmp_path, "games/sudoku", SUDOKU)
    make(tmp_path, "maimai", 'title = "maimai"\norder = 40\n[[mode]]\nid = "x"\nlabel = "x"')
    make(tmp_path, ".venv/ghost", SUDOKU)
    cat = hub.load(tmp_path)
    assert cat.errors == ()
    assert cat.contents["sudoku"].group == "games" and cat.contents["maimai"].group is None
    assert cat.contents["sudoku"].script == tmp_path / "games/sudoku/sudoku.py"
    assert "ghost" not in cat.contents
    menu = cat.menu()
    assert menu[0][0].title == "고전게임" and [c.name for c in menu[0][1]] == ["sudoku"]
    assert menu[1].name == "maimai"


def test_default_and_explicit_args(sudoku):
    assert hub.build_args(sudoku, "new", {}, hub.VISITOR) == ["--level", "medium"]
    assert hub.build_args(sudoku, "new", {"level": "hard"}, hub.VISITOR) == ["--level", "hard"]
    assert hub.build_args(sudoku, "answer", {"number": " SM482913 "}, hub.VISITOR) == ["--answer", "SM482913"]


@pytest.mark.parametrize("mode,values", [
    ("new", {"level": "extreme"}), ("new", {"nope": 1}), ("nope", {}),
    ("answer", {}), ("answer", {"number": ""}), ("answer", {"number": "안녕하세요"}),
    ("answer", {"number": "SM48291\n3"}), ("answer", {"number": 5}), ("new", {"level": ["hard"]}),
])
def test_rejects_bad_values(sudoku, mode, values):
    with pytest.raises(hub.HubError):
        hub.build_args(sudoku, mode, values, hub.VISITOR)


def test_text_cannot_look_like_an_option(tmp_path):
    c = one(tmp_path, FREE_TEXT)
    for bad in ["--preview", "-x", "a\nb", "a\x00b", "가" * 101]:
        with pytest.raises(hub.HubError):
            hub.build_args(c, "m", {"words": bad}, hub.STAFF)
    assert hub.build_args(c, "m", {"words": "나름,청소년"}, hub.STAFF) == ["--words", "나름,청소년"]


def test_staff_only_mode_and_field(tmp_path):
    c = one(tmp_path, STAFF_PARTS)
    with pytest.raises(hub.HubError):
        hub.build_args(c, "draw", {}, hub.VISITOR)
    with pytest.raises(hub.HubError):
        hub.build_args(c, "new", {"level": 5}, hub.VISITOR)
    assert hub.build_args(c, "new", {}, hub.VISITOR) == []
    assert hub.build_args(c, "new", {"level": 5}, hub.STAFF) == ["--level", "5"]
    assert hub.build_args(c, "draw", {}, hub.STAFF) == ["--draw"]


def test_number_range_and_optional(tmp_path):
    c = one(tmp_path, DOTS)
    assert hub.build_args(c, "m", {}, hub.VISITOR) == ["--size", "8"]
    assert hub.build_args(c, "m", {"size": 6, "rows": 12}, hub.VISITOR) == ["--size", "6", "--rows", "12"]
    assert hub.build_args(c, "m", {"size": "6", "rows": ""}, hub.VISITOR) == ["--size", "6"]
    for bad in [{"size": 13}, {"size": "abc"}, {"rows": 3}, {"size": 6.5}, {"size": True}]:
        with pytest.raises(hub.HubError):
            hub.build_args(c, "m", bad, hub.VISITOR)


def test_names_visitor_must_pick_from_nicknames(tmp_path):
    c = one(tmp_path, LADDER)
    nick = ["토끼", "여우", "수달"]
    assert hub.build_args(c, "m", {"names": ["토끼", "여우"]}, hub.VISITOR, nick) == ["--names", "토끼,여우"]
    for bad in [["토끼"], ["토끼", "민수"], ["토끼", "토끼"], "토끼,여우", [], None]:
        with pytest.raises(hub.HubError):
            hub.build_args(c, "m", {"names": bad}, hub.VISITOR, nick)
    assert hub.build_args(c, "m", {"names": ["민수", " 지아 "]}, hub.STAFF) == ["--names", "민수,지아"]
    for bad in [["민수", "지,아"], ["민수", "-x"], ["민수", "가" * 9], ["민수", ""], ["a"] * 9]:
        with pytest.raises(hub.HubError):
            hub.build_args(c, "m", {"names": bad}, hub.STAFF)


def test_positional_first_then_fixed_args_and_empty_choice_is_omitted(tmp_path):
    c = one(tmp_path, MAIMAI_ALL)
    assert hub.build_args(c, "all", {"handle": "gupying"}, hub.STAFF) == ["gupying", "--all", "--top", "3"]
    assert hub.build_args(c, "all", {"handle": "gupying", "top": ""}, hub.STAFF) == ["gupying", "--all"]
    with pytest.raises(hub.HubError):
        hub.build_args(c, "all", {"handle": "https://x/y"}, hub.STAFF)


def test_sheets(sudoku):
    new, answer = sudoku.modes
    assert hub.check_sheets(new, 4, hub.VISITOR) == 4 and hub.check_sheets(new, 20, hub.STAFF) == 20
    assert hub.check_sheets(answer, 4, hub.VISITOR) == 1
    for sheets, role in [(5, hub.VISITOR), (21, hub.STAFF), (0, hub.VISITOR), ("3", hub.VISITOR), (None, hub.STAFF)]:
        with pytest.raises(hub.HubError):
            hub.check_sheets(new, sheets, role)


def test_broken_file_is_skipped_not_fatal(tmp_path):
    make(tmp_path, "good", SUDOKU)
    make(tmp_path, "bad", 'title = "깨짐"\n[[mode]\n')
    make(tmp_path, "typo", SUDOKU.replace('type = "choice"', 'type = "choise"').replace('"S"', '"T"'))
    make(tmp_path, "regex", SUDOKU.replace(r"'[Ss][EMHemh]\d{6}'", "'[Ss'").replace('"S"', '"R"'))
    make(tmp_path, "noscript", SUDOKU.replace('"S"', '"N"'))
    (tmp_path / "noscript/noscript.py").unlink()
    cat = hub.load(tmp_path)
    assert list(cat.contents) == ["good"] and len(cat.errors) == 4
    for name in ["bad", "typo", "regex", "noscript"]:
        assert any(name in e for e in cat.errors), name


def test_duplicate_seed_prefix_is_reported(tmp_path):
    make(tmp_path, "alpha", SUDOKU)
    make(tmp_path, "beta", SUDOKU)
    cat = hub.load(tmp_path)
    assert list(cat.contents) == ["alpha"]
    assert len(cat.errors) == 1 and "beta" in cat.errors[0] and "S" in cat.errors[0] and "alpha" in cat.errors[0]


def test_describe_hides_staff_parts_and_patterns(tmp_path):
    make(tmp_path, "loot", STAFF_PARTS)
    make(tmp_path, "ladder", LADDER)
    make(tmp_path, "sudoku", SUDOKU)
    make(tmp_path, "text", 'title = "텍스트"\nkiosk = false\n')
    cat = hub.load(tmp_path)
    assert cat.errors == ()
    v = hub.describe(cat, hub.VISITOR, ["토끼", "여우"])
    s = hub.describe(cat, hub.STAFF)
    names = lambda d: [i["name"] for i in d["menu"]]
    assert "text" not in names(v) and "text" not in names(s)
    assert "text" in names(hub.describe(cat, hub.STAFF, kiosk_only=False))
    loot_v = next(i for i in v["menu"] if i["name"] == "loot")
    assert [m["id"] for m in loot_v["modes"]] == ["new"] and loot_v["modes"][0]["fields"] == []
    loot_s = next(i for i in s["menu"] if i["name"] == "loot")
    assert [m["id"] for m in loot_s["modes"]] == ["new", "draw"] and loot_s["modes"][0]["fields"][0]["id"] == "level"
    pick = next(i for i in v["menu"] if i["name"] == "ladder")["modes"][0]["fields"][0]
    assert pick["type"] == "pick" and pick["options"] == ["토끼", "여우"] and pick["min"] == 2 and pick["max"] == 8
    typed = next(i for i in s["menu"] if i["name"] == "ladder")["modes"][0]["fields"][0]
    assert typed["type"] == "names" and "options" not in typed
    level = next(i for i in v["menu"] if i["name"] == "sudoku")["modes"][0]["fields"][0]
    assert level == {"id": "level", "type": "choice", "label": "난이도", "default": "medium",
                     "choices": [["쉬움", "easy"], ["보통", "medium"], ["어려움", "hard"]],
                     "min": None, "max": None, "max_length": 40, "example": "", "required": True}
    assert v["role"] == "visitor" and v["max_sheets"] == 4 and s["max_sheets"] == 20
    assert "pattern" not in json.dumps(v)


def test_describe_groups(tmp_path):
    (tmp_path / "games").mkdir()
    (tmp_path / "games/group.toml").write_text('title = "고전게임"\norder = 20', encoding="utf-8")
    (tmp_path / "staffonly").mkdir()
    (tmp_path / "staffonly/group.toml").write_text('title = "운영자 묶음"\norder = 30', encoding="utf-8")
    make(tmp_path, "games/sudoku", SUDOKU)
    make(tmp_path, "staffonly/thing", STAFF_PARTS.replace('id = "new"', 'id = "new"\naudience = "staff"'))
    v = hub.describe(hub.load(tmp_path), hub.VISITOR)
    assert [(i["kind"], i["name"]) for i in v["menu"]] == [("group", "games")]
    assert v["menu"][0]["title"] == "고전게임" and v["menu"][0]["items"][0]["name"] == "sudoku"
    assert v["menu"][0]["items"][0]["kind"] == "content"


def test_load_nicknames(tmp_path):
    p = tmp_path / "n.txt"
    p.write_text("# 설명\n토끼\n\n 여우 \n", encoding="utf-8")
    assert hub.load_nicknames(p) == ["토끼", "여우"]
    assert hub.load_nicknames(tmp_path / "missing.txt") == []


def test_unknown_keys_are_errors_so_an_audience_typo_cannot_fail_open(tmp_path):
    make(tmp_path, "modetypo", STAFF_PARTS.replace('audience = "staff"\nargs', 'audiance = "staff"\nargs'))
    make(tmp_path, "fieldtypo", STAFF_PARTS.replace('max = 30\naudience = "staff"', 'max = 30\naudeince = "staff"'))
    make(tmp_path, "toptypo", 'title = "x"\nkoisk = false\n')
    cat = hub.load(tmp_path)
    assert cat.contents == {} and len(cat.errors) == 3
    assert any("audiance" in e for e in cat.errors) and any("audeince" in e for e in cat.errors)
    assert any("koisk" in e for e in cat.errors)


def test_visitor_text_field_must_have_a_pattern(tmp_path):
    open_text = FREE_TEXT.replace('audience = "staff"\n', "")
    make(tmp_path, "open", open_text)
    make(tmp_path, "staffmode", open_text.replace('label = "m"', 'label = "m"\naudience = "staff"'))
    cat = hub.load(tmp_path)
    assert list(cat.contents) == ["staffmode"]
    assert len(cat.errors) == 1 and "open" in cat.errors[0] and "pattern" in cat.errors[0]


BAD_SHAPES = [
    'title = "x"\nmode = [1]\n',
    'title = "x"\nmode = "new"\n',
    'title = "x"\n[[mode]]\nid = "m"\nlabel = "m"\nfield = ["a"]\n',
    'title = "x"\n[[mode]]\nid = "m"\nlabel = "m"\n[[mode.field]]\nid = "c"\ntype = "choice"\nlabel = "c"\n'
    'arg = "--c"\nchoices = "ab"\ndefault = "a"\n',
]


@pytest.mark.parametrize("text", BAD_SHAPES)
def test_wrongly_typed_entries_do_not_crash_the_catalog(tmp_path, text):
    make(tmp_path, "good", SUDOKU)
    make(tmp_path, "bad", text)
    cat = hub.load(tmp_path)
    assert list(cat.contents) == ["good"] and len(cat.errors) == 1 and "bad" in cat.errors[0]


def test_patterns_match_ascii_digits_only_and_line_separators_are_refused(sudoku, tmp_path):
    with pytest.raises(hub.HubError):
        hub.build_args(sudoku, "answer", {"number": "SM４８２９１３"}, hub.VISITOR)
    c = one(tmp_path, FREE_TEXT)
    for bad in ["a b", "a b", "a\u0085b"]:
        with pytest.raises(hub.HubError):
            hub.build_args(c, "m", {"words": bad}, hub.STAFF)


def test_error_names_the_field_it_is_about(sudoku):
    with pytest.raises(hub.HubError) as e:
        hub.build_args(sudoku, "answer", {"number": "안녕"}, hub.VISITOR)
    assert e.value.field == "number"
    with pytest.raises(hub.HubError) as e:
        hub.build_args(sudoku, "nope", {}, hub.VISITOR)
    assert e.value.field is None


# ---------------------------------------------------------------- 같은 문제 여러 장 (same_sheets)

SAME_SUDOKU = SUDOKU.replace('label = "새 판"', 'label = "새 판"\nsame_sheets = true')


def test_same_sheets_defaults_to_false_and_is_described(tmp_path, sudoku):
    assert [m.same_sheets for m in sudoku.modes] == [False, False]
    plain = hub.describe(hub.load(tmp_path), hub.VISITOR)["menu"][0]["modes"]
    assert [m["same_sheets"] for m in plain] == [False, False]
    make(tmp_path, "sudoku", SAME_SUDOKU)
    cat = hub.load(tmp_path)
    assert cat.errors == () and [m.same_sheets for m in cat.contents["sudoku"].modes] == [True, False]
    assert [m["same_sheets"] for m in hub.describe(cat, hub.VISITOR)["menu"][0]["modes"]] == [True, False]


def test_same_sheets_on_a_one_sheet_mode_is_a_config_error(tmp_path):
    make(tmp_path, "sudoku", SUDOKU.replace("sheets = false", "sheets = false\nsame_sheets = true"))
    cat = hub.load(tmp_path)
    assert cat.contents == {} and "same_sheets" in cat.errors[0]


def test_same_sheets_must_be_a_boolean(tmp_path):
    make(tmp_path, "sudoku", SUDOKU.replace('label = "새 판"', 'label = "새 판"\nsame_sheets = "yes"'))
    cat = hub.load(tmp_path)
    assert cat.contents == {} and "same_sheets" in cat.errors[0]


@pytest.mark.parametrize("same,expected", [(None, False), (False, False), (True, True)])
def test_check_same_on_a_supporting_mode(tmp_path, same, expected):
    new = one(tmp_path, SAME_SUDOKU, "sudoku").modes[0]
    assert hub.check_same(new, same) is expected


@pytest.mark.parametrize("same", ["yes", 1, 0, "true", []])
def test_check_same_refuses_non_booleans(tmp_path, same):
    new = one(tmp_path, SAME_SUDOKU, "sudoku").modes[0]
    with pytest.raises(hub.HubError):
        hub.check_same(new, same)


def test_check_same_refuses_modes_without_it(sudoku):
    new = sudoku.modes[0]
    assert hub.check_same(new, None) is False and hub.check_same(new, False) is False
    with pytest.raises(hub.HubError):
        hub.check_same(new, True)
