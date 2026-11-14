"""사다리 타기를 영수증 프린터로 인쇄한다. 실행할 때마다 사다리가 달라진다.

사용법 (프로젝트 폴더에서):
    python games/ladder/ladder.py                              # 4명, 당첨 1개
    python games/ladder/ladder.py --players 6                  # 인원 (2~8)
    python games/ladder/ladder.py --names "민수,지아,하준"      # 위에 이름을 찍는다 (인원은 이름 수)
    python games/ladder/ladder.py --results "설거지,청소,통과"  # 아래 결과 (모자라면 나머지는 '통과')
    python games/ladder/ladder.py --wins 2                     # 결과를 안 줬을 때 '당첨' 개수
    python games/ladder/ladder.py --blank                      # 결과 칸을 비워 손으로 적는다
    python games/ladder/ladder.py --preview                    # 인쇄 없이 이미지만 저장

이미지는 games/ladder/output/ 에 저장된다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import CONTENT_W, MARGIN, PAPER_W, add_output_args, draw_run, fit, output, render, stack

LEVELS = 14      # 가로대를 놓을 수 있는 높이의 수
LEVEL_GAP = 34


def make_rungs(players, rng):
    """높이마다 가로대가 놓인 틈 번호의 집합. 옆 틈과는 같은 높이에 놓지 않고, 틈마다 3개 이상 놓는다."""
    while True:
        levels = []
        for _ in range(LEVELS):
            row, gap = set(), 0
            while gap < players - 1:
                if rng.random() < 0.4:
                    row.add(gap)
                    gap += 2
                else:
                    gap += 1
            levels.append(row)
        if all(sum(g in row for row in levels) >= 3 for g in range(players - 1)):
            return levels


def label_row(texts, xs, col_w, style="bold"):
    runs = [draw_run(fit(t, style, col_w - 6), style) if t else None for t in texts]
    h = max((r.height for r in runs if r), default=24)
    row = Image.new("1", (PAPER_W, h + 8), 1)
    d = ImageDraw.Draw(row)
    for run, x in zip(runs, xs):
        if run:
            row.paste(run, (x - run.width // 2, 4))
        else:   # 빈 결과 칸: 손으로 적을 밑줄
            d.rectangle([x - col_w // 2 + 8, h + 2, x + col_w // 2 - 8, h + 3], fill=0)
    return row


def draw_ladder(levels, xs):
    h = (LEVELS + 1) * LEVEL_GAP
    im = Image.new("1", (PAPER_W, h), 1)
    d = ImageDraw.Draw(im)
    t = 4
    for x in xs:
        d.rectangle([x - t // 2, 0, x + t // 2 - 1, h - 1], fill=0)
    for k, row in enumerate(levels, 1):
        y = k * LEVEL_GAP
        for gap in row:
            d.rectangle([xs[gap], y - t // 2, xs[gap + 1], y + t // 2 - 1], fill=0)
    return im


def main():
    ap = argparse.ArgumentParser(description="사다리 타기를 영수증 프린터로 인쇄")
    ap.add_argument("--players", type=int, default=4, help="인원 (2~8, 기본 4)")
    ap.add_argument("--names", metavar="이름,이름", help="위에 찍을 이름 (쉼표로 구분, 인원은 이름 수가 된다)")
    ap.add_argument("--results", metavar="결과,결과", help="아래에 찍을 결과 (쉼표로 구분)")
    ap.add_argument("--wins", type=int, default=1, help="--results가 없을 때 '당첨' 개수 (기본 1)")
    ap.add_argument("--blank", action="store_true", help="결과 칸을 비워 둔다")
    add_output_args(ap)
    args = ap.parse_args()

    names = [n.strip() for n in args.names.split(",") if n.strip()] if args.names else None
    players = len(names) if names else args.players
    if not 2 <= players <= 8:
        ap.error("인원은 2~8명이어야 합니다")
    names = names or [str(i + 1) for i in range(players)]
    if args.blank:
        results = [""] * players
    elif args.results:
        results = [r.strip() for r in args.results.split(",") if r.strip()]
        if len(results) > players:
            ap.error(f"결과가 인원({players}명)보다 많습니다")
        results += ["통과"] * (players - len(results))
        random.shuffle(results)
    else:
        if not 1 <= args.wins < players:
            ap.error(f"--wins는 1~{players - 1} 사이여야 합니다")
        results = ["당첨"] * args.wins + ["꽝"] * (players - args.wins)
        random.shuffle(results)

    levels = make_rungs(players, random.Random())
    col_w = CONTENT_W // players
    xs = [MARGIN + col_w // 2 + i * col_w for i in range(players)]
    style = "bold" if col_w >= 90 else "small"   # 7명부터는 칸이 좁아 작은 글씨로
    today = datetime.date.today().isoformat()
    sheet = stack(
        render(["^ # 사다리 타기", f"^ {today} · {players}명", ""]),
        label_row(names, xs, col_w, style),
        draw_ladder(levels, xs),
        label_row(results, xs, col_w, style),
        render(["", "@20 위에서 하나를 골라 선을 따라 내려갑니다. 가로대를 만나면 반드시 건너갑니다.",
                "@20 사다리를 접어 가리고 고른 다음 펼치면 더 재미있습니다."]),
    )
    print(f"사다리 {players}명 " + output(sheet, "games/ladder", args, f"{players}p"))  # 결과는 화면에 안 보여 준다


if __name__ == "__main__":
    main()
