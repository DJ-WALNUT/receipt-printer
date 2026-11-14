"""펜으로 두는 오목판(오목종이)을 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python games/omok/omok.py               # 15x15 오목판 한 장
    python games/omok/omok.py --size 13     # 가로세로 13줄 (9~19, 줄이 적을수록 칸이 커진다)
    python games/omok/omok.py --rows 25     # 세로만 25줄로 길게 (가로는 --size)
    python games/omok/omok.py --sheets 3    # 세 장 연속
    python games/omok/omok.py --preview     # 인쇄 없이 이미지만 저장

이미지는 games/omok/output/ 에 저장된다.
"""
import argparse
import datetime
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, output, render, stack

SIDE_PAD = 20        # 가장자리 줄 바깥 여백 (끝줄에 그린 돌이 종이 밖으로 안 나가게)
MIN_LINES, MAX_LINES, MAX_ROWS = 9, 19, 60


def star_points(n):
    """화점이 놓일 줄 번호. 홀수 줄이면 한가운데, 13줄 이상이면 귀 쪽도."""
    if n % 2 == 0:
        return set()
    return {3, n // 2, n - 4} if n >= 13 else {n // 2}


def draw_board(cols, rows):
    gap = (PAPER_W - SIDE_PAD * 2) // (cols - 1)
    line, edge = 2, 4
    w, h = gap * (cols - 1), gap * (rows - 1)
    x0, y0 = (PAPER_W - w) // 2, SIDE_PAD
    im = Image.new("1", (PAPER_W, h + SIDE_PAD * 2), 1)
    d = ImageDraw.Draw(im)

    def bar(x1, y1, x2, y2, t):  # 두께 t인 선 (가운데 맞춤)
        d.rectangle([x1 - t // 2, y1 - t // 2, x2 + (t - 1) // 2, y2 + (t - 1) // 2], fill=0)

    for c in range(cols):
        x = x0 + c * gap
        bar(x, y0, x, y0 + h, edge if c in (0, cols - 1) else line)
    for r in range(rows):
        y = y0 + r * gap
        bar(x0, y, x0 + w, y, edge if r in (0, rows - 1) else line)
    dot = 5
    for r in star_points(rows):
        for c in star_points(cols):
            x, y = x0 + c * gap, y0 + r * gap
            d.ellipse([x - dot, y - dot, x + dot, y + dot], fill=0)
    return im


def main():
    ap = argparse.ArgumentParser(description="오목판을 영수증 프린터로 인쇄")
    ap.add_argument("--size", type=int, default=15, help=f"가로세로 줄 수 ({MIN_LINES}~{MAX_LINES}, 기본 15)")
    ap.add_argument("--rows", type=int, help=f"세로 줄 수만 따로 지정 ({MIN_LINES}~{MAX_ROWS})")
    ap.add_argument("--sheets", type=int, default=1, help="인쇄할 장 수")
    add_output_args(ap)
    args = ap.parse_args()
    rows = args.rows or args.size
    if not MIN_LINES <= args.size <= MAX_LINES:
        ap.error(f"--size는 {MIN_LINES}~{MAX_LINES} 사이여야 합니다")
    if not MIN_LINES <= rows <= MAX_ROWS:
        ap.error(f"--rows는 {MIN_LINES}~{MAX_ROWS} 사이여야 합니다")
    if args.sheets < 1:
        ap.error("--sheets는 1 이상이어야 합니다")

    today = datetime.date.today().isoformat()
    sheet = stack(
        render(["^ # 오목", f"^ {today} · {args.size}x{rows}", "", "● 흑 __________ || ○ 백 __________"]),
        draw_board(args.size, rows),
        render([
            "@20 줄이 만나는 점에 흑(●)부터 번갈아 돌을 그리세요.",
            "@20 가로, 세로, 대각선으로 먼저 다섯 개를 나란히 놓으면 승리!",
        ]),
    )
    for _ in range(args.sheets):
        print(f"오목판 {args.size}x{rows} " + output(sheet, "games/omok", args, f"{args.size}x{rows}"))


if __name__ == "__main__":
    main()
