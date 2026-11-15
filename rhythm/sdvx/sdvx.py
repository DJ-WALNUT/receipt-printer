"""Vaddict(vaddict.b35.jp) 유저 페이지를 읽어 '볼포스 영수증'으로 인쇄한다. (시험판)

사용법 (프로젝트 폴더에서):
    python rhythm/sdvx/sdvx.py 저장한페이지.html              # 볼포스 대상곡 상위 5곡
    python rhythm/sdvx/sdvx.py 저장한페이지.html --top 10     # 상위 10곡
    python rhythm/sdvx/sdvx.py 저장한페이지.html --all        # 볼포스 대상 50곡 전부 (아주 길다)
    python rhythm/sdvx/sdvx.py 저장한페이지.html --preview    # 인쇄 없이 이미지만 저장

지금은 브라우저에서 저장한 페이지 파일(Ctrl+S, "웹페이지, HTML만")만 읽는다. 사이트에 접속하지 않는다.
Vaddict는 robots.txt와 2차 이용 공지에서 자동 접근을 금지하고 있다. 운영자에게 API를 받으면
load_page() 대신 그 API를 읽는 함수를 끼우면 된다 (docs/작업-정리.md 의 "사운드 볼텍스 볼포스 영수증").
이미지는 rhythm/sdvx/output/ 에 저장된다.
"""
import argparse
import datetime
import html
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # 공용 모듈 receipt.py
from PIL import Image, ImageDraw

from receipt import (CONTENT_W, MARGIN, PAPER_W, add_output_args, draw_run, fit, output, raw, render, stack,
                     text_width)

VF_TRACKS = 50          # 볼포스는 단일곡 VF 상위 50보면의 합이다
PRICE_PER_PLAY = 1000   # '결제 내역' 농담용: 1판 값을 이 금액으로 어림한다

# 점수 기준 그레이드
GRADES = [(9900000, "S"), (9800000, "AAA+"), (9700000, "AAA"), (9500000, "AA+"), (9300000, "AA"),
          (9000000, "A+"), (8700000, "A"), (7500000, "B"), (6500000, "C"), (0, "D")]
PUC = 10000000
S_SCORE = GRADES[0][0]
# 클리어 마크: 페이지의 표시 -> (영수증에 찍을 이름, 순위). 순위가 높을수록 좋은 마크
MEDALS = {"PUC": ("PUC", 5), "UC": ("UC", 4), "MXV": ("MXV", 3), "EX": ("EXC", 2), "C": ("COMP", 1)}
NO_MEDAL = ("PLAYED", 0)
MEDAL_ORDER = ("PUC", "UC", "MXV", "EXC", "COMP")
MEDAL_LEGEND = "PUC 만점 · UC 노미스 · MXV/EXC/COMP 게이지별 클리어"
# 볼포스 구간과 한마디 (구간 이름은 페이지에 적힌 것을 그대로 쓴다)
COMMENTS = [
    (23.0, "사람이 맞는지 기계가 확인하고 싶어 합니다."),
    (22.0, "오락실 직원이 이름을 외웠을 실력입니다."),
    (20.0, "임페리얼. 노브가 손의 일부가 된 사람."),
    (19.0, "크림슨. 임페리얼이 보이는데 손이 안 따라옵니다."),
    (18.0, "엘도라. 금빛이지만 지갑은 가벼워졌습니다."),
    (17.0, "아르젠토. 18레벨과 눈을 마주치기 시작했습니다."),
    (16.0, "코랄. 노브를 돌리다 손목에서 소리가 납니다."),
    (15.0, "스칼렛. 레이저가 슬슬 재미있어질 시기입니다."),
    (14.0, "시안. 양손이 따로 노는 법을 배우는 중입니다."),
    (12.0, "단델리온. 민들레처럼 꾸준히 올라갑니다."),
    (10.0, "코발트. 버튼 위치를 손이 기억하기 시작했습니다."),
    (0.0, "어서 오세요. 노브는 돌리라고 있는 겁니다."),
]


class SdvxError(Exception):
    pass


# ---------------------------------------------------------------- 페이지 읽기

def _text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _find(pattern, text, what):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SdvxError(f"페이지에서 {what}을(를) 찾지 못했습니다. Vaddict 유저 페이지가 맞는지 확인해 주세요.")
    return m.group(1)


def _track(segment):
    """보면 하나의 HTML 조각 -> dict. 꼭 있어야 하는 값이 없으면 None."""
    def get(pattern):
        m = re.search(pattern, segment, re.S)
        return m.group(1) if m else None

    name, dif, level = get(r'class="music_name">(.*?)</div>'), get(r'class="dif \w+">(\w+)<'), get(r'class="level">([\d.]+)<')
    vf, score = get(r"単曲VF: ([\d.]+)"), get(r'class="score">(\d+)<')
    if None in (name, dif, level, vf, score):
        return None
    name = re.sub(r'<span class="star">.*?</span>', "", name)
    gain = get(r'class="score_diff">\+(\d+)')
    return {"title": _text(name), "dif": dif, "level": float(level), "vf": float(vf), "score": int(score),
            "medal": MEDALS.get(_text(get(r'class="clear_medal [\w ]+">(.*?)<') or ""), NO_MEDAL),
            "gain": int(gain) if gain else 0}


def load_page(path):
    """저장한 Vaddict 유저 페이지 -> {"name", "id", "plays", "last", "volforce", "klass", "next", "tracks"}"""
    try:
        page = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise SdvxError(f"파일을 읽을 수 없습니다 ({e}).") from None
    if 'id="user_page"' not in page:
        raise SdvxError("Vaddict 유저 페이지가 아닙니다.")

    def value(label):
        return _text(_find(rf"<h5>{label}</h5>\s*<div class=\"value[^\"]*\">(.*?)</div>", page, label))

    def svg(element):
        m = re.search(rf'id="{element}"[^>]*>(.*?)</text>', page, re.S)
        return _text(m.group(1)) if m else ""

    starts = [m.start() for m in re.finditer(r'<div class="tracks">', page)]
    tracks = [t for t in (_track(page[a:b]) for a, b in zip(starts, starts[1:] + [len(page)])) if t]
    if not tracks:
        raise SdvxError("기록이 하나도 없습니다. 플레이 데이터가 공개되어 있는지 확인해 주세요.")
    tracks.sort(key=lambda t: -t["vf"])
    try:
        volforce = float(svg("volforce_num"))
    except ValueError:
        volforce = sum(t["vf"] for t in tracks[:VF_TRACKS]) / 100
    plays = re.sub(r"\D", "", value("プレー回数"))
    return {"name": value("Player Name"), "id": value("Player ID"), "plays": int(plays) if plays else 0,
            "last": value("最終プレー"), "volforce": volforce, "klass": svg("volforce_class"),
            "next": (svg("volforce_next"), svg("volforce_next_class")), "tracks": tracks}


# ---------------------------------------------------------------- 영수증 만들기

def grade_of(score):
    return next(name for floor, name in GRADES if score >= floor)


def near_miss(tracks):
    """다음 그레이드(또는 PUC)까지 가장 조금 남은 보면 -> (보면, 목표 이름, 남은 점수) 또는 None"""
    best = None
    for t in tracks:
        goals = [(PUC, "PUC")] + GRADES
        higher = [(floor, name) for floor, name in goals if floor > t["score"]]
        if higher:
            floor, name = higher[-1]
            if best is None or floor - t["score"] < best[2]:
                best = (t, name, floor - t["score"])
    return best


def chart(t):
    return f"{t['dif']} {t['level']:.1f}"


def song_rows(tracks):
    rows = []
    for t in tracks:
        price = f"{t['vf']:.1f}"
        room = CONTENT_W - text_width(price, "body") * 2 - 24
        rows.append(raw("body", fit(t["title"], "body", room), right=price))
        rows.append(raw("small", f"  {chart(t)} · {t['score']:,} · {grade_of(t['score'])} · {t['medal'][0]}"))
    return rows


def medal_table(tracks):
    """클리어 마크별 보면 수를 다섯 칸짜리 표로 그린다. 윗줄은 마크 이름, 아랫줄은 개수."""
    count = Counter(t["medal"][0] for t in tracks)
    row_h, line = 38, 2
    col_w = CONTENT_W // len(MEDAL_ORDER)
    width = col_w * len(MEDAL_ORDER)
    table = Image.new("1", (PAPER_W, row_h * 2 + line * 3 + 8), 1)
    d = ImageDraw.Draw(table)
    left, top = MARGIN + (CONTENT_W - width) // 2, 2
    bottom = top + row_h * 2 + line * 2
    d.rectangle([left, top, left + width - 1, top + row_h + line - 1], fill=0)          # 이름 줄은 검은 바탕
    for y in (top, top + row_h + line, bottom):
        d.rectangle([left, y, left + width - 1, y + line - 1], fill=0)
    for i, name in enumerate(MEDAL_ORDER):
        x = left + col_w * i
        head = draw_run(name, "reverse")
        table.paste(head, (x + (col_w - head.width) // 2, top + line + (row_h - head.height) // 2))
        cell = draw_run(f"{count[name]:,}", "body")
        table.paste(cell, (x + (col_w - cell.width) // 2, top + row_h + line * 2 + (row_h - cell.height) // 2))
    for i in range(len(MEDAL_ORDER) + 1):                                                # 세로 칸막이는 개수 줄에만
        x = min(left + col_w * i, left + width - line)
        d.rectangle([x, top + row_h + line, x + line - 1, bottom + line - 1], fill=0)
    return table


def compose(items):
    """줄(문자열, raw)과 이미지가 섞인 목록을 한 장으로 만든다. 이어진 줄들은 한꺼번에 render 한다."""
    parts, lines = [], []
    for item in items:
        if isinstance(item, Image.Image):
            if lines:
                parts.append(render(lines))
                lines = []
            parts.append(item)
        else:
            lines.append(item)
    if lines:
        parts.append(render(lines))
    return stack(*parts)


def build_sheet(info, top=5):
    tracks = info["tracks"]
    target = tracks[:VF_TRACKS]
    shown = target if top is None else target[:top]
    volforce = info["volforce"]

    lines = [
        "^ @36b 볼포스 영수증",
        raw("small", f"SOUND VOLTEX · {info['id']}", align="center"),
        "---",
        raw("@48b", info["name"], align="center"),   # 플레이어 이름은 8자까지라 넘치지 않는다
        "---",
        f"플레이 횟수 || {info['plays']:,}회",
        f"기록한 보면 || {len(tracks):,}개",
        raw("body", "마지막 플레이", right=info["last"][:10] or "-"),
        "---",
        f"## 볼포스 대상곡 ({len(target)}곡 중 상위 {len(shown)}곡)" if len(shown) < len(target)
        else f"## 볼포스 대상곡 ({len(target)}곡)",
    ]
    lines += song_rows(shown)
    subtotal = sum(t["vf"] for t in target)
    lines += [
        f"**단일곡 VF 소계 ({len(target)}곡) || {subtotal:,.1f}**",
        "> 볼포스 = 소계 ÷ 100",
        "---",
        f"@36b 합계 VOLFORCE || {volforce:.3f}",
    ]
    gap, upper = info["next"]
    lines.append(raw("small", f"{info['klass']} · {upper}까지 {gap}" if gap and upper else info["klass"] or "-"))
    lines.append("---")

    levels, n = Counter(int(t["level"]) for t in target).most_common(1)[0]
    hardest = max(target, key=lambda t: t["level"])
    cleared = [t for t in tracks if t["medal"] != NO_MEDAL]
    lines += [
        "[[손님 분석]]",
        f"> 볼포스 대상 {len(target)}곡 기준",
        f"평균 점수 || {sum(t['score'] for t in target) / len(target):,.0f}",
        f"주력 레벨 || {levels} ({n}곡)",
        f"그레이드 S (990만점 이상) || {sum(t['score'] >= S_SCORE for t in target)}곡",
        f"최고 레벨 || {chart(hardest)}",
        raw("small", "  " + fit(hardest["title"], "small", CONTENT_W - 40)),
        f"> 클리어 마크별 곡 수 (대상 {len(target)}곡)",
        medal_table(target),
        raw("small", MEDAL_LEGEND),
        "",
        "[[전체 기록]]",
        f"> 지금까지 기록한 보면 {len(tracks):,}개 기준",
        f"그레이드 S (990만점 이상) || {sum(t['score'] >= S_SCORE for t in tracks):,}개",
        f"클리어한 보면 || {len(cleared):,}개",
        f"클리어 못 한 보면 || {len(tracks) - len(cleared):,}개",
        f"> 클리어 마크별 보면 수 (클리어한 {len(cleared):,}개)",
        medal_table(cleared),
        "",
        "[[아깝다 상]]",
    ]
    miss = near_miss(tracks)
    if miss:
        t, name, gap = miss
        lines += [raw("body", fit(t["title"], "body", CONTENT_W)),
                  f"> {chart(t)} · {t['score']:,} · {name}까지 단 {gap:,}점"]
    else:
        lines.append("> 해당 없음. 전부 PUC 입니다. 무섭네요.")

    improved = [t for t in tracks if 0 < t["gain"] < t["score"]]   # 처음 친 보면(오른 점수 = 점수)은 뺀다
    fresh = sum(1 for t in tracks if t["gain"])
    if fresh:
        lines += ["", "[[이번 갱신]]", f"신기록 || {fresh:,}개"]
        if improved:
            best = max(improved, key=lambda t: t["gain"])
            lines += [raw("body", "가장 많이 오른 곡", right=f"+{best['gain']:,}"),
                      raw("small", "  " + fit(f"{best['title']} · {chart(best)}", "small", CONTENT_W - 40))]
    lines.append("---")

    if info["plays"]:
        spent = info["plays"] * PRICE_PER_PLAY
        lines += [
            "[[결제 내역]]",
            f"{info['plays']:,}판 × {PRICE_PER_PLAY:,}원 || {spent:,}원",
            f"볼포스 1.000당 || 약 {spent / volforce:,.0f}원" if volforce else "볼포스 1.000당 || 계산 불가",
            f"> 1판을 {PRICE_PER_PLAY:,}원으로 어림한 금액입니다. 실제와 다릅니다.",
            "---",
        ]

    lines += [
        raw("body", next(text for floor, text in COMMENTS if volforce >= floor), align="center"),
        "---",
        f"^ > 기록 갱신 {info['last'][:10] or '?'} · 출력 {datetime.date.today().isoformat()}",
        "^ > 교환·환불 불가. 이미 친 곡은 되돌릴 수 없습니다.",
        "^ > Data: Vaddict (vaddict.b35.jp)",
    ]
    return compose(lines)


def main():
    ap = argparse.ArgumentParser(description="저장한 Vaddict 유저 페이지를 볼포스 영수증으로 인쇄")
    ap.add_argument("page", help="브라우저에서 저장한 Vaddict 유저 페이지 (.html)")
    ap.add_argument("--top", type=int, default=5, help="볼포스 대상곡 중 몇 곡을 찍을지 (기본 5)")
    ap.add_argument("--all", action="store_true", help="볼포스 대상 50곡 전부 찍기")
    add_output_args(ap)
    args = ap.parse_args()

    try:  # 여기서 실패하면 프린터에는 아무것도 보내지 않는다
        info = load_page(args.page)
        sheet = build_sheet(info, None if args.all else max(1, args.top))
    except SdvxError as e:
        sys.exit(f"오류: {e} 인쇄하지 않았습니다.")

    tag = re.sub(r"[^A-Za-z0-9-]", "", info["id"]) or "sdvx"
    print(f"{info['name']} (VOLFORCE {info['volforce']:.3f}) -> " + output(sheet, "rhythm/sdvx", args, tag))


if __name__ == "__main__":
    main()
