"""TRPG 전리품 뽑기: 랜덤 아이템 감정서를 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python fortune/loot/loot.py                 # 한 장 뽑기
    python fortune/loot/loot.py --loop          # Enter를 누를 때마다 한 장 (버튼 자판기 모드)
    python fortune/loot/loot.py --level 20      # 아이템 레벨 지정 (기본: 1~30 무작위)
    python fortune/loot/loot.py --seed L482913   # 같은 시드번호의 아이템 다시 뽑기
    python fortune/loot/loot.py --preview       # 인쇄 없이 이미지만 저장

이미지는 fortune/loot/output/ 에 저장된다.
"""
import argparse
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import PAPER_W, add_output_args, strip_seed, output, render, stack

SEED_PREFIX = "L"  # 시드번호 맨 앞 글자. 콘텐츠마다 다르다.

# (이름, 확률 가중치, 능력치 배율, 추가 옵션 수, 별)
RARITIES = [
    ("일반", 60, 1.0, 0, "★"),
    ("고급", 25, 1.2, 1, "★★"),
    ("희귀", 10, 1.5, 2, "★★★"),
    ("영웅",  4, 1.9, 3, "★★★★"),
    ("전설",  1, 2.5, 4, "★★★★★"),
]
PREFIXES = [
    ["낡은", "녹슨", "평범한", "삐걱대는", "누군가 쓰던"],
    ["튼튼한", "잘 손질된", "묵직한", "반짝이는"],
    ["불타는", "얼어붙은", "번개 깃든", "바람을 탄"],
    ["속삭이는", "굶주린", "달빛에 젖은", "피를 기억하는"],
    ["태초의", "별을 삼킨", "신이 잃어버린", "이름을 잃은"],
]
MATERIALS = [
    ["나무", "구리", "무쇠"],
    ["강철", "은"],
    ["미스릴", "흑요석"],
    ["용뼈", "운석"],
    ["별빛", "심연"],
]
# 종류: (이름, 분류, 아이콘, 주 능력치 이름 또는 None)
BASES = [
    ("장검", "한손 무기", "sword", "공격력"),
    ("전투도끼", "양손 무기", "axe", "공격력"),
    ("장궁", "원거리 무기", "bow", "공격력"),
    ("지팡이", "마법 무기", "staff", "마력"),
    ("방패", "방어구", "shield", "방어력"),
    ("흉갑", "방어구", "armor", "방어력"),
    ("반지", "장신구", "ring", None),
]
POTIONS = [("체력 물약", "HP 회복"), ("마나 물약", "MP 회복"), ("수상한 물약", "효과")]
OPTIONS = [
    ("힘", "+{}", 1), ("민첩", "+{}", 1), ("지능", "+{}", 1), ("체력", "+{}", 1), ("행운", "+{}", 1),
    ("치명타 확률", "+{}%", 0.6), ("이동 속도", "+{}%", 0.6), ("화염 저항", "+{}%", 2),
    ("골드 획득", "+{}%", 2), ("흡혈", "{}%", 0.4),
]
UNIQUE_EFFECTS = [
    "하루 한 번, 주사위 하나를 다시 굴린다.",
    "전투의 첫 공격은 반드시 명중한다.",
    "쓰러질 때 한 번, HP 1로 버틴다.",
    "상점 물건을 10% 싸게 산다.",
    "어둠 속에서 은은하게 빛난다. 횃불이 필요 없다.",
    "함정을 밟기 직전에 미세하게 떨린다.",
]
CURSES = [
    "벗으려면 GM의 허락이 필요하다.",
    "밤마다 주인의 간식을 하나 먹는다.",
    "거짓말을 하면 딸꾹질이 난다.",
]
FLAVORS = [
    "대장장이가 술김에 만든 걸작.",
    "전 주인의 행방은 묻지 마시오.",
    "고블린 세 마리가 이걸 두고 싸웠다.",
    "환불 불가. 저주 포함 여부 미확인.",
    "안쪽에 '엄마가'라고 새겨져 있다.",
    "밤이 되면 희미하게 콧노래를 부른다.",
    "드래곤의 이쑤시개였다는 소문이 있다.",
    "감정사가 세 번 확인하고 한숨을 쉬었다.",
    "상자 안에는 이것과 먼지뿐이었다.",
    "주사위 신이 당신을 지켜보고 있다.",
]

# 16x16 도트 아이콘. '#' = 검정
ICONS = {
    "sword": """
..............##
.............###
............###.
...........###..
..........###...
.........###....
........###.....
.##....###......
.###..###.......
..######........
...####.........
...#####........
..###.###.......
.###...##.......
###.............
##..............""",
    "axe": """
................
....###..##.....
...#####.##.....
..#########.....
..#########.....
..#########.....
...#####.##.....
....###..##.....
.........##.....
.........##.....
.........##.....
.........##.....
.........##.....
.........##.....
.........##.....
................""",
    "bow": """
......####......
....##...#......
...#.....#......
..#......#......
.#.......#......
.#.......#......
#........#..#...
#..###########..
#........#..#...
#........#......
.#.......#......
.#.......#......
..#......#......
...#.....#......
....##...#......
......####......""",
    "staff": """
.....####.......
....#....#......
...#..##..#.....
...#.####.#.....
...#..##..#.....
....#....#......
.....####.......
......##........
......##........
......##........
......##........
......##........
......##........
......##........
......##........
......##........""",
    "shield": """
.##############.
.##############.
.######..######.
.######..######.
.##..........##.
.##..........##.
.######..######.
.######..######.
..#####..#####..
..#####..#####..
...##########...
....########....
.....######.....
......####......
.......##.......
................""",
    "armor": """
................
..###......###..
.#####....#####.
.######..######.
.##############.
..############..
...##########...
...##########...
...####..####...
...##########...
...##########...
...####..####...
...##########...
...##########...
....########....
................""",
    "ring": """
................
.......##.......
......####......
.....######.....
......####......
....########....
...###....###...
..###......###..
..##........##..
..##........##..
..##........##..
..###......###..
...###....###...
....########....
.....######.....
................""",
    "potion": """
................
.....######.....
.....######.....
......####......
......#..#......
......#..#......
.....#....#.....
....#......#....
...#........#...
..#..........#..
..############..
..############..
..############..
...##########...
....########....
................""",
}


def icon_image(name, scale=8):
    rows = ICONS[name].strip().splitlines()
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), name
    im = Image.new("1", (16, 16), 1)
    im.putdata([0 if ch == "#" else 1 for r in rows for ch in r])
    im = im.resize((16 * scale, 16 * scale), Image.NEAREST)
    row = Image.new("1", (PAPER_W, im.height + 16), 1)
    row.paste(im, ((PAPER_W - im.width) // 2, 8))
    return row


def roll(seed, level=None):
    """아이템 하나를 만들어 dict로 돌려준다. 같은 seed와 level이면 같은 아이템."""
    rng = random.Random(f"{seed}/{level}")
    level = level or rng.randint(1, 30)
    tier = rng.choices(range(5), weights=[r[1] for r in RARITIES])[0]
    rarity, _, mult, n_opts, stars = RARITIES[tier]
    power = (level * 2 + 5) * mult
    item = {"level": level, "rarity": rarity, "stars": stars, "tier": tier,
            "stats": [], "unique": None, "curse": None}

    if rng.random() < 0.15:  # 물약
        name, effect = rng.choice(POTIONS)
        item.update(name=f"{PREFIXES[tier][rng.randrange(len(PREFIXES[tier]))]} {name}",
                    kind="소모품", icon="potion")
        amount = "마셔 봐야 안다" if effect == "효과" else str(round(power * 4 / 10) * 10)
        item["stats"] = [(effect, amount), ("사용 횟수", f"{rng.randint(1, 3)}회")]
        price = power * 3
    else:
        base, kind, icon, main = rng.choice(BASES)
        item.update(name=f"{rng.choice(PREFIXES[tier])} {rng.choice(MATERIALS[tier])} {base}",
                    kind=kind, icon=icon)
        if main == "공격력":
            lo = round(power * rng.uniform(0.8, 1.0))
            item["stats"].append((main, f"{lo}~{lo + round(power * 0.3) + 1}"))
        elif main:
            item["stats"].append((main, f"+{round(power * rng.uniform(0.6, 0.9))}"))
        else:
            n_opts += 1  # 반지는 주 능력치 대신 옵션 하나 더
        for label, fmt, weight in rng.sample(OPTIONS, n_opts):
            value = max(1, round(power * weight * rng.uniform(0.15, 0.3)))
            item["stats"].append((label, fmt.format(value)))
        if tier >= 3:
            item["unique"] = rng.choice(UNIQUE_EFFECTS)
        if rng.random() < 0.08:
            item["curse"] = rng.choice(CURSES)
        price = power * 10 * mult
    item["price"] = max(5, round(price * rng.uniform(0.8, 1.2) / 5) * 5)
    item["flavor"] = rng.choice(FLAVORS)
    return item


def build_sheet(item, number):
    top = render([
        "^ @36b 전리품 감정서",
        f"^ > 모험가 길드 감정소 · Seed No. {number}",
        "---",
    ])
    body = [
        f"^ [[[ {item['stars']} {item['rarity']} ]]]",
        f"^ @36b {item['name']}",
        f"^ > {item['kind']} · 요구 레벨 {item['level']}",
        "---",
    ]
    body += [f"{label} || {value}" for label, value in item["stats"]]
    if item["unique"]:
        body += ["", "[[고유 효과]]", item["unique"]]
    if item["curse"]:
        body += ["", "[[저주]]", item["curse"]]
    body += [
        "---",
        f"> \"{item['flavor']}\"",
        f"**감정가 || {item['price']:,} G**",
        "---",
        "^ > 감정 수수료는 이미 떼었습니다.",
    ]
    return stack(top, icon_image(item["icon"]), render(body))


def draw_one(args, seed):
    item = roll(seed, args.level)
    seed_no = SEED_PREFIX + seed
    sheet = build_sheet(item, seed_no)
    print(f"No. {seed_no}: [{item['rarity']}] {item['name']} -> " + output(sheet, "fortune/loot", args, seed_no))


def main():
    ap = argparse.ArgumentParser(description="TRPG 전리품 감정서를 영수증 프린터로 인쇄")
    ap.add_argument("--level", type=int, help="아이템 레벨 (기본: 1~30 무작위)")
    ap.add_argument("--seed", help="다시 뽑을 아이템의 시드번호 (예: L482913)")
    ap.add_argument("--loop", action="store_true", help="Enter를 누를 때마다 한 장씩 뽑기")
    add_output_args(ap)
    args = ap.parse_args()

    new_seed = lambda: str(random.randrange(100000, 1000000))
    seed = None
    if args.seed:
        seed = strip_seed(args.seed, SEED_PREFIX, ap, "L482913")
        if not (seed.isdigit() and len(seed) == 6):
            ap.error("시드번호는 L 뒤에 숫자 여섯 자리입니다 (예: L482913)")
    draw_one(args, seed or new_seed())
    while args.loop:
        try:
            if input("Enter = 한 장 더, q = 종료 > ").strip().lower() == "q":
                break
        except EOFError:
            break
        draw_one(args, new_seed())


if __name__ == "__main__":
    main()
