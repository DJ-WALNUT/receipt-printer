"""점과 상자(땅따먹기) 판을 영수증 프린터로 인쇄한다. 둘이서 펜으로 선을 그으며 논다.

사용법 (프로젝트 폴더에서):
    python games/dots/dots.py               # 가로세로 점 8개 (상자 7x7)
    python games/dots/dots.py --size 6      # 가로세로 점 수 (4~12, 적을수록 칸이 크고 빨리 끝난다)
    python games/dots/dots.py --rows 12     # 세로만 점 12개로 길게 (가로는 --size)
    python games/dots/dots.py --preview     # 인쇄 없이 이미지만 저장

이미지는 games/dots/output/ 에 저장된다.
"""
import argparse
import datetime
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, output, render, stack

SIDE_PAD = 36
MIN_DOTS, MAX_DOTS, MAX_ROWS = 4, 12, 30


def draw_board(cols, rows):
    gap = (PAPER_W - SIDE_PAD * 2) // (cols - 1)
    x0 = (PAPER_W - gap * (cols - 1)) // 2
    im = Image.new("1", (PAPER_W, gap * (rows - 1) + SIDE_PAD * 2), 1)
    d = ImageDraw.Draw(im)
    r = 5
    for row in range(rows):
        for col in range(cols):
            x, y = x0 + col * gap, SIDE_PAD + row * gap
            d.ellipse([x - r, y - r, x + r, y + r], fill=0)
    return im


def main():
    ap = argparse.ArgumentParser(description="점과 상자 판을 영수증 프린터로 인쇄")
    ap.add_argument("--size", type=int, default=8, help=f"가로세로 점 수 ({MIN_DOTS}~{MAX_DOTS}, 기본 8)")
    ap.add_argument("--rows", type=int, help=f"세로 점 수만 따로 지정 ({MIN_DOTS}~{MAX_ROWS})")
    add_output_args(ap)
    args = ap.parse_args()
    rows = args.rows or args.size
    if not MIN_DOTS <= args.size <= MAX_DOTS:
        ap.error(f"--size는 {MIN_DOTS}~{MAX_DOTS} 사이여야 합니다")
    if not MIN_DOTS <= rows <= MAX_ROWS:
        ap.error(f"--rows는 {MIN_DOTS}~{MAX_ROWS} 사이여야 합니다")

    boxes = (args.size - 1) * (rows - 1)
    today = datetime.date.today().isoformat()
    sheet = stack(
        render(["^ # 점과 상자", f"^ {today} · 상자 {args.size - 1}x{rows - 1} = {boxes}칸", "",
                "이름 ________ || 이름 ________"]),
        draw_board(args.size, rows),
        render([
            "@20 번갈아 가며 이웃한 두 점을 가로나 세로 선으로 잇습니다.",
            "@20 상자의 네 번째 변을 그은 사람이 그 상자에 자기 표시를 하고 한 번 더 긋습니다.",
            "@20 선을 다 그었을 때 상자를 더 많이 가진 사람이 이깁니다.",
        ]),
    )
    print(f"점과 상자 {args.size}x{rows} " + output(sheet, "games/dots", args, f"{args.size}x{rows}"))


if __name__ == "__main__":
    main()
