"""낱말 찾기 한 판을 만들어 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python games/wordsearch/wordsearch.py                        # 보통 난이도, 주제 무작위
    python games/wordsearch/wordsearch.py --level hard           # easy | medium | hard
    python games/wordsearch/wordsearch.py --theme animal         # animal | food | fruit | school | space | job | sports | ...
    python games/wordsearch/wordsearch.py --words "나름,청소년,광명,동아리"   # 낱말을 직접 지정
    python games/wordsearch/wordsearch.py --preview              # 인쇄 없이 이미지만 저장
    python games/wordsearch/wordsearch.py --answer WM3482913      # 그 판의 정답 인쇄 (번호는 영수증 아래에 찍힘)

이미지는 games/wordsearch/output/ 에 저장된다.
시드번호는 W + 난이도 글자 + 주제 글자(1~9, A~Z) + 여섯 자리 숫자다. 번호만 있으면 같은 판과 정답을 다시 만들 수 있다.
낱말을 직접 지정한 판(주제 글자 0)의 정답은 --answer 와 함께 같은 --words 를 다시 줘야 한다.
"""
import argparse
import datetime
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from receipt import CONTENT_W, MARGIN, PAPER_W, add_output_args, strip_seed, draw_run, output, render, size_style, stack

SEED_PREFIX = "W"  # 시드번호 맨 앞 글자. 콘텐츠마다 다르다.
ACROSS, DOWN = (0, 1), (1, 0)
DIAGONAL = [(1, 1), (-1, 1)]
BACKWARD = [(0, -1), (-1, 0), (-1, -1), (1, -1)]
ALL_DIRS = [ACROSS, DOWN] + DIAGONAL + BACKWARD

LEVELS = {  # 글자: (이름, 표시, 가로 칸, 세로 칸, 낱말 수, 칸 크기, 정답지 칸 크기, 방향, 방향 설명)
    "E": ("easy", "쉬움", 8, 8, 6, 64, 40, [ACROSS, DOWN],
          "낱말은 가로(→)나 세로(↓)로 숨어 있습니다."),
    "M": ("medium", "보통", 10, 10, 8, 54, 36, [ACROSS, DOWN] + DIAGONAL,
          "낱말은 가로, 세로, 대각선으로 숨어 있습니다."),
    "H": ("hard", "어려움", 12, 14, 10, 46, 32, ALL_DIRS,
          "가로, 세로, 대각선에 거꾸로 적힌 낱말도 있습니다."),
}

THEMES = [  # 번호 1부터. (이름, 표시, 낱말들) - 순서를 바꾸면 예전 시드번호가 다른 판이 된다. 새 주제는 맨 뒤에.
    ("animal", "동물", "호랑이 코끼리 기린 토끼 고양이 강아지 다람쥐 펭귄 돌고래 거북이 사자 여우 늑대 판다 하마 악어 "
                       "캥거루 고슴도치 너구리 부엉이 원숭이 코알라 수달 상어 앵무새 독수리 얼룩말 낙타 두더지 표범 "
                       "햄스터 오소리"),
    ("food", "음식", "떡볶이 김밥 라면 비빔밥 불고기 만두 치킨 피자 햄버거 짜장면 김치찌개 돈가스 냉면 순대 튀김 "
                     "샌드위치 칼국수 붕어빵 호떡 삼겹살 잡채 갈비 떡국 쫄면 우동 초밥 파스타 핫도그 오므라이스 "
                     "감자탕 된장찌개 닭강정"),
    ("fruit", "과일", "사과 바나나 딸기 포도 수박 참외 복숭아 오렌지 파인애플 블루베리 키위 망고 자두 체리 레몬 "
                      "감귤 한라봉 멜론 석류 살구 무화과 코코넛 아보카도 라임 매실 대추 유자 앵두 용과 두리안 자몽"),
    ("school", "학교", "교실 칠판 운동장 급식 선생님 친구 숙제 방학 소풍 체육 음악 미술 도서관 필통 지우개 연필 "
                       "공책 시험 동아리 수학여행 교과서 책상 의자 사물함 운동회 졸업식 입학식 반장 실내화 가방 과학실"),
    ("space", "우주", "태양 지구 화성 목성 토성 은하수 별자리 우주선 블랙홀 혜성 보름달 유성 망원경 로켓 인공위성 "
                      "금성 외계인 천왕성 해왕성 북극성 수성 명왕성 소행성 우주인 성운 일식 월식 오로라 초신성 궤도"),
    ("job", "직업", "의사 간호사 경찰관 소방관 요리사 가수 배우 화가 작가 기자 변호사 판사 군인 농부 어부 미용사 "
                    "제빵사 과학자 우주비행사 운동선수 유튜버 약사 건축가 조종사 사진가 경비원 바리스타 집배원"),
    ("sports", "운동", "축구 야구 농구 테니스 수영 태권도 씨름 양궁 펜싱 골프 볼링 스키 마라톤 줄넘기 "
                       "배드민턴 체조 유도 복싱 스케이트 서핑 등산 승마 역도 하키 컬링 줄다리기 스노보드 달리기"),
    ("weather", "날씨", "봄비 장마 태풍 무지개 소나기 눈사람 번개 천둥 안개 이슬 햇살 단풍 낙엽 고드름 눈꽃 우박 "
                        "황사 미세먼지 열대야 첫눈 바람 구름 서리 폭염 한파 일기예보 우산 꽃샘추위"),
    ("ride", "탈것", "자동차 버스 지하철 기차 비행기 헬리콥터 자전거 오토바이 택시 트럭 유람선 잠수함 구급차 "
                     "소방차 경찰차 킥보드 케이블카 열기구 요트 기관차 굴착기 트랙터 로켓 마차 썰매 모노레일"),
    ("music", "악기", "피아노 기타 바이올린 드럼 플루트 하모니카 리코더 트럼펫 첼로 실로폰 가야금 장구 꽹과리 "
                      "탬버린 캐스터네츠 오카리나 우쿨렐레 색소폰 거문고 단소 해금 하프 아코디언 트라이앵글 징"),
    ("snack", "간식", "아이스크림 초콜릿 젤리 쿠키 케이크 마카롱 와플 도넛 빙수 팝콘 솜사탕 푸딩 츄러스 약과 "
                      "식혜 붕어빵 호떡 계란빵 꽈배기 찹쌀떡 바나나우유 감자칩 요구르트 티라미수 크루아상 호두과자"),
    ("country", "나라", "한국 일본 중국 미국 영국 프랑스 독일 이탈리아 스페인 캐나다 호주 브라질 인도 러시아 "
                        "멕시코 이집트 베트남 태국 스위스 네덜란드 몽골 칠레 그리스 노르웨이 핀란드 케냐 페루"),
    ("sea", "바다", "해파리 불가사리 오징어 문어 꽃게 조개 미역 산호초 소라 등대 파도 모래사장 갈매기 고래 "
                    "거북 해초 진주 잠수부 수평선 갯벌 해안선 해녀 바닷가재 새우 멸치 고등어"),
]
# 시드번호에서 주제를 나타내는 글자. 0은 직접 고른 낱말, 그다음 1~9, A~Z 순서다.
THEME_CODES = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
assert len(THEMES) < len(THEME_CODES)

FILLER = ("가나다라마바사아자차카타파하고노도로모보소오조초코토포호구누두루무부수우주추쿠투푸후"
          "기니디리미비시이지치키티피히개내대래매배새애재채강낭당랑망방상앙장창공농동롱몽봉송옹종총"
          "군눈문분순운준춘김림심임진신인민빈산단반안잔한")


def try_place(grid, word, dirs, rng):
    """낱말을 빈칸이나 같은 글자 위에 놓는다. 놓은 칸 목록을 돌려주고, 자리가 없으면 None."""
    rows, cols = len(grid), len(grid[0])
    for _ in range(300):
        dr, dc = rng.choice(dirs)
        r, c = rng.randrange(rows), rng.randrange(cols)
        cells = [(r + dr * k, c + dc * k) for k in range(len(word))]
        if all(0 <= y < rows and 0 <= x < cols and grid[y][x] in ("", ch) for (y, x), ch in zip(cells, word)):
            for (y, x), ch in zip(cells, word):
                grid[y][x] = ch
            return cells
    return None


def count_hits(grid, word):
    """판 전체에서 이 낱말이 읽히는 횟수 (여덟 방향 모두)."""
    rows, cols = len(grid), len(grid[0])
    hits = 0
    for r in range(rows):
        for c in range(cols):
            for dr, dc in ALL_DIRS:
                er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                if 0 <= er < rows and 0 <= ec < cols and all(
                        grid[r + dr * k][c + dc * k] == ch for k, ch in enumerate(word)):
                    hits += 1
    return hits


def generate(level, number, pool, fixed):
    """(글자판, {낱말: 칸 목록}) 반환. fixed=True면 pool의 낱말을 전부 넣어야 한다.

    빈칸을 채운 뒤 어떤 낱말이 두 군데서 읽히면 처음부터 다시 만든다. 그래서 정답은 항상 하나다.
    """
    cols, rows, want, dirs = LEVELS[level][2], LEVELS[level][3], LEVELS[level][4], LEVELS[level][7]
    for attempt in range(200):
        rng = random.Random(f"{number}|{','.join(pool)}|{attempt}")
        grid = [[""] * cols for _ in range(rows)]
        order = pool[:]
        rng.shuffle(order)
        if fixed:
            order.sort(key=len, reverse=True)  # 긴 낱말부터 놓아야 자리가 난다
        placed = {}
        for word in order:
            if len(placed) == (len(pool) if fixed else want):
                break
            if any(word in w or w in word for w in placed):
                continue
            cells = try_place(grid, word, dirs, rng)
            if cells:
                placed[word] = cells
        if len(placed) < (len(pool) if fixed else want):
            continue
        own = "".join(placed)  # 낱말에 든 글자를 섞어 넣어 헷갈리게 한다 (쉬움은 제외)
        for r in range(rows):
            for c in range(cols):
                if not grid[r][c]:
                    grid[r][c] = rng.choice(own if level != "E" and rng.random() < 0.35 else FILLER)
        # 거꾸로 읽어도 같은 낱말(토마토)은 한 자리에서 양쪽으로 두 번 읽힌다
        if all(count_hits(grid, w) == (2 if w == w[::-1] else 1) for w in placed):
            return grid, placed
    sys.exit("이 낱말들로는 판을 만들지 못했습니다. 낱말을 줄이거나 난이도를 올려 판을 키워 보세요.")


def draw_grid(grid, cell, placed=None):
    """글자판. placed를 주면 정답지: 낱말 글자만 굵게 찍고 나머지 칸은 점으로 둔다."""
    rows, cols = len(grid), len(grid[0])
    frame = 3
    w, h = cols * cell, rows * cell
    x0, y0 = (PAPER_W - w) // 2, 6 + frame
    im = Image.new("1", (PAPER_W, h + (6 + frame) * 2), 1)
    d = ImageDraw.Draw(im)
    for k in range(frame):
        d.rectangle([x0 - 1 - k, y0 - 1 - k, x0 + w + k, y0 + h + k], outline=0)
    answer = {cell_ for cells in placed.values() for cell_ in cells} if placed else None
    style = size_style(24, True) if placed else size_style(36, False)
    for r in range(rows):
        for c in range(cols):
            cx, cy = x0 + c * cell + cell // 2, y0 + r * cell + cell // 2
            if answer is not None and (r, c) not in answer:
                d.rectangle([cx - 1, cy - 1, cx + 1, cy + 1], fill=0)
                continue
            glyph = draw_run(grid[r][c], style)
            im.paste(glyph, (cx - glyph.width // 2, cy - glyph.height // 2))
    return im


def draw_words(words, per_row=3):
    """찾을 낱말 목록. 찾으면 표시할 네모 칸과 함께 세 줄 단으로 늘어놓는다."""
    runs = [draw_run(w, "body") for w in words]
    box, gap = 20, 8
    row_h = max(r.height for r in runs) + 8
    col_w = CONTENT_W // per_row
    im = Image.new("1", (PAPER_W, row_h * -(-len(words) // per_row) + 4), 1)
    d = ImageDraw.Draw(im)
    for i, run in enumerate(runs):
        x, y = MARGIN + (i % per_row) * col_w, (i // per_row) * row_h
        by = y + (run.height - box) // 2
        d.rectangle([x, by, x + box - 1, by + box - 1], outline=0, width=2)
        im.paste(run, (x + box + gap, y))
    return im


def main():
    names = [t[0] for t in THEMES]
    ap = argparse.ArgumentParser(description="낱말 찾기를 영수증 프린터로 인쇄")
    ap.add_argument("--level", choices=[v[0] for v in LEVELS.values()], default="medium")
    ap.add_argument("--theme", choices=names, help="주제 (기본: 무작위)")
    ap.add_argument("--words", metavar="낱말,낱말", help="주제 대신 직접 넣을 낱말 (쉼표로 구분)")
    ap.add_argument("--answer", metavar="번호", help="해당 판의 정답을 인쇄 (예: WM3482913)")
    add_output_args(ap)
    args = ap.parse_args()
    if args.answer:
        args.answer = strip_seed(args.answer, SEED_PREFIX, ap, "WM3482913")

    if args.answer:
        level, theme, seed = args.answer[:1].upper(), args.answer[1:2].upper(), args.answer[2:]
        if (level not in LEVELS or not theme or THEME_CODES.find(theme) not in range(len(THEMES) + 1)
                or not (seed.isdigit() and seed.isascii())):
            ap.error("시드번호는 W + 난이도(E/M/H) + 주제 글자 + 숫자 형식입니다 (예: WM3482913)")
        theme = THEME_CODES.index(theme)
        if theme == 0 and not args.words:
            ap.error("낱말을 직접 넣은 판입니다. 인쇄할 때 쓴 --words 를 함께 주세요.")
        if theme != 0 and args.words:
            ap.error("이 번호는 주제로 만든 판입니다. --words 없이 실행하세요.")
    else:
        level = next(k for k, v in LEVELS.items() if v[0] == args.level)
        theme = 0 if args.words else names.index(args.theme) + 1 if args.theme else random.randint(1, len(THEMES))
        seed = str(random.randrange(100000, 1000000))
    number = f"{level}{THEME_CODES[theme]}{seed}"
    seed_no = SEED_PREFIX + number
    cols, rows = LEVELS[level][2:4]

    if theme == 0:
        pool = list(dict.fromkeys(w.replace(" ", "") for w in args.words.split(",") if w.strip()))
        longest = max(cols, rows)
        bad = [w for w in pool if not 2 <= len(w) <= longest]
        if bad or not pool:
            ap.error(f"이 난이도에서 낱말은 2~{longest}글자여야 합니다: {', '.join(bad) or '(낱말 없음)'}")
        theme_name = "직접 고른 낱말"
    else:
        theme_name, pool = THEMES[theme - 1][1], THEMES[theme - 1][2].split()
    grid, placed = generate(level, number, pool, fixed=theme == 0)
    words = sorted(placed)

    if args.answer:
        sheet = stack(
            render(["^ ## 낱말 찾기 정답", f"^ > No. {seed_no} · {theme_name}"]),
            draw_grid(grid, LEVELS[level][6], placed),
            render(["> " + ", ".join(words)]),
        )
    else:
        today = datetime.date.today().isoformat()
        sheet = stack(
            render(["^ # 낱말 찾기", f"^ {today} · {LEVELS[level][1]} · Seed No. {seed_no}"]),
            draw_grid(grid, LEVELS[level][5]),
            render([f"**찾을 낱말: {theme_name} {len(words)}개**"]),
            draw_words(words),
            render([
                f"@20 {LEVELS[level][8]}",
                f"@20 정답: 시드번호 지참해서 사무실에 문의하세요 - {seed_no}",
            ]),
        )

    tag = f"{seed_no}_answer" if args.answer else seed_no
    print(f"No. {seed_no} ({theme_name}, 낱말 {len(words)}개) " + output(sheet, "games/wordsearch", args, tag))


if __name__ == "__main__":
    main()
