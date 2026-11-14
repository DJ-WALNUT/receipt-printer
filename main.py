"""영수증 프린터 허브: 모든 콘텐츠를 여기서 실행한다.

사용법 (프로젝트 폴더에서):
    python main.py                        # 메뉴에서 골라 실행
    python main.py sudoku --level hard    # 콘텐츠 이름 뒤에 그 스크립트의 옵션을 그대로 전달
    python main.py loot --loop
    python main.py text text/examples/sample.txt --preview
    python main.py maimai myshft_id

메뉴에서는 콘텐츠마다 몇 장 뽑을지 묻는다 (장마다 다른 판).
콘텐츠를 새로 만들면 아래 CONTENTS에 한 줄, 메뉴에 보이게 하려면 MENU에도 이름을 추가한다.
"""
import subprocess
import sys
import time
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
        number = ask("시드 번호 (예: M482913) > ")
        return ["--answer", number] if number else None
    level = {"1": "easy", "2": "medium", "3": "hard"}.get(choice)
    if not level:
        print("1~4 중에서 골라 주세요.")
        return None
    return ["--level", level]


def ask_maze():
    print("  1. 쉬움   2. 보통   3. 어려움   4. 정답 인쇄")
    choice = ask("선택 (기본 2) > ", "2")
    if choice == "4":
        number = ask("시드 번호 (예: M482913) > ")
        return ["--answer", number] if number else None
    level = {"1": "easy", "2": "medium", "3": "hard"}.get(choice)
    if not level:
        print("1~4 중에서 골라 주세요.")
        return None
    return ["--level", level]


def ask_wordsearch():
    print("  1. 쉬움   2. 보통   3. 어려움   4. 정답 인쇄")
    choice = ask("선택 (기본 2) > ", "2")
    if choice == "4":
        number = ask("시드 번호 (예: M3482913) > ")
        if not number:
            return None
        if number[1:2] == "0":  # 낱말을 직접 넣은 판은 같은 낱말이 있어야 정답을 만든다
            words = ask("그 판에 넣었던 낱말 (쉼표로 구분) > ")
            return ["--answer", number, "--words", words] if words else None
        return ["--answer", number]
    level = {"1": "easy", "2": "medium", "3": "hard"}.get(choice)
    if not level:
        print("1~4 중에서 골라 주세요.")
        return None
    themes = {"1": "animal", "2": "food", "3": "fruit", "4": "school", "5": "space"}
    print("  주제: 1. 동물   2. 음식   3. 과일   4. 학교   5. 우주   t. 낱말 직접 입력")
    theme = ask("주제 (Enter = 무작위) > ").lower()
    if theme == "t":
        words = ask("낱말 (쉼표로 구분) > ")
        return ["--level", level, "--words", words] if words else None
    return ["--level", level] + (["--theme", themes[theme]] if theme in themes else [])


def ask_levels(levels, example):
    """난이도 고르기 + 정답 인쇄 메뉴. levels: [(표시, --level 값)]"""
    answer = str(len(levels) + 1)
    print("  " + "   ".join(f"{i}. {label}" for i, (label, _) in enumerate(levels, 1)) + f"   {answer}. 정답 인쇄")
    default = str((len(levels) + 1) // 2)
    choice = ask(f"선택 (기본 {default}) > ", default)
    if choice == answer:
        number = ask(f"판 번호 (예: {example}) > ")
        return ["--answer", number] if number else None
    if not (choice.isdigit() and 1 <= int(choice) <= len(levels)):
        print(f"1~{answer} 중에서 골라 주세요.")
        return None
    return ["--level", levels[int(choice) - 1][1]]


def ask_nonogram():
    return ask_levels([("쉬움 10x10", "easy"), ("어려움 16x16", "hard")], "E03")


def ask_minesweeper():
    return ask_levels([("쉬움", "easy"), ("보통", "medium"), ("어려움", "hard")], "M482913")


def ask_futoshiki():
    return ask_levels([("쉬움 4x4", "easy"), ("보통 5x5", "medium"), ("어려움 6x6", "hard")], "M482913")


def ask_spot():
    print("  1. 새 판   2. 정답 인쇄")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "2":
        number = ask("시드 번호 (예: 5482913) > ")
        return ["--answer", number] if number else None
    if choice != "1":
        print("1~2 중에서 골라 주세요.")
        return None
    count = ask("다른 곳 개수 3~8 (Enter = 5) > ", "5")
    return ["--count", count] if count.isdigit() else None


def ask_dots():
    size = ask("가로 점 수 4~12 (Enter = 8) > ", "8")
    rows = ask("세로 점 수 (Enter = 가로와 같게) > ", size)
    if not (size.isdigit() and rows.isdigit()):
        print("숫자를 입력해 주세요.")
        return None
    return ["--size", size, "--rows", rows]


def ask_bingo():
    print("  1. 5x5 (1~25)   2. 칸 수·숫자 범위 정하기   3. 빈 판   4. 진행자용 부를 순서")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "1":
        return []
    if choice not in ("2", "3", "4"):
        print("1~4 중에서 골라 주세요.")
        return None
    args = []
    if choice != "4":
        size = ask("한 변 칸 수 3~7 (Enter = 5) > ", "5")
        if not size.isdigit():
            print("숫자를 입력해 주세요.")
            return None
        args += ["--size", size]
    if choice == "3":
        return args + ["--blank"]
    top = ask("가장 큰 숫자 (Enter = 칸 수만큼) > ")
    if top.isdigit():
        args += ["--max", top]
    return args + (["--caller"] if choice == "4" else [])


def ask_ladder():
    names = ask("이름들 (쉼표로 구분, Enter = 번호만) > ")
    if names:
        args = ["--names", names]
    else:
        players = ask("인원 2~8 (Enter = 4) > ", "4")
        if not players.isdigit():
            print("숫자를 입력해 주세요.")
            return None
        args = ["--players", players]
    print("  결과: Enter = 당첨 1개 + 꽝,  b = 빈칸(손으로 적기),  또는 결과를 쉼표로 구분해 입력")
    results = ask("결과 > ")
    if results.lower() == "b":
        return args + ["--blank"]
    return args + (["--results", results] if results else [])


def ask_tictactoe():
    print("  1. 3x3 판 6개   2. 판 개수 정하기   3. 슈퍼 틱택토")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "1":
        return []
    if choice == "3":
        return ["--super"]
    if choice != "2":
        print("1~3 중에서 골라 주세요.")
        return None
    boards = ask("판 개수 2~12 (Enter = 6) > ", "6")
    return ["--boards", boards] if boards.isdigit() else None


def ask_hangman():
    print("  1. 한글 (자음·모음)   2. 영어 (알파벳)")
    choice = ask("선택 (기본 1) > ", "1")
    if choice not in ("1", "2"):
        print("1~2 중에서 골라 주세요.")
        return None
    return ["--lang", "ko" if choice == "1" else "en"]


def ask_omok():
    print("  1. 15x15   2. 줄 수 정하기")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "1":
        return []
    if choice != "2":
        print("1~2 중에서 골라 주세요.")
        return None
    size = ask("가로 줄 수 9~19 (Enter = 15) > ", "15")
    rows = ask("세로 줄 수 (Enter = 가로와 같게) > ", size)
    if not (size.isdigit() and rows.isdigit()):
        print("숫자를 입력해 주세요.")
        return None
    return ["--size", size, "--rows", rows]


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
    print("  1. 자동 5게임   2. 게임 수 정하기   3. 추첨 결과 용지")
    choice = ask("선택 (기본 1) > ", "1")
    if choice == "1":
        return []
    if choice == "3":
        return ["--draw"]
    if choice != "2":
        print("1~3 중에서 골라 주세요.")
        return None
    games = ask("한 장에 몇 게임? (Enter = 5) > ", "5")
    if not (games.isdigit() and int(games) > 0):
        print("1 이상의 숫자를 입력해 주세요.")
        return None
    return ["--games", games]


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
    "sudoku": ("스도쿠",               "games/sudoku/sudoku.py",   ask_sudoku),
    "maze":   ("미로찾기",             "games/maze/maze.py",       ask_maze),
    "wordsearch": ("낱말 찾기",        "games/wordsearch/wordsearch.py", ask_wordsearch),
    "nonogram":    ("노노그램",        "games/nonogram/nonogram.py",       ask_nonogram),
    "minesweeper": ("지뢰찾기 퍼즐",   "games/minesweeper/minesweeper.py", ask_minesweeper),
    "futoshiki":   ("부등호 스도쿠",   "games/futoshiki/futoshiki.py",     ask_futoshiki),
    "spot":        ("다른 그림 찾기",  "games/spot/spot.py",               ask_spot),
    "dots":        ("점과 상자",       "games/dots/dots.py",               ask_dots),
    "bingo":       ("빙고",            "games/bingo/bingo.py",             ask_bingo),
    "ladder":      ("사다리 타기",     "games/ladder/ladder.py",           ask_ladder),
    "tictactoe":   ("틱택토",          "games/tictactoe/tictactoe.py",     ask_tictactoe),
    "hangman":     ("행맨",            "games/hangman/hangman.py",         ask_hangman),
    "omok":   ("오목판",               "games/omok/omok.py",       ask_omok),
    "loot":   ("전리품 뽑기 (TRPG)",   "fortune/loot/loot.py",       ask_loot),
    "maimai": ("maimai 레이팅 영수증", "maimai/maimai.py",   ask_maimai),
    "lotto":  ("나름로또",             "fortune/lotto/lotto.py",     ask_lotto),
    "tarot":  ("오늘의 타로",          "fortune/tarot/tarot.py",     ask_tarot),
}


def run(name, args):
    script = ROOT / CONTENTS[name][1]
    return subprocess.run([sys.executable, str(script), *args]).returncode


# 메뉴 구성. 콘텐츠 이름을 바로 적거나, (묶음 제목, [콘텐츠 이름들])로 묶는다.
MENU = [
    "text",
    ("고전게임", ["sudoku", "futoshiki", "nonogram", "minesweeper", "maze", "wordsearch", "spot",   # 혼자 푸는 퍼즐
                  "omok", "dots", "tictactoe", "bingo", "ladder", "hangman"]),                    # 여럿이 하는 판
    ("오늘의 운세", ["loot", "lotto", "tarot"]),
    "maimai",
]
MAX_SHEETS = 20
WAIT_BETWEEN = {"maimai": 5}  # 여러 장 뽑을 때 장 사이에 쉴 시간(초). maishift가 요청 간격 5초를 요구한다.


def ask_sheets():
    """몇 장 뽑을지. 잘못 입력하면 None."""
    count = ask(f"몇 장? (Enter = 1, 최대 {MAX_SHEETS}) > ", "1")
    if count.isdigit() and 1 <= int(count) <= MAX_SHEETS:
        return int(count)
    print(f"1~{MAX_SHEETS} 사이의 숫자를 입력해 주세요.")
    return None


def run_from_menu(name, preview):
    print(f"\n[{CONTENTS[name][0]}]")
    args = CONTENTS[name][2]()
    if args is None:
        return
    count = 1 if "--loop" in args else ask_sheets()  # 연속 뽑기는 Enter마다 한 장이라 묻지 않는다
    if count is None:
        return
    for i in range(count):  # 장마다 새로 실행하므로 퍼즐·뽑기는 장마다 다른 판이 나온다
        if i and name in WAIT_BETWEEN:
            time.sleep(WAIT_BETWEEN[name])
        if run(name, args + (["--preview"] if preview else [])) != 0:
            break


def menu():
    preview = False
    group = None  # 지금 들어가 있는 묶음 (제목, 이름들). 맨 위 메뉴면 None
    while True:
        items = group[1] if group else MENU
        print()
        print(f"=== {group[0] if group else '영수증 프린터'} ===")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {CONTENTS[item][0] if isinstance(item, str) else item[0] + ' >'}")
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
        if isinstance(item, str):
            run_from_menu(item, preview)
        else:
            group = item


def main():
    if len(sys.argv) == 1:
        return menu()
    name, args = sys.argv[1], sys.argv[2:]
    if name in ("-h", "--help") or name not in CONTENTS:
        print(__doc__)
        print("콘텐츠:")
        for key, (title, script, _) in CONTENTS.items():
            print(f"  {key:11} {title}  ({script})")
        sys.exit(0 if name in ("-h", "--help") else f"\n'{name}'은(는) 없는 콘텐츠입니다.")
    sys.exit(run(name, args))


if __name__ == "__main__":
    main()
