"""스도쿠 한 판을 만들어 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python games/sudoku/sudoku.py                    # 보통 난이도 한 판 인쇄
    python games/sudoku/sudoku.py --level hard       # easy | medium | hard
    python games/sudoku/sudoku.py --preview          # 인쇄 없이 이미지만 저장
    python games/sudoku/sudoku.py --answer M482913   # 그 판의 정답 인쇄 (번호는 영수증 아래에 찍힘)

이미지는 games/sudoku/output/ 에 저장된다.
모든 퍼즐은 정답이 하나뿐이다. 판 번호(난이도 글자 + 숫자)만 있으면 같은 판과 정답을 다시 만들 수 있다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import FONT_DIR, PAPER_W, add_output_args, output, render, stack

LEVELS = {  # 글자: (이름, 표시, 남길 숫자 개수)
    "E": ("easy", "쉬움", 40),
    "M": ("medium", "보통", 32),
    "H": ("hard", "어려움", 26),
}

PEERS = []
for i in range(81):
    r, c = divmod(i, 9)
    box = {(r // 3 * 3 + dr) * 9 + (c // 3 * 3 + dc) for dr in range(3) for dc in range(3)}
    PEERS.append(sorted(({r * 9 + k for k in range(9)} | {k * 9 + c for k in range(9)} | box) - {i}))


def candidates(grid, i):
    used = {grid[p] for p in PEERS[i]}
    return [d for d in range(1, 10) if d not in used]


def pick_cell(grid):
    """후보가 가장 적은 빈칸. 빈칸이 없으면 (None, None)."""
    best, best_c = None, None
    for i in range(81):
        if grid[i] == 0:
            c = candidates(grid, i)
            if best is None or len(c) < len(best_c):
                best, best_c = i, c
                if len(c) <= 1:
                    break
    return best, best_c


def fill(grid, rng):
    """빈 판을 무작위 정답으로 채운다."""
    i, cands = pick_cell(grid)
    if i is None:
        return True
    rng.shuffle(cands)
    for d in cands:
        grid[i] = d
        if fill(grid, rng):
            return True
    grid[i] = 0
    return False


def count_solutions(grid, limit=2):
    i, cands = pick_cell(grid)
    if i is None:
        return 1
    total = 0
    for d in cands:
        grid[i] = d
        total += count_solutions(grid, limit)
        if total >= limit:
            break
    grid[i] = 0
    return total


def generate(level, seed):
    """(문제, 정답) 반환. 정답이 하나로 유지되는 동안만 숫자를 지운다."""
    rng = random.Random(f"{level}{seed}")
    solution = [0] * 81
    fill(solution, rng)
    puzzle = solution[:]
    target = LEVELS[level][2]
    order = list(range(81))
    rng.shuffle(order)
    clues = 81
    for i in order:
        if clues <= target:
            break
        keep = puzzle[i]
        puzzle[i] = 0
        if count_solutions(puzzle[:]) == 1:
            clues -= 1
        else:
            puzzle[i] = keep
    return puzzle, solution


def draw_digit(d, font, scale):
    """숫자 하나를 원래 픽셀 크기로 그려 여백 없이 잘라낸 뒤 정수배 확대."""
    l, t, r, b = font.getbbox(str(d))
    im = Image.new("1", (r - l, b - t), 1)
    dr = ImageDraw.Draw(im)
    dr.fontmode = "1"
    dr.text((-l, -t), str(d), font=font, fill=0)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def draw_grid(puzzle, solution=None, cell=60, scale=3):
    """9x9 판. solution을 주면 빈칸을 정답(보통 굵기)으로 채운다."""
    thick, thin = 4, 2
    size = cell * 9 + thick
    x0 = (PAPER_W - size) // 2
    im = Image.new("1", (PAPER_W, size + 8), 1)
    d = ImageDraw.Draw(im)
    for k in range(10):
        w = thick if k % 3 == 0 else thin
        off = (thick - w) // 2
        p = k * cell + off
        d.rectangle([x0 + p, 4, x0 + p + w - 1, 4 + size - 1], fill=0)
        d.rectangle([x0, 4 + p, x0 + size - 1, 4 + p + w - 1], fill=0)

    bold = ImageFont.truetype(str(FONT_DIR / "Galmuri11-Bold.ttf"), 12)
    regular = ImageFont.truetype(str(FONT_DIR / "Galmuri11.ttf"), 12)
    for i in range(81):
        r, c = divmod(i, 9)
        if puzzle[i]:
            glyph = draw_digit(puzzle[i], bold, scale)
        elif solution:
            glyph = draw_digit(solution[i], regular, scale)
        else:
            continue
        cx = x0 + c * cell + thick // 2 + (cell - glyph.width) // 2
        cy = 4 + r * cell + thick // 2 + (cell - glyph.height) // 2
        im.paste(glyph, (cx, cy))
    return im


def main():
    ap = argparse.ArgumentParser(description="스도쿠를 영수증 프린터로 인쇄")
    ap.add_argument("--level", choices=[v[0] for v in LEVELS.values()], default="medium")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답을 인쇄 (예: M482913)")
    add_output_args(ap)
    args = ap.parse_args()

    if args.answer:
        level, seed = args.answer[0].upper(), args.answer[1:]
        if level not in LEVELS or not seed.isdigit():
            ap.error("번호는 E/M/H 글자 뒤에 숫자가 오는 형식입니다 (예: M482913)")
    else:
        level = next(k for k, v in LEVELS.items() if v[0] == args.level)
        seed = str(random.randrange(100000, 1000000))
    number = f"{level}{seed}"
    puzzle, solution = generate(level, seed)
    clues = sum(1 for v in puzzle if v)

    if args.answer:
        sheet = stack(
            render([f"^ ## 스도쿠 정답", f"^ > No. {number}"]),
            draw_grid(puzzle, solution, cell=44, scale=2),
            render(["> 굵은 숫자가 처음에 주어진 숫자입니다."]),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 스도쿠", f"^ {today} · {LEVELS[level][1]} · Seed No. {number}"]),
            draw_grid(puzzle),
            render([
                "@20 가로줄, 세로줄, 3x3 칸에 1~9를 한 번씩 채우세요.",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {number}",
            ]),
        )

    tag = f"{number}_answer" if args.answer else number
    print(f"No. {number} (주어진 숫자 {clues}개) " + output(sheet, "games/sudoku", args, tag))


if __name__ == "__main__":
    main()
