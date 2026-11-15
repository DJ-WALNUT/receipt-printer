"""공용 모듈: 갈무리 폰트로 글자를 그리고, 이미지를 저장하고, 영수증 프린터(CPP-3000)로 보낸다.

각 콘텐츠 폴더(text/, sudoku/, loot/)의 스크립트가 이 파일을 가져다 쓴다.
만든 이미지는 인쇄 여부와 상관없이 <콘텐츠>/output/연월일_시분초_이름.png 로 저장된다.

줄 문법 (한 줄에 스타일 하나):
    # 제목            큰 제목 (Galmuri11 Bold x4)
    ## 소제목         소제목 (Galmuri14 x2)
    본문              본문 (Galmuri11 x2, 내장 폰트와 같은 크기)
    **굵게**          굵은 본문 (Galmuri11 Bold x2)
    > 작은 글씨       작은 글씨 (Galmuri9 x2)
    [[반전]]          반전 라벨 (Galmuri11 Bold x2)
    [[[큰 반전]]]     큰 반전 라벨 (Galmuri11 Bold x3)
    @36 텍스트        글자 높이를 도트로 직접 지정 (16 20 24 30 36 40 45 48 60)
    @36b 텍스트       굵게 (24 36 48만 가능)
    ---               구분선
    (빈 줄)           여백
    ^ 로 시작         가운데 정렬 (예: "^ # 제목")
    왼쪽 || 오른쪽    양쪽 정렬 (예: "아메리카노 || 4,500")
"""
import argparse
import datetime
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).parent
FONT_DIR = ROOT / "Galmuri-v2.40.4"
PAPER_W = 576          # 72mm @ 203dpi
MARGIN = 8
CONTENT_W = PAPER_W - MARGIN * 2
LINE_GAP = 6
BLANK_H = 16

# (폰트 파일, 원래 픽셀 크기, 정수 배율, 반전 여부)
# 픽셀 폰트라 원래 크기로 그린 뒤 정수배로만 키워야 점이 깨끗하게 떨어진다.
# 반전은 감열지 번짐 때문에 Bold만 쓴다 (보통 굵기 x2는 뭉개져서 못 읽음).
STYLES = {
    "title":       ("Galmuri11-Bold.ttf", 12, 4, False),
    "heading":     ("Galmuri14.ttf",      15, 2, False),
    "body":        ("Galmuri11.ttf",      12, 2, False),
    "bold":        ("Galmuri11-Bold.ttf", 12, 2, False),
    "small":       ("Galmuri9.ttf",       10, 2, False),
    "reverse":     ("Galmuri11-Bold.ttf", 12, 2, True),
    "reverse_big": ("Galmuri11-Bold.ttf", 12, 3, True),
}
REVERSE_PAD = 2  # 반전 라벨 안쪽 여백 (원래 픽셀 기준)

# "@높이 텍스트"로 고를 수 있는 글자 높이(도트, 8도트 = 1mm).
# 픽셀 폰트는 정수배로만 키울 수 있어서, 폰트 4종 x 배율 조합이 곧 가능한 크기 전부다.
SIZES = {
    16: ("Galmuri7.ttf",   8, 2),
    20: ("Galmuri9.ttf",  10, 2),
    24: ("Galmuri11.ttf", 12, 2),
    30: ("Galmuri14.ttf", 15, 2),
    36: ("Galmuri11.ttf", 12, 3),
    40: ("Galmuri9.ttf",  10, 4),
    45: ("Galmuri14.ttf", 15, 3),
    48: ("Galmuri11.ttf", 12, 4),
    60: ("Galmuri14.ttf", 15, 4),
}
BOLD_SIZES = {24: 2, 36: 3, 48: 4}  # 굵은 글꼴은 Galmuri11에만 있다
SIZE_RE = re.compile(r"@(\d+)(b?) (.*)")


def size_style(height, bold):
    """'@36b' 같은 크기 지정을 STYLES에 등록하고 스타일 이름을 돌려준다."""
    name = f"@{height}{'b' if bold else ''}"
    if name not in STYLES:
        if bold and height in BOLD_SIZES:
            STYLES[name] = ("Galmuri11-Bold.ttf", 12, BOLD_SIZES[height], False)
        elif not bold and height in SIZES:
            STYLES[name] = SIZES[height] + (False,)
        else:
            ok = sorted(BOLD_SIZES) if bold else sorted(SIZES)
            sys.exit(f"'{name}'은 쓸 수 없는 크기입니다. 가능한 {'굵은 ' if bold else ''}크기: "
                     + ", ".join(map(str, ok)))
    return name

_fonts = {}


def get_font(style):
    file, px, _, _ = STYLES[style]
    if style not in _fonts:
        _fonts[style] = ImageFont.truetype(str(FONT_DIR / file), px)
    return _fonts[style]


# 글자가 없을 때 대신 쓰는 폰트. Galmuri11 보통 굵기가 글자가 가장 많다 (일본어 가나·한자 포함).
# Bold에는 일본어가 없어서, 굵은 줄에 일본어가 섞이면 그 글자만 보통 굵기로 나온다.
# 없는 파일은 건너뛴다. MS Gothic은 Windows, Unifont는 라즈베리파이(apt install fonts-unifont)용이다.
# Unifont는 16픽셀 비트맵 글꼴이라 정수 배로 키워도 점이 깨끗하다.
FALLBACKS = [
    (FONT_DIR / "Galmuri11.ttf", 12),
    (Path("C:/Windows/Fonts/msgothic.ttc"), 12),
    (Path("/usr/share/fonts/opentype/unifont/unifont.otf"), 16),
    (Path("/usr/share/fonts/truetype/unifont/unifont.ttf"), 16),
]
_fallback_fonts = None
_glyph_cache = {}


def _has_glyph(font, ch):
    """폰트에 이 글자가 있는지. 없는 글자는 전부 같은 '빈 네모'로 그려지는 것을 이용한다."""
    key = (id(font), ch)
    if key not in _glyph_cache:
        missing, mask = font.getmask("\uFFFE"), font.getmask(ch)
        _glyph_cache[key] = ch.isspace() or (mask.size, bytes(mask)) != (missing.size, bytes(missing))
    return _glyph_cache[key]


def split_runs(text, style):
    """텍스트를 (폰트, 문자열) 조각으로 나눈다. 기본 폰트에 없는 글자만 대체 폰트로 간다."""
    global _fallback_fonts
    if _fallback_fonts is None:
        _fallback_fonts = [ImageFont.truetype(str(p), px) for p, px in FALLBACKS if p.exists()]
    primary = get_font(style)
    runs = []
    for ch in text:
        font = primary
        if not _has_glyph(primary, ch):
            font = next((f for f in _fallback_fonts if _has_glyph(f, ch)), primary)
        if runs and runs[-1][0] is font:
            runs[-1][1] += ch
        else:
            runs.append([font, ch])
    return runs


def text_width(text, style):
    """원래 픽셀 크기 기준 폭 (확대 전)."""
    return sum(font.getlength(seg) for font, seg in split_runs(text, style))


def fit(text, style, max_px):
    """확대 후 폭이 max_px를 넘으면 끝을 잘라 '…'을 붙인다."""
    limit = max_px / STYLES[style][2]
    if text_width(text, style) <= limit:
        return text
    while text and text_width(text.rstrip() + "…", style) > limit:
        text = text[:-1]
    return text.rstrip() + "…"


def wrap(text, style, max_w):
    """폭을 넘으면 줄바꿈. 가능하면 공백에서 끊고, 없으면 글자 단위로 끊는다."""
    lines, cur = [], ""
    for ch in text:
        if text_width(cur + ch, style) <= max_w:
            cur += ch
            continue
        cut = cur.rfind(" ")
        if ch != " " and cut > 0:
            lines.append(cur[:cut])
            cur = cur[cut + 1:] + ch
        else:
            lines.append(cur)
            cur = "" if ch == " " else ch
    lines.append(cur)
    return [ln.rstrip() for ln in lines]


def draw_run(text, style):
    """한 줄을 원래 크기·안티앨리어싱 없이 그린 뒤 정수배 확대. 흰색=1, 검정=0."""
    _, _, scale, invert = STYLES[style]
    pad = REVERSE_PAD if invert else 0
    runs = split_runs(text, style)
    metrics = [get_font(style).getmetrics()] + [font.getmetrics() for font, _ in runs]
    ascent, descent = max(m[0] for m in metrics), max(m[1] for m in metrics)
    w = max(1, round(sum(font.getlength(seg) for font, seg in runs))) + pad * 2
    h = ascent + descent + pad * 2
    im = Image.new("1", (w, h), 0 if invert else 1)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    x = pad
    for font, seg in runs:  # 폰트가 달라도 글자 밑선(baseline)을 맞춘다
        d.text((round(x), pad + ascent), seg, font=font, fill=1 if invert else 0, anchor="ls")
        x += font.getlength(seg)
    return im.resize((w * scale, h * scale), Image.NEAREST)


def parse(line):
    """줄 -> (스타일, 텍스트, 정렬)"""
    align = "left"
    if line.startswith("^ "):
        align, line = "center", line[2:]
    s = line.strip()
    m = SIZE_RE.fullmatch(s)
    if m:
        return size_style(int(m.group(1)), bool(m.group(2))), m.group(3), align
    if s.startswith("## "):
        return "heading", s[3:], align
    if s.startswith("# "):
        return "title", s[2:], align
    if s.startswith("> "):
        return "small", s[2:], align
    if s.startswith("[[[") and s.endswith("]]]") and len(s) > 6:
        return "reverse_big", s[3:-3], align
    if s.startswith("[[") and s.endswith("]]") and len(s) > 4:
        return "reverse", s[2:-2], align
    if s.startswith("**") and s.endswith("**") and len(s) > 4:
        return "bold", s[2:-2], align
    return "body", line.rstrip(), align


def raw(style, text, right=None, align="left"):
    """문법 해석 없이 그대로 찍을 줄. 외부에서 가져온 글(곡 제목, 닉네임 등)에 쓴다.

    style은 STYLES의 이름("body", "small", "bold" ...)이나 "@36", "@24b" 같은 크기 지정.
    """
    if style.startswith("@"):
        style = size_style(int(style[1:].rstrip("b")), style.endswith("b"))
    return {"style": style, "text": text, "right": right, "align": align}


def render_line(line):
    """줄 하나 -> PAPER_W 폭의 행 이미지 목록. line은 문법이 있는 문자열이거나 raw()의 결과."""
    if isinstance(line, dict):
        style, text, right, align = line["style"], line["text"], line["right"], line["align"]
    else:
        if not line.strip():
            return [Image.new("1", (PAPER_W, BLANK_H), 1)]
        if line.strip() == "---":
            row = Image.new("1", (PAPER_W, 10), 1)
            ImageDraw.Draw(row).rectangle([MARGIN, 4, PAPER_W - MARGIN - 1, 5], fill=0)
            return [row]
        style, text, align = parse(line)
        right = None
        if " || " in text and not STYLES[style][3]:
            text, right = (p.strip() for p in text.split(" || ", 1))

    _, _, scale, invert = STYLES[style]
    max_w = CONTENT_W // scale - (REVERSE_PAD * 2 if invert else 0)
    rows = []

    def place(run, x):
        row = Image.new("1", (PAPER_W, run.height), 1)
        row.paste(run, (x, 0))
        return row

    if right is not None:
        left = text
        r_run = draw_run(right, style)
        left_lines = wrap(left, style, max_w - r_run.width // scale - 4)
        for i, ln in enumerate(left_lines):
            row = place(draw_run(ln, style), MARGIN)
            if i == len(left_lines) - 1:
                row.paste(r_run, (PAPER_W - MARGIN - r_run.width, 0))
            rows.append(row)
        return rows

    for ln in wrap(text, style, max_w):
        run = draw_run(ln, style)
        x = (PAPER_W - run.width) // 2 if align == "center" else MARGIN
        rows.append(place(run, x))
    return rows


def render(lines):
    rows = [row for line in lines for row in render_line(line)]
    height = sum(r.height + LINE_GAP for r in rows) + LINE_GAP
    sheet = Image.new("1", (PAPER_W, height), 1)
    y = LINE_GAP
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + LINE_GAP
    return sheet


def stack(*images):
    """PAPER_W 폭 이미지들을 위에서 아래로 이어 붙인다."""
    sheet = Image.new("1", (PAPER_W, sum(i.height for i in images)), 1)
    y = 0
    for i in images:
        sheet.paste(i, (0, y))
        y += i.height
    return sheet


def send(sheet, port, cut=True):
    """1비트 이미지를 ESC/POS 래스터(GS v 0)로 전송."""
    import serial

    raster = ImageChops.invert(sheet.convert("L")).convert("1").tobytes()  # 1 = 검은 점
    wb = PAPER_W // 8
    for attempt in range(3):  # 포트가 가끔 첫 시도에 안 열린다
        try:
            s = serial.Serial(port, 38400, timeout=2, write_timeout=10)
            break
        except serial.SerialException:
            if attempt == 2:
                raise
            time.sleep(0.5)
    with s:
        s.write(b"\x1b@")
        band = 64
        for y in range(0, sheet.height, band):
            n = min(band, sheet.height - y)
            s.write(b"\x1dv0\x00" + bytes([wb & 255, wb >> 8, n & 255, n >> 8])
                    + raster[y * wb:(y + n) * wb])
            s.flush()
            time.sleep(0.05)
        s.write(b"\x1bd\x04")
        if cut:
            s.write(b"\x1dVB\x00")
        s.flush()


def save_output(sheet, content, tag=""):
    """<콘텐츠>/output/<연월일_시분초>[_태그].png 로 저장하고 경로를 돌려준다. 덮어쓰지 않는다."""
    folder = ROOT / content / "output"
    folder.mkdir(parents=True, exist_ok=True)
    stem = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + (f"_{tag}" if tag else "")
    path = folder / f"{stem}.png"
    n = 2
    while path.exists():  # 같은 초에 여러 장 만들 때
        path = folder / f"{stem}_{n}.png"
        n += 1
    sheet.save(path)
    return path


def strip_seed(text, prefix, ap, example):
    """시드번호 맨 앞의 콘텐츠 글자를 떼고 나머지를 돌려준다. 글자가 다르면 사용법 오류로 끝낸다.

    시드번호는 콘텐츠마다 다른 글자로 시작한다 (스도쿠 S, 타로 T ...). 대소문자는 가리지 않는다.
    """
    text = text.strip()
    if text[:1].upper() != prefix:
        ap.error(f"시드번호는 {prefix}로 시작합니다 (예: {example})")
    return text[1:]


MAX_COPIES = 20


def _copies(text):
    """--copies 의 값. 1~MAX_COPIES 의 정수가 아니면 사용법 오류가 된다."""
    if not text.isdigit() or not 1 <= int(text) <= MAX_COPIES:
        raise argparse.ArgumentTypeError(f"1~{MAX_COPIES} 사이의 숫자여야 합니다")
    return int(text)


def add_output_args(ap):
    # 다른 PC에서는 포트 번호가 다르다. 환경 변수 RECEIPT_PORT로 기본값을 바꿀 수 있다.
    ap.add_argument("--port", default=os.environ.get("RECEIPT_PORT", "COM17"),
                    help="프린터 시리얼 포트 (기본: 환경 변수 RECEIPT_PORT, 없으면 COM17)")
    ap.add_argument("--preview", action="store_true", help="인쇄하지 않고 이미지만 저장")
    ap.add_argument("--no-cut", action="store_true", help="인쇄 후 자르지 않음")
    ap.add_argument("--copies", type=_copies, default=1, metavar="장수",
                    help=f"같은 이미지를 여러 장 인쇄 (1~{MAX_COPIES})")


def output(sheet, content, args, tag=""):
    """이미지를 항상 저장하고, --preview가 아니면 인쇄까지 한다. 결과 설명 문자열을 돌려준다.

    --copies 가 2 이상이면 같은 이미지를 그만큼 인쇄한다 (이미지는 한 번만 저장한다).
    """
    path = save_output(sheet, content, tag)
    shown = path.relative_to(ROOT)
    mm = sheet.height / 8
    copies = getattr(args, "copies", 1)
    same = f" · 같은 것 {copies}장" if copies > 1 else ""
    if args.preview:
        return f"미리보기 저장: {shown} (약 {mm:.0f}mm){same}"
    for _ in range(copies):
        send(sheet, args.port, cut=not args.no_cut)
    return f"인쇄 전송 완료: {args.port} (약 {mm:.0f}mm), 이미지: {shown}{same}"
