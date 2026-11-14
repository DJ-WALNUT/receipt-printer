"""빙고판을 영수증 프린터로 인쇄한다. 실행할 때마다 숫자 배치가 다른 판이 나온다.

사용법 (프로젝트 폴더에서):
    python games/bingo/bingo.py                 # 5x5 판 한 장 (1~25를 섞어 채움)
    python games/bingo/bingo.py --sheets 10     # 서로 다른 판 10장
    python games/bingo/bingo.py --size 4        # 4x4 판 (3~7)
    python games/bingo/bingo.py --max 50        # 1~50 중에서 뽑아 채움 (판마다 들어가는 숫자가 달라진다)
    python games/bingo/bingo.py --blank         # 빈 판 (숫자나 낱말을 직접 적는 용)
    python games/bingo/bingo.py --caller        # 진행자용: 부를 순서를 섞어 놓은 용지
    python games/bingo/bingo.py --preview       # 인쇄 없이 이미지만 저장

이미지는 games/bingo/output/ 에 저장된다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, draw_run, output, render, size_style, stack


def draw_card(size, numbers):
    """numbers가 None이면 빈 판."""
    cell = min(104, 540 // size)
    thick = 4
    w = cell * size + thick
    x0 = (PAPER_W - w) // 2
    im = Image.new("1", (PAPER_W, w + 12), 1)
    d = ImageDraw.Draw(im)
    for k in range(size + 1):
        t = thick if k in (0, size) else 2
        p = k * cell + (thick - t) // 2
        d.rectangle([x0 + p, 6, x0 + p + t - 1, 6 + w - 1], fill=0)
        d.rectangle([x0, 6 + p, x0 + w - 1, 6 + p + t - 1], fill=0)
    if numbers:
        style = size_style(48, True) if cell >= 80 else size_style(36, True)
        for i, n in enumerate(numbers):
            r, c = divmod(i, size)
            glyph = draw_run(str(n), style)
            im.paste(glyph, (x0 + thick // 2 + c * cell + (cell - glyph.width) // 2,
                             6 + thick // 2 + r * cell + (cell - glyph.height) // 2))
    return im


def draw_calls(order, per_row=6):
    """부를 순서: 번호를 순서대로 늘어놓고, 부른 번호를 지울 수 있게 칸으로 나눈다."""
    cell_w, cell_h = 540 // per_row, 64
    rows = -(-len(order) // per_row)
    x0 = (PAPER_W - cell_w * per_row) // 2
    im = Image.new("1", (PAPER_W, rows * cell_h + 12), 1)
    d = ImageDraw.Draw(im)
    style = size_style(36, True)
    for i, n in enumerate(order):
        r, c = divmod(i, per_row)
        x, y = x0 + c * cell_w, 6 + r * cell_h
        d.rectangle([x, y, x + cell_w, y + cell_h], outline=0, width=2)
        glyph = draw_run(str(n), style)
        im.paste(glyph, (x + (cell_w - glyph.width) // 2 + 1, y + (cell_h - glyph.height) // 2 + 1))
    return im


def main():
    ap = argparse.ArgumentParser(description="빙고판을 영수증 프린터로 인쇄")
    ap.add_argument("--size", type=int, default=5, help="한 변 칸 수 (3~7, 기본 5)")
    ap.add_argument("--max", type=int, help="가장 큰 숫자 (기본: 칸 수와 같게, 5x5면 25)")
    ap.add_argument("--sheets", type=int, default=1, help="인쇄할 장 수 (장마다 다른 판)")
    ap.add_argument("--blank", action="store_true", help="숫자 없는 빈 판")
    ap.add_argument("--caller", action="store_true", help="진행자용 부를 순서 용지")
    add_output_args(ap)
    args = ap.parse_args()
    cells = args.size * args.size
    top = args.max or cells
    if not 3 <= args.size <= 7:
        ap.error("--size는 3~7 사이여야 합니다")
    if not cells <= top <= 99:
        ap.error(f"--max는 {cells}~99 사이여야 합니다 (칸이 {cells}개)")
    if args.sheets < 1:
        ap.error("--sheets는 1 이상이어야 합니다")

    today = datetime.date.today().isoformat()
    for _ in range(args.sheets):
        if args.caller:
            order = random.sample(range(1, top + 1), top)
            sheet = stack(
                render(["^ # 빙고 진행자용", f"^ {today} · 1~{top}", "",
                        "@20 왼쪽 위부터 가로로 한 줄씩, 순서대로 부르고 지우세요."]),
                draw_calls(order),
            )
            tag = f"caller_{top}"
        else:
            numbers = None if args.blank else random.sample(range(1, top + 1), cells)
            guide = ("@20 칸마다 숫자나 낱말을 하나씩 적으세요." if args.blank
                     else "@20 부르는 숫자가 있으면 그 칸에 표시하세요.")
            sheet = stack(
                render(["^ # 빙고", f"^ {today} · {args.size}x{args.size}"
                        + ("" if args.blank else f" · 1~{top}"), "", "이름 ____________ || ____줄 빙고!"]),
                draw_card(args.size, numbers),
                render([guide, "@20 가로, 세로, 대각선으로 한 줄이 모두 표시되면 한 줄 빙고!"]),
            )
            tag = f"{args.size}x{args.size}" + ("_blank" if args.blank else "")
        print("빙고 " + ("진행자용 " if args.caller else "") + output(sheet, "games/bingo", args, tag))


if __name__ == "__main__":
    main()
