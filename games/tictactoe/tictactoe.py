"""틱택토 판 묶음을 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python games/tictactoe/tictactoe.py              # 3x3 판 6개 한 장
    python games/tictactoe/tictactoe.py --boards 10  # 판 개수 (2~12, 두 개씩 한 줄)
    python games/tictactoe/tictactoe.py --super      # 슈퍼 틱택토 (작은 판 9개를 엮은 큰 판)
    python games/tictactoe/tictactoe.py --preview    # 인쇄 없이 이미지만 저장

이미지는 games/tictactoe/output/ 에 저장된다.
"""
import argparse
import datetime
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, draw_run, output, render, stack


def hash_lines(d, x, y, cell, t):
    """(x, y)를 왼쪽 위로 하는 3x3 판의 우물 정(井) 자 선."""
    size = cell * 3
    for k in (1, 2):
        d.rectangle([x + k * cell - t // 2, y, x + k * cell + (t - 1) // 2, y + size - 1], fill=0)
        d.rectangle([x, y + k * cell - t // 2, x + size - 1, y + k * cell + (t - 1) // 2], fill=0)


def draw_boards(count):
    cell, per_row = 68, 2
    size = cell * 3
    gap_x = (PAPER_W - size * per_row) // (per_row + 1)
    label_h, gap_y = 30, 26
    rows = -(-count // per_row)
    im = Image.new("1", (PAPER_W, rows * (label_h + size + gap_y) + 6), 1)
    d = ImageDraw.Draw(im)
    for i in range(count):
        r, c = divmod(i, per_row)
        x, y = gap_x + c * (size + gap_x), 6 + r * (label_h + size + gap_y)
        im.paste(draw_run(f"{i + 1}판", "small"), (x, y))
        hash_lines(d, x, y + label_h, cell, 4)
    return im


def draw_super():
    small, pad = 52, 14
    big = small * 3 + pad * 2
    size = big * 3
    x0 = (PAPER_W - size) // 2
    im = Image.new("1", (PAPER_W, size + 16), 1)
    d = ImageDraw.Draw(im)
    hash_lines(d, x0, 8, big, 6)
    for r in range(3):
        for c in range(3):
            hash_lines(d, x0 + c * big + pad, 8 + r * big + pad, small, 2)
    return im


def main():
    ap = argparse.ArgumentParser(description="틱택토 판을 영수증 프린터로 인쇄")
    ap.add_argument("--boards", type=int, default=6, help="판 개수 (2~12, 기본 6)")
    ap.add_argument("--super", action="store_true", help="슈퍼 틱택토 판")
    add_output_args(ap)
    args = ap.parse_args()
    if not 2 <= args.boards <= 12:
        ap.error("--boards는 2~12 사이여야 합니다")

    today = datetime.date.today().isoformat()
    names = "O ________ || X ________"
    if args.super:
        sheet = stack(
            render(["^ # 슈퍼 틱택토", f"^ {today}", "", names]),
            draw_super(),
            render([
                "@20 작은 판에서 한 줄을 만들면 그 판을 차지합니다. 차지한 판으로 큰 판에서 한 줄을 만들면 승리!",
                "@20 상대가 방금 둔 칸의 자리와 같은 자리의 작은 판에만 둘 수 있습니다. (가운데 칸에 뒀다면 가운데 판)",
                "@20 그 판이 이미 끝났거나 꽉 찼으면 아무 판에나 둡니다.",
            ]),
        )
        tag = "super"
    else:
        sheet = stack(
            render(["^ # 틱택토", f"^ {today} · {args.boards}판", "", names]),
            draw_boards(args.boards),
            render(["@20 번갈아 O와 X를 그려, 가로·세로·대각선으로 먼저 세 개를 나란히 놓으면 이깁니다.",
                    "@20 판마다 먼저 두는 사람을 바꾸세요."]),
        )
        tag = f"{args.boards}boards"
    print("틱택토 " + output(sheet, "games/tictactoe", args, tag))


if __name__ == "__main__":
    main()
