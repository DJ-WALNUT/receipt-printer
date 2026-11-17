"""숨은 글자 찾기: 시드번호로 판이 정해지고, 숨은 글자는 서로 떨어져 있으며, 짝은 인쇄해도 구분된다."""
import sys

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "games" / "oddchar"))
import oddchar  # noqa: E402
from receipt import CONTENT_W, PAPER_W, draw_run, size_style  # noqa: E402

NUMBERS = [f"{level}{count}{100000 + k * 7919}" for level in "EMH" for count in "123" for k in range(20)]


def test_same_number_same_board():
    assert oddchar.make("M1482913") == oddchar.make("M1482913")
    assert len(oddchar.make("M2482913")[3]) == 2
    assert oddchar.make("M1482913") != oddchar.make("M1482914")


@pytest.mark.parametrize("number", NUMBERS)
def test_hidden_cells_hold_the_odd_char_and_do_not_touch(number):
    base, odd, board, spots = oddchar.make(number)
    cols, rows = oddchar.LEVELS[number[0]][2:4]
    assert len(board) == rows and all(len(row) == cols for row in board)
    assert len(spots) == int(number[1]) and base != odd
    for r, row in enumerate(board):
        for c, ch in enumerate(row):
            assert ch == (odd if (r, c) in spots else base)
    for i, (r1, c1) in enumerate(spots):
        for r2, c2 in spots[i + 1:]:
            assert max(abs(r1 - r2), abs(c1 - c2)) >= 2


def test_each_level_uses_only_pairs_that_look_almost_the_same_at_its_size():
    for level in oddchar.LEVELS:
        pairs = oddchar.close_pairs(level)
        assert len(pairs) >= 8, level              # 판이 늘 같은 짝만 나오지 않게
        height = oddchar.LEVELS[level][4]
        for a, b in pairs:
            assert 1 <= oddchar.dots_apart(a, b, height) <= oddchar.MAX_DOTS
            assert draw_run(a, size_style(height, False)).tobytes() != draw_run(b, size_style(height, False)).tobytes()
    for number in NUMBERS:
        base, odd = oddchar.make(number)[:2]
        assert (base, odd) in oddchar.close_pairs(number[0]) or (odd, base) in oddchar.close_pairs(number[0])


def test_glyphs_fit_their_cells():
    for level, (_, _, cols, _, height) in oddchar.LEVELS.items():
        glyph = draw_run("붕", size_style(height, False))
        assert glyph.width < CONTENT_W // cols and glyph.height <= CONTENT_W // cols, level


@pytest.mark.parametrize("level", list("EMH"))
def test_board_fits_paper(level):
    base, odd, board, spots = oddchar.make(f"{level}3123456")
    assert oddchar.draw_board(board, level).width == PAPER_W
    assert oddchar.draw_board(board, level, spots).width == PAPER_W
