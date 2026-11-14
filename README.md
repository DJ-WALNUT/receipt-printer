# receipt-printer
영수증사진기? 명언랜덤뽑기? 뭐 그런거

## 프린터

CPP-3000 (80mm 감열, 203dpi, 가로 576도트). USB 가상 시리얼 `COM17`로 ESC/POS 명령을 직접 보낸다. 드라이버 설치 불필요.

## 폴더 구조

메뉴와 같은 모양이다. 고전게임은 `games/`, 오늘의 운세는 `fortune/` 아래에 콘텐츠마다 폴더 하나씩 있고, 폴더 이름과 같은 스크립트(`games/sudoku/sudoku.py`), 설정 파일(`content.toml`), 그 스크립트가 만든 이미지(`output/`)가 함께 들어간다.

```
main.py              터미널 메뉴 (콘텐츠 골라 실행)
hub.py               허브 (콘텐츠 설정 파일을 읽고 입력값을 검사)
receipt.py           공용 모듈 (갈무리 글자 그리기, 이미지 저장, 프린터 전송)

text/                텍스트 인쇄 (print_text.py, examples/ 예시 텍스트)

games/               고전게임
  sudoku/            스도쿠                 ┐
  futoshiki/         부등호 스도쿠          │
  nonogram/          노노그램               │
  minesweeper/       지뢰찾기 퍼즐          │ 혼자 푸는 퍼즐
  maze/              미로찾기               │
  wordsearch/        낱말 찾기              │
  spot/              다른 그림 찾기         ┘
  omok/              오목판                 ┐
  dots/              점과 상자              │
  tictactoe/         틱택토                 │ 여럿이 하는 판
  bingo/             빙고                   │
  ladder/            사다리 타기            │
  hangman/           행맨                   ┘

fortune/             오늘의 운세
  loot/              전리품 뽑기 (TRPG)
  lotto/             나름로또 (나름청소년활동센터 체험용 복권)
  tarot/             오늘의 타로 (도트 카드 그림 + 운세)

maimai/              maimai 레이팅 영수증 (maishift 프로필)

Galmuri-v2.40.4/     폰트
docs/                작업 정리 문서
```

인쇄하든 `--preview`만 하든, 만든 이미지는 전부 그 콘텐츠 폴더의 `output/`에 제작 일시로 저장된다. 덮어쓰지 않는다.

```
text/output/20261114_153012_sample.png
games/sudoku/output/20261114_153045_SM482913.png
games/sudoku/output/20261114_153101_SM482913_answer.png
fortune/loot/output/20261114_153130_L482913.png
```

## 설치

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

아래 명령은 모두 프로젝트 폴더에서 실행한다.

### 다른 PC에서 쓰기

```powershell
git clone -b receipt-contents https://github.com/DJ-WALNUT/receipt-printer.git
cd receipt-printer
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py sudoku --preview    # 프린터 없이 이미지만 만들어 확인
```

- 프린터를 USB로 꽂고 장치 관리자의 "포트(COM & LPT)"에서 번호를 확인한다. PC마다 다르다.
- 기본 포트는 `COM17`이다. 다르면 한 번만 `setx RECEIPT_PORT COM5`처럼 환경 변수를 정해 두거나(터미널을 새로 열어야 적용), 실행할 때마다 `--port COM5`를 붙인다.
- 프린터가 없어도 `--preview`나 메뉴의 `p`(미리보기 모드)로 이미지는 만들 수 있다.
- Windows 기준으로 만들었다. 폰트는 저장소에 들어 있어 따로 설치하지 않는다.
- 테스트를 돌리려면 `.venv\Scripts\pip install -r requirements-dev.txt` 후 `.venv\Scripts\python -m pytest`.

## 허브 (main.py)

모든 콘텐츠를 한 곳에서 실행한다.

```powershell
.venv\Scripts\python main.py                        # 메뉴에서 골라 실행
.venv\Scripts\python main.py sudoku --level hard    # 이름 뒤에 그 콘텐츠의 옵션을 그대로 전달
.venv\Scripts\python main.py loot --loop
.venv\Scripts\python main.py text text/examples/sample.txt --preview
```

메뉴는 텍스트 인쇄, 고전게임(스도쿠·부등호 스도쿠·노노그램·지뢰찾기·미로찾기·낱말 찾기·다른 그림 찾기·오목판·점과 상자·틱택토·빙고·사다리 타기·행맨), 오늘의 운세(전리품 뽑기·나름로또·오늘의 타로), maimai 순서다. 묶음에 들어가면 `b`로 돌아온다.

- `p`를 누르면 인쇄 모드와 미리보기 모드(종이 안 씀)가 바뀐다.
- 콘텐츠를 고르면 옵션 다음에 몇 장 뽑을지 묻는다 (Enter = 1장, 최대 20장). 퍼즐과 뽑기는 장마다 다른 판이 나온다. 정답 인쇄처럼 한 장만 뽑는 메뉴에서는 묻지 않는다.
- Enter를 누를 때마다 한 장씩 뽑는 연속 뽑기는 메뉴에 없다. `python main.py loot --loop`처럼 직접 실행한다.
- 메뉴는 콘텐츠 폴더의 `content.toml`에서 만들어진다. 설정 파일에 문제가 있는 콘텐츠는 메뉴에서 빠지고, 시작할 때 이유가 한 줄로 나온다.

## 콘텐츠 추가하기

콘텐츠 하나는 폴더 하나다. 폴더에 스크립트와 `content.toml`을 두면 터미널 메뉴와 키오스크에 함께 나타난다. `main.py`나 다른 파일은 고치지 않는다.

1. `games/<이름>/<이름>.py`를 만든다 (묶음에 넣지 않으려면 맨 위에 `<이름>/<이름>.py`). 명령줄 옵션을 받아 한 장을 만들고 끝나는 프로그램이어야 하고, `receipt.add_output_args`로 `--preview`를 받아야 한다.
2. 같은 폴더에 `content.toml`을 쓴다. 가까운 콘텐츠의 것을 복사해 고치는 것이 빠르다.
3. `python main.py`로 메뉴에 나타나는지 보고, `p`(미리보기 모드)로 뽑아 본다.
4. `.venv\Scripts\python -m pytest`를 돌린다. 설정 파일의 모든 메뉴를 실제로 한 번씩 실행해 본다.

키오스크에 올리려면 `kiosk` 브랜치에서 `git merge receipt-contents` 한 뒤 올린다. 키오스크용 작업은 따로 없다.

### 콘텐츠 설정 파일 (content.toml)

```toml
title = "스도쿠"          # 메뉴에 보이는 이름 (필수)
order = 10                # 묶음 안에서의 순서 (기본 100)
seed_prefix = "S"         # 시드번호 맨 앞 글자. 시드번호가 있는 콘텐츠만. 다른 콘텐츠와 겹치면 오류
# kiosk = false           # 키오스크에 올리지 않을 때
# wait_between = 5        # 여러 장 뽑을 때 장 사이에 쉴 시간(초)
# script = "다른이름.py"   # 스크립트 이름이 폴더 이름과 다를 때

[[mode]]                  # 메뉴에서 번호로 고르는 갈래. 첫 번째가 기본
id = "new"
label = "새 판"
# audience = "staff"      # 운영자(터미널, 키오스크 관리자 화면)에게만 보일 때. 기본은 "all"
# sheets = false          # 항상 한 장만 뽑을 때
# args = ["--super"]      # 이 갈래에서 항상 붙는 옵션

[[mode.field]]            # 묻는 항목. 적힌 순서대로 묻는다
id = "level"
type = "choice"
label = "난이도"
arg = "--level"           # 스크립트 옵션 이름. ""이면 옵션 이름 없이 값만 넘긴다
choices = [["쉬움", "easy"], ["보통", "medium"], ["어려움", "hard"]]
default = "medium"
```

| type | 쓰는 키 | 설명 |
|---|---|---|
| `choice` | `choices`, `default` | 고르기. 값이 `""`인 선택지는 옵션을 붙이지 않는다 (예: 주제 무작위) |
| `number` | `min`, `max`, `default` | 정수. `default`가 없으면 비워 둘 수 있고, 비우면 옵션을 붙이지 않는다 |
| `text` | `pattern`, `max_length`(기본 40), `example`, `required`(기본 true) | 글자 입력. `pattern`은 전체가 맞아야 하는 정규식 |
| `names` | `min`, `max`(개수), `max_length`(이름 하나, 기본 8) | 이름 목록. 쉼표로 이어 넘긴다. 키오스크 방문자는 준비된 닉네임에서 고른다 |

- 항목에도 `audience = "staff"`를 붙일 수 있다. 방문자에게는 그 항목이 없는 것처럼 동작한다.
- 방문자가 글자를 직접 넣는 `text` 항목에는 반드시 `pattern`을 준다. 넣은 글자가 영수증에 찍히기 때문이다. `pattern`이 없으면 허브가 그 콘텐츠를 오류로 뺀다 (운영자만 쓰는 항목은 `audience = "staff"`).
- 표에 없는 키를 쓰면 오타로 보고 그 콘텐츠를 오류로 뺀다. `audience`를 잘못 적어 운영자 전용 메뉴가 방문자에게 열리는 일을 막기 위해서다.
- 묶음(`games/`, `fortune/`)의 제목과 순서는 그 폴더의 `group.toml`에 있다. 새 묶음은 폴더와 `group.toml`을 만들면 된다.

### 시드번호

같은 판을 다시 만들 수 있는 콘텐츠는 영수증에 시드번호를 찍는다. 맨 앞 글자가 콘텐츠마다 달라서 번호만 보고 어느 콘텐츠인지 알 수 있다.

| 콘텐츠 | 글자 | 예시 | 구성 |
|---|---|---|---|
| 스도쿠 | S | `SM482913` | 글자 + 난이도(E/M/H) + 숫자 6자리 |
| 부등호 스도쿠 | F | `FM482913` | 위와 같음 |
| 지뢰찾기 퍼즐 | M | `MM482913` | 위와 같음 |
| 미로찾기 | Z | `ZM482913` | 위와 같음 |
| 노노그램 | N | `NE03` | 글자 + 난이도(E/H) + 그림 번호 |
| 낱말 찾기 | W | `WM3482913` | 글자 + 난이도 + 주제 숫자 + 숫자 6자리 |
| 다른 그림 찾기 | D | `D5482913` | 글자 + 다른 곳 개수 + 숫자 6자리 |
| 전리품 뽑기 | L | `L482913` | 글자 + 숫자 6자리 |
| 오늘의 타로 | T | `T482913` | 글자 + 숫자 6자리 |

시드번호가 있는 콘텐츠를 새로 만들 때는 스크립트의 `SEED_PREFIX`와 `content.toml`의 `seed_prefix`에 아직 쓰지 않은 글자를 적는다. 겹치면 허브가 알려 준다.

## 텍스트 인쇄

갈무리 폰트로 글자를 그려서 이미지로 인쇄한다.

```powershell
.venv\Scripts\python text/print_text.py text/examples/sample.txt             # 인쇄
.venv\Scripts\python text/print_text.py text/examples/sample.txt --preview   # 종이 없이 이미지만 저장
.venv\Scripts\python text/print_text.py -t "# 제목" -t "본문 한 줄"
```

## 스도쿠

```powershell
.venv\Scripts\python games/sudoku/sudoku.py                    # 보통 난이도 한 판 인쇄
.venv\Scripts\python games/sudoku/sudoku.py --level hard       # easy | medium | hard
.venv\Scripts\python games/sudoku/sudoku.py --preview          # 종이 없이 이미지만 저장
.venv\Scripts\python games/sudoku/sudoku.py --answer SM482913   # 영수증의 시드번호로 정답 인쇄
```

## 미로찾기

길이 하나뿐인 미로. 왼쪽 위가 출발, 오른쪽 아래가 도착이고, 어려울수록 세로로 길어진다 (쉬움 12x12칸 약 10cm, 보통 16x22칸 약 13cm, 어려움 20x32칸 약 15cm).

```powershell
.venv\Scripts\python games/maze/maze.py                    # 보통 난이도 한 판 인쇄
.venv\Scripts\python games/maze/maze.py --level hard       # easy | medium | hard
.venv\Scripts\python games/maze/maze.py --preview          # 종이 없이 이미지만 저장
.venv\Scripts\python games/maze/maze.py --answer ZM482913   # 영수증의 시드번호로 정답 인쇄
```

칸 수와 칸 크기는 `games/maze/maze.py` 맨 위 `LEVELS`에서 바꾼다.

## 낱말 찾기

한글 글자판에 숨은 낱말을 찾는 퍼즐. 쉬움은 8x8칸에 6개(가로·세로만), 보통은 10x10칸에 8개(대각선 포함), 어려움은 12x14칸에 10개(거꾸로 포함)다. 어떤 낱말도 두 군데서 읽히지 않게 만든다.

```powershell
.venv\Scripts\python games/wordsearch/wordsearch.py                      # 보통 난이도, 주제 무작위 (약 11cm)
.venv\Scripts\python games/wordsearch/wordsearch.py --level hard         # easy | medium | hard
.venv\Scripts\python games/wordsearch/wordsearch.py --theme animal       # animal | food | fruit | school | space
.venv\Scripts\python games/wordsearch/wordsearch.py --words "나름,청소년,광명,동아리"   # 낱말 직접 지정
.venv\Scripts\python games/wordsearch/wordsearch.py --preview            # 종이 없이 이미지만 저장
.venv\Scripts\python games/wordsearch/wordsearch.py --answer WM3482913    # 영수증의 시드번호로 정답 인쇄
```

시드번호는 W + 난이도 글자 + 주제 숫자 + 여섯 자리 숫자다. 낱말을 직접 지정한 판(주제 숫자 0)의 정답은 `--answer WE0123456 --words "..."`처럼 같은 낱말을 다시 줘야 한다. 주제별 낱말은 `games/wordsearch/wordsearch.py`의 `THEMES`에서 고친다. 새 주제는 맨 뒤에 추가한다 (순서나 낱말을 바꾸면 예전 번호의 정답이 달라진다).

## 오목판

펜으로 돌을 그려 가며 두는 오목종이. 기본은 15x15줄(줄 간격 약 4.8mm)이고 화점이 찍힌다.

```powershell
.venv\Scripts\python games/omok/omok.py               # 15x15 한 장 (약 10cm)
.venv\Scripts\python games/omok/omok.py --size 13     # 가로세로 13줄 (9~19, 줄이 적을수록 칸이 커진다)
.venv\Scripts\python games/omok/omok.py --rows 25     # 세로만 25줄로 길게
.venv\Scripts\python games/omok/omok.py --sheets 3    # 세 장 연속
.venv\Scripts\python games/omok/omok.py --preview     # 종이 없이 이미지만 저장
```

## 노노그램

숫자 힌트대로 칸을 칠하면 도트 그림이 나온다. 쉬움은 10x10 그림 12종, 어려움은 전리품 뽑기의 16x16 아이콘 중 논리만으로 풀리는 4종이다.

```powershell
.venv\Scripts\python games/nonogram/nonogram.py                # 쉬움 한 판 (약 9cm)
.venv\Scripts\python games/nonogram/nonogram.py --level hard   # easy | hard
.venv\Scripts\python games/nonogram/nonogram.py --answer NE03   # 정답 그림 인쇄
.venv\Scripts\python games/nonogram/nonogram.py --list         # 시드번호와 그림 이름 보기
```

그림은 `games/nonogram/nonogram.py`의 `PICTURES`에 `#`과 `.`으로 그려 맨 뒤에 추가한다. 찍어야만 풀리는 그림은 자동으로 빠진다.

## 지뢰찾기 퍼즐

숫자를 보고 지뢰가 숨은 칸을 전부 찾는다. 쉬움 6x6(지뢰 6), 보통 7x7(지뢰 10), 어려움 8x8(지뢰 14). 정답은 하나뿐이다.

```powershell
.venv\Scripts\python games/minesweeper/minesweeper.py                    # 보통 한 판 (약 9cm)
.venv\Scripts\python games/minesweeper/minesweeper.py --level hard       # easy | medium | hard
.venv\Scripts\python games/minesweeper/minesweeper.py --answer MM482913   # 정답 인쇄
```

## 부등호 스도쿠

가로줄·세로줄에 1~N을 한 번씩 넣되 칸 사이 부등호를 지키는 퍼즐(후토시키). 쉬움 4x4, 보통 5x5, 어려움 6x6. 정답은 하나뿐이다. 어려움은 판을 만드는 데 몇 초 걸릴 수 있다.

```powershell
.venv\Scripts\python games/futoshiki/futoshiki.py                    # 보통 한 판 (약 9cm)
.venv\Scripts\python games/futoshiki/futoshiki.py --level hard       # easy | medium | hard
.venv\Scripts\python games/futoshiki/futoshiki.py --answer FM482913   # 정답 인쇄
```

## 다른 그림 찾기

타로 카드 도트 그림 두 장을 나란히 찍는다. 오른쪽 그림에 점이 생기거나 지워진 곳을 찾는다.

```powershell
.venv\Scripts\python games/spot/spot.py                    # 다른 곳 5군데 (약 6cm)
.venv\Scripts\python games/spot/spot.py --count 7          # 다른 곳 개수 (3~8)
.venv\Scripts\python games/spot/spot.py --answer D5482913   # 정답 인쇄 (다른 곳에 동그라미)
```

## 점과 상자

둘이서 점 사이에 선을 긋고 상자를 차지하는 놀이(땅따먹기) 판.

```powershell
.venv\Scripts\python games/dots/dots.py             # 가로세로 점 8개 (약 11cm)
.venv\Scripts\python games/dots/dots.py --size 6    # 점 수 (4~12)
.venv\Scripts\python games/dots/dots.py --rows 12   # 세로만 길게
```

## 틱택토

```powershell
.venv\Scripts\python games/tictactoe/tictactoe.py              # 3x3 판 6개 (약 13cm)
.venv\Scripts\python games/tictactoe/tictactoe.py --boards 10  # 판 개수 (2~12)
.venv\Scripts\python games/tictactoe/tictactoe.py --super      # 슈퍼 틱택토 (작은 판 9개를 엮은 큰 판)
```

## 빙고

실행할 때마다 숫자 배치가 다른 판이 나온다.

```powershell
.venv\Scripts\python games/bingo/bingo.py               # 5x5 판 (1~25, 약 9cm)
.venv\Scripts\python games/bingo/bingo.py --sheets 10   # 서로 다른 판 10장
.venv\Scripts\python games/bingo/bingo.py --size 4      # 칸 수 (3~7)
.venv\Scripts\python games/bingo/bingo.py --max 50      # 1~50 중에서 뽑아 채움
.venv\Scripts\python games/bingo/bingo.py --blank       # 빈 판 (직접 적는 용)
.venv\Scripts\python games/bingo/bingo.py --caller      # 진행자용 부를 순서 용지
```

## 사다리 타기

실행할 때마다 사다리가 달라진다. 결과는 화면에 보여 주지 않는다.

```powershell
.venv\Scripts\python games/ladder/ladder.py                              # 4명, 당첨 1개 (약 10cm)
.venv\Scripts\python games/ladder/ladder.py --players 6 --wins 2         # 인원 (2~8), 당첨 개수
.venv\Scripts\python games/ladder/ladder.py --names "민수,지아,하준"      # 이름을 찍는다
.venv\Scripts\python games/ladder/ladder.py --results "설거지,청소"       # 결과 지정 (모자라면 나머지는 '통과')
.venv\Scripts\python games/ladder/ladder.py --blank                      # 결과 칸을 비워 손으로 적기
```

## 행맨

교수대, 글자 칸, 지워 가며 쓰는 글자표가 찍힌 놀이판. 낱말은 출제자가 정한다. 한글판은 낱말을 자음·모음으로 풀어서 맞힌다.

```powershell
.venv\Scripts\python games/hangman/hangman.py              # 한글판 (약 13cm)
.venv\Scripts\python games/hangman/hangman.py --lang en    # 영어판
.venv\Scripts\python games/hangman/hangman.py --slots 14   # 글자 칸 개수 (4~20)
```

## 전리품 뽑기 (TRPG)

```powershell
.venv\Scripts\python fortune/loot/loot.py                 # 랜덤 아이템 감정서 한 장
.venv\Scripts\python fortune/loot/loot.py --loop          # Enter를 누를 때마다 한 장 (버튼 자판기 모드)
.venv\Scripts\python fortune/loot/loot.py --level 20      # 아이템 레벨 지정
.venv\Scripts\python fortune/loot/loot.py --seed L482913   # 같은 시드번호의 아이템 다시 뽑기
.venv\Scripts\python fortune/loot/loot.py --preview       # 종이 없이 이미지만 저장
```

## maimai 레이팅 영수증

[maishift](https://maimai.shiftpsh.com) 프로필을 읽어 레이팅 대상곡을 "구매 내역"처럼 찍는다. 한 번 실행에 사이트 요청은 한 번.

```powershell
.venv\Scripts\python maimai/maimai.py gupying             # 아이디로 한 장 (신곡·구곡 상위 3곡씩, 약 20cm)
.venv\Scripts\python maimai/maimai.py gupying --top 10    # 10곡씩
.venv\Scripts\python maimai/maimai.py gupying --all       # 레이팅 대상곡 전부 (아주 길다)
.venv\Scripts\python maimai/maimai.py gupying --preview   # 종이 없이 이미지만 저장
```

아이디가 없거나 비공개면 오류 메시지만 내고 인쇄하지 않는다. 사이트 구조가 바뀌면 `maimai.py`의 `extract_loader`를 고쳐야 한다.

## 나름로또

실제 로또 용지처럼 생긴 나름청소년활동센터 체험용 복권. 금액 대신 상품 칸이 있고, 실제 복권이 아니라는 문구가 함께 찍힌다.

```powershell
.venv\Scripts\python fortune/lotto/lotto.py                               # 자동 5게임 한 장 (약 13cm)
.venv\Scripts\python fortune/lotto/lotto.py --games 3                     # 한 장에 3게임
.venv\Scripts\python fortune/lotto/lotto.py --sheets 5                    # 다섯 장 연속
.venv\Scripts\python fortune/lotto/lotto.py --manual "3 11 17 24 38 42"   # 수동 한 게임 + 나머지 자동
.venv\Scripts\python fortune/lotto/lotto.py --prize "문화상품권"           # 상품 칸에 찍을 글자 (없으면 손으로 적는 밑줄)
.venv\Scripts\python fortune/lotto/lotto.py --draw                        # 추첨 결과 용지
.venv\Scripts\python fortune/lotto/lotto.py --preview                     # 종이 없이 이미지만 저장
```

숫자 범위와 상품은 `fortune/lotto/lotto.py` 맨 위 설정(`NUMBER_MIN`, `NUMBER_MAX`, `PICKS`, `GAMES`, `PRIZE_TEXT`)에서 바꾼다.

## 오늘의 타로

메이저 아르카나 22장 중 한 장을 도트 카드 그림과 함께 뽑는다. 역방향이면 카드가 거꾸로 찍힌다. "카드 효과"는 게임 Balatro의 타로 효과를 일상 버전으로 바꾼 농담이다.

```powershell
.venv\Scripts\python fortune/tarot/tarot.py                 # 한 장 뽑기 (약 14cm)
.venv\Scripts\python fortune/tarot/tarot.py --loop          # Enter를 누를 때마다 한 장
.venv\Scripts\python fortune/tarot/tarot.py --seed T482913   # 같은 시드번호의 결과 다시 뽑기
.venv\Scripts\python fortune/tarot/tarot.py --card 16       # 카드 지정 (0~21), --reversed 로 역방향
.venv\Scripts\python fortune/tarot/tarot.py --preview       # 종이 없이 이미지만 저장
```

카드 그림은 `fortune/tarot/tarot.py`의 `art_*` 함수들이 71x95 도트로 그린다. 문구는 `CARDS` 표에서 고친다.

## 텍스트 문법

| 문법 | 스타일 |
|---|---|
| `# 제목` | 큰 제목 (Galmuri11 Bold x4) |
| `## 소제목` | 소제목 (Galmuri14 x2) |
| `본문` | 본문 (Galmuri11 x2) |
| `**굵게**` | 굵은 본문 (Galmuri11 Bold x2) |
| `> 작은 글씨` | 작은 글씨 (Galmuri9 x2) |
| `[[반전]]` / `[[[큰 반전]]]` | 반전 라벨 (Bold x2 / x3) |
| `@36 텍스트` | 글자 높이를 도트로 지정: 16, 20, 24, 30, 36, 40, 45, 48, 60 (8도트 = 1mm) |
| `@36b 텍스트` | 굵게 지정: 24, 36, 48 |
| `---` | 구분선 |
| `^ ` 로 시작 | 가운데 정렬 |
| `왼쪽 \|\| 오른쪽` | 양쪽 정렬 |
