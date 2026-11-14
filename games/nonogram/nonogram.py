"""노노그램(네모로직) 한 판을 영수증 프린터로 인쇄한다. 다 칠하면 도트 그림이 나온다.

사용법 (프로젝트 폴더에서):
    python games/nonogram/nonogram.py                  # 쉬움(10x10) 한 판, 그림 무작위
    python games/nonogram/nonogram.py --level hard     # easy(10x10) | hard(16x16)
    python games/nonogram/nonogram.py --preview        # 인쇄 없이 이미지만 저장
    python games/nonogram/nonogram.py --answer E03     # 그 판의 정답 그림 인쇄 (번호는 영수증 아래에 찍힘)
    python games/nonogram/nonogram.py --list           # 쓸 수 있는 판 번호 보기

이미지는 games/nonogram/output/ 에 저장된다.
쉬움 그림은 이 파일의 PICTURES, 어려움 그림은 전리품 뽑기(fortune/loot/loot.py)의 16x16 아이콘이다.
찍지 않고 논리만으로 끝까지 풀리는 그림만 쓴다 (안 풀리는 그림은 자동으로 빠진다).
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))            # 공용 모듈 receipt.py
sys.path.insert(0, str(ROOT / "fortune" / "loot"))   # 16x16 아이콘
from receipt import PAPER_W, add_output_args, draw_run, output, render, stack
from loot import ICONS

# 10x10 그림. '#' = 칠하는 칸. 새 그림은 맨 뒤에 추가한다 (순서를 바꾸면 판 번호가 달라진다).
PICTURES = [
    ("하트", """
.##....##.
####..####
##########
##########
##########
.########.
..######..
...####...
....##....
.........."""),
    ("우산", """
...####...
.########.
##########
##########
....#.....
....#.....
....#.....
....#.....
....#.#...
....###..."""),
    ("나무", """
...####...
..######..
.########.
.########.
..######..
...####...
....##....
....##....
....##....
..######.."""),
    ("버섯", """
..######..
.########.
##.####.##
##########
##########
...####...
...#..#...
...#..#...
...#..#...
...####..."""),
    ("물고기", """
..........
..###....#
.#####..##
###.######
##########
##########
.#####..##
..###....#
..........
.........."""),
    ("머그컵", """
..........
#######...
#######.##
########.#
########.#
#######.##
#######...
#######...
.#####....
.........."""),
    ("오리", """
....###...
...#####..
...##.####
...#####..
#...###...
##.#####..
########..
########..
.######...
..####...."""),
    ("고양이", """
#........#
##......##
###....###
##########
#.##..##.#
#.##..##.#
##########
####..####
.########.
..######.."""),
    ("돛단배", """
....#.....
....##....
....###...
....####..
....#####.
....#.....
##########
.########.
..######..
.........."""),
    ("집", """
....##....
...####...
..######..
.########.
##########
.########.
.##.##.##.
.##.##.##.
.#####.##.
.#####.##."""),
    ("열쇠", """
..####....
.##..##...
.#....#...
.##..##...
..####....
...##.....
...##.....
...####...
...##.....
...####..."""),
    ("로켓", """
....##....
...####...
...#..#...
...#..#...
...####...
..######..
.########.
.##.##.##.
....##....
...#..#..."""),
]
HARD_NAMES = {"sword": "장검", "axe": "전투도끼", "bow": "장궁", "staff": "지팡이", "shield": "방패",
              "armor": "갑옷", "ring": "반지", "potion": "물약"}


def to_grid(text):
    rows = text.strip().splitlines()
    assert len({len(r) for r in rows}) == 1, text
    return [[ch == "#" for ch in row] for row in rows]


def clue(line):
    """한 줄의 힌트: 연달아 칠한 칸 수들. 빈 줄은 [0]."""
    runs, n = [], 0
    for filled in list(line) + [False]:
        if filled:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    return runs or [0]


def line_options(runs, known):
    """힌트에 맞고 이미 정해진 칸(known: True/False/None)과 어긋나지 않는 모든 배치."""
    size = len(known)
    runs = [r for r in runs if r]

    def place(i, start):
        if i == len(runs):
            yield [False] * (size - start)
            return
        rest = sum(runs[i + 1:]) + len(runs) - i - 1
        for gap in range(size - start - runs[i] - rest + 1):
            head = [False] * gap + [True] * runs[i] + ([False] if i < len(runs) - 1 else [])
            for tail in place(i + 1, start + len(head)):
                yield head + tail

    return [o for o in place(0, 0) if all(k is None or k == v for k, v in zip(known, o))]


def solvable(grid):
    """한 줄씩 확실한 칸만 채우는 방법으로 끝까지 풀리는지."""
    rows, cols = len(grid), len(grid[0])
    row_clues = [clue(r) for r in grid]
    col_clues = [clue([grid[r][c] for r in range(rows)]) for c in range(cols)]
    known = [[None] * cols for _ in range(rows)]
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            options = line_options(row_clues[r], known[r])
            for c in range(cols):
                if known[r][c] is None and len({o[c] for o in options}) == 1:
                    known[r][c], changed = options[0][c], True
        for c in range(cols):
            options = line_options(col_clues[c], [known[r][c] for r in range(rows)])
            for r in range(rows):
                if known[r][c] is None and len({o[r] for o in options}) == 1:
                    known[r][c], changed = options[0][r], True
    return all(v is not None for row in known for v in row)


def catalog():
    """{판 번호: (이름, 그림)}. 논리로 풀리는 그림만 담는다."""
    found = {}
    for i, (name, text) in enumerate(PICTURES, 1):
        found[f"E{i:02d}"] = (name, to_grid(text))
    for i, (key, text) in enumerate(ICONS.items(), 1):
        found[f"H{i:02d}"] = (HARD_NAMES.get(key, key), to_grid(text))
    return {k: v for k, v in found.items() if solvable(v[1])}


def draw_puzzle(grid):
    rows, cols = len(grid), len(grid[0])
    row_clues = [clue(r) for r in grid]
    col_clues = [clue([grid[r][c] for r in range(rows)]) for c in range(cols)]
    slot = 22
    left = max(len(c) for c in row_clues) * slot + 6
    top = max(len(c) for c in col_clues) * slot + 6
    cell = min(44, (PAPER_W - 12 - left) // cols)
    w, h = cols * cell, rows * cell
    x0 = (PAPER_W - left - w) // 2 + left
    y0 = top
    im = Image.new("1", (PAPER_W, top + h + 10), 1)
    d = ImageDraw.Draw(im)

    def number(n, cx, cy):
        run = draw_run(str(n), "small")
        im.paste(run, (cx - run.width // 2, cy - run.height // 2))

    for r, runs in enumerate(row_clues):   # 줄 힌트는 판 쪽으로 붙여 적는다
        for k, n in enumerate(reversed(runs)):
            number(n, x0 - 6 - k * slot - slot // 2, y0 + r * cell + cell // 2)
    for c, runs in enumerate(col_clues):
        for k, n in enumerate(reversed(runs)):
            number(n, x0 + c * cell + cell // 2, y0 - 6 - k * slot - slot // 2)
    for k in range(cols + 1):              # 다섯 칸마다 굵은 줄
        t = 4 if k % 5 == 0 or k == cols else 2
        d.rectangle([x0 + k * cell - t // 2, y0 - 2, x0 + k * cell + (t - 1) // 2, y0 + h + 1], fill=0)
    for k in range(rows + 1):
        t = 4 if k % 5 == 0 or k == rows else 2
        d.rectangle([x0 - 2, y0 + k * cell - t // 2, x0 + w + 1, y0 + k * cell + (t - 1) // 2], fill=0)
    return im


def draw_answer(grid, cell=20):
    rows, cols = len(grid), len(grid[0])
    x0 = (PAPER_W - cols * cell) // 2
    im = Image.new("1", (PAPER_W, rows * cell + 20), 1)
    d = ImageDraw.Draw(im)
    d.rectangle([x0 - 3, 7, x0 + cols * cell + 2, 12 + rows * cell], outline=0, width=2)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c]:
                d.rectangle([x0 + c * cell, 10 + r * cell, x0 + (c + 1) * cell - 1, 9 + (r + 1) * cell], fill=0)
    return im


def main():
    ap = argparse.ArgumentParser(description="노노그램을 영수증 프린터로 인쇄")
    ap.add_argument("--level", choices=["easy", "hard"], default="easy")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답 그림을 인쇄 (예: E03)")
    ap.add_argument("--list", action="store_true", help="쓸 수 있는 판 번호를 보여 주고 끝낸다")
    add_output_args(ap)
    args = ap.parse_args()
    boards = catalog()
    if args.list:
        for number, (name, grid) in boards.items():
            print(f"  {number}  {len(grid[0])}x{len(grid)}  {name}")
        return

    if args.answer:
        number = args.answer.upper()
        if number not in boards:
            ap.error(f"없는 판 번호입니다. 가능한 번호: {', '.join(boards)}")
    else:
        number = random.choice([k for k in boards if k[0] == args.level[0].upper()])
    name, grid = boards[number]
    size = f"{len(grid[0])}x{len(grid)}"

    if args.answer:
        sheet = stack(
            render(["^ ## 노노그램 정답", f"^ > No. {number} · {name}"]),
            draw_answer(grid),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 노노그램", f"^ {today} · {size} · No. {number}"]),
            draw_puzzle(grid),
            render([
                "@20 숫자는 그 줄에서 연달아 칠하는 칸 수입니다. 숫자가 여럿이면 그 사이를 한 칸 이상 띄웁니다.",
                "@20 다 칠하면 그림이 나옵니다!",
                f"@20 정답: 판 번호 지참해서 사무실에 문의하세요 - {number}",
            ]),
        )
    tag = f"{number}_answer" if args.answer else number
    shown = name if args.answer else "그림은 비밀"
    print(f"No. {number} ({size}, {shown}) " + output(sheet, "games/nonogram", args, tag))


if __name__ == "__main__":
    main()
