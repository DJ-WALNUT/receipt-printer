---
version: 1
slug: "kiosk-static-index-html"
primary_target: "kiosk/static/index.html"
related_targets: ["kiosk/static/app.js","kiosk/static/style.css"]
---

# 키오스크 화면 (kiosk/static)

- 범위: 방문자와 관리자가 쓰는 키오스크 화면 전체. 모드: Operate.
- 사람과 일: 센터에 온 청소년이 가로로 거치된 아이패드에서 콘텐츠를 고르고, 옵션을 정하고, 뽑기를 누른다. 관리자는 같은 화면에서 비밀번호로 들어가 여러 장을 뽑는다.
- 내용: 서버의 /api/catalog 가 주는 메뉴만으로 그린다. 콘텐츠 이름으로 갈라지는 코드는 없다.
- 제약: 터치 전용, 오래된 iPad WebKit에서도 동작, 빌드 없음, 겉모습(이름·색·글꼴)은 kiosk/theme.toml 한 곳에서 바꾼다.
- 고른 방향: 문방구 뽑기판 (사용자가 방향 고르기 페이지에서 직접 골랐다).
- 기억에 남을 순간: 뽑기를 누르면 그 칸이 뜯긴 칸으로 바뀌고 종이가 나온다.
- 미정: 키오스크 이름 (기본값 "영수증 뽑기", theme.toml에서 바꾼다).

## Direction contract

THESIS: 화면은 문방구 앞 종이 뽑기판이다. 번호가 적힌 칸을 하나 골라 뜯으면 종이가 나온다. 흰 카드가 떠 있는 보통의 주문 키오스크 배치를 거부하고, 칸이 절취선으로 맞붙은 한 장의 판을 쓴다.

OWN-WORLD: 원색 마분지. 노란 판(#FFD400) 바탕, 빨간 머리띠와 뽑기 버튼(#E4002B), 고른 칸은 남색(#1E3A8A), 흰 칸, 먹색(#1A1A1A) 굵은 테두리와 점선 절취선. 제목과 칸 번호는 통통한 주아체, 나머지는 시스템 고딕. 모서리는 알약 탭과 둥근 버튼, 칸 격자는 직각. 그림자는 쓰지 않는다.

STORY: 방문자는 판에서 칸 하나를 누르고, 오른쪽에서 난이도와 장 수를 정하고, 빨간 뽑기 버튼을 누른다. 그 칸이 뜯긴 칸이 되고 몇 장째인지 보이며, 다 나오면 가져가라는 안내와 함께 처음으로 돌아간다.

FIRST VIEWPORT: 1024x768 가로. 위에 80px 빨간 머리띠(왼쪽 이름, 오른쪽 상태 알약). 그 아래 왼쪽 약 64%에 알약 탭 줄과 3열 번호 칸 격자, 오른쪽 372px 흰 패널에 고른 칸의 이름, 옵션, 장 수, 92px 높이 빨간 뽑기 버튼. 맨 아래 64px 먹색 띠에 지금 뜯는 중인 작업.

FORM: 문방구 뽑기판, 내 목록 1순위 (IMPECCABLE'S PICK 카드를 사용자가 고름). seed:c011f6f158616f98

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
