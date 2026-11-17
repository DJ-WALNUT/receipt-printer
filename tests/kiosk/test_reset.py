"""지난 이력 지우기 (python -m kiosk.reset)."""
from kiosk import reset


def setup(tmp_path):
    root = tmp_path / "root"
    for rel in ["games/sudoku/output", "fortune/tarot/output", ".venv/x/output"]:
        (root / rel).mkdir(parents=True)
    (root / "games/sudoku/output/20261117_090000_SM1.png").write_bytes(b"x")
    (root / "fortune/tarot/output/20261117_090000_T1.png").write_bytes(b"x")
    (root / ".venv/x/output/keep.png").write_bytes(b"x")          # 저장소 밖 폴더는 건드리지 않는다
    usage = tmp_path / "data" / "usage.csv"
    usage.parent.mkdir()
    usage.write_text("﻿시각,콘텐츠\n2026-11-17 09:00:00,sudoku\n2026-11-17 09:01:00,tarot\n", encoding="utf-8")
    return root, usage


def test_asks_first_and_stops_unless_yes(tmp_path, capsys):
    root, usage = setup(tmp_path)
    assert reset.main([], root, usage, ask=lambda _: "n") == 1
    assert usage.exists() and (root / "games/sudoku/output/20261117_090000_SM1.png").exists()
    out = capsys.readouterr().out
    assert "이용실적 기록 2건" in out and "영수증 이미지 2개" in out


def test_yes_removes_both(tmp_path, capsys):
    root, usage = setup(tmp_path)
    assert reset.main([], root, usage, ask=lambda _: "y") == 0
    assert not usage.exists()
    assert not list(root.glob("games/*/output/*.png")) and not list(root.glob("fortune/*/output/*.png"))
    assert (root / ".venv/x/output/keep.png").exists()
    assert "이용실적 2건, 이미지 2개" in capsys.readouterr().out


def test_only_one_side_and_no_prompt(tmp_path):
    root, usage = setup(tmp_path)
    def never(_):
        raise AssertionError("--yes 인데 물어봤다")
    assert reset.main(["--only", "usage", "--yes"], root, usage, ask=never) == 0
    assert not usage.exists() and (root / "games/sudoku/output/20261117_090000_SM1.png").exists()
    assert reset.main(["--only", "images", "--yes"], root, usage, ask=never) == 0
    assert not (root / "games/sudoku/output/20261117_090000_SM1.png").exists()


def test_nothing_to_remove(tmp_path, capsys):
    assert reset.main(["--yes"], tmp_path, tmp_path / "none.csv") == 0
    assert "지울 것이 없습니다" in capsys.readouterr().out
