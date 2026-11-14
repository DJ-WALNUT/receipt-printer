"""나름로또: 실제 로또 용지처럼 생긴 나름청소년활동센터 체험용 복권을 인쇄한다.

사용법 (프로젝트 폴더에서):
    python fortune/lotto/lotto.py                        # 자동 5게임 한 장
    python fortune/lotto/lotto.py --games 3              # 한 장에 3게임
    python fortune/lotto/lotto.py --sheets 5             # 다섯 장 연속 인쇄
    python fortune/lotto/lotto.py --manual "3 11 17 24 38 42"   # 수동 한 게임 + 나머지 자동
    python fortune/lotto/lotto.py --prize "문화상품권"    # 상품 칸에 찍을 글자 (없으면 손으로 적는 밑줄)
    python fortune/lotto/lotto.py --draw                 # 이번 회차 추첨 결과 용지
    python fortune/lotto/lotto.py --preview              # 인쇄 없이 이미지만 저장

이미지는 fortune/lotto/output/ 에 저장된다. 숫자 범위와 개수는 바로 아래 설정에서 바꾼다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import CONTENT_W, PAPER_W, STYLES, add_output_args, output, raw, render, size_style, stack, text_width

# ------------------------------------------------------------------ 설정 (여기만 고치면 된다)
NUMBER_MIN = 1      # 가장 작은 숫자
NUMBER_MAX = 45     # 가장 큰 숫자
PICKS = 6           # 한 게임에 뽑는 숫자 개수
GAMES = 5           # 한 장에 들어가는 기본 게임 수
PRIZE_TEXT = ""     # 상품 칸에 찍을 글자. 비워 두면 손으로 적을 수 있게 밑줄만 찍는다

# ------------------------------------------------------------------ 나름청소년활동센터
CENTER = "나름청소년활동센터"
FOUNDATION = "광명시청소년재단"
ADDRESS = "광명시 철산로 56, 6층"
MISSION = "청소년의 상상력에 날개를 달아주다."
VALUES = "성장 · 가치 · 공동체"
OPENED = datetime.date(2013, 2, 1)  # 개관일. 회차는 개관한 주를 1회로 센다
AGE_TEXT = "9~24세 청소년 누구나"
# 게임 줄마다 하나씩 붙는 센터 공간 이름 (A~E가 대관 공간 다섯 곳과 짝이 맞는다)
SPACES = ["창의키움터", "탐구개발터", "생각나눔터", "활력충전터", "상상이룸터", "행복가득터"]

WEEKDAYS = "월화수목금토일"


def check_settings():
    if NUMBER_MAX - NUMBER_MIN + 1 < PICKS:
        sys.exit(f"설정 오류: {NUMBER_MIN}~{NUMBER_MAX} 범위에서는 숫자 {PICKS}개를 겹치지 않게 뽑을 수 없습니다.")


def pick(rng):
    return sorted(rng.sample(range(NUMBER_MIN, NUMBER_MAX + 1), PICKS))


def fmt(numbers):
    width = len(str(NUMBER_MAX))
    return " ".join(str(n).zfill(width) for n in numbers)


def parse_manual(text):
    try:
        numbers = sorted(int(x) for x in text.replace(",", " ").split())
    except ValueError:
        sys.exit(f"수동 번호 '{text}'에 숫자가 아닌 것이 있습니다.")
    if len(numbers) != PICKS or len(set(numbers)) != PICKS:
        sys.exit(f"수동 번호는 서로 다른 숫자 {PICKS}개여야 합니다: '{text}'")
    if numbers[0] < NUMBER_MIN or numbers[-1] > NUMBER_MAX:
        sys.exit(f"수동 번호는 {NUMBER_MIN}~{NUMBER_MAX} 사이여야 합니다: '{text}'")
    return numbers


def game_title():
    return f"나름 Lotto {PICKS}/{NUMBER_MAX}"


def round_number(day):
    return (day - OPENED).days // 7 + 1


def draw_day(day):
    """실제 로또처럼 그 주 토요일 (오늘이 토요일이면 오늘)."""
    return day + datetime.timedelta(days=(5 - day.weekday()) % 7)


def date_text(day):
    return f"{day:%Y/%m/%d} ({WEEKDAYS[day.weekday()]})"


def biggest_style(text, heights, bold=False, room=CONTENT_W):
    """room 폭에 들어가는 가장 큰 글자 크기를 고른다. 숫자 범위를 키워도 줄이 넘치지 않게."""
    for h in heights:
        style = size_style(h, bold)
        if text_width(text, style) * STYLES[style][2] <= room:
            return style
    return size_style(heights[-1], bold)


def barcode(rng):
    """장식용 바코드 (읽히지 않는 무작위 막대)."""
    im = Image.new("1", (PAPER_W, 72), 1)
    d = ImageDraw.Draw(im)
    x = 88
    while x < PAPER_W - 88:
        w = rng.choice([2, 2, 4, 6])
        d.rectangle([x, 6, x + w - 1, 65], fill=0)
        x += w + rng.choice([2, 2, 4])
    return im


def footer():
    return [
        "---",
        raw("body", MISSION, align="center"),
        f"^ > {VALUES}",
        f"^ > 판매점: {CENTER} ({ADDRESS})",
        f"^ > 구매 가능 연령: {AGE_TEXT}",
        "^ > 체험용 복권입니다. 실제 복권이 아닙니다.",
    ]


def prize_lines(prize):
    """상품 칸. 글자가 길면 크기를 줄이고, 그래도 넘치면 아래 줄로 내린다."""
    if not prize:
        return [raw("@36b", "상품", right="____________")]
    for style in ("@36b", "@24b"):
        name = size_style(int(style[1:-1]), True)
        room = CONTENT_W - (text_width("상품", name) + 2) * STYLES[name][2]
        if text_width(prize, name) * STYLES[name][2] <= room:
            return [raw(style, "상품", right=prize)]
    return [raw("@36b", "상품"), raw("bold", prize)]


def build_ticket(games, now, rng, prize=""):
    """games: [(종류, 숫자 목록)] -> (이미지, 일련번호)"""
    serial = " ".join(f"{rng.randrange(100000):05d}" for _ in range(6))
    label_room = 150  # "A 자 동" 자리
    number_style = biggest_style(fmt(games[0][1]), [36, 30, 24, 20], room=CONTENT_W - label_room)
    label_style = "@" + number_style[1:]

    top = [
        f"^ @48b {game_title()}",
        f"^ > {FOUNDATION} {CENTER}",
        "---",
        f"**제 {round_number(now.date())} 회**",
        f"발 행 일 || {date_text(now.date())} {now:%H:%M:%S}",
        f"추 첨 일 || {date_text(draw_day(now.date()))}",
        "지급기한 || 상상력에는 기한이 없음",
        f"^ > {serial}",
        "---",
    ]
    for i, (kind, numbers) in enumerate(games):
        letter = chr(ord("A") + i % 26)
        top.append(raw(label_style, f"{letter} {' '.join(kind)}", right=fmt(numbers)))
        top.append(f"> 　 {SPACES[i % len(SPACES)]}에서 고른 번호")
    bottom = ["---"] + prize_lines(prize)
    return stack(render(top + bottom), barcode(rng), render(footer())), serial.split()[0]


def build_draw(now, rng, prize=""):
    """추첨 결과 용지: 당첨번호 + 보너스 번호"""
    pool = list(range(NUMBER_MIN, NUMBER_MAX + 1))
    rng.shuffle(pool)
    winning = sorted(pool[:PICKS])
    bonus = pool[PICKS] if len(pool) > PICKS else None
    lines = [
        f"^ @36b {game_title()}",
        f"^ > {FOUNDATION} {CENTER}",
        "---",
        f"^ @36b 제 {round_number(now.date())} 회 추첨 결과",
        f"^ > 추첨 {date_text(now.date())} {now:%H:%M:%S}",
        "",
        "^ [[당첨번호]]",
        raw(biggest_style(fmt(winning), [48, 36, 24], bold=True), fmt(winning), align="center"),
    ]
    if bonus is not None:
        lines += ["", f"@36b 보너스 || {fmt([bonus])}"]
    if prize:
        lines += ["---"] + prize_lines(prize)
    return render(lines + footer())


def main():
    check_settings()
    ap = argparse.ArgumentParser(description="나름로또: 나름청소년활동센터 체험용 복권 인쇄")
    ap.add_argument("--games", type=int, default=GAMES, help=f"한 장에 넣을 게임 수 (기본 {GAMES})")
    ap.add_argument("--sheets", type=int, default=1, help="인쇄할 장 수 (기본 1)")
    ap.add_argument("--manual", action="append", default=[], metavar="번호",
                    help='수동 번호 한 게임, 예: "3 11 17 24 38 42" (여러 번 사용 가능, 나머지는 자동)')
    ap.add_argument("--prize", default=PRIZE_TEXT, metavar="상품",
                    help="상품 칸에 찍을 글자 (기본: 설정의 PRIZE_TEXT, 비어 있으면 밑줄)")
    ap.add_argument("--draw", action="store_true", help="복권 대신 추첨 결과 용지를 인쇄")
    add_output_args(ap)
    args = ap.parse_args()
    if args.games < 1 or args.sheets < 1:
        ap.error("게임 수와 장 수는 1 이상이어야 합니다.")
    manual = [parse_manual(m) for m in args.manual]
    if len(manual) > args.games:
        ap.error(f"수동 번호가 게임 수({args.games})보다 많습니다.")

    rng = random.SystemRandom()
    now = datetime.datetime.now()
    if args.draw:
        print(f"제 {round_number(now.date())} 회 추첨 결과 -> " + output(build_draw(now, rng, args.prize), "fortune/lotto", args, "draw"))
        return
    for _ in range(args.sheets):
        games = [("수동", m) for m in manual] + [("자동", pick(rng)) for _ in range(args.games - len(manual))]
        sheet, serial = build_ticket(games, now, rng, args.prize)
        print(f"{len(games)}게임 -> " + output(sheet, "fortune/lotto", args, serial))


if __name__ == "__main__":
    main()
