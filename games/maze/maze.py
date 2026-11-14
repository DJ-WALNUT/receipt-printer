"""미로 한 판을 만들어 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python games/maze/maze.py                    # 보통 난이도 한 판 인쇄
    python games/maze/maze.py --level hard       # easy | medium | hard
    python games/maze/maze.py --preview          # 인쇄 없이 이미지만 저장
    python games/maze/maze.py --answer M482913   # 그 판의 정답 인쇄 (번호는 영수증 아래에 찍힘)

이미지는 games/maze/output/ 에 저장된다.
모든 미로는 길이 하나뿐이다. 판 번호(난이도 글자 + 숫자)만 있으면 같은 판과 정답을 다시 만들 수 있다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, draw_run, output, render, stack

LEVELS = {  # 글자: (이름, 표시, 가로 칸, 세로 칸, 칸 크기(도트), 정답지 칸 크기)
    "E": ("easy", "쉬움", 12, 12, 44, 32),
    "M": ("medium", "보통", 16, 22, 34, 24),
    "H": ("hard", "어려움", 20, 32, 28, 20),
}


def generate(level, seed):
    """(뚫린 벽 집합, 정답 경로) 반환. 출발은 왼쪽 위 칸, 도착은 오른쪽 아래 칸.

    되돌아가기 방식(깊이 우선)이라 고리가 없어서 두 칸 사이의 길은 항상 하나뿐이다.
    뚫린 벽은 이웃한 두 칸 (r, c)의 쌍으로 적는다 (작은 쪽이 앞).
    """
    cols, rows = LEVELS[level][2:4]
    rng = random.Random(f"{level}{seed}")
    start, goal = (0, 0), (rows - 1, cols - 1)
    opened, parent = set(), {start: None}
    trail = [start]
    while trail:
        r, c = trail[-1]
        nexts = [(r + dr, c + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                 if 0 <= r + dr < rows and 0 <= c + dc < cols and (r + dr, c + dc) not in parent]
        if not nexts:
            trail.pop()
            continue
        nxt = rng.choice(nexts)
        opened.add((min((r, c), nxt), max((r, c), nxt)))
        parent[nxt] = (r, c)
        trail.append(nxt)

    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return opened, path[::-1]


def arrow(size):
    """아래를 가리키는 화살표."""
    im = Image.new("1", (size, size), 1)
    d = ImageDraw.Draw(im)
    stem = max(2, size // 4)
    d.rectangle([(size - stem) // 2, 0, (size - stem) // 2 + stem - 1, size // 2], fill=0)
    d.polygon([(0, size // 2 - 1), (size - 1, size // 2 - 1), (size // 2, size - 1)], fill=0)
    return im


def draw_maze(level, opened, path=None, answer=False):
    """미로 그림. answer=True면 작게 그리고 정답 경로를 굵은 선으로 덧그린다."""
    cols, rows = LEVELS[level][2:4]
    cell = LEVELS[level][5 if answer else 4]
    wall = 2 if answer else 3
    w, h = cols * cell + wall, rows * cell + wall
    start_label, goal_label = draw_run("출발", "bold"), draw_run("도착", "bold")
    tip = 14
    x0 = (PAPER_W - w) // 2
    y0 = start_label.height + tip + 8
    im = Image.new("1", (PAPER_W, y0 + h + 8 + tip + goal_label.height + 4), 1)
    d = ImageDraw.Draw(im)

    def is_open(a, b):
        return (a, b) in opened

    def hwall(r, c):  # 칸 (r, c)의 위쪽 벽
        d.rectangle([x0 + c * cell, y0 + r * cell, x0 + (c + 1) * cell + wall - 1, y0 + r * cell + wall - 1], fill=0)

    def vwall(r, c):  # 칸 (r, c)의 왼쪽 벽
        d.rectangle([x0 + c * cell, y0 + r * cell, x0 + c * cell + wall - 1, y0 + (r + 1) * cell + wall - 1], fill=0)

    for r in range(rows):
        for c in range(cols):
            if (r == 0 and c != 0) or (r > 0 and not is_open((r - 1, c), (r, c))):
                hwall(r, c)
            if c == 0 or not is_open((r, c - 1), (r, c)):
                vwall(r, c)
        vwall(r, cols)                      # 오른쪽 테두리
    for c in range(cols - 1):               # 아래 테두리 (도착 칸만 열어 둔다)
        hwall(rows, c)

    def center(r, c):
        return x0 + c * cell + (cell + wall) // 2, y0 + r * cell + (cell + wall) // 2

    if answer:
        t = max(4, cell // 4)
        sx, sy = center(0, 0)
        gx, gy = center(rows - 1, cols - 1)
        points = [(sx, y0 - 4)] + [center(r, c) for r, c in path] + [(gx, y0 + h + 3)]
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            d.rectangle([min(ax, bx) - t // 2, min(ay, by) - t // 2,
                         max(ax, bx) + (t - 1) // 2, max(ay, by) + (t - 1) // 2], fill=0)

    # 출발·도착 표시: 글자는 미로 가장자리에 맞추고, 화살표는 열린 칸 한가운데를 가리킨다.
    tip_im = arrow(tip)
    sx, _ = center(0, 0)
    gx, _ = center(rows - 1, cols - 1)
    im.paste(start_label, (x0, 0))
    im.paste(tip_im, (sx - tip // 2, start_label.height + 2))
    im.paste(tip_im, (gx - tip // 2, y0 + h + 6))
    im.paste(goal_label, (x0 + w - goal_label.width, y0 + h + 8 + tip))
    return im


def main():
    ap = argparse.ArgumentParser(description="미로찾기를 영수증 프린터로 인쇄")
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
    opened, path = generate(level, seed)
    cols, rows = LEVELS[level][2:4]

    if args.answer:
        sheet = stack(
            render(["^ ## 미로찾기 정답", f"^ > No. {number}"]),
            draw_maze(level, opened, path, answer=True),
            render(["> 굵은 선이 정답 길입니다."]),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 미로찾기", f"^ {today} · {LEVELS[level][1]} · Seed No. {number}"]),
            draw_maze(level, opened),
            render([
                "@20 출발에서 도착까지 가는 길을 찾으세요. 길은 하나뿐입니다.",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {number}",
            ]),
        )

    tag = f"{number}_answer" if args.answer else number
    print(f"No. {number} ({cols}x{rows}칸, 정답 길이 {len(path)}칸) " + output(sheet, "games/maze", args, tag))


if __name__ == "__main__":
    main()
