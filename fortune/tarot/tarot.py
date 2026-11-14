"""오늘의 타로: 메이저 아르카나 한 장을 도트 카드 그림과 함께 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python fortune/tarot/tarot.py                 # 한 장 뽑기
    python fortune/tarot/tarot.py --loop          # Enter를 누를 때마다 한 장
    python fortune/tarot/tarot.py --seed T482913   # 같은 시드번호의 결과 다시 뽑기
    python fortune/tarot/tarot.py --card 16       # 카드 지정 (0~21), --reversed 로 역방향
    python fortune/tarot/tarot.py --preview       # 인쇄 없이 이미지만 저장

카드 그림은 71x95 도트로 직접 그린 것이고, '카드 효과'는 게임 Balatro의 타로 효과를 일상 버전으로 바꾼 농담이다.
이미지는 fortune/tarot/output/ 에 저장된다.
"""
import argparse
import datetime
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import FONT_DIR, PAPER_W, add_output_args, strip_seed, output, raw, render, stack

SEED_PREFIX = "T"  # 시드번호 맨 앞 글자. 콘텐츠마다 다르다.
CARD_W, CARD_H, CARD_SCALE = 71, 95, 4     # 카드 원본 크기(도트)와 인쇄 배율
REVERSED_CHANCE = 0.3
K, D, G, L, W = 0, 64, 128, 192, 255       # 검정, 진한 망점, 중간 망점, 옅은 망점, 흰색

ROMAN = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
         "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]

# (영문, 한글, 키워드, 정방향 운세, 역방향 운세, 카드 효과)
CARDS = [
    ("FOOL", "바보", "시작 · 모험",
     "일단 저지르고 보는 날입니다. 준비가 덜 됐어도 첫발을 떼면 길이 생깁니다.",
     "신나서 달리기 전에 신발 끈부터 확인하세요. 오늘의 덤벙은 내일의 흑역사입니다.",
     "가장 최근에 한 일을 한 번 더 하게 됩니다. (바보짓은 제외)"),
    ("MAGICIAN", "마법사", "재주 · 실행",
     "가진 재료는 이미 충분합니다. 오늘 손댄 일은 생각보다 잘 풀립니다.",
     "잔재주로 넘기려다 들키는 날. 정석대로 가는 편이 빠릅니다.",
     "오늘 손댄 일 두 가지에 운이 붙습니다. 다섯 번에 한 번은 기대 이상으로 풀립니다."),
    ("PRIESTESS", "고위 여사제", "직감 · 비밀",
     "말보다 눈치가 정확한 날입니다. 떠오른 첫 느낌을 믿어 보세요.",
     "혼자만 알던 것이 새어 나갈 수 있습니다. 비밀번호는 좀 바꾸세요.",
     "오늘 밤 하늘을 올려다보세요. 별 두 개만 찾아도 고민이 작아 보입니다."),
    ("EMPRESS", "여제", "풍요 · 다정",
     "먹을 복이 있습니다. 누가 간식을 나눠 주면 사양하지 마세요.",
     "베풀다가 내 몫이 사라지는 날. 오늘은 나부터 챙기세요.",
     "칭찬 한 마디에 기분이 네 배로 좋아집니다. 먼저 건네면 두 번까지 돌아옵니다."),
    ("EMPEROR", "황제", "책임 · 리더십",
     "오늘은 당신이 정하면 그게 규칙입니다. 대신 책임도 당신 것.",
     "고집과 리더십은 한 끗 차이. 한 번쯤은 남의 말을 들어 보세요.",
     "타로를 2장 더 뽑고 싶어집니다. (종이는 아껴 주세요)"),
    ("HIEROPHANT", "교황", "배움 · 조언",
     "모르는 건 물어보면 되는 날. 좋은 선생님이 가까이에 있습니다.",
     "잔소리로 들리던 말이 사실은 정답일 수 있습니다.",
     "오늘 새로 배운 것 두 가지는 오래 기억에 남습니다. 적어 두면 더 오래갑니다."),
    ("LOVERS", "연인", "인연 · 선택",
     "마음이 맞는 사람을 만납니다. 같이 하면 두 배로 재밌는 날.",
     "둘 중 하나를 골라야 하는 순간이 옵니다. 미루면 둘 다 놓칩니다.",
     "오늘은 어느 무리에 껴도 잘 어울립니다. 낯선 자리에 한 번 끼어 보세요."),
    ("CHARIOT", "전차", "돌파 · 승리",
     "밀어붙이면 되는 날입니다. 망설이던 일에 시동을 거세요.",
     "속도는 충분한데 방향이 문제입니다. 지도부터 다시 보세요.",
     "자리를 지키기만 해도 한몫하는 날입니다. 든든하다는 말을 듣게 됩니다."),
    ("JUSTICE", "정의", "균형 · 공정",
     "한 만큼 돌아오는 날. 미뤄 둔 정산이 깔끔하게 끝납니다.",
     "저울이 기울어 보인다면 내 쪽 추부터 확인하세요.",
     "오늘 들인 노력은 두 배로 돌아옵니다. 다만 유리처럼 깨지기 쉬우니 컵과 약속은 살살 다루세요."),
    ("HERMIT", "은둔자", "혼자 · 성찰",
     "혼자 있는 시간이 약이 됩니다. 조용한 곳에서 답이 떠오릅니다.",
     "너무 오래 숨어 있었습니다. 오늘은 누구에게든 먼저 연락해 보세요.",
     "지갑 속 돈이 두 배가 된 기분이 듭니다. (최대 20,000원, 기분만)"),
    ("WHEEL", "운명의 수레바퀴", "변화 · 운",
     "판이 바뀝니다. 흐름에 올라타면 뜻밖의 행운이 따라옵니다.",
     "운이 아직 돌고 있습니다. 큰 결정은 내일로 미루는 게 좋습니다.",
     "네 번에 한 번 꼴로 평범한 하루가 반짝이는 하루로 바뀝니다."),
    ("STRENGTH", "힘", "용기 · 인내",
     "힘으로 누르지 않아도 이기는 날. 부드럽게 말하면 통합니다.",
     "버티는 데도 한계가 있습니다. 오늘은 일찍 자는 게 용기입니다.",
     "오늘의 나는 어제보다 딱 한 단계 셉니다. 계단 한 층쯤은 거뜬합니다."),
    ("HANGED MAN", "매달린 사람", "멈춤 · 관점",
     "거꾸로 보면 답이 보입니다. 서두르지 말고 한 박자 쉬어 가세요.",
     "기다림이 길어지고 있습니다. 이제 내려올 때가 됐습니다.",
     "할 일 목록에서 두 가지를 지워도 아무 일도 일어나지 않습니다."),
    ("DEATH", "죽음", "끝 · 새 출발",
     "무서운 카드가 아닙니다. 하나가 끝나야 다음 판이 시작됩니다.",
     "이미 끝난 일을 붙잡고 있습니다. 놓아야 손이 빕니다.",
     "나쁜 습관 하나가 옆에 있던 좋은 습관으로 바뀝니다."),
    ("TEMPERANCE", "절제", "조화 · 중용",
     "섞으면 더 좋아지는 날. 반반 메뉴가 정답입니다.",
     "과하면 탈이 납니다. '한 입만 더'는 오늘 금지.",
     "주머니와 서랍을 뒤져 보세요. 잊고 있던 것이 나옵니다. (많아야 50,000원어치)"),
    ("DEVIL", "악마", "유혹 · 집착",
     "달콤한 유혹이 옵니다. '딱 한 번만'이라는 말을 조심하세요.",
     "끊기 힘들던 것에서 풀려납니다. 폰을 내려놓을 기회입니다.",
     "오늘 끝까지 손에서 놓지 않은 것이 3,000원어치 값을 합니다. (휴대폰은 제외)"),
    ("TOWER", "탑", "급변 · 깨달음",
     "예상 못 한 일이 터집니다. 무너진 자리에는 더 튼튼한 걸 지을 수 있습니다.",
     "아슬아슬하게 피해 갑니다. 저장 버튼은 자주 누르세요.",
     "돌처럼 묵직해지는 날. 누가 흔들어도 제자리를 지키면 믿음을 얻습니다."),
    ("STAR", "별", "희망 · 회복",
     "바라던 일에 초록불이 켜집니다. 소원은 구체적으로 빌어 보세요.",
     "기대가 조금 빗나가도 실망은 금물. 별은 낮에도 떠 있습니다.",
     "반짝이는 것 세 가지에 운이 붙습니다. 동전, 창문, 잘 닦은 안경을 눈여겨보세요."),
    ("MOON", "달", "불안 · 상상",
     "생각이 많아지는 밤입니다. 걱정의 절반은 상상이니 일단 주무세요.",
     "안개가 걷힙니다. 헷갈리던 일의 진짜 모습이 보입니다.",
     "세잎클로버 세 개면 네잎 하나만큼의 행운입니다. 풀밭 근처를 지나가 보세요."),
    ("SUN", "태양", "성공 · 활력",
     "뭘 해도 되는 날입니다. 밖으로 나가서 볕을 쬐세요.",
     "좋은 날인데 살짝 흐립니다. 자랑은 반만 하세요.",
     "오늘 건네는 인사 세 번에는 진심이 실립니다. 하트 이모티콘을 아끼지 마세요."),
    ("JUDGEMENT", "심판", "부름 · 결과",
     "미뤄 둔 결과가 나옵니다. 노력한 만큼은 확실히 돌아옵니다.",
     "다시 볼 기회가 옵니다. 지난번에 틀린 문제를 떠올려 보세요.",
     "뜻밖의 웃긴 친구가 나타납니다. 자리가 없으면 못 만나니 옆자리를 비워 두세요."),
    ("WORLD", "세계", "완성 · 여행",
     "한 바퀴를 다 돌았습니다. 마무리가 깔끔하게 떨어지는 날.",
     "99%에서 멈춰 있습니다. 마지막 한 조각을 찾으세요.",
     "오늘 판 삽질 세 번은 전부 밑거름이 됩니다. 헛수고는 없습니다."),
]
NO_ARTICLE = {"JUSTICE", "STRENGTH", "DEATH", "TEMPERANCE", "JUDGEMENT"}  # 이름 앞에 THE가 안 붙는 카드
CARD_SUITS = {17: "♦", 18: "♣", 19: "♥", 21: "♠"}  # 행운의 무늬를 정해 주는 카드
# (족보, 칩, 배수, 나올 가중치)
HANDS = [("하이 카드", 5, 1, 20), ("원 페어", 10, 2, 30), ("투 페어", 20, 2, 18), ("트리플", 30, 3, 12),
         ("스트레이트", 30, 4, 8), ("플러시", 35, 4, 6), ("풀 하우스", 40, 4, 4), ("포 카드", 60, 7, 1.5),
         ("스트레이트 플러시", 100, 8, 0.5)]


# ---------------------------------------------------------------- 도트 그림 도구

def star(d, cx, cy, r_out, r_in, points, fill=None, outline=None, turn=-90):
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(turn + i * 180 / points)
        pts.append((round(cx + r * math.cos(a)), round(cy + r * math.sin(a))))
    d.polygon(pts, fill=fill, outline=outline)


def sparkle(d, x, y, r=2, fill=K):
    d.line([x - r, y, x + r, y], fill=fill)
    d.line([x, y - r, x, y + r], fill=fill)


def heart(d, cx, cy, s, fill=K):
    d.ellipse([cx - s, cy - s, cx, cy], fill=fill)
    d.ellipse([cx, cy - s, cx + s, cy], fill=fill)
    d.polygon([(cx - s, cy - s // 2 + 1), (cx + s, cy - s // 2 + 1), (cx, cy + s)], fill=fill)


def waves(d, y, fill=K):
    for x in range(8, 62, 6):
        d.line([x, y, x + 2, y - 2, x + 4, y], fill=fill)


def mirror(pts):
    return [(70 - x, y) for x, y in pts]


# ---------------------------------------------------------------- 카드별 그림 (그림 영역: x 7~63, y 18~78)

def art_fool(d):
    d.ellipse([10, 21, 20, 31], fill=W, outline=K)                       # 해
    for a in range(0, 360, 45):
        d.line([15 + 7 * math.cos(math.radians(a)), 26 + 7 * math.sin(math.radians(a)),
                15 + 9 * math.cos(math.radians(a)), 26 + 9 * math.sin(math.radians(a))], fill=K)
    d.polygon([(6, 78), (6, 64), (36, 64), (44, 72), (47, 78)], fill=G, outline=K)   # 절벽
    d.line([18, 46, 44, 30], fill=K)                                     # 막대
    d.ellipse([40, 22, 49, 31], fill=D, outline=K)                       # 보따리
    d.polygon([(30, 40), (23, 56), (37, 56)], fill=L, outline=K)         # 몸
    d.line([27, 56, 25, 64], fill=K, width=2)
    d.line([33, 56, 38, 63], fill=K, width=2)
    d.ellipse([26, 31, 34, 39], fill=W, outline=K)                       # 머리
    d.polygon([(25, 33), (35, 33), (33, 25), (30, 30), (27, 25)], fill=K)  # 광대 모자
    d.rectangle([50, 70, 58, 74], fill=W, outline=K)                     # 강아지
    d.rectangle([56, 66, 61, 70], fill=W, outline=K)
    d.point([(59, 68)], fill=K)
    d.line([50, 70, 48, 67], fill=K)
    d.line([51, 74, 51, 77], fill=K)
    d.line([57, 74, 57, 77], fill=K)


def art_magician(d):
    d.ellipse([25, 19, 34, 26], outline=K)
    d.ellipse([34, 19, 43, 26], outline=K)
    d.polygon([(34, 38), (23, 64), (45, 64)], fill=D, outline=K)
    d.line([39, 42, 50, 32], fill=K, width=2)
    d.line([50, 34, 50, 20], fill=K)
    sparkle(d, 50, 19, 3)
    d.line([29, 42, 20, 52], fill=K, width=2)
    d.ellipse([29, 28, 39, 38], fill=W, outline=K)
    d.rectangle([9, 64, 61, 67], fill=K)
    d.rectangle([12, 67, 14, 78], fill=K)
    d.rectangle([56, 67, 58, 78], fill=K)
    d.polygon([(12, 56), (20, 56), (18, 63), (14, 63)], fill=W, outline=K)   # 컵
    d.ellipse([49, 57, 57, 63], fill=W, outline=K)                           # 동전
    sparkle(d, 53, 60, 1)


def art_priestess(d):
    d.rectangle([20, 24, 50, 62], fill=L)
    d.rectangle([9, 23, 19, 78], fill=K)
    d.rectangle([51, 23, 61, 78], fill=W, outline=K)
    d.rectangle([7, 20, 21, 23], fill=K)
    d.rectangle([49, 20, 63, 23], fill=K)
    d.polygon([(35, 38), (21, 78), (49, 78)], fill=G, outline=K)
    d.line([35, 46, 35, 58], fill=K)
    d.line([31, 50, 39, 50], fill=K)
    d.rectangle([28, 62, 42, 67], fill=W, outline=K)
    d.line([29, 28, 27, 21], fill=K)
    d.line([41, 28, 43, 21], fill=K)
    d.ellipse([32, 20, 38, 26], fill=W, outline=K)
    d.ellipse([30, 27, 40, 37], fill=W, outline=K)


def art_empress(d):
    for x, y in ((25, 23), (35, 20), (45, 23)):
        star(d, x, y, 3, 1, 4, fill=K)
    d.polygon([(35, 36), (17, 76), (53, 76)], fill=L, outline=K)
    for x, y in ((30, 56), (40, 56), (35, 64), (26, 70), (44, 70)):
        sparkle(d, x, y, 1)
    d.ellipse([30, 26, 40, 36], fill=W, outline=K)
    d.line([52, 40, 57, 76], fill=K)
    d.ellipse([48, 33, 56, 41], fill=K)
    heart(d, 17, 58, 6)
    d.ellipse([15, 54, 17, 56], fill=W)
    for x in range(9, 62, 5):
        d.line([x, 78, x, 75], fill=K)


def art_emperor(d):
    d.rectangle([18, 24, 52, 78], fill=D, outline=K)
    d.ellipse([12, 18, 22, 28], fill=W, outline=K)
    d.ellipse([48, 18, 58, 28], fill=W, outline=K)
    d.ellipse([15, 21, 19, 25], outline=K)
    d.ellipse([51, 21, 55, 25], outline=K)
    d.polygon([(25, 44), (45, 44), (49, 78), (21, 78)], fill=W, outline=K)
    d.line([35, 50, 35, 78], fill=K)
    d.ellipse([30, 30, 40, 40], fill=W, outline=K)
    d.polygon([(29, 31), (29, 23), (32, 27), (35, 22), (38, 27), (41, 23), (41, 31)], fill=K)
    d.polygon([(31, 38), (39, 38), (35, 47)], fill=W, outline=K)
    d.line([55, 46, 55, 76], fill=K, width=2)
    d.ellipse([52, 36, 59, 43], outline=K)
    d.line([51, 48, 60, 48], fill=K, width=2)
    d.ellipse([9, 52, 19, 62], fill=K)
    d.line([14, 47, 14, 52], fill=K)
    d.line([12, 49, 16, 49], fill=K)


def art_hierophant(d):
    d.line([35, 19, 35, 56], fill=K, width=3)
    for half, y in ((6, 25), (9, 32), (12, 39)):
        d.line([35 - half, y, 35 + half, y], fill=K, width=3)
    for flip in (False, True):
        pts = lambda p: mirror(p) if flip else p
        d.line(pts([(18, 76), (44, 54)]), fill=K, width=2)
        (x1, y1), (x2, y2) = pts([(43, 46), (53, 56)])
        d.ellipse([min(x1, x2), y1, max(x1, x2), y2], outline=K, width=2)
        d.line(pts([(22, 73), (26, 77)]), fill=K, width=2)
        d.line(pts([(26, 69), (30, 73)]), fill=K, width=2)
    sparkle(d, 12, 24, 2)
    sparkle(d, 58, 24, 2)


def art_lovers(d):
    for a in range(0, 360, 30):
        d.line([35 + 9 * math.cos(math.radians(a)), 27 + 9 * math.sin(math.radians(a)),
                35 + 12 * math.cos(math.radians(a)), 27 + 12 * math.sin(math.radians(a))], fill=K)
    d.ellipse([28, 20, 42, 34], fill=W, outline=K)
    heart(d, 35, 47, 6)
    d.line([25, 64, 45, 64], fill=K, width=2)
    d.polygon([(18, 56), (10, 78), (26, 78)], fill=G, outline=K)
    d.polygon([(52, 56), (44, 78), (60, 78)], fill=W, outline=K)
    d.ellipse([14, 48, 22, 56], fill=W, outline=K)
    d.ellipse([48, 48, 56, 56], fill=W, outline=K)


def art_chariot(d):
    d.rectangle([17, 20, 53, 27], fill=K)
    for x in (22, 29, 36, 43, 49):
        d.point([(x, 23), (x - 1, 23), (x, 24), (x, 22), (x + 1, 23)], fill=W)
    d.line([19, 27, 19, 46], fill=K)
    d.line([51, 27, 51, 46], fill=K)
    d.rectangle([29, 37, 41, 46], fill=G, outline=K)
    d.ellipse([30, 28, 40, 38], fill=W, outline=K)
    d.rectangle([15, 46, 55, 60], fill=W, outline=K, width=2)
    d.ellipse([31, 49, 39, 57], fill=K)
    d.polygon([(31, 53), (22, 50), (26, 55)], fill=K)
    d.polygon([(39, 53), (48, 50), (44, 55)], fill=K)
    for cx in (12, 58):
        d.ellipse([cx - 6, 54, cx + 6, 66], fill=W, outline=K, width=2)
        d.line([cx - 5, 60, cx + 5, 60], fill=K)
        d.line([cx, 55, cx, 65], fill=K)
    d.polygon([(19, 78), (26, 66), (33, 78)], fill=K)
    d.ellipse([22, 61, 30, 69], fill=K)
    d.polygon([(37, 78), (44, 66), (51, 78)], fill=W, outline=K)
    d.ellipse([40, 61, 48, 69], fill=W, outline=K)


def art_justice(d):
    d.rectangle([34, 19, 36, 62], fill=W, outline=K)
    d.polygon([(34, 19), (36, 19), (35, 16)], fill=K)
    d.rectangle([28, 62, 42, 64], fill=K)
    d.rectangle([34, 64, 36, 72], fill=K)
    d.ellipse([32, 72, 38, 78], fill=K)
    d.line([13, 30, 57, 30], fill=K, width=2)
    for cx in (16, 54):
        d.line([cx, 30, cx - 7, 48], fill=K)
        d.line([cx, 30, cx + 7, 48], fill=K)
        d.chord([cx - 9, 40, cx + 9, 56], 0, 180, fill=G, outline=K)
    d.ellipse([32, 27, 38, 33], fill=K)


def art_hermit(d):
    for x, y in ((12, 22), (26, 19), (46, 24), (60, 20), (56, 60)):
        d.point([(x, y)], fill=K)
    d.line([7, 78, 63, 78], fill=K)
    d.line([15, 24, 15, 78], fill=K, width=2)
    d.polygon([(28, 30), (18, 78), (44, 78), (40, 32)], fill=D, outline=K)
    d.ellipse([25, 20, 41, 38], fill=D, outline=K)
    d.ellipse([29, 26, 38, 35], fill=W)
    d.polygon([(30, 34), (37, 34), (34, 44)], fill=W, outline=K)
    d.line([40, 44, 50, 40], fill=K, width=2)
    d.rectangle([50, 36, 54, 39], fill=K)
    d.rectangle([47, 39, 57, 51], fill=W, outline=K)
    star(d, 52, 45, 4, 1, 4, fill=K)
    for x1, y1, x2, y2 in ((52, 30, 52, 33), (61, 45, 63, 45), (59, 36, 61, 34), (43, 34, 45, 36), (59, 54, 61, 56)):
        d.line([x1, y1, x2, y2], fill=K)


def art_wheel(d):
    for x, y in ((11, 22), (59, 22), (11, 75), (59, 75)):
        star(d, x, y, 3, 1, 4, fill=K)
    d.ellipse([11, 25, 59, 73], fill=G, outline=K, width=2)
    d.ellipse([17, 31, 53, 67], fill=W, outline=K)
    for a in range(0, 360, 45):
        d.line([35, 49, 35 + 18 * math.cos(math.radians(a)), 49 + 18 * math.sin(math.radians(a))], fill=K)
    for a in range(0, 360, 90):
        x, y = 35 + 21 * math.cos(math.radians(a)), 49 + 21 * math.sin(math.radians(a))
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=W, outline=K)
    d.ellipse([29, 43, 41, 55], fill=K)
    d.ellipse([33, 47, 37, 51], fill=W)
    d.polygon([(31, 18), (39, 18), (35, 27)], fill=K)


def art_strength(d):
    d.ellipse([25, 18, 35, 25], outline=K)
    d.ellipse([35, 18, 45, 25], outline=K)
    star(d, 35, 53, 25, 19, 14, fill=G, outline=K)
    d.ellipse([20, 34, 30, 44], fill=W, outline=K)
    d.ellipse([40, 34, 50, 44], fill=W, outline=K)
    d.ellipse([22, 38, 48, 68], fill=W, outline=K)
    d.rectangle([28, 48, 30, 51], fill=K)
    d.rectangle([40, 48, 42, 51], fill=K)
    d.polygon([(31, 55), (39, 55), (35, 60)], fill=K)
    d.line([35, 60, 35, 63], fill=K)
    d.line([35, 63, 30, 65], fill=K)
    d.line([35, 63, 40, 65], fill=K)
    for x in (26, 44):
        d.point([(x, 58), (x, 60), (x + (2 if x > 35 else -2), 59)], fill=K)


def art_hanged(d):
    d.rectangle([11, 20, 59, 23], fill=K)
    d.rectangle([11, 20, 14, 78], fill=K)
    d.rectangle([56, 20, 59, 78], fill=K)
    d.line([35, 23, 35, 28], fill=K)                                      # 밧줄
    d.line([35, 28, 35, 44], fill=K, width=2)                             # 곧은 다리
    d.line([36, 44, 44, 38, 37, 32], fill=K, width=2)                     # 굽힌 다리
    d.polygon([(29, 44), (41, 44), (39, 58), (31, 58)], fill=G, outline=K)  # 몸
    d.line([30, 46, 24, 52, 31, 56], fill=K)                              # 뒷짐 진 팔
    d.line([40, 46, 46, 52, 39, 56], fill=K)
    for a in range(0, 360, 30):                                           # 후광
        d.line([35 + 8 * math.cos(math.radians(a)), 64 + 8 * math.sin(math.radians(a)),
                35 + 11 * math.cos(math.radians(a)), 64 + 11 * math.sin(math.radians(a))], fill=K)
    d.ellipse([29, 58, 41, 70], fill=W, outline=K)                        # 머리
    d.point([(32, 65), (38, 65)], fill=K)
    d.line([33, 61, 37, 61], fill=K)


def art_death(d):
    d.line([14, 78, 50, 22], fill=K, width=2)
    d.polygon([(50, 22), (58, 22), (63, 30), (62, 40), (58, 30), (50, 26)], fill=K)
    d.ellipse([18, 30, 52, 62], fill=W, outline=K, width=2)
    d.rectangle([26, 56, 44, 70], fill=W, outline=K)
    for x in (30, 35, 40):
        d.line([x, 62, x, 70], fill=K)
    d.line([26, 62, 44, 62], fill=K)
    d.ellipse([23, 40, 33, 51], fill=K)
    d.ellipse([37, 40, 47, 51], fill=K)
    d.polygon([(35, 50), (32, 57), (38, 57)], fill=K)


def art_temperance(d):
    d.polygon([(22, 18), (48, 18), (35, 26)], fill=W, outline=K)
    d.ellipse([33, 19, 37, 23], fill=K)
    d.line([27, 34, 34, 38, 40, 46, 44, 56, 46, 62], fill=D, width=3)
    for x, y in ((38, 36), (46, 46), (30, 44), (50, 54)):
        d.point([(x, y), (x, y + 1)], fill=K)
    d.polygon([(10, 26), (28, 26), (25, 42), (13, 42)], fill=W, outline=K)
    d.line([12, 30, 26, 30], fill=K)
    d.rectangle([18, 42, 20, 47], fill=K)
    d.rectangle([14, 47, 24, 49], fill=K)
    d.polygon([(37, 60), (57, 60), (54, 72), (40, 72)], fill=W, outline=K)
    d.rectangle([39, 62, 55, 64], fill=G)
    d.rectangle([46, 72, 48, 75], fill=K)
    d.rectangle([42, 75, 52, 77], fill=K)
    waves(d, 78)


def art_devil(d):
    star(d, 35, 23, 6, 2, 5, outline=K, turn=90)
    wing = [(27, 46), (8, 34), (12, 46), (7, 52), (14, 54), (11, 62), (27, 58)]
    d.polygon(wing, fill=D, outline=K)
    d.polygon(mirror(wing), fill=D, outline=K)
    d.polygon([(26, 40), (21, 26), (33, 36)], fill=K)
    d.polygon(mirror([(26, 40), (21, 26), (33, 36)]), fill=K)
    d.ellipse([23, 34, 47, 62], fill=W, outline=K, width=2)
    d.polygon([(27, 44), (33, 47), (27, 49)], fill=K)
    d.polygon(mirror([(27, 44), (33, 47), (27, 49)]), fill=K)
    d.chord([28, 46, 42, 58], 0, 180, fill=K)
    for x in (32, 35, 38):
        d.line([x, 52, x, 54], fill=W)
    d.polygon([(32, 62), (38, 62), (35, 70)], fill=K)
    for x in range(13, 56, 7):
        d.ellipse([x, 72, x + 5, 77], outline=K)


def art_tower(d):
    d.rectangle([5, 17, 65, 79], fill=L)
    d.polygon([(25, 36), (45, 36), (48, 79), (22, 79)], fill=W, outline=K)
    d.rectangle([23, 30, 47, 36], fill=W, outline=K)
    for x in (23, 30, 37):
        d.rectangle([x, 25, x + 4, 30], fill=W, outline=K)
    d.polygon([(9, 30), (9, 23), (12, 26), (15, 22), (18, 26), (21, 23), (21, 30)], fill=K)  # 날아간 왕관
    d.rectangle([33, 42, 37, 49], fill=K)
    d.rectangle([28, 58, 31, 64], fill=K)
    d.rectangle([39, 58, 42, 64], fill=K)
    d.chord([31, 66, 39, 82], 180, 360, fill=K)
    d.rectangle([31, 74, 39, 79], fill=K)
    for x1, y1, x2 in ((25, 52, 30), (36, 54, 44), (27, 68, 31), (40, 70, 46)):
        d.line([x1, y1, x2, y1], fill=K)
    d.polygon([(63, 18), (50, 32), (55, 32), (45, 46), (61, 28), (56, 28)], fill=W, outline=K)  # 번개
    for x, y in ((12, 48), (58, 54)):
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=W, outline=K)
        d.line([x, y + 2, x, y + 8], fill=K)
        d.line([x - 3, y + 4, x + 3, y + 6], fill=K)
    for x, y in ((14, 26), (18, 38), (10, 66), (54, 40), (60, 68), (52, 66)):
        d.point([(x, y), (x, y + 1)], fill=K)


def art_star(d):
    star(d, 35, 40, 17, 6, 8, fill=W, outline=K)
    star(d, 35, 40, 7, 3, 4, fill=K)
    for x, y in ((13, 24), (57, 24), (11, 46), (59, 46), (20, 60), (50, 60), (35, 64)):
        star(d, x, y, 4, 1, 4, fill=K)
    waves(d, 72)
    waves(d, 77)


def art_moon(d):
    d.ellipse([18, 19, 52, 53], fill=W, outline=K, width=2)
    d.ellipse([26, 21, 54, 49], fill=L, outline=K)
    d.point([(24, 34), (24, 35)], fill=K)
    d.line([22, 41, 25, 43], fill=K)
    for x, y in ((16, 58), (24, 56), (32, 60), (40, 56), (48, 60), (54, 57)):
        d.line([x, y, x, y + 2], fill=K)
    d.polygon([(30, 78), (40, 78), (36, 64), (34, 64)], fill=G, outline=K)
    for x in (8, 53):
        d.rectangle([x, 62, x + 9, 78], fill=W, outline=K)
        d.rectangle([x, 58, x + 2, 62], fill=K)
        d.rectangle([x + 7, 58, x + 9, 62], fill=K)
        d.rectangle([x + 3, 67, x + 6, 72], fill=K)
    waves(d, 78)


def art_sun(d):
    star(d, 35, 44, 25, 15, 12, fill=G, outline=K)
    d.ellipse([21, 30, 49, 58], fill=W, outline=K, width=2)
    d.rectangle([28, 39, 30, 43], fill=K)
    d.rectangle([40, 39, 42, 43], fill=K)
    d.arc([28, 40, 42, 53], 20, 160, fill=K, width=2)
    d.point([(26, 47), (44, 47)], fill=K)
    for x in (12, 58):
        d.line([x, 78, x, 71], fill=K)
        star(d, x, 68, 4, 2, 8, fill=K)
        d.ellipse([x - 1, 67, x + 1, 69], fill=W)


def art_judgement(d):
    d.polygon([(20, 30), (23, 26), (50, 42), (58, 38), (58, 58), (48, 50)], fill=W, outline=K)  # 나팔
    d.line([50, 42, 48, 50], fill=K)
    d.rectangle([27, 40, 41, 56], fill=W, outline=K)                      # 깃발
    d.line([34, 43, 34, 53], fill=K, width=2)
    d.line([29, 48, 39, 48], fill=K, width=2)
    for box in ([7, 22, 19, 32], [12, 18, 26, 30], [22, 20, 34, 30]):     # 구름
        d.ellipse(box, fill=W, outline=K)
    d.rectangle([11, 25, 30, 29], fill=W)
    d.line([10, 32, 30, 32], fill=K)
    for x1, y1, x2, y2 in ((61, 40, 63, 38), (61, 48, 64, 48), (61, 56, 63, 58)):
        d.line([x1, y1, x2, y2], fill=K)
    for x in (15, 35, 55):
        d.rectangle([x - 5, 72, x + 5, 78], fill=G, outline=K)
        d.line([x - 3, 72, x - 6, 63], fill=K)
        d.line([x + 3, 72, x + 6, 63], fill=K)
        d.ellipse([x - 3, 62, x + 3, 68], fill=W, outline=K)


def art_world(d):
    for x, y in ((11, 23), (59, 23), (11, 74), (59, 74)):
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=K)
        d.point([(x, y)], fill=W)
    for a in range(0, 360, 18):
        x, y = 35 + 21 * math.cos(math.radians(a)), 48 + 27 * math.sin(math.radians(a))
        d.ellipse([x - 3, y - 2, x + 3, y + 2], fill=D, outline=K)
    d.ellipse([22, 35, 48, 61], fill=W, outline=K, width=2)
    d.ellipse([29, 35, 41, 61], outline=K)
    d.line([35, 35, 35, 61], fill=K)
    d.line([22, 48, 48, 48], fill=K)
    d.arc([22, 28, 48, 46], 20, 160, fill=K)
    d.arc([22, 50, 48, 68], 200, 340, fill=K)


ART = [art_fool, art_magician, art_priestess, art_empress, art_emperor, art_hierophant, art_lovers,
       art_chariot, art_justice, art_hermit, art_wheel, art_strength, art_hanged, art_death,
       art_temperance, art_devil, art_tower, art_star, art_moon, art_sun, art_judgement, art_world]


# ---------------------------------------------------------------- 카드 조립

def dither(gray):
    """5단계 회색을 도트 무늬로 바꾼다 (흰색=1, 검정=0)."""
    out = Image.new("1", gray.size, 1)
    src, dst = gray.load(), out.load()
    for y in range(gray.height):
        for x in range(gray.width):
            v = src[x, y]
            if v < 32:
                black = True
            elif v < 96:
                black = not (x % 2 == 0 and y % 2 == 0)
            elif v < 160:
                black = (x + y) % 2 == 0
            elif v < 224:
                black = x % 2 == 0 and y % 2 == 0
            else:
                black = False
            dst[x, y] = 0 if black else 1
    return out


def card_image(index, reversed_=False, scale=CARD_SCALE):
    """카드 한 장 -> 1비트 이미지 (원본 71x95를 정수배 확대)."""
    im = Image.new("L", (CARD_W, CARD_H), W)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=5, fill=W, outline=K, width=2)
    ART[index](d)
    d.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=5, outline=K, width=2)
    d.rectangle([2, 2, CARD_W - 3, CARD_H - 3], outline=W)
    d.rectangle([4, 4, CARD_W - 5, CARD_H - 5], outline=K)
    d.rectangle([5, 5, CARD_W - 6, 16], fill=K)
    d.rectangle([5, 80, CARD_W - 6, CARD_H - 6], fill=K)
    numeral = ImageFont.truetype(str(FONT_DIR / "Galmuri9.ttf"), 10)
    label = ImageFont.truetype(str(FONT_DIR / "Galmuri7.ttf"), 8)
    d.text((CARD_W // 2 + 1, 11), ROMAN[index], font=numeral, fill=W, anchor="mm")
    d.text((CARD_W // 2 + 1, 85), CARDS[index][0], font=label, fill=W, anchor="mm")
    for x in (8, CARD_W - 9):  # 띠 양 끝 장식
        d.point([(x, 10), (x, 11), (x, 84), (x, 85)], fill=W)
    out = dither(im).resize((CARD_W * scale, CARD_H * scale), Image.NEAREST)
    return out.rotate(180) if reversed_ else out


def centered(im, pad=10):
    row = Image.new("1", (PAPER_W, im.height + pad * 2), 1)
    row.paste(im, ((PAPER_W - im.width) // 2, pad))
    return row


def draw_card(seed, index=None, reversed_=None):
    """한 번 뽑기 -> 결과 dict. 같은 seed면 같은 결과."""
    rng = random.Random(f"fortune/tarot/{seed}")
    picked = rng.randrange(len(CARDS))
    flipped = rng.random() < REVERSED_CHANCE
    hand = rng.choices(HANDS, weights=[h[3] for h in HANDS])[0]
    result = {
        "index": picked if index is None else index,
        "reversed": flipped if reversed_ is None else reversed_,
        "hand": hand,
        "suit": rng.choice("♠♥♦♣"),
        "wheel_hit": rng.random() < 0.25,
    }
    result["suit"] = CARD_SUITS.get(result["index"], result["suit"])
    return result


def build_sheet(result, seed):
    i = result["index"]
    en, ko, keywords, upright, reverse, effect = CARDS[i]
    name, chips, mult, _ = result["hand"]
    top = render([
        "^ @36b 오늘의 타로",
        f"^ > Seed No. {seed} · {datetime.date.today().isoformat()}",
        "---",
    ])
    lines = [
        f"^ @48b {ko}",
        f"^ > {ROMAN[i]} · {'' if en in NO_ARTICLE else 'THE '}{en} · {'역방향' if result['reversed'] else '정방향'}",
        f"^ [[ {keywords} ]]",
        "---",
        raw("body", reverse if result["reversed"] else upright),
        "",
        "[[카드 효과]]",
        raw("body", effect),
    ]
    if en == "WHEEL":
        lines.append("**판정 || " + ("반짝! 오늘이 그날입니다**" if result["wheel_hit"] else "꽝! 평소대로 가세요**"))
    lines += [
        "---",
        f"오늘의 족보 || {name}",
        f"점수 || {chips} x {mult} = {chips * mult:,}",
        raw("body", "행운의 무늬", right=result["suit"]),
        "---",
        "^ > 재미로 보는 운세입니다. 카드를 뒤집어도 결과는 같습니다.",
    ]
    return stack(top, centered(card_image(i, result["reversed"])), render(lines))


def draw_one(args, seed):
    if args.card is not None and not 0 <= args.card < len(CARDS):
        sys.exit(f"카드 번호는 0~{len(CARDS) - 1} 사이여야 합니다.")
    result = draw_card(seed, args.card, True if args.reversed else None)
    ko = CARDS[result["index"]][1]
    way = "역방향" if result["reversed"] else "정방향"
    seed_no = SEED_PREFIX + seed
    print(f"No. {seed_no}: {ROMAN[result['index']]} {ko} ({way}) -> "
          + output(build_sheet(result, seed_no), "fortune/tarot", args, f"{seed_no}_{CARDS[result['index']][0].replace(' ', '')}"))


def main():
    ap = argparse.ArgumentParser(description="오늘의 타로를 영수증 프린터로 인쇄")
    ap.add_argument("--seed", help="다시 뽑을 시드번호 (예: T482913)")
    ap.add_argument("--card", type=int, help="카드 지정 (0~21)")
    ap.add_argument("--reversed", action="store_true", help="역방향으로 고정")
    ap.add_argument("--loop", action="store_true", help="Enter를 누를 때마다 한 장씩 뽑기")
    add_output_args(ap)
    args = ap.parse_args()

    new_seed = lambda: str(random.randrange(100000, 1000000))
    seed = None
    if args.seed:
        seed = strip_seed(args.seed, SEED_PREFIX, ap, "T482913")
        if not (seed.isdigit() and len(seed) == 6):
            ap.error("시드번호는 T 뒤에 숫자 여섯 자리입니다 (예: T482913)")
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
