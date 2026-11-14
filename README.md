# receipt-printer
영수증사진기? 명언랜덤뽑기? 뭐 그런거

## 프린터

CPP-3000 (80mm 감열, 203dpi, 가로 576도트). USB 가상 시리얼 `COM17`로 ESC/POS 명령을 직접 보낸다. 드라이버 설치 불필요.

## 폴더 구조

콘텐츠마다 폴더 하나. 스크립트와 그 스크립트가 만든 이미지가 같은 폴더에 들어간다.

```
main.py              허브 (메뉴에서 콘텐츠 골라 실행)
receipt.py           공용 모듈 (갈무리 글자 그리기, 이미지 저장, 프린터 전송)
text/
  print_text.py      텍스트 인쇄
  examples/          예시 텍스트
  output/            만든 이미지
sudoku/
  sudoku.py          스도쿠
  output/
loot/
  loot.py            TRPG 전리품 뽑기
  output/
maimai/
  maimai.py          maimai 레이팅 영수증 (maishift 프로필)
  output/
lotto/
  lotto.py           나름로또 (나름청소년활동센터 체험용 복권)
  output/
tarot/
  tarot.py           오늘의 타로 (도트 카드 그림 + 운세)
  output/
Galmuri-v2.40.4/     폰트
```

인쇄하든 `--preview`만 하든, 만든 이미지는 전부 `<콘텐츠>/output/`에 제작 일시로 저장된다. 덮어쓰지 않는다.

```
text/output/20261114_153012_sample.png
sudoku/output/20261114_153045_M482913.png
sudoku/output/20261114_153101_M482913_answer.png
loot/output/20261114_153130_482913.png
```

## 설치

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

아래 명령은 모두 프로젝트 폴더에서 실행한다.

## 허브 (main.py)

모든 콘텐츠를 한 곳에서 실행한다.

```powershell
.venv\Scripts\python main.py                        # 메뉴에서 골라 실행
.venv\Scripts\python main.py sudoku --level hard    # 이름 뒤에 그 콘텐츠의 옵션을 그대로 전달
.venv\Scripts\python main.py loot --loop
.venv\Scripts\python main.py text text/examples/sample.txt --preview
```

메뉴에서 `p`를 누르면 인쇄 모드와 미리보기 모드(종이 안 씀)가 바뀐다. 콘텐츠를 새로 만들면 `main.py`의 `CONTENTS`에 한 줄 추가한다.

## 텍스트 인쇄

갈무리 폰트로 글자를 그려서 이미지로 인쇄한다.

```powershell
.venv\Scripts\python text/print_text.py text/examples/sample.txt             # 인쇄
.venv\Scripts\python text/print_text.py text/examples/sample.txt --preview   # 종이 없이 이미지만 저장
.venv\Scripts\python text/print_text.py -t "# 제목" -t "본문 한 줄"
```

## 스도쿠

```powershell
.venv\Scripts\python sudoku/sudoku.py                    # 보통 난이도 한 판 인쇄
.venv\Scripts\python sudoku/sudoku.py --level hard       # easy | medium | hard
.venv\Scripts\python sudoku/sudoku.py --preview          # 종이 없이 이미지만 저장
.venv\Scripts\python sudoku/sudoku.py --answer M482913   # 영수증 아래 번호로 정답 인쇄
```

## 전리품 뽑기 (TRPG)

```powershell
.venv\Scripts\python loot/loot.py                 # 랜덤 아이템 감정서 한 장
.venv\Scripts\python loot/loot.py --loop          # Enter를 누를 때마다 한 장 (버튼 자판기 모드)
.venv\Scripts\python loot/loot.py --level 20      # 아이템 레벨 지정
.venv\Scripts\python loot/loot.py --seed 482913   # 같은 번호의 아이템 다시 뽑기
.venv\Scripts\python loot/loot.py --preview       # 종이 없이 이미지만 저장
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
.venv\Scripts\python lotto/lotto.py                               # 자동 5게임 한 장 (약 13cm)
.venv\Scripts\python lotto/lotto.py --games 3                     # 한 장에 3게임
.venv\Scripts\python lotto/lotto.py --sheets 5                    # 다섯 장 연속
.venv\Scripts\python lotto/lotto.py --manual "3 11 17 24 38 42"   # 수동 한 게임 + 나머지 자동
.venv\Scripts\python lotto/lotto.py --prize "문화상품권"           # 상품 칸에 찍을 글자 (없으면 손으로 적는 밑줄)
.venv\Scripts\python lotto/lotto.py --draw                        # 추첨 결과 용지
.venv\Scripts\python lotto/lotto.py --preview                     # 종이 없이 이미지만 저장
```

숫자 범위와 상품은 `lotto/lotto.py` 맨 위 설정(`NUMBER_MIN`, `NUMBER_MAX`, `PICKS`, `GAMES`, `PRIZE_TEXT`)에서 바꾼다.

## 오늘의 타로

메이저 아르카나 22장 중 한 장을 도트 카드 그림과 함께 뽑는다. 역방향이면 카드가 거꾸로 찍힌다. "카드 효과"는 게임 Balatro의 타로 효과를 일상 버전으로 바꾼 농담이다.

```powershell
.venv\Scripts\python tarot/tarot.py                 # 한 장 뽑기 (약 14cm)
.venv\Scripts\python tarot/tarot.py --loop          # Enter를 누를 때마다 한 장
.venv\Scripts\python tarot/tarot.py --seed 482913   # 같은 번호의 결과 다시 뽑기
.venv\Scripts\python tarot/tarot.py --card 16       # 카드 지정 (0~21), --reversed 로 역방향
.venv\Scripts\python tarot/tarot.py --preview       # 종이 없이 이미지만 저장
```

카드 그림은 `tarot/tarot.py`의 `art_*` 함수들이 71x95 도트로 그린다. 문구는 `CARDS` 표에서 고친다.

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
