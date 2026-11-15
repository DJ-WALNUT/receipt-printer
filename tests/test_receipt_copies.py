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
