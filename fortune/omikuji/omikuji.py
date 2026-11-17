"""오미쿠지(御神籤): 신사에서 뽑는 제비 운세를 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python fortune/omikuji/omikuji.py                  # 한 장 뽑기
    python fortune/omikuji/omikuji.py --loop           # Enter를 누를 때마다 한 장
    python fortune/omikuji/omikuji.py --seed O482913   # 같은 시드번호의 결과 다시 뽑기
    python fortune/omikuji/omikuji.py --grade 0        # 등급 지정 (0 대길 ~ 8 대흉)
    python fortune/omikuji/omikuji.py --preview        # 인쇄 없이 이미지만 저장

등급 글자는 한자와 한글을 함께 찍는다. 한자는 Galmuri14를 8배로 키워 굵게 그린다.
이미지는 fortune/omikuji/output/ 에 저장된다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import FONT_DIR, PAPER_W, add_output_args, output, raw, render, stack, strip_seed, wrap

SEED_PREFIX = "O"  # 시드번호 맨 앞 글자. 콘텐츠마다 다르다.
BIG_SCALE = 8      # 등급 한자 배율 (Galmuri14 15px x 8 = 120도트)
FRAME_X = 14       # 운세 상자 바깥 테두리의 좌우 여백
INNER_W = PAPER_W - FRAME_X * 2 - 44   # 상자 안 글이 차지할 수 있는 폭 (도트)

# (한자, 한글, 뜻, 운 게이지 0~10, 구간, 뽑힐 비중, 로마자, 한마디들)
GRADES = [
    ("大吉", "대길", "크게 길하다", 10, "good", 12, "daikichi", [
        "오늘은 자판기도 음료를 두 개 떨어뜨려 줄 기세입니다. 뭘 해도 됩니다. 진짜로.",
        "우주가 당신 편입니다. 단, 우주는 숙제를 대신 해 주지 않습니다.",
        "신호등이 전부 초록불로 바뀌는 날. 이 기세로 미뤄 둔 일 하나만 끝내 보세요.",
    ]),
    ("吉", "길", "길하다", 8, "good", 18, "kichi", [
        "평범하게 좋은 날. 평범하게 좋은 게 제일 어렵다는 거, 아시죠?",
        "점심 메뉴 고르기에 실패하지 않는 날입니다. 그거면 충분합니다.",
        "누가 칭찬을 하면 '아닙니다' 말고 '감사합니다'라고 받으세요. 운이 두 배가 됩니다.",
    ]),
    ("中吉", "중길", "제법 길하다", 7, "good", 15, "chukichi", [
        "버스를 놓쳐도 다음 버스가 바로 옵니다. 딱 그런 운입니다.",
        "행운이 70% 충전되었습니다. 나머지 30%는 간식으로 채우세요.",
        "반에서 중간 가는 운이 아니라, 맛있는 거 중에 중간 가는 운입니다. 충분히 맛있습니다.",
    ]),
    ("小吉", "소길", "조금 길하다", 6, "mid", 15, "shokichi", [
        "엘리베이터가 딱 내 층에 서 있는 정도의 행운이 찾아옵니다.",
        "작은 행운이 주머니 속 동전처럼 짤랑거립니다. 줍는 건 본인 몫입니다.",
        "과자 봉지를 뜯었는데 질소보다 과자가 많은 날입니다.",
    ]),
    ("半吉", "반길", "반쯤 길하다", 5, "mid", 9, "hankichi", [
        "와이파이가 한 칸. 연결은 됩니다. 연결은.",
        "반은 성공, 반은 경험. 컵에 물이 반이나 남았다고 생각하세요.",
        "붕어빵으로 치면 꼬리까지는 팥이 안 든 날. 머리부터 드세요.",
    ]),
    ("末吉", "말길", "나중에 길하다", 4, "mid", 12, "suekichi", [
        "지금은 로딩 중입니다. 끝에 가서 웃는 운이니 새로고침은 하지 마세요.",
        "늦게 피는 꽃이 오래갑니다. 일단 물부터 한 잔 드세요.",
        "라면은 3분을 기다려야 맛있습니다. 당신의 운은 지금 2분 30초.",
    ]),
    ("末小吉", "말소길", "나중에 조금 길하다", 3, "mid", 7, "sueshokichi", [
        "아주 나중에, 아주 조금 좋아집니다. 기대치를 낮추면 대박처럼 느껴집니다.",
        "행운이 택배로 오고 있습니다. 배송 조회는 '집화 처리 중'.",
        "고생 끝에 낙이 옵니다. 고생이 조금 길 뿐입니다.",
    ]),
    ("凶", "흉", "흉하다", 2, "bad", 9, "kyo", [
        "우산을 챙기세요. 비가 안 와도 챙기세요. 마음의 우산입니다.",
        "바닥을 찍었으니 이제 올라갈 일만 남았습니다. 축하합니다(?)",
        "오늘은 레벨업보다 체력 회복의 날. 일찍 자면 내일 아침에 운이 리셋됩니다.",
    ]),
    ("大凶", "대흉", "크게 흉하다", 1, "bad", 3, "daikyo", [
        "대흉은 대길보다 뽑기 어렵습니다. 쓸데없는 데서 운이 좋으시네요.",
        "축하합니다! 희귀 등급 획득! 오늘 불운을 여기서 다 썼으니 남은 하루는 무사합니다.",
        "신발 끈, 지퍼, 휴대폰 배터리를 한 번씩 확인하세요. 그러면 대흉도 별거 아닙니다.",
    ]),
]

# (한자, 한글, {구간: 문장들})
TOPICS = [
    ("願望", "소원", {
        "good": ["이루어집니다. 소원을 크게 비세요. 작게 빌면 작게 옵니다.",
                 "말하는 대로 됩니다. 단, 오늘은 '배고파'라고 말하지 마세요."],
        "mid": ["천천히 이루어집니다. 재촉하면 소원도 삐집니다.",
                "반쯤 이루어집니다. 나머지 반은 본인 손으로."],
        "bad": ["오늘은 접수만 됩니다. 처리는 다음 영업일에.",
                "소원보다 낮잠이 먼저입니다."],
    }),
    ("待人", "기다리는 사람", {
        "good": ["옵니다. 그것도 간식을 들고 옵니다.",
                 "생각보다 빨리 옵니다. 머리는 미리 감아 두세요."],
        "mid": ["늦게 옵니다. 그래도 옵니다.",
                "연락이 옵니다. 답장은 너무 빨리 하지 마세요."],
        "bad": ["안 옵니다. 대신 택배가 옵니다.",
                "기다리지 말고 먼저 연락하세요. 그게 빠릅니다."],
    }),
    ("失物", "잃어버린 물건", {
        "good": ["나옵니다. 아까 본 그 주머니를 한 번 더 보세요.",
                 "찾습니다. 의외로 손에 들고 있을지도 모릅니다."],
        "mid": ["늦게 나옵니다. 소파 밑을 수상하게 여기세요.",
                "새로 사자마자 나옵니다. 세상의 법칙입니다."],
        "bad": ["나오기 어렵습니다. 그 물건도 여행이 하고 싶었나 봅니다.",
                "찾는 대신 이름표를 붙이는 습관을 얻습니다."],
    }),
    ("学問", "공부", {
        "good": ["찍은 게 맞습니다. 그래도 공부는 하세요.",
                 "집중력이 오릅니다. 휴대폰을 뒤집어 두면 두 배."],
        "mid": ["보통입니다. 형광펜만 칠하고 끝내지 마세요.",
                "외운 것의 절반이 기억납니다. 나머지 절반은 내일 다시."],
        "bad": ["책을 베개로 쓰면 지식이 스며든다는 설은 거짓입니다.",
                "오늘은 복습만. 새 진도는 머리가 거부합니다."],
    }),
    ("恋愛", "연애", {
        "good": ["눈이 마주치면 먼저 웃으세요. 오늘은 그게 통합니다.",
                 "인연이 가까이 있습니다. 거울 말고 옆을 보세요."],
        "mid": ["서두르지 마세요. 라면도 불면 맛이 없습니다.",
                "썸은 탑니다. 썸만 탑니다."],
        "bad": ["오늘은 나 자신과 연애하는 날. 맛있는 거 사 주세요.",
                "보낸 메시지에 오타가 있습니다. 보내기 전에 다시 읽으세요."],
    }),
    ("金運", "금전운", {
        "good": ["주머니에서 잊고 있던 돈이 나옵니다.",
                 "할인 쿠폰 운이 폭발합니다. 장바구니를 확인하세요."],
        "mid": ["들어온 만큼 나갑니다. 계산은 정확한 편입니다.",
                "1+1 상품이 당신을 부릅니다. 하나만 필요해도요."],
        "bad": ["지갑을 꼭 닫으세요. 특히 편의점 앞에서.",
                "오늘의 쇼핑은 장바구니에만 담으세요. 결제는 내일의 나에게."],
    }),
]

LUCKY_ITEMS = ["따뜻한 캔커피", "짝이 맞는 양말", "편의점 삼각김밥", "충전 100% 보조배터리", "볼펜 뚜껑",
               "귤 한 개", "고무줄", "지금 들고 있는 이 영수증", "빨간 펜", "주머니 속 동전", "포스트잇",
               "줄 이어폰", "손수건", "사탕 한 알", "새 지우개"]
DIRECTIONS = [("東", "동"), ("西", "서"), ("南", "남"), ("北", "북"),
              ("東南", "동남"), ("東北", "동북"), ("西南", "서남"), ("西北", "서북")]
FOOTERS = {
    "good": "좋은 운은 지갑에 넣어 가지고 다니세요. 효과에는 개인차가 있습니다.",
    "mid": "가지고 다니다가 좋은 일이 생기면, 그때 이 종이를 보고 한 번 웃으세요.",
    "bad": "흉이 나왔다면 접어서 근처 나뭇가지에 묶어 두세요. 나무가 없으면 우산꽂이도 됩니다. "
           "나쁜 운은 여기 두고 가는 겁니다.",
}

KANJI_DIGITS = "〇一二三四五六七八九"


def kanji_number(n):
    """1~100 -> 一, 十, 二十七, 百 같은 한자 숫자."""
    if n == 100:
        return "百"
    tens, ones = divmod(n, 10)
    return (("" if tens == 1 else KANJI_DIGITS[tens]) + "十" if tens else "") + (KANJI_DIGITS[ones] if ones else "")


# ---------------------------------------------------------------- 그림

def big_text(text, scale=BIG_SCALE, bold=True):
    """Galmuri14로 원래 크기에 그린 뒤 정수배 확대. bold면 한 픽셀 옆으로 겹쳐 굵게 한다."""
    font = ImageFont.truetype(str(FONT_DIR / "Galmuri14.ttf"), 15)
    ascent, descent = font.getmetrics()
    w = round(font.getlength(text)) + (1 if bold else 0)
    im = Image.new("1", (w, ascent + descent), 1)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((0, ascent), text, font=font, fill=0, anchor="ls")
    if bold:
        im = ImageChops.logical_and(im, ImageChops.offset(im, 1, 0))
    bbox = ImageChops.invert(im.convert("L")).getbbox()  # 위아래 빈칸을 잘라 낸다
    if bbox:
        im = im.crop((0, bbox[1], w, bbox[3]))
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def shide(d, x, y, fill=0):
    """신사 금줄에 매다는 번개 모양 종이(紙垂)."""
    d.line([x, y, x, y + 1], fill=fill)
    d.polygon([(x - 2, y + 2), (x + 3, y + 2), (x + 3, y + 4), (x + 1, y + 6), (x + 4, y + 6),
               (x + 4, y + 8), (x + 1, y + 11), (x - 1, y + 11), (x + 1, y + 8), (x - 2, y + 8),
               (x - 2, y + 6), (x, y + 4), (x - 2, y + 4)], fill=1, outline=fill)


def tied_slips(d, x0, x1, y):
    """줄에 묶어 둔 오미쿠지들."""
    d.line([x0, y, x1, y], fill=0)
    for x in range(x0 + 3, x1 - 2, 7):
        d.rectangle([x, y - 2, x + 2, y + 2], fill=0)        # 매듭
        d.line([x - 1, y - 4, x + 1, y - 2], fill=0)
        d.line([x + 3, y + 2, x + 4, y + 5], fill=0)


def sparkle(d, x, y, r=2):
    d.line([x - r, y, x + r, y], fill=0)
    d.line([x, y - r, x, y + r], fill=0)


def torii_header():
    """도리이 + 금줄 + 묶인 제비들. 192x52 도트로 그려 3배 확대한다."""
    w, h, s = PAPER_W // 3, 52, 3
    im = Image.new("1", (w, h), 1)
    d = ImageDraw.Draw(im)
    cx = w // 2
    # 가사기(맨 위 지붕보): 양 끝이 살짝 들린다
    d.polygon([(cx - 48, 4), (cx - 40, 7), (cx + 40, 7), (cx + 48, 4), (cx + 46, 10), (cx - 46, 10)], fill=0)
    d.rectangle([cx - 42, 11, cx + 42, 13], fill=0)                 # 시마키
    d.rectangle([cx - 44, 21, cx + 44, 24], fill=0)                 # 누키
    d.rectangle([cx - 7, 13, cx + 7, 21], fill=1, outline=0)        # 현판
    d.rectangle([cx - 5, 15, cx + 5, 19], fill=1, outline=0)
    d.point([(cx - 2, 17), (cx, 17), (cx + 2, 17)], fill=0)
    for px in (cx - 31, cx + 31):                                   # 기둥 (아래로 갈수록 살짝 넓다)
        d.polygon([(px - 2, 11), (px + 2, 11), (px + 3, 45), (px - 3, 45)], fill=0)
        d.rectangle([px - 4, 44, px + 4, 47], fill=0)               # 받침
    # 금줄과 종이
    for x in range(cx - 27, cx + 28, 2):
        d.point([(x, 29 + (1 if (x // 2) % 2 else 0))], fill=0)
    d.line([cx - 27, 30, cx - 27, 29], fill=0)
    for x in (cx - 16, cx, cx + 16):
        shide(d, x, 30)
    d.line([4, 48, w - 5, 48], fill=0)                              # 땅
    for x in range(8, w - 8, 9):
        d.point([(x, 50)], fill=0)
    # 양옆: 묶인 제비, 반짝이
    tied_slips(d, 6, cx - 40, 34)
    tied_slips(d, cx + 40, w - 7, 34)
    for x, y in ((14, 14), (28, 6), (44, 18), (w - 15, 14), (w - 29, 6), (w - 45, 18)):
        sparkle(d, x, y)
    return im.resize((w * s, h * s), Image.NEAREST)


def gauge(level, cells=10):
    """운 게이지: 칸 10개 중 level칸을 채운다."""
    cw, ch, gap, s = 9, 7, 2, 3
    w = cells * (cw + gap) - gap
    im = Image.new("1", (w + 2, ch + 2), 1)
    d = ImageDraw.Draw(im)
    for i in range(cells):
        x = 1 + i * (cw + gap)
        if i < level:
            d.rectangle([x, 1, x + cw - 1, ch], fill=0)
        else:
            d.rectangle([x, 1, x + cw - 1, ch], outline=0)
            d.point([(x + cw // 2, ch // 2 + 1)], fill=0)
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def centered(im, pad=8):
    row = Image.new("1", (PAPER_W, im.height + pad * 2), 1)
    row.paste(im, ((PAPER_W - im.width) // 2, pad))
    return row


def framed(inner, pad=22, edge=10):
    """운세 상자: 두 줄 테두리에 네 귀퉁이 마름모 장식. edge는 장식이 잘리지 않게 둔 위아래 여백."""
    h = inner.height + pad * 2 + edge * 2
    im = Image.new("1", (PAPER_W, h), 1)
    im.paste(inner, (0, pad + edge))
    d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = FRAME_X, PAPER_W - FRAME_X - 1, edge, h - 1 - edge
    d.rectangle([x0, y0, x1, y1], outline=0, width=4)
    d.rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=0, width=2)
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):           # 귀퉁이 마름모
        d.polygon([(x, y - 9), (x + 9, y), (x, y + 9), (x - 9, y)], fill=1, outline=0)
        d.polygon([(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)], fill=0)
    return im


def centered_wrapped(text, style="body", scale=2):
    return [raw(style, ln, align="center") for ln in wrap(text, style, INNER_W // scale)]


# ---------------------------------------------------------------- 뽑기와 조립

def draw_omikuji(seed, grade=None):
    """한 번 뽑기 -> 결과 dict. 같은 seed면 같은 결과."""
    rng = random.Random(f"fortune/omikuji/{seed}")
    picked = rng.choices(range(len(GRADES)), weights=[g[5] for g in GRADES])[0]
    result = {
        "grade": picked if grade is None else grade,
        "stick": rng.randint(1, 100),
        "line": rng.random(),
        "topics": [rng.random() for _ in TOPICS],
        "item": rng.choice(LUCKY_ITEMS),
        "direction": rng.choice(DIRECTIONS),
        "number": rng.randint(1, 99),
    }
    return result


def pick(options, r):
    return options[int(r * len(options))]


def build_sheet(result, seed):
    kanji, ko, meaning, level, tier, _, _, lines = GRADES[result["grade"]]
    stick = result["stick"]
    top = stack(
        torii_header(),
        render([
            "^ @60 御 神 籤",
            "^ > おみくじ · 오 미 쿠 지",
            "",
            f"^ @30 第{kanji_number(stick)}番 · 제{stick}번",
        ]),
    )
    inner = stack(
        centered(big_text(kanji), pad=4),
        render([
            f"^ @48b {' '.join(ko)}",
            f"^ > {meaning}",
        ]),
        centered(gauge(level), pad=4),
        render(["^ > 運 운 게이지", ""] + centered_wrapped(pick(lines, result["line"]))),
    )
    body = [
        "",
        "^ ## 運勢 細目 · 항목별 운세",
        "---",
    ]
    for (tk, tko, texts), r in zip(TOPICS, result["topics"]):
        body += [f"@30 ◆ {tk} {tko}", raw("body", pick(texts[tier], r)), ""]
    dk, dko = result["direction"]
    body += [
        "---",
        f"幸運の品 행운의 물건 || {result['item']}",
        f"方角 행운의 방향 || {dk} {dko}",
        f"数字 행운의 숫자 || {result['number']}",
        "---",
        raw("small", FOOTERS[tier]),
        "",
        f"^ > No. {seed} · {datetime.date.today().isoformat()} · 재미로 보는 운세입니다.",
    ]
    return stack(top, render([""]), framed(inner), render(body))


def draw_one(args, seed):
    if args.grade is not None and not 0 <= args.grade < len(GRADES):
        sys.exit(f"등급 번호는 0~{len(GRADES) - 1} 사이여야 합니다.")
    result = draw_omikuji(seed, args.grade)
    kanji, ko, _, _, _, _, roman, _ = GRADES[result["grade"]]
    seed_no = SEED_PREFIX + seed
    print(f"No. {seed_no}: 第{result['stick']}番 {kanji} {ko} -> "
          + output(build_sheet(result, seed_no), "fortune/omikuji", args, f"{seed_no}_{roman}"))


def main():
    ap = argparse.ArgumentParser(description="오미쿠지를 영수증 프린터로 인쇄")
    ap.add_argument("--seed", help="다시 뽑을 시드번호 (예: O482913)")
    ap.add_argument("--grade", type=int, help="등급 지정 (0 대길 ~ 8 대흉)")
    ap.add_argument("--loop", action="store_true", help="Enter를 누를 때마다 한 장씩 뽑기")
    add_output_args(ap)
    args = ap.parse_args()

    new_seed = lambda: str(random.randrange(100000, 1000000))
    seed = None
    if args.seed:
        seed = strip_seed(args.seed, SEED_PREFIX, ap, "O482913")
        if not (seed.isdigit() and len(seed) == 6):
            ap.error("시드번호는 O 뒤에 숫자 여섯 자리입니다 (예: O482913)")
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
