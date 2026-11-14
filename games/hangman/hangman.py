"""행맨 놀이판을 영수증 프린터로 인쇄한다. 출제자가 낱말을 정하고, 도전자가 글자를 하나씩 맞힌다.

사용법 (프로젝트 폴더에서):
    python games/hangman/hangman.py              # 한글판 (자음·모음으로 풀어서 맞힘), 글자 칸 10개
    python games/hangman/hangman.py --lang en    # 영어판 (알파벳)
    python games/hangman/hangman.py --slots 14   # 글자 칸 개수 (4~20)
    python games/hangman/hangman.py --preview    # 인쇄 없이 이미지만 저장

이미지는 games/hangman/output/ 에 저장된다.
"""
import argparse
import datetime
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, draw_run, output, render, size_style, stack

LETTERS = {
    "ko": ["ㄱㄴㄷㄹㅁㅂㅅ", "ㅇㅈㅊㅋㅌㅍㅎ", "ㄲㄸㅃㅆㅉ", "ㅏㅑㅓㅕㅗㅛㅜ", "ㅠㅡㅣㅐㅒㅔㅖ"],
    "en": ["ABCDEFG", "HIJKLMN", "OPQRSTU", "VWXYZ"],
}
PARTS = ["머리", "몸통", "왼팔", "오른팔", "왼다리", "오른다리"]


def draw_gallows():
    """왼쪽에 교수대, 오른쪽에 틀릴 때마다 그릴 순서."""
    h = 300
    im = Image.new("1", (PAPER_W, h), 1)
    d = ImageDraw.Draw(im)
    t = 6
    d.rectangle([40, h - 14, 250, h - 14 + t - 1], fill=0)        # 바닥
    d.rectangle([80, 14, 80 + t - 1, h - 14], fill=0)             # 기둥
    d.rectangle([80, 14, 200, 14 + t - 1], fill=0)                # 가로대
    d.line([(80 + t, 60), (126, 14 + t)], fill=0, width=4)        # 버팀목
    d.rectangle([197, 14, 200, 52], fill=0)                       # 줄
    x = 300
    im.paste(draw_run("틀릴 때마다 하나씩!", "bold"), (x, 14))
    for i, part in enumerate(PARTS):
        im.paste(draw_run(f"{i + 1}. {part}", "body"), (x, 54 + i * 34))
    im.paste(draw_run("다 그리면 도전자의 패배", "small"), (x, 54 + len(PARTS) * 34 + 6))
    return im


def draw_slots(count, per_row=10):
    w, gap, h = 44, 10, 62
    rows = -(-count // per_row)
    im = Image.new("1", (PAPER_W, rows * h + 8), 1)
    d = ImageDraw.Draw(im)
    for i in range(count):
        r, c = divmod(i, per_row)
        n = min(per_row, count - r * per_row)
        x0 = (PAPER_W - (n * w + (n - 1) * gap)) // 2
        x, y = x0 + c * (w + gap), (r + 1) * h - 6
        d.rectangle([x, y, x + w - 1, y + 3], fill=0)
    return im


def draw_letters(rows):
    style = size_style(36, False)
    step, h = 68, 56
    im = Image.new("1", (PAPER_W, len(rows) * h + 8), 1)
    for r, letters in enumerate(rows):
        x0 = (PAPER_W - step * len(letters)) // 2
        for c, ch in enumerate(letters):
            glyph = draw_run(ch, style)
            im.paste(glyph, (x0 + c * step + (step - glyph.width) // 2, 4 + r * h + (h - glyph.height) // 2))
    return im


def main():
    ap = argparse.ArgumentParser(description="행맨 놀이판을 영수증 프린터로 인쇄")
    ap.add_argument("--lang", choices=["ko", "en"], default="ko", help="ko = 한글 자음·모음, en = 알파벳")
    ap.add_argument("--slots", type=int, default=10, help="글자 칸 개수 (4~20, 기본 10)")
    add_output_args(ap)
    args = ap.parse_args()
    if not 4 <= args.slots <= 20:
        ap.error("--slots는 4~20 사이여야 합니다")

    how = ("@20 출제자: 낱말을 자음·모음으로 풀어 글자 수만큼만 칸을 쓰고, 남는 칸은 지웁니다. (예: 나무 → ㄴㅏㅁㅜ)"
           if args.lang == "ko" else "@20 출제자: 낱말의 글자 수만큼만 칸을 쓰고, 남는 칸은 지웁니다.")
    today = datetime.date.today().isoformat()
    sheet = stack(
        render(["^ # 행맨", f"^ {today} · {'한글' if args.lang == 'ko' else 'English'}"]),
        draw_gallows(),
        render(["**낱말**"]),
        draw_slots(args.slots),
        render(["", "**부른 글자는 지우세요**"]),
        draw_letters(LETTERS[args.lang]),
        render([
            how,
            "@20 도전자: 글자를 하나씩 부릅니다. 낱말에 있으면 출제자가 그 칸을 모두 채우고, 없으면 사람을 한 획 그립니다.",
            "@20 사람이 다 그려지기 전에 낱말을 맞히면 도전자의 승리!",
        ]),
    )
    print("행맨 " + output(sheet, "games/hangman", args, args.lang))


if __name__ == "__main__":
    main()
