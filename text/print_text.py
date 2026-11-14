"""텍스트 파일을 갈무리 폰트로 그려서 영수증 프린터로 인쇄한다.

사용법 (프로젝트 폴더에서):
    python text/print_text.py text/examples/sample.txt             # 파일 인쇄
    python text/print_text.py -t "# 제목" -t "본문"                 # 줄 단위로 직접 입력
    python text/print_text.py text/examples/sample.txt --preview   # 인쇄 없이 이미지만 저장

이미지는 text/output/ 에 저장된다. 줄 문법은 receipt.py 맨 위 설명 참고.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 공용 모듈 receipt.py
from receipt import add_output_args, output, render


def main():
    ap = argparse.ArgumentParser(description="갈무리 폰트로 영수증 프린터에 텍스트 인쇄")
    ap.add_argument("file", nargs="?", help="인쇄할 텍스트 파일 (UTF-8). 생략하면 표준 입력")
    ap.add_argument("-t", "--text", action="append", help="직접 입력할 줄 (여러 번 사용 가능)")
    add_output_args(ap)
    args = ap.parse_args()

    if args.text:
        lines = args.text
    elif args.file:
        lines = Path(args.file).read_text(encoding="utf-8-sig").splitlines()
    else:
        lines = sys.stdin.read().splitlines()

    tag = Path(args.file).stem if args.file and not args.text else ""
    print(output(render(lines), "text", args, tag))


if __name__ == "__main__":
    main()
