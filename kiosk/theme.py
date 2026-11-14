"""키오스크의 겉모습(theme.toml)을 읽어 CSS 변수로 바꾼다. 잘못된 값은 기본값으로 돌아간다."""
import re
import tomllib
from pathlib import Path

DEFAULT_NAME = "영수증 뽑기"
DEFAULT_COLORS = {
    "board": "#FFD400", "board_shade": "#F2C200", "accent": "#E4002B",
    "select": "#1E3A8A", "ink": "#1A1A1A", "paper": "#FFFFFF",
}
DEFAULT_FONTS = {
    "display": "'DNF Bit Bit v2', 'Jua', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
    "body": "'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif",
}
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
FONT = re.compile(r"[\w가-힣 ,'\"-]{1,200}")   # CSS를 깨뜨릴 수 있는 ; { } 등은 받지 않는다


def load_theme(path: Path) -> dict:
    """{"name": str, "colors": {...}, "fonts": {...}}. 파일이 없거나 깨졌으면 전부 기본값."""
    try:
        table = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        table = {}

    def pick(section, defaults, pattern):
        given = table.get(section) if isinstance(table.get(section), dict) else {}
        return {key: value if isinstance(value := given.get(key), str) and pattern.fullmatch(value) else default
                for key, default in defaults.items()}

    name = table.get("name")
    if not (isinstance(name, str) and 0 < len(name.strip()) <= 20):
        name = DEFAULT_NAME
    return {"name": name.strip(), "colors": pick("colors", DEFAULT_COLORS, COLOR),
            "fonts": pick("fonts", DEFAULT_FONTS, FONT)}


def theme_css(theme: dict) -> str:
    lines = [f"  --{key.replace('_', '-')}: {value};" for key, value in theme["colors"].items()]
    lines += [f"  --font-{key}: {value};" for key, value in theme["fonts"].items()]
    return ":root {\n" + "\n".join(lines) + "\n}\n"
