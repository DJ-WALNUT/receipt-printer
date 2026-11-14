"""지뢰찾기 퍼즐 한 판을 영수증 프린터로 인쇄한다. 숫자를 보고 지뢰가 숨은 칸을 전부 찾는다.

사용법 (프로젝트 폴더에서):
    python games/minesweeper/minesweeper.py                    # 보통 난이도 한 판 인쇄
    python games/minesweeper/minesweeper.py --level hard       # easy | medium | hard
    python games/minesweeper/minesweeper.py --preview          # 인쇄 없이 이미지만 저장
    python games/minesweeper/minesweeper.py --answer M482913   # 그 판의 정답 인쇄

이미지는 games/minesweeper/output/ 에 저장된다.
모든 판은 정답이 하나뿐이다. 판 번호(난이도 글자 + 숫자)만 있으면 같은 판과 정답을 다시 만들 수 있다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, draw_run, output, render, size_style, stack

LEVELS = {  # 글자: (이름, 표시, 한 변 칸 수, 지뢰 수, 남길 숫자 개수)
    "E": ("easy", "쉬움", 6, 6, 18),
    "M": ("medium", "보통", 7, 10, 18),
    "H": ("hard", "어려움", 8, 14, 20),
}


def neighbors(i, n):
    r, c = divmod(i, n)
    return [(r + dr) * n + c + dc for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr or dc) and 0 <= r + dr < n and 0 <= c + dc < n]


def count_solutions(n, clues, mines, limit=2):
    """숫자(clues: {칸: 수})와 지뢰 총수에 맞는 지뢰 배치의 수 (limit에서 멈춤)."""
    unknown = [i for i in range(n * n) if i not in clues]
    pos = {cell: k for k, cell in enumerate(unknown)}
    near = {cell: [pos[j] for j in neighbors(cell, n) if j in pos] for cell in clues}
    if any(len(near[cell]) < v for cell, v in clues.items()):
        return 0
    touching = [[] for _ in unknown]          # 빈칸마다 영향을 받는 숫자 칸
    for cell, ks in near.items():
        for k in ks:
            touching[k].append(cell)
    need = dict(clues)                        # 숫자마다 아직 더 필요한 지뢰 수
    left = {cell: len(ks) for cell, ks in near.items()}  # 숫자마다 아직 안 정한 주변 칸 수

    def go(k, remaining):
        if k == len(unknown):
            return 1 if remaining == 0 else 0
        if remaining > len(unknown) - k:
            return 0
        total = 0
        for mine in (1, 0):
            if mine and not remaining:
                continue
            ok = True
            for cell in touching[k]:
                need[cell] -= mine
                left[cell] -= 1
                if need[cell] < 0 or need[cell] > left[cell]:
                    ok = False
            if ok:
                total += go(k + 1, remaining - mine)
            for cell in touching[k]:
                need[cell] += mine
                left[cell] += 1
            if total >= limit:
                break
        return total

    return go(0, mines)


def generate(level, seed):
    """(숫자 {칸: 수}, 지뢰 칸 집합) 반환. 정답이 하나로 유지되는 동안만 숫자를 지운다."""
    _, _, n, mines, target = LEVELS[level]
    rng = random.Random(f"mine{level}{seed}")
    bombs = set(rng.sample(range(n * n), mines))
    clues = {i: sum(j in bombs for j in neighbors(i, n)) for i in range(n * n) if i not in bombs}
    order = list(clues)
    rng.shuffle(order)
    for cell in order:
        if len(clues) <= target:
            break
        keep = clues.pop(cell)
        if count_solutions(n, clues, mines) != 1:
            clues[cell] = keep
    return clues, bombs


def draw_grid(n, clues, bombs=None, cell=64):
    """판. bombs를 주면 정답지: 지뢰 칸에 검은 동그라미를 그린다."""
    thick = 4
    size = cell * n + thick
    x0 = (PAPER_W - size) // 2
    im = Image.new("1", (PAPER_W, size + 12), 1)
    d = ImageDraw.Draw(im)
    for k in range(n + 1):
        t = thick if k in (0, n) else 2
        p = k * cell + (thick - t) // 2
        d.rectangle([x0 + p, 6, x0 + p + t - 1, 6 + size - 1], fill=0)
        d.rectangle([x0, 6 + p, x0 + size - 1, 6 + p + t - 1], fill=0)
    style = size_style(36, True) if cell >= 56 else size_style(24, True)
    for i in range(n * n):
        r, c = divmod(i, n)
        cx, cy = x0 + thick // 2 + c * cell + cell // 2, 6 + thick // 2 + r * cell + cell // 2
        if i in clues:
            glyph = draw_run(str(clues[i]), style)
            im.paste(glyph, (cx - glyph.width // 2, cy - glyph.height // 2))
        elif bombs and i in bombs:
            rad = cell // 4
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=0)
    return im


def main():
    ap = argparse.ArgumentParser(description="지뢰찾기 퍼즐을 영수증 프린터로 인쇄")
    ap.add_argument("--level", choices=[v[0] for v in LEVELS.values()], default="medium")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답을 인쇄 (예: M482913)")
    add_output_args(ap)
    args = ap.parse_args()

    if args.answer:
        level, seed = args.answer[:1].upper(), args.answer[1:]
        if level not in LEVELS or not seed.isdigit():
            ap.error("번호는 E/M/H 글자 뒤에 숫자가 오는 형식입니다 (예: M482913)")
    else:
        level = next(k for k, v in LEVELS.items() if v[0] == args.level)
        seed = str(random.randrange(100000, 1000000))
    number = f"{level}{seed}"
    _, label, n, mines, _ = LEVELS[level]
    clues, bombs = generate(level, seed)

    if args.answer:
        sheet = stack(
            render(["^ ## 지뢰찾기 정답", f"^ > No. {number}"]),
            draw_grid(n, clues, bombs, cell=44),
            render(["> 검은 동그라미가 지뢰입니다."]),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 지뢰찾기", f"^ {today} · {label} · Seed No. {number}"]),
            draw_grid(n, clues, cell=min(64, 540 // n)),
            render([
                f"**빈칸 가운데 {mines}칸에 지뢰가 숨어 있습니다.**",
                "@20 숫자는 그 칸을 둘러싼 여덟 칸에 있는 지뢰의 수입니다. 숫자 칸에는 지뢰가 없습니다.",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {number}",
            ]),
        )
    tag = f"{number}_answer" if args.answer else number
    print(f"No. {number} ({n}x{n}, 지뢰 {mines}개, 숫자 {len(clues)}개) " + output(sheet, "games/minesweeper", args, tag))


if __name__ == "__main__":
    main()
