"""부등호 스도쿠(후토시키) 한 판을 영수증 프린터로 인쇄한다.

가로줄과 세로줄에 1~N을 한 번씩 넣되, 칸 사이의 부등호(<, >)를 지켜야 하는 작은 숫자 퍼즐이다.

사용법 (프로젝트 폴더에서):
    python games/futoshiki/futoshiki.py                    # 보통 난이도(5x5) 한 판 인쇄
    python games/futoshiki/futoshiki.py --level hard       # easy(4x4) | medium(5x5) | hard(6x6)
    python games/futoshiki/futoshiki.py --preview          # 인쇄 없이 이미지만 저장
    python games/futoshiki/futoshiki.py --answer FM482913   # 그 판의 정답 인쇄

이미지는 games/futoshiki/output/ 에 저장된다.
모든 판은 정답이 하나뿐이다. 시드번호(F + 난이도 글자 + 숫자)만 있으면 같은 판과 정답을 다시 만들 수 있다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, strip_seed, draw_run, output, render, size_style, stack

SEED_PREFIX = "F"  # 시드번호 맨 앞 글자. 콘텐츠마다 다르다.
LEVELS = {  # 글자: (이름, 표시, 한 변 칸 수, 남길 부등호 수, 칸 크기, 칸 사이 간격)
    "E": ("easy", "쉬움", 4, 12, 84, 44),
    "M": ("medium", "보통", 5, 16, 70, 34),
    "H": ("hard", "어려움", 6, 22, 60, 28),
}


def count_solutions(n, given, less, limit=2):
    """given: {칸: 숫자}, less: [(a, b)] = a칸 < b칸. 조건에 맞는 채우기의 수 (limit에서 멈춤)."""
    grid = [0] * (n * n)
    for cell, v in given.items():
        grid[cell] = v
    smaller = [[] for _ in grid]   # 칸마다: 이 칸보다 작아야 하는 칸들
    bigger = [[] for _ in grid]    # 칸마다: 이 칸보다 커야 하는 칸들
    for a, b in less:
        bigger[a].append(b)
        smaller[b].append(a)

    def options(i):
        r, c = divmod(i, n)
        used = {grid[r * n + k] for k in range(n)} | {grid[k * n + c] for k in range(n)}
        lo = max([grid[j] or 1 for j in smaller[i]], default=0) + 1 if smaller[i] else 1
        hi = min([grid[j] or n for j in bigger[i]], default=n + 1) - 1 if bigger[i] else n
        return [v for v in range(lo, hi + 1) if v not in used]

    def go():
        best, best_o = None, None
        for i in range(n * n):
            if not grid[i]:
                o = options(i)
                if best is None or len(o) < len(best_o):
                    best, best_o = i, o
                    if len(o) <= 1:
                        break
        if best is None:
            return 1
        total = 0
        for v in best_o:
            grid[best] = v
            total += go()
            if total >= limit:
                break
        grid[best] = 0
        return total

    for i, v in given.items():     # 처음 주어진 숫자끼리 어긋나면 해가 없다
        grid[i] = 0
        ok = v in options(i)
        grid[i] = v
        if not ok:
            return 0
    return go()


def generate(level, seed):
    """(주어진 숫자 {칸: 수}, 부등호 [(작은 칸, 큰 칸)], 정답) 반환."""
    _, _, n, target, _, _ = LEVELS[level]
    rng = random.Random(f"futo{level}{seed}")
    rows, cols, digits = list(range(n)), list(range(n)), list(range(1, n + 1))
    rng.shuffle(rows), rng.shuffle(cols), rng.shuffle(digits)
    solution = [digits[(rows[r] + cols[c]) % n] for r in range(n) for c in range(n)]

    pairs = [(i, i + 1) for i in range(n * n) if i % n != n - 1] + [(i, i + n) for i in range(n * n - n)]
    less = [(a, b) if solution[a] < solution[b] else (b, a) for a, b in pairs]
    given = {}
    cells = list(range(n * n))
    rng.shuffle(cells)
    while count_solutions(n, given, less) != 1:   # 부등호를 전부 줘도 모자라면 숫자를 보탠다
        cell = cells.pop()
        given[cell] = solution[cell]
    for cell in list(given):                      # 보탠 숫자 중 없어도 되는 것은 다시 뺀다
        value = given.pop(cell)
        if count_solutions(n, given, less) != 1:
            given[cell] = value
    rng.shuffle(less)
    for pair in less[:]:
        if len(less) <= target:
            break
        less.remove(pair)
        if count_solutions(n, given, less) != 1:
            less.append(pair)
    return given, less, solution


def draw_grid(level, given, less, solution=None, shrink=1.0):
    """판. solution을 주면 빈칸을 정답(보통 굵기)으로 채운다."""
    n = LEVELS[level][2]
    cell, gap = int(LEVELS[level][4] * shrink), int(LEVELS[level][5] * shrink)
    step = cell + gap
    size = n * cell + (n - 1) * gap
    x0, y0 = (PAPER_W - size) // 2, 8
    im = Image.new("1", (PAPER_W, size + 16), 1)
    d = ImageDraw.Draw(im)
    big = shrink == 1.0
    bold, regular = size_style(36 if big else 24, True), size_style(36 if big else 24, False)
    for i in range(n * n):
        r, c = divmod(i, n)
        x, y = x0 + c * step, y0 + r * step
        d.rectangle([x, y, x + cell - 1, y + cell - 1], outline=0, width=3)
        value, style = (given[i], bold) if i in given else (solution[i], regular) if solution else (0, None)
        if value:
            glyph = draw_run(str(value), style)
            im.paste(glyph, (x + (cell - glyph.width) // 2, y + (cell - glyph.height) // 2))
    arm, t = max(6, gap // 4), 3
    for a, b in less:   # 뾰족한 쪽이 작은 칸을 가리킨다
        (ra, ca), (rb, cb) = divmod(a, n), divmod(b, n)
        cx = x0 + (ca + cb) * step // 2 + cell // 2
        cy = y0 + (ra + rb) * step // 2 + cell // 2
        if ra == rb:
            tip = -arm if ca < cb else arm
            pts = [(cx - tip, cy - arm), (cx + tip, cy), (cx - tip, cy + arm)]
        else:
            tip = -arm if ra < rb else arm
            pts = [(cx - arm, cy - tip), (cx, cy + tip), (cx + arm, cy - tip)]
        d.line(pts, fill=0, width=t, joint="curve")
    return im


def main():
    ap = argparse.ArgumentParser(description="부등호 스도쿠를 영수증 프린터로 인쇄")
    ap.add_argument("--level", choices=[v[0] for v in LEVELS.values()], default="medium")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답을 인쇄 (예: FM482913)")
    add_output_args(ap)
    args = ap.parse_args()
    if args.answer:
        args.answer = strip_seed(args.answer, SEED_PREFIX, ap, "FM482913")

    if args.answer:
        level, seed = args.answer[:1].upper(), args.answer[1:]
        if level not in LEVELS or not seed.isdigit():
            ap.error("시드번호는 F + 난이도(E/M/H) + 숫자 형식입니다 (예: FM482913)")
    else:
        level = next(k for k, v in LEVELS.items() if v[0] == args.level)
        seed = str(random.randrange(100000, 1000000))
    number = f"{level}{seed}"
    seed_no = SEED_PREFIX + number
    label, n = LEVELS[level][1], LEVELS[level][2]
    given, less, solution = generate(level, seed)

    if args.answer:
        sheet = stack(
            render(["^ ## 부등호 스도쿠 정답", f"^ > No. {seed_no}"]),
            draw_grid(level, given, less, solution, shrink=0.7),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 부등호 스도쿠", f"^ {today} · {label} · Seed No. {seed_no}"]),
            draw_grid(level, given, less),
            render([
                f"@20 가로줄과 세로줄마다 1~{n}을 한 번씩 채우세요.",
                "@20 칸 사이의 부등호는 뾰족한 쪽 칸이 더 작다는 뜻입니다.",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {seed_no}",
            ]),
        )
    tag = f"{seed_no}_answer" if args.answer else seed_no
    print(f"No. {seed_no} ({n}x{n}, 부등호 {len(less)}개, 주어진 숫자 {len(given)}개) "
          + output(sheet, "games/futoshiki", args, tag))


if __name__ == "__main__":
    main()
