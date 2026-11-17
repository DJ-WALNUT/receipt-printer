"""숨은 글자 찾기 한 판을 영수증 프린터로 인쇄한다. 같은 글자가 가득한 판에서 섞인 비슷한 글자를 찾는다 (6 사이의 8).

사용법 (프로젝트 폴더에서):
    python games/oddchar/oddchar.py                    # 보통 난이도, 숨은 글자 1개
    python games/oddchar/oddchar.py --level hard       # easy | medium | hard
    python games/oddchar/oddchar.py --count 3          # 숨은 글자 개수 (1~3)
    python games/oddchar/oddchar.py --preview          # 인쇄 없이 이미지만 저장
    python games/oddchar/oddchar.py --answer GM1482913  # 그 판의 정답 인쇄 (번호는 영수증 아래에 찍힘)

이미지는 games/oddchar/output/ 에 저장된다.
시드번호는 G + 난이도 글자 + 숨은 글자 개수 + 여섯 자리 숫자다. 번호만 있으면 같은 판과 정답을 다시 만들 수 있다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import CONTENT_W, PAPER_W, add_output_args, draw_run, output, render, size_style, stack, strip_seed

SEED_PREFIX = "G"  # 시드번호 맨 앞 글자. 콘텐츠마다 다르다.

LEVELS = {  # 글자: (이름, 표시, 가로 칸, 세로 칸, 글자 높이)
    "E": ("easy", "쉬움", 10, 12, 48),
    "M": ("medium", "보통", 14, 18, 36),
    "H": ("hard", "어려움", 18, 26, 24),
}

# (바탕 글자, 숨은 글자, 아주 닮았는지). 어려움은 아주 닮은 짝만 쓴다.
# 순서를 바꾸거나 중간에 끼우면 예전 시드번호가 다른 판이 된다. 새 짝은 맨 뒤에 추가한다.
PAIRS = [
    ("6", "8", True), ("9", "8", True), ("3", "8", True), ("5", "6", True), ("0", "8", True), ("1", "7", False),
    ("O", "Q", True), ("E", "F", True), ("P", "R", True), ("C", "G", True), ("M", "N", False), ("b", "d", False),
    ("p", "q", False), ("U", "V", True), ("V", "W", False),
    ("ㅂ", "ㅍ", False), ("ㅏ", "ㅓ", False), ("ㅗ", "ㅜ", False), ("ㅈ", "ㅊ", True), ("ㄱ", "ㅋ", True),
    ("ㄷ", "ㅌ", True), ("ㅁ", "ㅂ", True), ("ㅇ", "ㅎ", True), ("ㅐ", "ㅔ", True),
    ("물", "몰", True), ("빛", "빚", True), ("곰", "공", True), ("밤", "방", True), ("달", "닭", True),
    ("굴", "귤", True), ("복", "북", True), ("개", "게", True), ("웃", "옷", True), ("입", "잎", True),
    ("감", "강", True), ("왕", "웡", True),
]


def make(number):
    """(바탕 글자, 숨은 글자, 판[줄][칸], 숨은 칸 목록). number 는 시드번호에서 G를 뗀 것 (예: M1482913)."""
    level, count = number[0], int(number[1])
    cols, rows = LEVELS[level][2:4]
    rng = random.Random(number)
    pairs = [p for p in PAIRS if p[2]] if level == "H" else PAIRS
    base, odd, _ = rng.choice(pairs)
    if rng.random() < 0.5 and level != "E":   # 보통·어려움은 짝을 거꾸로도 쓴다 (8 사이의 6)
        base, odd = odd, base
    spots = []
    while len(spots) < count:   # 숨은 글자끼리 붙어 있으면 하나로 보이니 한 칸 이상 띄운다
        cell = (rng.randrange(rows), rng.randrange(cols))
        if all(max(abs(cell[0] - r), abs(cell[1] - c)) >= 2 for r, c in spots):
            spots.append(cell)
    board = [[odd if (r, c) in spots else base for c in range(cols)] for r in range(rows)]
    return base, odd, board, spots


def draw_board(board, level, spots=None):
    """글자판. spots 를 주면 정답지: 숨은 글자에 동그라미를 치고 나머지 칸은 점으로 둔다."""
    rows, cols = len(board), len(board[0])
    cell = CONTENT_W // cols
    w, h = cols * cell, rows * cell
    frame = 3
    x0, y0 = (PAPER_W - w) // 2, 6 + frame
    im = Image.new("1", (PAPER_W, h + (6 + frame) * 2), 1)
    d = ImageDraw.Draw(im)
    for k in range(frame):
        d.rectangle([x0 - 1 - k, y0 - 1 - k, x0 + w + k, y0 + h + k], outline=0)
    style = size_style(LEVELS[level][4], False)
    glyphs = {}
    for r, row in enumerate(board):
        for c, ch in enumerate(row):
            cx, cy = x0 + c * cell + cell // 2, y0 + r * cell + cell // 2
            if spots is not None and (r, c) not in spots:
                d.rectangle([cx - 1, cy - 1, cx + 1, cy + 1], fill=0)
                continue
            glyph = glyphs.get(ch) or glyphs.setdefault(ch, draw_run(ch, style))
            im.paste(glyph, (cx - glyph.width // 2, cy - glyph.height // 2))
            if spots is not None:
                rad = cell // 2 + 2
                d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=0, width=3)
    return im


def main():
    ap = argparse.ArgumentParser(description="숨은 글자 찾기를 영수증 프린터로 인쇄")
    ap.add_argument("--level", choices=[v[0] for v in LEVELS.values()], default="medium")
    ap.add_argument("--count", type=int, default=1, help="숨은 글자 개수 (1~3, 기본 1)")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답을 인쇄 (예: GM1482913)")
    add_output_args(ap)
    args = ap.parse_args()

    if args.answer:
        number = strip_seed(args.answer, SEED_PREFIX, ap, "GM1482913").upper()
        if (len(number) != 8 or number[0] not in LEVELS or number[1] not in "123"
                or not (number[2:].isdigit() and number[2:].isascii())):
            ap.error("시드번호는 G + 난이도(E/M/H) + 개수(1~3) + 여섯 자리 숫자입니다 (예: GM1482913)")
    else:
        if not 1 <= args.count <= 3:
            ap.error("--count는 1~3 사이여야 합니다")
        level = next(k for k, v in LEVELS.items() if v[0] == args.level)
        number = f"{level}{args.count}{random.randrange(100000, 1000000)}"
    level, count = number[0], int(number[1])
    seed_no = SEED_PREFIX + number
    base, odd, board, spots = make(number)
    where = ", ".join(f"{r + 1}째 줄 {c + 1}째 칸" for r, c in sorted(spots))

    if args.answer:
        sheet = stack(
            render(["^ ## 숨은 글자 찾기 정답", f"^ > No. {seed_no}"]),
            draw_board(board, level, spots),
            render([f"> '{base}' 사이에 숨은 '{odd}': {where}"]),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 숨은 글자 찾기", f"^ {today} · {LEVELS[level][1]} · Seed No. {seed_no}"]),
            render([f"^ **'{base}' 사이에 숨은 '{odd}' {count}개를 찾으세요!**"]),
            draw_board(board, level),
            render([
                "@20 찾으면 동그라미를 치세요. 누가 먼저 찾나 겨뤄 봐도 좋아요.",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {seed_no}",
            ]),
        )
    tag = f"{seed_no}_answer" if args.answer else seed_no
    print(f"No. {seed_no} ({LEVELS[level][1]}, {count}개) " + output(sheet, "games/oddchar", args, tag))


if __name__ == "__main__":
    main()
