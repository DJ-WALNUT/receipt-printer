"""시드번호: 콘텐츠마다 다른 글자로 시작하고, 그 번호로 같은 판을 다시 만든다."""
import hashlib
import re
import sys

import pytest

from conftest import ROOT, run_script

PUZZLES = {"games/sudoku/sudoku.py": "S", "games/futoshiki/futoshiki.py": "F",
           "games/minesweeper/minesweeper.py": "M", "games/maze/maze.py": "Z",
           "games/nonogram/nonogram.py": "N", "games/wordsearch/wordsearch.py": "W",
           "games/spot/spot.py": "D"}
DRAWS = {"fortune/loot/loot.py": "L", "fortune/tarot/tarot.py": "T"}


def seed_of(stdout):
    return re.search(r"No\. (\S+?)[: ]", stdout).group(1)


def test_prefixes_are_unique():
    letters = list(PUZZLES.values()) + list(DRAWS.values())
    assert len(set(letters)) == len(letters)


@pytest.mark.slow
@pytest.mark.parametrize("script,letter", PUZZLES.items())
def test_puzzle_seed_round_trip(script, letter):
    code, out, err = run_script(script)
    assert code == 0, err
    seed = seed_of(out)
    assert seed.startswith(letter)
    code, out2, err = run_script(script, "--answer", seed.lower())  # 소문자도 받는다
    assert code == 0, err
    assert seed_of(out2) == seed
    assert run_script(script, "--answer", seed[1:])[0] != 0        # 글자 없는 예전 번호는 거부
    assert run_script(script, "--answer", "Q" + seed[1:])[0] != 0   # 다른 콘텐츠 글자도 거부


@pytest.mark.slow
@pytest.mark.parametrize("script,letter", DRAWS.items())
def test_draw_seed_round_trip(script, letter):
    code, out, err = run_script(script)
    assert code == 0, err
    seed = seed_of(out)
    assert re.fullmatch(letter + r"\d{6}", seed)
    code, out2, err = run_script(script, "--seed", seed.lower())
    assert code == 0, err
    assert out2.split("->")[0] == out.split("->")[0]                # 같은 결과가 다시 나온다
    for bad in ["482913", "안녕하세요", letter + "안녕", letter + "12"]:
        assert run_script(script, "--seed", bad)[0] != 0, bad


def test_sudoku_board_is_the_same_as_before_the_prefix():
    """글자를 붙여도 난수 입력은 그대로다: 예전 M482913과 같은 판."""
    sys.path.insert(0, str(ROOT / "games/sudoku"))
    import sudoku
    digest = hashlib.sha256(repr(sudoku.generate("M", "482913")).encode()).hexdigest()
    assert digest == "f82c9c6b67bf98df31009ac2bc21d3a28023d6c600f9caa8b5a8ac4ac8ac5250"
