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
        "줄을 서면 내 앞에서 계산대가 하나 더 열립니다.",
        "머리가 한 번에 마음에 들게 마르는 날. 그 기세 그대로 나가세요.",
        "오늘의 당신은 버그 없는 업데이트입니다. 패치 노트: 모든 것이 좋아짐.",
        "가위바위보를 하면 이깁니다. 내기는 작게 하세요. 운은 아껴 쓰는 겁니다.",
        "오늘 뽑은 이 종이가 첫 번째 행운입니다. 두 번째부터는 세다가 잊어버릴 겁니다.",
    ]),
    ("吉", "길", "길하다", 8, "good", 18, "kichi", [
        "평범하게 좋은 날. 평범하게 좋은 게 제일 어렵다는 거, 아시죠?",
        "점심 메뉴 고르기에 실패하지 않는 날입니다. 그거면 충분합니다.",
        "누가 칭찬을 하면 '아닙니다' 말고 '감사합니다'라고 받으세요. 운이 두 배가 됩니다.",
        "양말이 한 번에 짝이 맞는 날. 사소하지만 그게 행운입니다.",
        "오늘 먹는 밥은 평소보다 한 숟갈 더 맛있습니다.",
        "계단 개수를 세면 딱 짝수로 끝납니다. 기분이 좋습니다. 이유는 없습니다.",
        "누군가 당신 얘기를 좋게 하고 있습니다. 귀가 간지러우면 그 탓입니다.",
        "좋은 소식이 도착합니다. 답장은 천천히 해도 됩니다. 좋은 소식은 안 도망갑니다.",
    ]),
    ("中吉", "중길", "제법 길하다", 7, "good", 15, "chukichi", [
        "버스를 놓쳐도 다음 버스가 바로 옵니다. 딱 그런 운입니다.",
        "행운이 70% 충전되었습니다. 나머지 30%는 간식으로 채우세요.",
        "반에서 중간 가는 운이 아니라, 맛있는 거 중에 중간 가는 운입니다. 충분히 맛있습니다.",
        "시험으로 치면 아는 문제가 하나 더 나오는 날입니다.",
        "우산을 안 가져왔는데 비가 그칩니다. 가져왔다면 쓸 일이 생깁니다. 어느 쪽이든 이득.",
        "좋은 일이 오는 중입니다. 지금 횡단보도 건너는 중.",
        "충전기가 손 닿는 곳에 꽂혀 있는 운입니다. 은근히 큽니다.",
        "웃을 일이 세 번 있습니다. 두 번은 남 때문이고 한 번은 내 실수 때문입니다.",
    ]),
    ("小吉", "소길", "조금 길하다", 6, "mid", 15, "shokichi", [
        "엘리베이터가 딱 내 층에 서 있는 정도의 행운이 찾아옵니다.",
        "작은 행운이 주머니 속 동전처럼 짤랑거립니다. 줍는 건 본인 몫입니다.",
        "과자 봉지를 뜯었는데 질소보다 과자가 많은 날입니다.",
        "작은 칭찬을 듣습니다. 크게 기뻐하면 두 배가 됩니다.",
        "한 정거장 일찍 내려 걸어도 기분 좋은 날씨입니다.",
        "오늘의 행운은 소확행 사이즈. 컵으로 치면 톨 사이즈.",
        "좋아하는 노래가 셔플로 나옵니다. 그 노래가 나오면 오늘 운을 다 쓴 겁니다.",
        "자판기 거스름돈 구멍을 확인해 보세요. 확인은 무료입니다.",
    ]),
    ("半吉", "반길", "반쯤 길하다", 5, "mid", 9, "hankichi", [
        "와이파이가 한 칸. 연결은 됩니다. 연결은.",
        "반은 성공, 반은 경험. 컵에 물이 반이나 남았다고 생각하세요.",
        "붕어빵으로 치면 꼬리까지는 팥이 안 든 날. 머리부터 드세요.",
        "택배가 옵니다. 상자는 큰데 내용물은 작습니다.",
        "밥은 맛있는데 국이 식었습니다. 그래도 밥은 맛있습니다.",
        "반만 하고 쉬어도 되는 날. 나머지 반은 내일의 나에게 맡기세요.",
        "웃긴 얘기를 하면 반만 웃습니다. 두 번 하면 다 웃을지도 모릅니다.",
        "배터리 50%. 하루를 버티기엔 충분합니다. 영상만 줄이세요.",
    ]),
    ("末吉", "말길", "나중에 길하다", 4, "mid", 12, "suekichi", [
        "지금은 로딩 중입니다. 끝에 가서 웃는 운이니 새로고침은 하지 마세요.",
        "늦게 피는 꽃이 오래갑니다. 일단 물부터 한 잔 드세요.",
        "라면은 3분을 기다려야 맛있습니다. 당신의 운은 지금 2분 30초.",
        "주인공은 원래 후반에 각성합니다. 지금은 1막입니다.",
        "오후부터 풀립니다. 오전은 그냥 커피 마시는 시간이라고 생각하세요.",
        "마지막 피자 한 조각은 당신 몫입니다. 처음 몇 조각은 양보하세요.",
        "엔딩 크레딧 뒤에 쿠키 영상이 있는 운입니다. 끝까지 앉아 있으세요.",
        "늦게 온 사람이 제일 좋은 자리를 얻는 날도 있습니다. 오늘이 그날일지도.",
    ]),
    ("末小吉", "말소길", "나중에 조금 길하다", 3, "mid", 7, "sueshokichi", [
        "아주 나중에, 아주 조금 좋아집니다. 기대치를 낮추면 대박처럼 느껴집니다.",
        "행운이 택배로 오고 있습니다. 배송 조회는 '집화 처리 중'.",
        "고생 끝에 낙이 옵니다. 고생이 조금 길 뿐입니다.",
        "로또 숫자 하나는 맞습니다. 하나요.",
        "운이 들어오고 있습니다. 다만 와이파이가 아니라 2G입니다.",
        "작은 행운이 지각합니다. 그래도 결석은 아닙니다.",
        "기다림의 미학을 배우는 날입니다. 수업료는 무료입니다.",
        "씨앗은 심었습니다. 물은 오늘부터 주세요.",
    ]),
    ("凶", "흉", "흉하다", 2, "bad", 9, "kyo", [
        "우산을 챙기세요. 비가 안 와도 챙기세요. 마음의 우산입니다.",
        "바닥을 찍었으니 이제 올라갈 일만 남았습니다. 축하합니다(?)",
        "오늘은 레벨업보다 체력 회복의 날. 일찍 자면 내일 아침에 운이 리셋됩니다.",
        "새 신발 말고 편한 신발을 신으세요. 운도 발 편한 쪽을 좋아합니다.",
        "10분 일찍 출발하면 흉이 반으로 줄어듭니다. 20분이면 거의 길입니다.",
        "말실수 주의보. 오늘은 '그렇구나'를 많이 쓰세요.",
        "넘어져도 일어나면 됩니다. 단, 오늘은 계단에서 휴대폰을 보지 마세요.",
        "흉은 '조심하면 괜찮다'는 뜻입니다. 오늘은 조심하는 날입니다.",
    ]),
    ("大凶", "대흉", "크게 흉하다", 1, "bad", 3, "daikyo", [
        "대흉은 대길보다 뽑기 어렵습니다. 쓸데없는 데서 운이 좋으시네요.",
        "축하합니다! 희귀 등급 획득! 오늘 불운을 여기서 다 썼으니 남은 하루는 무사합니다.",
        "신발 끈, 지퍼, 휴대폰 배터리를 한 번씩 확인하세요. 그러면 대흉도 별거 아닙니다.",
        "이 종이를 뽑은 것 자체가 액땜입니다. 이제 묶어 두고 가기만 하면 됩니다.",
        "대흉은 운세계의 한정판입니다. 친구에게 자랑하세요.",
        "더 내려갈 데가 없다는 건 사실 좋은 소식입니다.",
        "오늘은 큰 결정 대신 큰 낮잠을 자세요.",
        "불운이 당신을 찾고 있습니다. 조용히 숨어 계세요. 이불 속이 제일 안전합니다.",
    ]),
]

# (한자, 한글, {구간: 문장들})
TOPICS = [
    ("願望", "소원", {
        "good": ["이루어집니다. 소원을 크게 비세요. 작게 빌면 작게 옵니다.",
                 "말하는 대로 됩니다. 단, 오늘은 '배고파'라고 말하지 마세요.",
                 "기다리던 답이 '네'로 옵니다.",
                 "별똥별이 없어도 됩니다. 오늘은 그냥 말해도 들립니다.",
                 "생각보다 큰 걸로 이루어집니다. 받을 준비를 하세요.",
                 "망설이던 그 일, 시작하면 이루어집니다."],
        "mid": ["천천히 이루어집니다. 재촉하면 소원도 삐집니다.",
                "반쯤 이루어집니다. 나머지 반은 본인 손으로.",
                "조건부로 이루어집니다. 조건은 '꾸준히'.",
                "이루어지긴 하는데 모양이 조금 다릅니다. 그것도 괜찮습니다.",
                "소원 목록을 하나로 줄이면 빨라집니다.",
                "정말 그게 소원인지 한 번 더 생각해 보세요. 그러면 됩니다."],
        "bad": ["오늘은 접수만 됩니다. 처리는 다음 영업일에.",
                "소원보다 낮잠이 먼저입니다.",
                "지금은 때가 아닙니다. 소원을 냉장고에 잠깐 넣어 두세요.",
                "욕심을 하나 내려놓으면 길이 보입니다.",
                "소원 대신 계획을 세우는 날입니다.",
                "오늘 빈 소원은 반송됩니다. 주소를 다시 확인하세요."],
    }),
    ("待人", "기다리는 사람", {
        "good": ["옵니다. 그것도 간식을 들고 옵니다.",
                 "생각보다 빨리 옵니다. 머리는 미리 감아 두세요.",
                 "먼저 연락이 옵니다. 휴대폰 무음은 풀어 두세요.",
                 "반가운 얼굴이 뜻밖의 곳에서 나타납니다.",
                 "좋은 소식까지 들고 옵니다.",
                 "약속보다 일찍 옵니다. 당신만 안 늦으면 됩니다."],
        "mid": ["늦게 옵니다. 그래도 옵니다.",
                "연락이 옵니다. 답장은 너무 빨리 하지 마세요.",
                "오긴 오는데 길을 한 번 헤맵니다. 위치를 보내 주세요.",
                "'곧 도착'이라는 말은 15분을 뜻합니다.",
                "기다리는 동안 할 일을 하나 챙기세요. 덜 기다린 기분이 듭니다.",
                "오기는 오는데 빈손입니다. 간식은 당신이 준비하세요."],
        "bad": ["안 옵니다. 대신 택배가 옵니다.",
                "기다리지 말고 먼저 연락하세요. 그게 빠릅니다.",
                "오늘은 엇갈립니다. 약속은 내일 다시 잡으세요.",
                "기다리는 사람은 지금 자고 있습니다.",
                "읽고 답이 없는 게 아니라 못 본 겁니다. 아마도요.",
                "혼자서도 재밌게 놀고 있으면 그때 옵니다."],
    }),
    ("失物", "잃어버린 물건", {
        "good": ["나옵니다. 아까 본 그 주머니를 한 번 더 보세요.",
                 "찾습니다. 의외로 손에 들고 있을지도 모릅니다.",
                 "누군가 맡아 두고 있습니다. 분실물 보관함을 찾아보세요.",
                 "다른 걸 찾다가 같이 나옵니다. 일석이조입니다.",
                 "가방 맨 안쪽 주머니. 거기 맞습니다.",
                 "찾는 순간 '아, 여기 뒀지' 하게 됩니다."],
        "mid": ["늦게 나옵니다. 소파 밑을 수상하게 여기세요.",
                "새로 사자마자 나옵니다. 세상의 법칙입니다.",
                "어제 입은 옷 주머니를 뒤져 보세요.",
                "찾긴 찾는데 조금 낡았습니다.",
                "한참 뒤 대청소하는 날 나옵니다.",
                "높은 곳보다 낮은 곳을 보세요. 침대 밑이 수상합니다."],
        "bad": ["나오기 어렵습니다. 그 물건도 여행이 하고 싶었나 봅니다.",
                "찾는 대신 이름표를 붙이는 습관을 얻습니다.",
                "그 물건은 지금 새 주인을 만나 잘 지냅니다.",
                "찾다가 다른 걸 잃어버릴 수 있습니다. 오늘은 그만 찾으세요.",
                "포기하는 순간 나타나는 타입입니다. 포기한 척하세요.",
                "새로 사는 것도 방법입니다. 기분 전환도 되고요."],
    }),
    ("学問", "공부", {
        "good": ["찍은 게 맞습니다. 그래도 공부는 하세요.",
                 "집중력이 오릅니다. 휴대폰을 뒤집어 두면 두 배.",
                 "어렵던 개념이 갑자기 이해됩니다. 그 순간을 적어 두세요.",
                 "오늘 외운 건 오래갑니다. 중요한 걸 외우세요.",
                 "질문하면 좋은 답을 듣습니다. 손을 드세요.",
                 "공부한 데서 문제가 나옵니다. 운이 아니라 실력입니다."],
        "mid": ["보통입니다. 형광펜만 칠하고 끝내지 마세요.",
                "외운 것의 절반이 기억납니다. 나머지 절반은 내일 다시.",
                "책상 정리부터 하게 됩니다. 정리만 하고 끝내지는 마세요.",
                "30분 집중, 10분 휴식이 딱 맞는 날입니다.",
                "어려운 건 내일로, 쉬운 건 오늘. 그것도 전략입니다.",
                "아는 것 같은데 설명은 못 하는 상태. 소리 내어 읽어 보세요."],
        "bad": ["책을 베개로 쓰면 지식이 스며든다는 설은 거짓입니다.",
                "오늘은 복습만. 새 진도는 머리가 거부합니다.",
                "의자에 앉자마자 졸립니다. 서서 해 보세요.",
                "공부보다 잠이 이기는 날. 일찍 자고 일찍 하세요.",
                "벼락치기 금지. 벼락은 피하는 게 맞습니다.",
                "펜이 안 나옵니다. 여분의 펜을 챙기세요."],
    }),
    ("恋愛", "연애", {
        "good": ["눈이 마주치면 먼저 웃으세요. 오늘은 그게 통합니다.",
                 "인연이 가까이 있습니다. 거울 말고 옆을 보세요.",
                 "먼저 말을 걸면 대화가 술술 이어집니다.",
                 "평소 입던 옷이 오늘따라 잘 어울립니다.",
                 "고백 운이 좋습니다. 단, 단체 대화방에서는 하지 마세요.",
                 "좋아하는 사람과 같은 메뉴를 고릅니다. 운명이라 우겨 보세요."],
        "mid": ["서두르지 마세요. 라면도 불면 맛이 없습니다.",
                "썸은 탑니다. 썸만 탑니다.",
                "진도는 천천히. 거북이도 결국 결승선에 갑니다.",
                "답장이 늦어도 마음은 있습니다. 바쁜 겁니다.",
                "친구 사이에서 한 걸음. 딱 한 걸음입니다.",
                "말보다 행동이 통합니다. 간식을 건네 보세요."],
        "bad": ["오늘은 나 자신과 연애하는 날. 맛있는 거 사 주세요.",
                "보낸 메시지에 오타가 있습니다. 보내기 전에 다시 읽으세요.",
                "오늘은 거울 속 나를 칭찬하는 날입니다.",
                "밤에 쓴 메시지는 아침에 다시 읽고 보내세요.",
                "인연은 오늘 휴무입니다. 내일 다시 영업합니다.",
                "연애보다 우정이 빛나는 날. 친구에게 밥을 사세요."],
    }),
    ("金運", "금전운", {
        "good": ["주머니에서 잊고 있던 돈이 나옵니다.",
                 "할인 쿠폰 운이 폭발합니다. 장바구니를 확인하세요.",
                 "생각지 못한 용돈이 들어옵니다.",
                 "중고 거래가 술술 풀립니다. 안 쓰는 물건을 올려 보세요.",
                 "원하던 물건이 할인 중입니다. 지금이 기회입니다.",
                 "오늘 아낀 돈은 다음 주에 두 배로 기쁩니다."],
        "mid": ["들어온 만큼 나갑니다. 계산은 정확한 편입니다.",
                "1+1 상품이 당신을 부릅니다. 하나만 필요해도요.",
                "커피 한 잔 아끼면 내일 커피 두 잔. 계산은 맞습니다.",
                "용돈 기입장을 쓰면 숨은 돈이 보입니다.",
                "충동구매 직전에 정신을 차립니다. 장하십니다.",
                "들어오는 것도 나가는 것도 없는 평화로운 날입니다."],
        "bad": ["지갑을 꼭 닫으세요. 특히 편의점 앞에서.",
                "오늘의 쇼핑은 장바구니에만 담으세요. 결제는 내일의 나에게.",
                "배달비가 음식값을 넘보는 날. 직접 가세요.",
                "안 쓰는 구독 하나를 해지하세요. 그게 오늘의 행운입니다.",
                "결제 알림이 무서운 날. 알림을 꺼도 돈은 나갑니다.",
                "남의 지갑 말고 내 지갑 지퍼부터 확인하세요."],
    }),
]

LUCKY_ITEMS = [
    "따뜻한 캔커피", "짝이 맞는 양말", "편의점 삼각김밥", "충전 100% 보조배터리", "볼펜 뚜껑",
    "귤 한 개", "고무줄", "지금 들고 있는 이 영수증", "빨간 펜", "주머니 속 동전",
    "포스트잇", "줄 이어폰", "손수건", "사탕 한 알", "새 지우개",
    "초코우유", "바나나맛 우유", "클립 하나", "물티슈", "립밤",
    "접이식 우산", "목도리", "핫팩", "붕어빵", "호두과자",
    "열쇠고리", "스티커 한 장", "형광펜", "샤프심", "15cm 자",
    "투명 테이프", "머리끈", "안경닦이", "손거울", "텀블러",
    "에코백", "운동화", "털모자", "장갑", "껌 한 통",
    "젤리", "감자칩", "컵라면", "김밥 꽁다리", "떡볶이",
    "도토리", "솔방울", "네잎클로버", "종이비행기", "고양이 사진",
    "강아지 영상", "좋아하는 노래 한 곡", "엽서", "교통카드", "500원짜리 동전",
    "새 공책", "연필깎이", "단팥빵", "보리차", "작은 화분",
]
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
