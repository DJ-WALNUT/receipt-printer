"""다른 그림 찾기 한 판을 영수증 프린터로 인쇄한다.

타로 카드 도트 그림(fortune/tarot/tarot.py) 두 장을 나란히 찍는다. 오른쪽 그림은 몇 군데가 다르다.

사용법 (프로젝트 폴더에서):
    python games/spot/spot.py                   # 다른 곳 5군데
    python games/spot/spot.py --count 7         # 다른 곳 개수 (3~8)
    python games/spot/spot.py --preview         # 인쇄 없이 이미지만 저장
    python games/spot/spot.py --answer 5482913  # 그 판의 정답 인쇄 (번호는 영수증 아래에 찍힘)

이미지는 games/spot/output/ 에 저장된다.
판 번호는 다른 곳 개수 + 여섯 자리 숫자다. 번호만 있으면 같은 판과 정답을 다시 만들 수 있다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))             # 공용 모듈 receipt.py
sys.path.insert(0, str(ROOT / "fortune" / "tarot"))   # 카드 그림
from receipt import PAPER_W, add_output_args, output, render, stack
import tarot

SCALE = 3
AREA = (7, 19, 63, 77)   # 그림을 바꿔도 되는 범위 (카드 테두리와 위아래 이름 띠는 건드리지 않는다)


def make(number):
    """(원본, 바뀐 그림, 다른 곳 [(x, y, 크기)]) 반환. 좌표는 확대 전 도트 기준."""
    count = int(number[0])
    rng = random.Random(f"spot{number}")
    original = tarot.card_image(rng.randrange(len(tarot.ART)), scale=1)
    changed = original.copy()
    src, d = original.load(), ImageDraw.Draw(changed)
    spots = []
    for _ in range(5000):
        if len(spots) == count:
            break
        s = rng.randint(5, 7)
        x, y = rng.randint(AREA[0], AREA[2] - s), rng.randint(AREA[1], AREA[3] - s)
        if any(abs(x - px) < s + ps + 3 and abs(y - py) < s + ps + 3 for px, py, ps in spots):
            continue   # 다른 곳끼리 너무 붙지 않게
        black = sum(src[x + i, y + j] == 0 for i in range(s) for j in range(s)) / (s * s)
        if black < 0.3:      # 밝은 곳에는 검은 점을 찍고
            d.ellipse([x, y, x + s - 1, y + s - 1], fill=0)
        elif black > 0.5:    # 어두운 곳은 하얗게 지운다
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=1)
        else:                # 어중간한 곳은 바꿔도 티가 안 나서 건너뛴다
            continue
        spots.append((x, y, s))
    return original, changed, spots


def big(im):
    return im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)


def side_by_side(left, right):
    gap = (PAPER_W - left.width - right.width) // 3
    row = Image.new("1", (PAPER_W, left.height + 16), 1)
    row.paste(left, (gap, 8))
    row.paste(right, (gap * 2 + left.width, 8))
    return row


def circled(changed, spots):
    """정답지: 바뀐 그림 위에 다른 곳마다 동그라미."""
    im = big(changed)
    d = ImageDraw.Draw(im)
    for x, y, s in spots:
        cx, cy, r = (x + s / 2) * SCALE, (y + s / 2) * SCALE, s * SCALE
        d.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], outline=1, width=7)  # 흰 테를 먼저 둘러 잘 보이게
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=3)
    row = Image.new("1", (PAPER_W, im.height + 16), 1)
    row.paste(im, ((PAPER_W - im.width) // 2, 8))
    return row


def main():
    ap = argparse.ArgumentParser(description="다른 그림 찾기를 영수증 프린터로 인쇄")
    ap.add_argument("--count", type=int, default=5, help="다른 곳 개수 (3~8, 기본 5)")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답을 인쇄 (예: 5482913)")
    add_output_args(ap)
    args = ap.parse_args()

    if args.answer:
        number = args.answer
        if not (number.isdigit() and len(number) > 1 and 3 <= int(number[0]) <= 8):
            ap.error("번호는 숫자로만 되어 있고 첫 자리가 3~8입니다 (예: 5482913)")
    else:
        if not 3 <= args.count <= 8:
            ap.error("--count는 3~8 사이여야 합니다")
        number = f"{args.count}{random.randrange(100000, 1000000)}"
    original, changed, spots = make(number)

    if args.answer:
        sheet = stack(
            render(["^ ## 다른 그림 찾기 정답", f"^ > No. {number}"]),
            circled(changed, spots),
            render([f"> 동그라미 친 {len(spots)}군데가 다릅니다."]),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 다른 그림 찾기", f"^ {today} · Seed No. {number}"]),
            side_by_side(big(original), big(changed)),
            render([
                f"**두 그림에서 다른 곳 {len(spots)}군데를 찾으세요.**",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {number}",
            ]),
        )
    tag = f"{number}_answer" if args.answer else number
    print(f"No. {number} (다른 곳 {len(spots)}군데) " + output(sheet, "games/spot", args, tag))


if __name__ == "__main__":
    main()
