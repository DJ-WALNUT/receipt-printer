"""지난 이력 지우기: 이용실적 기록(kiosk/data/usage.csv)과 만들어진 영수증 이미지(<콘텐츠>/output/*.png).

테스트하며 쌓인 기록을 정식 운영 전에 비울 때 쓴다. 되돌릴 수 없다.

    python -m kiosk.reset                 # 둘 다 지운다 (몇 개 지울지 보여 주고 확인을 받는다)
    python -m kiosk.reset --only usage    # 이용실적만
    python -m kiosk.reset --only images   # 이미지만
    python -m kiosk.reset --yes           # 확인 없이 바로 (스크립트에서 쓸 때)

키오스크 서버가 켜져 있어도 된다. 다음 인쇄부터 기록이 새로 쌓인다.
"""
import argparse
import sys
from pathlib import Path

import hub
from kiosk.server import USAGE_PATH, cleanup_outputs, output_images


def count_usage(path: Path) -> int:
    """기록 줄 수 (머리줄 제외). 파일이 없으면 0."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return 0
    return max(0, len([line for line in lines if line.strip()]) - 1)


def main(argv=None, root: Path = hub.ROOT, usage_path: Path = USAGE_PATH, ask=input) -> int:
    ap = argparse.ArgumentParser(prog="python -m kiosk.reset", description="이용실적 기록과 만들어진 이미지를 지운다")
    ap.add_argument("--only", choices=["usage", "images"], help="한쪽만 지운다 (기본: 둘 다)")
    ap.add_argument("--yes", action="store_true", help="확인을 묻지 않는다")
    args = ap.parse_args(argv)
    usage = args.only in (None, "usage")
    images = args.only in (None, "images")

    rows = count_usage(usage_path) if usage else 0
    pictures = len(output_images(root)) if images else 0
    plan = []
    if usage:
        plan.append(f"이용실적 기록 {rows}건 ({usage_path})")
    if images:
        plan.append(f"영수증 이미지 {pictures}개 (콘텐츠마다 output/ 폴더)")
    print("지울 것:\n  - " + "\n  - ".join(plan))
    if rows == 0 and pictures == 0:
        print("지울 것이 없습니다.")
        return 0
    if not args.yes:
        try:
            answer = ask("정말 지울까요? 되돌릴 수 없습니다. [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes", "ㅛ"):
            print("그만두었습니다.")
            return 1

    if usage and usage_path.exists():
        usage_path.unlink()
    removed = cleanup_outputs(root, 0) if images else 0
    print(f"지웠습니다: 이용실적 {rows}건, 이미지 {removed}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
