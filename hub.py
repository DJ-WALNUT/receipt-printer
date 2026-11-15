"""허브: 콘텐츠 폴더의 content.toml 을 읽고, 입력값을 검사해 스크립트 인자로 바꾼다.

터미널 메뉴(main.py)와 키오스크는 둘 다 이 모듈로만 콘텐츠를 안다.
콘텐츠를 새로 만들 때는 그 폴더에 스크립트와 content.toml 을 두면 된다. 다른 파일은 고치지 않는다.

    games/sudoku/sudoku.py        스크립트 (폴더 이름과 같은 이름)
    games/sudoku/content.toml     제목, 모드, 입력 항목
    games/group.toml              묶음 제목과 순서

content.toml 의 규칙은 README의 "콘텐츠 설정 파일" 절에 있다.
"""
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parent
VISITOR, STAFF = "visitor", "staff"
MAX_SHEETS = {VISITOR: 4, STAFF: 20}
COPIES_ARG = "--copies"   # 같은 이미지를 여러 장 인쇄하는 공통 옵션 (receipt.add_output_args)

FIELD_TYPES = ("choice", "number", "text", "names")
AUDIENCES = ("all", "staff")
SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", "tests"}
CONTROL = re.compile("[\x00-\x1f\x7f\x85  ]")   # 제어 문자와 줄 나눔 문자

# 설정 파일에 쓸 수 있는 키. 여기 없는 키는 오타로 보고 오류로 알린다.
# (audience 를 audiance 로 잘못 쓰면 운영자 전용이 방문자에게 열리기 때문에 조용히 넘기지 않는다.)
CONTENT_KEYS = {"title", "order", "kiosk", "wait_between", "script", "seed_prefix", "mode"}
MODE_KEYS = {"id", "label", "audience", "sheets", "same_sheets", "args", "field"}
FIELD_KEYS = {"id", "type", "label", "arg", "audience", "default", "choices", "min", "max",
              "pattern", "max_length", "example", "required"}
GROUP_KEYS = {"title", "order"}


class HubError(ValueError):
    """입력값이나 설정이 잘못됐다. str(e)는 사용자에게 그대로 보여줄 문장이다.

    field 는 어느 입력 항목 때문인지 (항목 id). 특정 항목 탓이 아니면 None.
    """

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


@dataclass(frozen=True)
class Field:
    id: str
    type: str
    label: str
    arg: str
    audience: str
    default: object
    choices: tuple
    min: int | None
    max: int | None
    pattern: str | None
    max_length: int
    example: str
    required: bool


@dataclass(frozen=True)
class Mode:
    id: str
    label: str
    audience: str
    sheets: bool
    same_sheets: bool
    args: tuple
    fields: tuple


@dataclass(frozen=True)
class Content:
    name: str
    title: str
    order: int
    group: str | None
    script: Path
    kiosk: bool
    wait_between: float
    seed_prefix: str | None
    modes: tuple


@dataclass(frozen=True)
class Group:
    name: str
    title: str
    order: int


@dataclass(frozen=True)
class Catalog:
    contents: dict
    groups: dict
    errors: tuple

    def menu(self):
        """메뉴 순서대로: 묶음 없는 콘텐츠는 Content, 묶음은 (Group, [Content, ...])."""
        top = [(c.order, c.name, c) for c in self.contents.values() if c.group is None]
        for g in self.groups.values():
            inside = sorted((c for c in self.contents.values() if c.group == g.name),
                            key=lambda c: (c.order, c.name))
            if inside:
                top.append((g.order, g.name, (g, inside)))
        return [item for _, _, item in sorted(top, key=lambda t: t[:2])]


# ---------------------------------------------------------------- 설정 파일 읽기

def _table(value, allowed, where):
    """설정의 한 덩어리가 표(dict)이고 아는 키만 담고 있는지 확인한다."""
    if not isinstance(value, dict):
        raise HubError(f"{where}: 표 모양이 아닙니다 ([[mode]] 나 [[mode.field]] 로 적어 주세요)")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise HubError(f"{where}: 모르는 키 {', '.join(unknown)} (오타인지 확인해 주세요)")
    return value


def _need(table, key, kind, where):
    if key not in table:
        raise HubError(f"{where}: '{key}'가 없습니다")
    return _typed(table, key, kind, where)


def _typed(table, key, kind, where, default=None):
    value = table.get(key, default)
    if value is None:
        return None
    if isinstance(value, bool) and kind is not bool or not isinstance(value, kind):
        raise HubError(f"{where}: '{key}'의 값이 올바르지 않습니다")
    return value


def _audience(table, where):
    value = table.get("audience", "all")
    if value not in AUDIENCES:
        raise HubError(f"{where}: audience는 \"all\" 또는 \"staff\"여야 합니다")
    return value


def _parse_field(table, where):
    _table(table, FIELD_KEYS, f"{where} 항목")
    fid = _need(table, "id", str, where)
    where = f"{where} 항목 '{fid}'"
    ftype = _need(table, "type", str, where)
    if ftype not in FIELD_TYPES:
        raise HubError(f"{where}: 모르는 type '{ftype}' (가능: {', '.join(FIELD_TYPES)})")
    label = _need(table, "label", str, where)
    arg = _need(table, "arg", str, where)
    default, choices, low, high, pattern = table.get("default"), (), None, None, None
    required = True

    if ftype == "choice":
        raw = _need(table, "choices", list, where)
        if not raw or not all(isinstance(c, list) and len(c) == 2 and all(isinstance(x, str) for x in c) for c in raw):
            raise HubError(f"{where}: choices는 [[\"표시\", \"값\"], ...] 모양이어야 합니다")
        choices = tuple((c[0], c[1]) for c in raw)
        if default not in [value for _, value in choices]:
            raise HubError(f"{where}: default가 choices 안에 없습니다")
    elif ftype in ("number", "names"):
        low, high = _need(table, "min", int, where), _need(table, "max", int, where)
        if low > high:
            raise HubError(f"{where}: min이 max보다 큽니다")
        if ftype == "number":
            required = False
            if default is not None and not (isinstance(default, int) and not isinstance(default, bool)
                                            and low <= default <= high):
                raise HubError(f"{where}: default가 min~max 범위의 정수가 아닙니다")
        else:
            default = None
    else:  # text
        default = None
        required = _typed(table, "required", bool, where, True)
        pattern = _typed(table, "pattern", str, where)
        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error as e:
                raise HubError(f"{where}: pattern이 올바른 정규식이 아닙니다 ({e})") from None

    max_length = _typed(table, "max_length", int, where, 8 if ftype == "names" else 40)
    return Field(fid, ftype, label, arg, _audience(table, where), default, choices, low, high, pattern,
                 max_length, _typed(table, "example", str, where, ""), required)


def _unique(items, what, where):
    seen = set()
    for item in items:
        if item.id in seen:
            raise HubError(f"{where}: {what} id '{item.id}'가 두 번 나옵니다")
        seen.add(item.id)


def _parse_mode(table, where):
    _table(table, MODE_KEYS, f"{where} 모드")
    mid = _need(table, "id", str, where)
    where = f"{where} 모드 '{mid}'"
    args = _typed(table, "args", list, where, [])
    if not all(isinstance(a, str) for a in args):
        raise HubError(f"{where}: args는 문자열 목록이어야 합니다")
    raw_fields = _typed(table, "field", list, where, [])
    fields = tuple(_parse_field(f, where) for f in raw_fields)
    _unique(fields, "항목", where)
    audience = _audience(table, where)
    for field in fields:
        # 방문자가 넣은 글자는 영수증에 그대로 찍힌다. 형식을 정하지 않은 칸을 방문자에게 열지 않는다.
        if field.type == "text" and field.pattern is None and "staff" not in (audience, field.audience):
            raise HubError(f"{where} 항목 '{field.id}': 방문자가 쓰는 글자 항목에는 pattern이 필요합니다 "
                           "(운영자만 쓰는 항목이면 audience = \"staff\")")
    sheets = _typed(table, "sheets", bool, where, True)
    same_sheets = _typed(table, "same_sheets", bool, where, False)
    if same_sheets and not sheets:
        raise HubError(f"{where}: same_sheets는 여러 장을 뽑는 모드에서만 쓸 수 있습니다")
    return Mode(mid, _need(table, "label", str, where), audience, sheets, same_sheets, tuple(args), fields)


def _read_toml(path):
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise HubError(f"TOML 문법 오류 ({e})") from None
    except OSError as e:
        raise HubError(f"파일을 읽을 수 없습니다 ({e})") from None


def _parse_content(path, group):
    table = _table(_read_toml(path), CONTENT_KEYS, "")
    folder = path.parent
    script = folder / _typed(table, "script", str, "", f"{folder.name}.py")
    if not script.is_file():
        raise HubError(f"스크립트 {script.name} 이(가) 없습니다")
    modes = tuple(_parse_mode(m, "") for m in _typed(table, "mode", list, "", []))
    _unique(modes, "모드", "")
    prefix = _typed(table, "seed_prefix", str, "")
    if prefix is not None and not re.fullmatch(r"[A-Z]", prefix):
        raise HubError("seed_prefix는 영문 대문자 한 글자여야 합니다")
    wait = table.get("wait_between", 0)
    if isinstance(wait, bool) or not isinstance(wait, (int, float)) or wait < 0:
        raise HubError("wait_between은 0 이상의 숫자여야 합니다")
    return Content(folder.name, _need(table, "title", str, ""), _typed(table, "order", int, "", 100), group,
                   script, _typed(table, "kiosk", bool, "", True), float(wait), prefix, modes)


def _folders(parent):
    return sorted(p for p in parent.iterdir()
                  if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_DIRS)


def load(root: Path = ROOT) -> Catalog:
    """root 아래의 콘텐츠를 모두 읽는다. 깨진 설정 파일은 빼고 errors에 이유를 남긴다."""
    root = Path(root)
    contents, groups, errors, prefixes = {}, {}, [], {}

    def add(path, group):
        shown = path.relative_to(root).as_posix()
        try:
            content = _parse_content(path, group)
            if content.name in contents:
                raise HubError(f"이름 '{content.name}'이(가) 다른 콘텐츠와 겹칩니다")
            owner = prefixes.get(content.seed_prefix)
            if content.seed_prefix and owner:
                raise HubError(f"시드 글자 '{content.seed_prefix}'는 {owner}가 이미 쓰고 있습니다")
        except HubError as e:
            errors.append(f"{shown}: {str(e).lstrip(' :')}")
            return
        contents[content.name] = content
        if content.seed_prefix:
            prefixes[content.seed_prefix] = content.name

    for folder in _folders(root):
        if (folder / "content.toml").is_file():
            add(folder / "content.toml", None)
        elif (folder / "group.toml").is_file():
            shown = (folder / "group.toml").relative_to(root).as_posix()
            try:
                table = _table(_read_toml(folder / "group.toml"), GROUP_KEYS, "")
                groups[folder.name] = Group(folder.name, _need(table, "title", str, ""),
                                            _typed(table, "order", int, "", 100))
            except HubError as e:
                errors.append(f"{shown}: {str(e).lstrip(' :')}")
                continue
            for sub in _folders(folder):
                if (sub / "content.toml").is_file():
                    add(sub / "content.toml", folder.name)
    return Catalog(contents, groups, tuple(errors))


def load_nicknames(path: Path) -> list:
    """한 줄에 하나씩 적힌 닉네임 목록. 빈 줄과 '#'으로 시작하는 줄은 건너뛴다."""
    path = Path(path)
    if not path.is_file():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


# ---------------------------------------------------------------- 입력값 검사

def _visible(item, role):
    return item.audience == "all" or role == STAFF


def _mode(content, mode_id, role):
    mode = next((m for m in content.modes if m.id == mode_id), None)
    if mode is None or not _visible(mode, role):
        raise HubError(f"'{content.title}'에 없는 메뉴예요.")
    return mode


def _clean_text(value, label, max_length):
    if not isinstance(value, str):
        raise HubError(f"{label}: 글자로 입력해 주세요.")
    value = value.strip()
    if CONTROL.search(value):
        raise HubError(f"{label}: 쓸 수 없는 글자가 들어 있어요.")
    if value.startswith("-"):
        raise HubError(f"{label}: '-'로 시작할 수 없어요.")
    if len(value) > max_length:
        raise HubError(f"{label}: {max_length}자까지 입력할 수 있어요.")
    return value


def _value(field, raw, role, nicknames):
    """항목 하나의 값을 검사해 인자에 넣을 문자열로 돌려준다. 붙이지 않을 값이면 None."""
    label = field.label
    if field.type == "choice":
        value = field.default if raw is None else raw
        if value not in [v for _, v in field.choices]:
            raise HubError(f"{label}: 고를 수 없는 값이에요.")
        return value or None

    if field.type == "number":
        if raw is None or raw == "":
            raw = field.default
        if raw is None:
            return None
        if isinstance(raw, str) and re.fullmatch(r"-?\d+", raw.strip()):
            raw = int(raw)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise HubError(f"{label}: 숫자를 입력해 주세요.")
        if not field.min <= raw <= field.max:
            raise HubError(f"{label}: {field.min}~{field.max} 사이여야 해요.")
        return str(raw)

    if field.type == "text":
        value = "" if raw is None else _clean_text(raw, label, field.max_length)
        if not value:
            if field.required:
                raise HubError(f"{label}: 입력해 주세요.")
            return None
        if field.pattern and not re.fullmatch(field.pattern, value, re.ASCII):  # \d 는 0-9 만
            hint = f" (예: {field.example})" if field.example else ""
            raise HubError(f"{label}: 형식이 맞지 않아요{hint}.")
        return value

    # names
    if not isinstance(raw, (list, tuple)):
        raise HubError(f"{label}: {field.min}~{field.max}개를 골라 주세요.")
    names = [_clean_text(n, label, field.max_length) for n in raw]
    if not field.min <= len(names) <= field.max:
        raise HubError(f"{label}: {field.min}~{field.max}개를 골라 주세요.")
    if any(not n or "," in n for n in names):
        raise HubError(f"{label}: 빈 이름이나 쉼표가 든 이름은 쓸 수 없어요.")
    if len(set(names)) != len(names):
        raise HubError(f"{label}: 같은 이름이 두 번 들어 있어요.")
    if role != STAFF and any(n not in nicknames for n in names):
        raise HubError(f"{label}: 목록에 있는 이름만 고를 수 있어요.")
    return ",".join(names)


def build_args(content: Content, mode_id: str, values: dict, role: str,
               nicknames: Sequence[str] = ()) -> list:
    """입력값을 검사해 스크립트에 넘길 인자 목록을 만든다. 잘못된 값이면 HubError."""
    mode = _mode(content, mode_id, role)
    if not isinstance(values, dict):
        raise HubError("입력값이 올바르지 않아요.")
    known = {f.id: f for f in mode.fields}
    for key in values:
        if key not in known or not _visible(known[key], role):
            raise HubError("입력할 수 없는 항목이 들어 있어요.")

    positional, options = [], []
    for field in mode.fields:
        if not _visible(field, role):
            continue  # 방문자에게 운영자 전용 항목은 없는 것과 같다 (기본값도 붙이지 않는다)
        try:
            value = _value(field, values.get(field.id), role, nicknames)
        except HubError as e:
            raise HubError(str(e), field.id) from None
        if value is None:
            continue
        if field.arg:
            options += [field.arg, value]
        else:
            positional.append(value)
    return positional + list(mode.args) + options


def check_sheets(mode: Mode, sheets, role: str) -> int:
    """몇 장 뽑을지 검사한다. 한 장만 뽑는 모드는 항상 1."""
    if not mode.sheets:
        return 1
    limit = MAX_SHEETS[role]
    if isinstance(sheets, bool) or not isinstance(sheets, int) or not 1 <= sheets <= limit:
        raise HubError(f"한 번에 1~{limit}장까지 뽑을 수 있어요.")
    return sheets


def check_same(mode: Mode, same) -> bool:
    """여러 장을 같은 문제로 뽑으라는 요청인지 검사한다. 그 모드가 받지 않으면 HubError.

    True 면 스크립트를 장마다 실행하지 않고, 한 번만 COPIES_ARG 와 장 수를 붙여 실행한다.
    """
    if same is None or same is False:
        return False
    if same is not True or not mode.same_sheets:
        raise HubError("같은 문제로 뽑을 수 없는 메뉴예요.")
    return True


# ---------------------------------------------------------------- 화면용 설명

def _describe_field(field, role, nicknames):
    out = {"id": field.id, "type": field.type, "label": field.label, "default": field.default,
           "choices": [list(c) for c in field.choices], "min": field.min, "max": field.max,
           "max_length": field.max_length, "example": field.example, "required": field.required}
    if field.type == "names" and role != STAFF:
        out["type"], out["options"] = "pick", list(nicknames)
    return out


def _describe_content(content, role, nicknames):
    modes = [{"id": m.id, "label": m.label, "sheets": m.sheets, "same_sheets": m.same_sheets,
              "fields": [_describe_field(f, role, nicknames) for f in m.fields if _visible(f, role)]}
             for m in content.modes if _visible(m, role)]
    return {"kind": "content", "name": content.name, "title": content.title, "modes": modes}


def describe(catalog: Catalog, role: str, nicknames: Sequence[str] = (), kiosk_only: bool = True) -> dict:
    """role에게 보이는 메뉴를 JSON으로 보낼 수 있는 dict로 만든다. 검사 규칙(pattern)은 담지 않는다."""
    def shown(content):
        if kiosk_only and not content.kiosk:
            return None
        described = _describe_content(content, role, nicknames)
        return described if described["modes"] or not kiosk_only else None

    menu = []
    for item in catalog.menu():
        if isinstance(item, Content):
            described = shown(item)
            if described:
                menu.append(described)
        else:
            group, inside = item
            items = [d for d in map(shown, inside) if d]
            if items:
                menu.append({"kind": "group", "name": group.name, "title": group.title, "items": items})
    return {"role": role, "max_sheets": MAX_SHEETS[role], "menu": menu}
