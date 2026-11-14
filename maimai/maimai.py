"""maishift(maimai.shiftpsh.com) 프로필을 읽어 '레이팅 영수증'으로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python maimai/maimai.py walnut              # 아이디로 한 장 인쇄
    python maimai/maimai.py walnut --top 10     # 신곡·구곡을 각각 10곡씩 (기본 3곡)
    python maimai/maimai.py walnut --all        # 레이팅 대상곡 전부 (길다)
    python maimai/maimai.py walnut --preview    # 인쇄 없이 이미지만 저장

아이디 자리에 프로필 주소를 통째로 붙여 넣어도 된다.
아이디가 없거나 비공개면 오류 메시지만 내고 인쇄하지 않는다. 이미지는 maimai/output/ 에 저장된다.
한 번 실행에 사이트 요청은 한 번만 한다.
"""
import argparse
import datetime
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 공용 모듈 receipt.py
from receipt import CONTENT_W, add_output_args, fit, output, raw, render, text_width

SITE = "https://maimai.shiftpsh.com"
PRICE_PER_PLAY = 1000  # '결제 내역' 농담용: 1판 값을 이 금액으로 어림한다

COURSE_RANKS = (["初心者"] + [f"{n}段" for n in "初二三四五六七八九十"] + ["皆伝"]
                + [f"真{n}段" for n in "初二三四五六七八九十"] + ["真皆伝", "裏皆伝"])
CLASS_RANKS = [f"{g}{n}" for g in ("B", "A", "S", "SS", "SSS") for n in (5, 4, 3, 2, 1)] + ["LEGEND"]
DIFFS = {"BASIC": "BAS", "ADVANCED": "ADV", "EXPERT": "EXP", "MASTER": "MAS", "RE_MASTER": "ReM"}
COMBOS = {"FULL_COMBO": "FC", "FULL_COMBO_PLUS": "FC+", "ALL_PERFECT": "AP", "ALL_PERFECT_PLUS": "AP+"}
GENRES = {
    "MAIMAI": "maimai 오리지널", "NICONICO_AND_VOCALOID": "니코니코&보컬로이드",
    "POPS_AND_ANIME": "팝&애니메", "TOUHOU_PROJECT": "동방Project",
    "GAME_AND_VARIETY": "게임&버라이어티", "ONGEKI_AND_CHUNITHM": "온게키&츄니즘",
}
# 달성률(x10000) 기준 랭크
RANKS = [(1005000, "SSS+"), (1000000, "SSS"), (995000, "SS+"), (990000, "SS"), (980000, "S+"),
         (970000, "S"), (940000, "AAA"), (900000, "AA"), (800000, "A"), (750000, "BBB"),
         (700000, "BB"), (600000, "B"), (500000, "C"), (0, "D")]
# 레이팅 색과 한마디
TIERS = [
    (15000, "무지개", "무지개 달성. 이제 걱정할 것은 손목과 지갑뿐."),
    (14500, "플래티넘", "무지개가 코앞입니다. 장갑은 챙기셨죠?"),
    (14000, "골드", "골드. 세탁기 앞에서 제일 빛나는 사람."),
    (13000, "실버", "MASTER가 슬슬 재미있어질 시기입니다."),
    (12000, "브론즈", "브론즈. 오락실 가는 길이 출근길처럼 익숙합니다."),
    (10000, "보라", "보라색 이름표. 이제 진짜 시작입니다."),
    (7000, "빨강", "EXPERT와 친해지는 중. 손바닥이 빨개질 때입니다."),
    (4000, "노랑", "버튼 위치를 손이 기억하기 시작했습니다."),
    (2000, "초록", "새싹입니다. 물 대신 100엔을 주세요."),
    (1000, "파랑", "어서 오세요. 세탁기는 돌리는 게 아니라 치는 겁니다."),
    (0, "하양", "어서 오세요. 세탁기는 처음이시죠?"),
]
HIGH_COMMENTS = [(16500, "사람이 맞는지 기계가 확인하고 싶어 합니다."),
                 (16000, "오락실 직원이 이름을 외웠을 실력입니다.")]


class MaimaiError(Exception):
    pass


# ---------------------------------------------------------------- 사이트 데이터 읽기

class TsrParser:
    """페이지에 박혀 있는 데이터(JS 리터럴의 작은 부분집합)를 읽는다. 코드를 실행하지 않는다."""

    REF = re.compile(r"\$R\[(\d+)\]")
    NUM = re.compile(r"-?\d+(\.\d+)?([eE][+-]?\d+)?")
    STR = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
    KEY = re.compile(r"[A-Za-z_$][\w$]*|\d+")

    def __init__(self, text, pos):
        self.t, self.i, self.refs = text, pos, {}

    def fail(self, what):
        raise MaimaiError(f"사이트 데이터 형식이 예상과 다릅니다 ({what}, 위치 {self.i}).")

    def value(self):
        t = self.t
        m = self.REF.match(t, self.i)
        if m:
            self.i = m.end()
            n = int(m.group(1))
            if t.startswith("=", self.i) and not t.startswith("==", self.i):
                self.i += 1
                self.refs[n] = self.value()
            return self.refs.get(n)
        c = t[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return self.string()
        for lit, val in (("!0", True), ("!1", False), ("null", None), ("void 0", None)):
            if t.startswith(lit, self.i):
                self.i += len(lit)
                return val
        if t.startswith("new Date(", self.i):
            self.i += len("new Date(")
            v = self.string()
            self.i += 1  # )
            return v
        m = self.NUM.match(t, self.i)
        if m:
            self.i = m.end()
            return float(m.group()) if re.search(r"[.eE]", m.group()) else int(m.group())
        self.fail("알 수 없는 값")

    def string(self):
        m = self.STR.match(self.t, self.i)
        if not m:
            self.fail("문자열")
        self.i = m.end()
        return json.loads(re.sub(r"\\x([0-9A-Fa-f]{2})", r"\\u00\1", m.group()), strict=False)

    def obj(self):
        self.i += 1
        out = {}
        while self.t[self.i] != "}":
            if self.t[self.i] == '"':
                key = self.string()
            else:
                m = self.KEY.match(self.t, self.i)
                if not m:
                    self.fail("키")
                key, self.i = m.group(), m.end()
            if self.t[self.i] != ":":
                self.fail("':'")
            self.i += 1
            out[key] = self.value()
            if self.t[self.i] == ",":
                self.i += 1
        self.i += 1
        return out

    def arr(self):
        self.i += 1
        out = []
        while self.t[self.i] != "]":
            if self.t[self.i] == ",":
                out.append(None)
                self.i += 1
                continue
            out.append(self.value())
            if self.t[self.i] == ",":
                self.i += 1
        self.i += 1
        return out


def extract_loader(html):
    """프로필 페이지 HTML에서 프로필 데이터 dict를 꺼낸다."""
    m = re.search(r'<script class="\$tsr"[^>]*>(.*?)</script>', html, re.S)
    hit = m and re.search(r'i:"\x00\{-\$locale\}\x00profile\x00\$handle\x00profile\x00[^"]*",u:\d+,s:"\w+",l:',
                          m.group(1))
    if not hit:
        raise MaimaiError("페이지에서 프로필 데이터를 찾지 못했습니다. 사이트 구조가 바뀐 것 같습니다.")
    try:
        return TsrParser(m.group(1), hit.end()).value()
    except IndexError:
        raise MaimaiError("사이트 데이터가 중간에 끊겼습니다.") from None


def clean_handle(text):
    """아이디, @아이디, 프로필 주소 어느 것이든 아이디만 남긴다."""
    text = text.strip()
    m = re.search(r"/profile/([^/?#]+)", text)
    handle = (m.group(1) if m else text).lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_.\-]{1,40}", handle):
        raise MaimaiError(f"'{text}'은(는) 아이디 형식이 아닙니다. 영문, 숫자, 밑줄(_)로 된 아이디를 입력해 주세요.")
    return handle


def fetch(handle):
    url = f"{SITE}/profile/{urllib.parse.quote(handle)}/home"
    req = urllib.request.Request(url, headers={"User-Agent": "receipt-printer-hobby-script/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise MaimaiError(f"아이디 '{handle}'을(를) 찾을 수 없습니다.") from None
        raise MaimaiError(f"사이트가 오류를 돌려줬습니다 (HTTP {e.code}).") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise MaimaiError(f"사이트에 연결하지 못했습니다 ({getattr(e, 'reason', e)}).") from None


def load_profile(handle, html):
    """HTML -> 영수증에 쓸 정보. 기록이 없거나 비공개면 MaimaiError."""
    data = extract_loader(html)
    record = (data or {}).get("userRecord")
    if not record or not record.get("profile"):
        raise MaimaiError(f"아이디 '{handle}'의 기록이 없거나 비공개입니다.")
    songs, tracks = record["tracks"]["songs"], record["tracks"]["tracks"]

    def entries(indices):
        out = []
        for i in indices or []:
            t = tracks[i]
            song, rec = songs[t["s"]], t.get("r") or {}
            out.append({
                "title": song["title"], "genre": song.get("genre"),
                "type": "DX" if song.get("type") == "DX" else "STD",
                "diff": DIFFS.get(t.get("d"), t.get("d") or "?"),
                "const": (t.get("l") or 0) / 10,
                "ach": rec.get("a") or 0,
                "rating": int(rec.get("g") or 0),
                "combo": COMBOS.get(rec.get("c")),
            })
        return out

    return {"handle": handle, "profile": record["profile"],
            "new": entries(record.get("ratingsLatest")), "old": entries(record.get("ratingsOld"))}


# ---------------------------------------------------------------- 영수증 만들기

def rank_of(ach):
    return next(name for floor, name in RANKS if ach >= floor)


def near_miss(entries):
    """다음 랭크까지 가장 조금 남은 곡 -> (곡, 다음 랭크, 남은 %) 또는 None"""
    best = None
    for e in entries:
        higher = [(floor, name) for floor, name in RANKS if floor > e["ach"]]
        if higher:
            floor, name = higher[-1]
            if best is None or floor - e["ach"] < best[2]:
                best = (e, name, floor - e["ach"])
    return best and (best[0], best[1], best[2] / 10000)


def kst_date(iso):
    try:
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (t + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
    except (AttributeError, ValueError):
        return "?"


def song_rows(entries):
    rows = []
    for e in entries:
        price = f"{e['rating']:,}"
        room = CONTENT_W - text_width(price, "body") * 2 - 24
        rows.append(raw("body", fit(e["title"], "body", room), right=price))
        detail = f"  {e['type']} {e['diff']} {e['const']:.1f} · {e['ach'] / 10000:.4f}% · {rank_of(e['ach'])}"
        rows.append(raw("small", detail + (f" · {e['combo']}" if e["combo"] else "")))
    return rows


def section(title, entries, top):
    if not entries:
        return [f"## {title}", "> 기록이 없습니다."]
    shown = entries if top is None else entries[:top]
    label = f"{len(entries)}곡" if len(shown) == len(entries) else f"{len(entries)}곡 중 상위 {len(shown)}곡"
    return ([f"## {title} ({label})"] + song_rows(shown)
            + [f"**{title} 소계 ({len(entries)}곡) || {sum(e['rating'] for e in entries):,}**"])


def build_sheet(info, top=3):
    p, new, old = info["profile"], info["new"], info["old"]
    both = new + old
    rating = p.get("rating") or 0
    plays = (p.get("playCount") or {}).get("total") or 0
    trophy = (p.get("trophy") or {}).get("title")
    course, klass = p.get("courseRank"), p.get("classRank")

    lines = [
        "^ @36b maimai 레이팅 영수증",
        raw("small", f"maishift · mai.sft.sh/{info['handle']}", align="center"),
        "---",
        raw("@48b", p.get("name") or info["handle"], align="center"),
    ]
    if trophy:
        lines.append(raw("small", f"「{trophy}」", align="center"))
    lines += [
        "---",
        raw("body", "단위", right=COURSE_RANKS[course] if isinstance(course, int) and 0 <= course < len(COURSE_RANKS) else "-"),
        raw("body", "CLASS", right=CLASS_RANKS[klass] if isinstance(klass, int) and 0 <= klass < len(CLASS_RANKS) else "-"),
        f"플레이 횟수 || {plays:,}회",
        f"투어 멤버 || ×{p.get('stars') or 0:,}",
        "---",
    ]
    lines += section("신곡", new, top) + [""] + section("구곡", old, top)

    floor, color, comment = next(t for t in TIERS if rating >= t[0])
    comment = next((c for r, c in HIGH_COMMENTS if rating >= r), comment)
    higher = [t for t in TIERS if t[0] > rating]
    goal = f"{higher[-1][1]}까지 {higher[-1][0] - rating:,}" if higher \
        else f"{(rating // 500 + 1) * 500:,}까지 {(rating // 500 + 1) * 500 - rating:,}"
    lines += [
        "---",
        f"@36b 합계 RATING || {rating:,}",
        f"> 레이팅 색: {color} · {goal}",
        "---",
    ]

    if both:
        genre, n = Counter(e["genre"] for e in both).most_common(1)[0]
        combos = Counter(e["combo"] for e in both)
        hardest = max(both, key=lambda e: e["const"])
        lines += [
            "[[손님 분석]]",
            f"> 레이팅 대상 {len(both)}곡 기준",
            raw("body", "단골 장르", right=f"{GENRES.get(genre, '기타')} {n}곡"),
            f"평균 달성률 || {sum(e['ach'] for e in both) / len(both) / 10000:.4f}%",
            f"AP · FC+ · FC || {combos['AP'] + combos['AP+']} · {combos['FC+']} · {combos['FC']}",
            f"최고 상수 || {hardest['const']:.1f}",
            raw("small", "  " + fit(hardest["title"], "small", CONTENT_W - 40)),
            "",
            "[[아깝다 상]]",
        ]
        miss = near_miss(both)
        if miss:
            e, name, gap = miss
            lines += [raw("body", fit(e["title"], "body", CONTENT_W)),
                      f"> {e['ach'] / 10000:.4f}% · {name}까지 단 {gap:.4f}%"]
        else:
            lines.append("> 해당 없음. 전부 SSS+ 입니다. 무섭네요.")
        lines.append("---")

    if plays:
        spent = plays * PRICE_PER_PLAY
        lines += [
            "[[결제 내역]]",
            f"{plays:,}판 × {PRICE_PER_PLAY:,}원 || {spent:,}원",
            f"레이팅 1점당 || 약 {spent / rating:,.0f}원" if rating else "레이팅 1점당 || 계산 불가",
            f"> 1판을 {PRICE_PER_PLAY:,}원으로 어림한 금액입니다. 실제와 다릅니다.",
            "---",
        ]

    lines += [
        raw("body", comment, align="center"),
        "---",
        f"^ > 기록 갱신 {kst_date(p.get('updatedAt'))} · 출력 {datetime.date.today().isoformat()}",
        "^ > 교환·환불 불가. 이미 친 곡은 되돌릴 수 없습니다.",
        "^ > 자료: maishift (maimai.shiftpsh.com)",
    ]
    return render(lines)


def main():
    ap = argparse.ArgumentParser(description="maishift 프로필을 레이팅 영수증으로 인쇄")
    ap.add_argument("handle", help="maishift 아이디 또는 프로필 주소")
    ap.add_argument("--top", type=int, default=3, help="신곡·구곡에서 각각 몇 곡씩 찍을지 (기본 3)")
    ap.add_argument("--all", action="store_true", help="레이팅 대상곡 전부 찍기")
    ap.add_argument("--html", metavar="파일", help="사이트 대신 저장해 둔 HTML 파일에서 읽기 (시험용)")
    add_output_args(ap)
    args = ap.parse_args()

    try:  # 여기서 실패하면 프린터에는 아무것도 보내지 않는다
        handle = clean_handle(args.handle)
        html = Path(args.html).read_text(encoding="utf-8") if args.html else fetch(handle)
        info = load_profile(handle, html)
        sheet = build_sheet(info, None if args.all else max(1, args.top))
    except MaimaiError as e:
        sys.exit(f"오류: {e} 인쇄하지 않았습니다.")
    except (KeyError, IndexError, TypeError) as e:
        sys.exit(f"오류: 사이트 데이터에 예상한 항목이 없습니다 ({e!r}). 인쇄하지 않았습니다.")

    p = info["profile"]
    print(f"{p.get('name')} (레이팅 {p.get('rating'):,}) -> " + output(sheet, "maimai", args, handle))


if __name__ == "__main__":
    main()
