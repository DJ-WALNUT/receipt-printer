"""영수증 프린터 허브: 모든 콘텐츠를 여기서 실행한다.

사용법 (프로젝트 폴더에서):
    python main.py                        # 메뉴에서 골라 실행
    python main.py sudoku --level hard    # 콘텐츠 이름 뒤에 그 스크립트의 옵션을 그대로 전달
    python main.py loot --loop
    python main.py text text/examples/sample.txt --preview
    python main.py maimai myshft_id

콘텐츠를 새로 만들면 아래 CONTENTS에 한 줄 추가하면 메뉴와 명령 양쪽에 나타난다.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ask(prompt, default=""):
    try:
        return input(prompt).strip() or default
    except EOFError:
        return "q"


def ask_text():
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


def ask_sudoku():
    print("  1. 쉬움   2. 보통   3. 어려움   4. 정답 인쇄")
    choice = ask("선택 (기본 2) > ", "2")
    if choice == "4":
        number = ask("판 번호 (예: M482913) > ")
        return ["--answer", number] if number else None
    level = {"1": "easy", "2": "medium", "3": "hard"}.get(choice)
    if not level:
        print("1~4 중에서 골라 주세요.")
        return None
    return ["--level", level]


def ask_loot():
    print("  1. 한 장 뽑기   2. 연속 뽑기 (Enter마다 한 장)   3. 번호로 다시 뽑기")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "3":
        seed = ask("아이템 번호 > ")
        return ["--seed", seed] if seed else None
    if choice not in ("1", "2"):
        print("1~3 중에서 골라 주세요.")
        return None
    args = ["--loop"] if choice == "2" else []
    level = ask("아이템 레벨 (Enter = 무작위) > ")
    if level.isdigit():
        args += ["--level", level]
    return args


def ask_maimai():
    handle = ask("maishift 아이디 (또는 프로필 주소) > ")
    if not handle or handle == "q":
        return None
    top = ask("신곡·구곡 각각 몇 곡씩? (Enter = 3, a = 전부) > ", "3").lower()
    if top == "a":
        return [handle, "--all"]
    return [handle, "--top", top] if top.isdigit() and int(top) > 0 else [handle]


def ask_lotto():
    print("  1. 자동 5게임 한 장   2. 게임 수·장 수 정하기   3. 추첨 결과 용지")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "1":
        return []
    if choice == "3":
        return ["--draw"]
    if choice != "2":
        print("1~3 중에서 골라 주세요.")
        return None
    games = ask("한 장에 몇 게임? (Enter = 5) > ", "5")
    sheets = ask("몇 장? (Enter = 1) > ", "1")
    if not (games.isdigit() and sheets.isdigit() and int(games) > 0 and int(sheets) > 0):
        print("1 이상의 숫자를 입력해 주세요.")
        return None
    return ["--games", games, "--sheets", sheets]


def ask_tarot():
    print("  1. 한 장 뽑기   2. 연속 뽑기 (Enter마다 한 장)   3. 번호로 다시 뽑기")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "1":
        return []
    if choice == "2":
        return ["--loop"]
    if choice == "3":
        seed = ask("번호 > ")
        return ["--seed", seed] if seed else None
    print("1~3 중에서 골라 주세요.")
    return None


# 이름: (메뉴에 보일 제목, 스크립트 경로, 메뉴에서 옵션을 묻는 함수)
CONTENTS = {
    "text":   ("텍스트 인쇄",          "text/print_text.py", ask_text),
    "sudoku": ("스도쿠",               "sudoku/sudoku.py",   ask_sudoku),
    "loot":   ("전리품 뽑기 (TRPG)",   "loot/loot.py",       ask_loot),
    "maimai": ("maimai 레이팅 영수증", "maimai/maimai.py",   ask_maimai),
    "lotto":  ("나름로또",             "lotto/lotto.py",     ask_lotto),
    "tarot":  ("오늘의 타로",          "tarot/tarot.py",     ask_tarot),
}


def run(name, args):
    script = ROOT / CONTENTS[name][1]
    return subprocess.run([sys.executable, str(script), *args]).returncode


def menu():
    preview = False
    names = list(CONTENTS)
    while True:
        print()
        print("=== 영수증 프린터 ===")
        for i, name in enumerate(names, 1):
            print(f"  {i}. {CONTENTS[name][0]}")
        print(f"  p. 모드 전환 (현재: {'미리보기만 - 종이 안 씀' if preview else '인쇄'})")
        print("  q. 종료")
        choice = ask("선택 > ").lower()
        if choice == "q":
            return
        if choice == "p":
            preview = not preview
            continue
        if not (choice.isdigit() and 1 <= int(choice) <= len(names)):
            print("목록에 있는 번호나 글자를 입력해 주세요.")
            continue
        name = names[int(choice) - 1]
        print(f"\n[{CONTENTS[name][0]}]")
        args = CONTENTS[name][2]()
        if args is None:
            continue
        run(name, args + (["--preview"] if preview else []))


def main():
    if len(sys.argv) == 1:
        return menu()
    name, args = sys.argv[1], sys.argv[2:]
    if name in ("-h", "--help") or name not in CONTENTS:
        print(__doc__)
        print("콘텐츠:")
        for key, (title, script, _) in CONTENTS.items():
            print(f"  {key:8} {title}  ({script})")
        sys.exit(0 if name in ("-h", "--help") else f"\n'{name}'은(는) 없는 콘텐츠입니다.")
    sys.exit(run(name, args))


if __name__ == "__main__":
    main()
