"""영수증 프린터 허브: 모든 콘텐츠를 여기서 실행한다.

사용법 (프로젝트 폴더에서):
    python main.py                        # 메뉴에서 골라 실행
    python main.py sudoku --level hard    # 콘텐츠 이름 뒤에 그 스크립트의 옵션을 그대로 전달
    python main.py loot --loop
    python main.py text text/examples/sample.txt --preview
    python main.py maimai myshft_id

메뉴는 콘텐츠 폴더마다 있는 content.toml 에서 만들어진다 (hub.py 가 읽는다).
콘텐츠를 새로 만들면 그 폴더에 content.toml 을 두면 된다. 이 파일은 고치지 않는다.
"""
import subprocess
import sys
import time
from pathlib import Path

import hub

ROOT = Path(__file__).resolve().parent
MAX_SHEETS = hub.MAX_SHEETS[hub.STAFF]


def ask(prompt, default=""):
    try:
        return input(prompt).strip() or default
    except EOFError:
        return "q"


def ask_text(content=None):
    """인쇄할 텍스트 고르기 -> print_text.py 인자"""
    files = sorted((ROOT / "text" / "examples").glob("*.txt"))
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    print("  t. 직접 입력")
    choice = ask("파일 번호, 파일 경로, 또는 t > ")
    if choice.lower() == "t":
        print("한 줄씩 입력하세요. 빈 줄을 입력하면 끝납니다. (문법: # 제목, > 작게, [[반전]] ...)")
        lines = []
        while (line := ask("  ")) not in ("", "q"):
            lines.append(line)
        return [arg for line in lines for arg in ("-t", line)] if lines else None
    if choice.isdigit() and 1 <= int(choice) <= len(files):
        return [str(files[int(choice) - 1])]
    if choice and Path(choice).is_file():
        return [choice]
    print("그런 파일이 없습니다.")
    return None


# content.toml 로 표현하기 어려운 질문(파일 고르기, 여러 줄 입력)만 손으로 쓴다.
CUSTOM_ASK = {"text": ask_text}


def pick(options, default=1):
    """번호 목록에서 하나 고르기. options: 표시 문자열들. 고른 순번(0부터)이나 None."""
    print("  " + "   ".join(f"{i}. {label}" for i, label in enumerate(options, 1)))
    choice = ask(f"선택 (기본 {default}) > ", str(default))
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return int(choice) - 1
    print(f"1~{len(options)} 중에서 골라 주세요.")
    return None


def ask_field(field):
    """항목 하나를 묻는다. (값,)을 돌려주고, 그만두려면 None. 값이 None이면 '입력 안 함'."""
    if field.type == "choice":
        default = [value for _, value in field.choices].index(field.default) + 1
        print(f"  {field.label}:")
        i = pick([label for label, _ in field.choices], default)
        return None if i is None else (field.choices[i][1],)
    if field.type == "number":
        fallback = field.default if field.default is not None else "자동"
        return (ask(f"{field.label} {field.min}~{field.max} (Enter = {fallback}) > ") or None,)
    if field.type == "names":
        typed = ask(f"{field.label} {field.min}~{field.max}명 (쉼표로 구분) > ")
        return None if typed in ("", "q") else ([n.strip() for n in typed.split(",") if n.strip()],)
    hint = f" (예: {field.example})" if field.example else ""
    typed = ask(f"{field.label}{hint}{'' if field.required else ' (Enter = 건너뜀)'} > ")
    if field.required and typed in ("", "q"):
        return None
    return (typed or None,)


def ask_content(content):
    """콘텐츠의 모드와 항목을 차례로 묻는다. (스크립트 인자, 고른 모드)를 돌려주고, 그만두면 None."""
    modes = content.modes
    index = 0 if len(modes) == 1 else pick([m.label for m in modes])
    if index is None:
        return None
    mode = modes[index]
    values = {}
    for field in mode.fields:
        answer = ask_field(field)
        if answer is None:
            return None
        if answer[0] is not None:
            values[field.id] = answer[0]
    try:
        return hub.build_args(content, mode.id, values, hub.STAFF), mode
    except hub.HubError as e:
        print(e)
        return None


def run(content, args):
    return subprocess.run([sys.executable, str(content.script), *args]).returncode


def ask_sheets():
    """몇 장 뽑을지. 잘못 입력하면 None."""
    count = ask(f"몇 장? (Enter = 1, 최대 {MAX_SHEETS}) > ", "1")
    if count.isdigit() and 1 <= int(count) <= MAX_SHEETS:
        return int(count)
    print(f"1~{MAX_SHEETS} 사이의 숫자를 입력해 주세요.")
    return None


def run_from_menu(content, preview):
    print(f"\n[{content.title}]")
    if content.name in CUSTOM_ASK:
        args, sheets = CUSTOM_ASK[content.name](content), True
    else:
        asked = ask_content(content)
        args, sheets = (asked[0], asked[1].sheets) if asked else (None, False)
    if args is None:
        return
    count = ask_sheets() if sheets else 1
    if count is None:
        return
    for i in range(count):  # 장마다 새로 실행하므로 퍼즐·뽑기는 장마다 다른 판이 나온다
        if i and content.wait_between:
            time.sleep(content.wait_between)
        if run(content, args + (["--preview"] if preview else [])) != 0:
            break


def menu():
    catalog = hub.load()
    for error in catalog.errors:
        print(f"설정 오류로 뺀 콘텐츠 - {error}")
    top = catalog.menu()
    preview = False
    group = None  # 지금 들어가 있는 묶음 (Group, [Content, ...]). 맨 위 메뉴면 None
    while True:
        items = group[1] if group else top
        print()
        print(f"=== {group[0].title if group else '영수증 프린터'} ===")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item.title if isinstance(item, hub.Content) else item[0].title + ' >'}")
        print(f"  p. 모드 전환 (현재: {'미리보기만 - 종이 안 씀' if preview else '인쇄'})")
        print("  b. 뒤로" if group else "  q. 종료")
        choice = ask("선택 > ").lower()
        if choice == "q":
            return
        if choice == "b" and group:
            group = None
            continue
        if choice == "p":
            preview = not preview
            continue
        if not (choice.isdigit() and 1 <= int(choice) <= len(items)):
            print("목록에 있는 번호나 글자를 입력해 주세요.")
            continue
        item = items[int(choice) - 1]
        if isinstance(item, hub.Content):
            run_from_menu(item, preview)
        else:
            group = item


def main():
    if len(sys.argv) == 1:
        return menu()
    name, args = sys.argv[1], sys.argv[2:]
    contents = hub.load().contents
    if name in ("-h", "--help") or name not in contents:
        print(__doc__)
        print("콘텐츠:")
        for key, content in contents.items():
            print(f"  {key:11} {content.title}  ({content.script.relative_to(ROOT).as_posix()})")
        sys.exit(0 if name in ("-h", "--help") else f"\n'{name}'은(는) 없는 콘텐츠입니다.")
    sys.exit(run(contents[name], args))


if __name__ == "__main__":
    main()
