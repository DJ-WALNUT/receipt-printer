---
name: 영수증 뽑기 키오스크
description: 문방구 앞 종이 뽑기판처럼 생긴, 영수증 프린터용 터치 키오스크 화면
colors:
  board: "#FFD400"
  board-shade: "#F2C200"
  accent: "#E4002B"
  select: "#1E3A8A"
  ink: "#1A1A1A"
  paper: "#FFFFFF"
  torn-ink: "#4d3c00"
  hint: "#5c5c5c"
  danger: "#b00020"
typography:
  display:
    fontFamily: "'DNF Bit Bit v2', 'Jua', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "3.25rem"
    fontWeight: 400
    lineHeight: 1.05
  action:
    fontFamily: "'DNF Bit Bit v2', 'Jua', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "2.75rem"
    fontWeight: 400
    lineHeight: 1
  headline:
    fontFamily: "'DNF Bit Bit v2', 'Jua', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "2.625rem"
    fontWeight: 400
    lineHeight: 1
  title:
    fontFamily: "'DNF Bit Bit v2', 'Jua', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "2.25rem"
    fontWeight: 400
    lineHeight: 1.1
  numeral:
    fontFamily: "'DNF Bit Bit v2', 'Jua', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "1.875rem"
    fontWeight: 400
    lineHeight: 1
    fontFeature: "tabular-nums"
  cell:
    fontFamily: "'Tuktakpotato', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"
    fontSize: "1.3125rem"
    fontWeight: 700
    lineHeight: 1.2
  control:
    fontFamily: "'Tuktakpotato', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.15
  body:
    fontFamily: "'Tuktakpotato', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "'Tuktakpotato', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.3
  hint:
    fontFamily: "'Tuktakpotato', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  none: "0"
  control: "0.75rem"
  go: "1rem"
  sheetbox: "1.25rem"
  pill: "999px"
spacing:
  xs: "0.375rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.25rem"
  gutter: "1.5rem"
components:
  bar:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    typography: "{typography.headline}"
    height: "5rem"
    padding: "0 1.5rem"
  pill:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "2.75rem"
    padding: "0 1rem"
  pill-staff:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.board}"
    rounded: "{rounded.pill}"
  pill-trouble:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
  tab:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    height: "3rem"
    padding: "0 1.25rem"
  tab-selected:
    backgroundColor: "{colors.select}"
    textColor: "{colors.paper}"
  tile:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.cell}"
    rounded: "{rounded.none}"
    height: "5.5rem"
    padding: "0.5rem 0.75rem 0.5rem 0.875rem"
  tile-active:
    backgroundColor: "{colors.board-shade}"
  tile-selected:
    backgroundColor: "{colors.select}"
    textColor: "{colors.paper}"
  tile-torn:
    backgroundColor: "{colors.board}"
    textColor: "{colors.torn-ink}"
  choice:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    height: "3.75rem"
    padding: "0.375rem 0.5rem"
  choice-selected:
    backgroundColor: "{colors.board}"
  segment:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    height: "3rem"
    padding: "0.25rem 0.5rem"
  segment-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  stepper-button:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    size: "3.75rem"
  textbox:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "3.75rem"
    padding: "0 1rem"
  go:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    typography: "{typography.action}"
    rounded: "{rounded.go}"
    height: "5.75rem"
    width: "100%"
  go-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  go-disabled:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.hint}"
  plain:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "3.5rem"
    width: "100%"
  plain-danger:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.danger}"
    rounded: "{rounded.control}"
  key:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "4.25rem"
  key-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
  notice:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.danger}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.75rem 1rem"
  strip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    height: "4rem"
    padding: "0.5rem 1.5rem"
  sheetbox:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheetbox}"
    padding: "1.5rem"
    width: "26rem"
---

# Design System: 영수증 뽑기 키오스크

## Overview

**Creative North Star: "문방구 뽑기판"**

화면은 문방구 앞에 걸려 있던 종이 뽑기판이다. 번호가 적힌 흰 칸들이 점선 절취선으로 맞붙어 한 장의 판을 이루고, 칸 하나를 골라 빨간 버튼을 누르면 그 칸이 뜯겨 노란 바탕이 드러나며 프린터에서 종이가 나온다. 재료는 원색 마분지다. 노란 판, 빨간 머리띠, 남색으로 칠한 고른 칸, 먹색의 굵은 테두리. 그림자도 그라데이션 광택도 없고, 깊이는 색면과 선의 굵기로만 말한다.

서서 팔을 뻗어 누르고, 서너 명이 한 걸음 떨어져서 함께 보는 화면이다. 그래서 글자는 크고 굵으며(본문 기본이 700), 누르는 대상은 최소 2.75rem, 주된 것은 3.75rem 이상이다. 터치 전용이라 호버 상태는 없고, 눌린 순간(`:active`)과 고른 상태만 있다. 색과 글꼴과 이름은 `kiosk/theme.toml` 한 곳에서 바꾸며, 화면 코드는 색 값을 직접 쓰지 않고 변수만 쓴다.

**Key Characteristics:**
- 떠 있는 카드가 아니라, 절취선으로 맞붙은 한 장의 판.
- 원색 네 가지(노랑, 빨강, 남색, 먹)와 흰색. 색마다 맡은 일이 하나씩이다.
- 3px 먹색 테두리. 실선은 가장자리, 점선은 뜯는 자리.
- 도톰한 픽셀 글꼴인 던파 비트비트체는 이름, 번호, 뽑기 버튼에만. 나머지는 시스템 고딕.
- 그림자 없음. 호버 없음. 움직임은 뜯기는 순간 하나.

## Colors

원색 마분지 팔레트다. 여섯 색은 `kiosk/theme.toml`에서 오고(`--board`, `--board-shade`, `--accent`, `--select`, `--ink`, `--paper`), 세 색은 `style.css`에 고정되어 있다(`--torn-ink`, `--hint`, `--danger`).

### Primary
- **뽑기 빨강** (`accent`): 머리띠, 뽑기 버튼, 비밀번호 확인 키의 바탕. 흰 글자가 올라간다. 글자색으로는 칸 번호와 탭의 개수에만 쓴다.

### Secondary
- **고른 칸 남색** (`select`): 판에서 고른 칸과 고른 탭의 바탕, 다 나온 종이 조각, 포커스 외곽선, 글자 선택 색. 흰 글자가 올라간다.

### Tertiary
- **판 노랑** (`board`): 화면 전체의 바탕. 패널에서 고른 옵션 버튼, 지금 나오는 종이 조각, 먹색 위의 강조 글자(아래 띠의 상태 말, 관리자 알약)에도 쓴다.
- **줄무늬 노랑** (`board-shade`): 뜯긴 칸의 135도 줄무늬(10px 간격)와, 흰 버튼이 눌린 순간의 바탕.

### Neutral
- **먹** (`ink`): 글자, 모든 테두리와 절취선, 아래 띠의 바탕, 맞붙은 고르기 줄에서 고른 것의 바탕.
- **흰 종이** (`paper`): 칸, 패널, 버튼, 입력칸, 덮개 상자의 바탕. 빨강, 남색, 먹 위의 글자.
- **뜯긴 칸 글자** (`torn-ink`): 줄무늬 노랑 위에 올라가는 글자와 번호.
- **보조 글자 회색** (`hint`): 흰 바탕 위의 도움말, 자리표시 글자, 못 누르는 버튼의 글자와 테두리.
- **경고 빨강** (`danger`): 잘못된 입력칸의 테두리, 알림 상자, 대기열을 지우는 버튼. 뽑기 빨강과 다른 색이며 서로 바꿔 쓰지 않는다.

덮개 뒤의 가림막은 먹색의 72% (`rgba(26, 26, 26, 0.72)`)다.

### Named Rules
**색마다 한 가지 일 규칙.** 빨강은 뽑는 일, 남색은 판에서 고른 것, 노랑은 판 바탕과 패널에서 고른 옵션, 먹은 선과 글자다. 빨강을 고른 상태에 쓰거나 남색을 버튼 바탕에 쓰지 않는다.

**변수만 쓰기 규칙.** 화면 코드는 색 값을 직접 쓰지 않고 `var(--…)`만 쓴다. 센터가 `theme.toml`을 고치면 화면 전체가 따라와야 한다.

**글자로도 알리기 규칙.** 상태는 색만으로 알리지 않는다. 뜯는 중, 실패, 연결 끊김은 알약과 아래 띠의 글자로도 말한다.

## Typography

**Display Font:** DNF Bit Bit v2 (대체: Jua, Apple SD Gothic Neo, Malgun Gothic, sans-serif). `kiosk/static/fonts/DNFBitBitv2.ttf`를 직접 내려준다. 이 파일이 없으면 함께 들어 있는 Jua(`Jua-Regular.ttf`)로 보인다.
**Body Font:** 뚝딱감자체 (Tuktakpotato; 대체: Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif). `kiosk/static/fonts/Tuktakpotato.ttf`를 직접 내려준다. 굵기가 하나뿐이라 모든 굵기에 같은 파일을 쓴다. 글자 몸통이 고딕보다 작아서, 2026-11-14에 본문 크기를 전부 0.125rem씩(칸 이름은 1.5rem으로) 키웠다. 아래 크기 목록은 고딕 기준 값이므로 실제 값은 `kiosk/static/style.css`를 따른다. 가운뎃점(·)은 이 글꼴에 없어 기기 고딕으로 나온다.

**Character:** 통통하고 둥근 던파 비트비트체가 간판과 번호를 맡고, 굵은 시스템 고딕이 나머지 전부를 맡는다. 던파 비트비트체는 굵기가 하나(400)뿐이며, 고딕은 700이 기본이고 400은 설명글에만 쓴다.

### Hierarchy
- **Display** (DNF Bit Bit v2 400, 3.25rem, 1.05): 뽑는 중과 다 나왔을 때 패널의 큰 말.
- **Action** (DNF Bit Bit v2 400, 2.75rem, 1): 뽑기 버튼의 글자.
- **Headline** (DNF Bit Bit v2 400, 2.625rem, 1): 머리띠의 키오스크 이름.
- **Title** (DNF Bit Bit v2 400, 2.25rem, 1.1): 패널 제목. 덮개 상자의 제목은 2rem.
- **Numeral** (DNF Bit Bit v2 400, 1.875rem, 1, tabular-nums): 칸 번호. 안내 순서의 번호는 1.75rem, 종이 조각의 번호는 1.5rem.
- **Cell** (고딕 700, 1.3125rem, 1.2): 칸의 콘텐츠 이름. 아래 띠의 글자도 같은 크기다.
- **Control** (고딕 700, 1.25rem, 1.15): 탭, 옵션 버튼, 안내 순서. 입력칸은 1.375rem, 숫자 값은 1.5rem, 비밀번호 키는 1.75rem.
- **Body** (고딕 400, 1.1875rem, 1.45): 패널의 설명글.
- **Label** (고딕 700, 1.0625rem, 1.3): 옵션의 이름표, 머리띠 버튼, 맞붙은 고르기 줄, 알림.
- **Hint** (고딕 400, 1rem, 1.3): 입력칸 아래 도움말. 가장 작은 글자다.

### Named Rules
**던파 비트비트체는 간판과 번호 규칙.** 던파 비트비트체는 키오스크 이름, 제목, 번호, 뽑기 버튼에만 쓴다. 옵션, 설명, 알림은 고딕이다.

**단어에서 끊지 않기 규칙.** 줄이 바뀌는 한국어 글자는 `word-break: keep-all`로 어절 단위로만 끊는다.

**1rem 바닥 규칙.** 1rem보다 작은 글자는 없다. 한 걸음 떨어져서 읽는 화면이다.

## Layout

화면은 스크롤되지 않는 세 줄이다. 위에 머리띠(최소 5rem), 가운데에 본문, 아래에 먹색 띠(최소 4rem). 본문은 왼쪽의 판(남는 너비 전부)과 오른쪽의 흰 패널(23.25rem 고정)로 나뉘고, 판과 패널은 각자 안에서만 스크롤된다. 띠와 본문, 판과 패널 사이의 경계는 6px 먹색 실선이다.

판은 알약 탭 한 줄과 3열 격자다. 칸은 사이 간격 없이 맞붙고 최소 높이 5.5rem이다. 마지막 줄의 빈자리는 흰 빈칸으로 채워 판이 늘 사각형이 되게 한다. 패널은 위에서부터 제목, 옵션을 0.75rem 간격으로 쌓고, 뽑기 버튼 묶음은 `margin-top: auto`로 바닥에 붙인다. 옵션 버튼끼리의 간격은 0.5rem, 판과 패널의 안쪽 여백은 1.25rem과 1.5rem이다.

크기는 전부 rem이고, 화면 크기에 따라 `html`의 글자 크기만 바꾼다. 기준은 1024x768 가로의 16px. 1150x800 이상은 17.5px, 1300x950 이상은 21px, 높이 700px 이하 가로는 14px, 너비 600px 이하 세로는 11px. 세로로 세우면 판이 위(최대 62%), 패널이 아래로 가고, 뽑기 버튼 묶음은 패널 바닥에 붙어 따라온다. 노치와 홈 막대 자리는 `env(safe-area-inset-*)`로 비운다.

### Named Rules
**오래된 아이패드 규칙.** `clamp()`, `:has()`, flex `gap`, `inset`, `aspect-ratio`는 쓰지 않는다. 간격은 margin과 `grid-gap`으로, 크기 변화는 미디어 쿼리로 만든다.

**손가락 크기 규칙.** 누르는 대상의 최소 높이는 2.75rem이다. 방문자가 누르는 것은 3rem 이상, 뽑기 버튼은 5.75rem이다.

## Elevation & Depth

그림자를 쓰지 않는다. `box-shadow`는 어디에도 없다. 깊이는 색면이 맞닿는 것으로 만든다. 노란 판 위에 흰 칸, 그 옆에 6px 먹선으로 갈린 흰 패널, 위아래의 빨간 띠와 먹색 띠. 유일하게 다른 것 위에 올라가는 것은 덮개 상자(관리자 비밀번호, 대기열)이며, 이것도 그림자 없이 먹색 72% 가림막과 4px 테두리로 떠 있음을 알린다.

### Named Rules
**마분지 규칙.** 면은 납작하다. 그림자, 그라데이션 광택, 흐림 효과로 깊이를 만들지 않는다. 뜯긴 칸의 줄무늬가 유일한 그라데이션이고, 그것은 무늬다.

## Shapes

테두리는 3px 먹색(`--line`)이 기본이다. 가장 중요한 두 가지인 뽑기 버튼과 덮개 상자는 4px, 화면을 나누는 구조선은 6px이다.

선의 모양에 뜻이 있다. 실선은 가장자리이고 점선은 절취선이다. 판 안쪽에서 칸과 칸이 만나는 선은 점선, 판의 바깥 가장자리는 실선이다. 아직 나오지 않은 종이 조각, 못 누르는 버튼, 목록의 줄 사이도 점선이다. 점선은 "여기서 떨어진다" 또는 "아직 아니다"를 뜻한다.

모서리는 세 가지다. 판에 속한 것(칸, 종이 조각, 맞붙은 고르기 줄)은 직각. 손으로 누르는 낱개 버튼과 입력칸은 0.75rem, 뽑기 버튼은 1rem, 덮개 상자는 1.25rem. 탭과 머리띠의 알약은 완전히 둥글다(999px). 아이콘은 글자가 아니라 인라인 SVG 선 그림이며 굵기 3, 끝이 둥글고 글자색을 따른다.

### Named Rules
**실선과 점선 규칙.** 실선은 가장자리, 점선은 뜯는 자리와 아직 아닌 것. 꾸미려고 점선을 쓰지 않는다.

**맞붙으면 직각 규칙.** 서로 맞붙은 것은 직각이고, 떨어져 있는 낱개는 둥글다.

## Components

모든 누르는 것은 흰 바탕에 3px 먹색 테두리에서 시작하고, 눌린 순간 줄무늬 노랑(`board-shade`)이 된다. 호버 상태는 없다. 포커스는 3px 남색 외곽선을 2px 띄워 그린다.

### Buttons
- **뽑기 버튼:** 패널 바닥의 빨간 버튼. 너비 전부, 최소 높이 5.75rem, 4px 먹색 테두리, 모서리 1rem, 던파 비트비트체 2.75rem 흰 글자. 눌린 순간 먹색이 된다. 못 누를 때는 흰 바탕에 회색 글자와 점선 테두리가 되고, 왜 못 누르는지를 버튼 위에 가운데 정렬 글(1.0625rem, 400)로 적는다. 화면에 하나뿐이다.
- **보통 버튼:** 흰 바탕, 3px 테두리, 모서리 0.75rem, 최소 높이 3.5rem, 1.1875rem. 그만두기, 처음으로 같은 두 번째 행동. 못 누를 때는 회색 점선. 위험한 행동은 테두리와 글자가 경고 빨강이고 눌린 순간 경고 빨강 바탕에 흰 글자.
- **머리띠 버튼:** 빨간 띠 위의 흰 테두리 알약(최소 높이 2.75rem). 눌린 순간 흰 바탕에 빨간 글자로 뒤집힌다. 관리자일 때만 보인다.
- **비밀번호 키:** 3열, 최소 높이 4.25rem, 1.75rem 숫자. 눌린 순간 판 노랑. 확인 키만 빨간 바탕에 흰 글자.

### Chips
- **탭:** 흰 알약, 3px 테두리, 최소 높이 3rem, 1.25rem. 개수는 빨간 글자로 뒤에 붙는다. 고른 탭은 남색 바탕에 흰 글자이고 개수는 노랑이 된다.
- **상태 알약:** 머리띠 오른쪽의 흰 알약(테두리 없음, 1.125rem). 관리자 표시는 먹 바탕에 노란 글자, 연결이 끊기면 먹 바탕에 흰 글자.

### Cards / Containers
- **패널:** 오른쪽 23.25rem 흰 면. 테두리 대신 왼쪽 6px 먹선 하나. 그림자 없음. 안쪽 여백 1.25rem 1.5rem.
- **덮개 상자:** 가림막 위 가운데의 흰 상자. 최대 너비 26rem(대기열은 38rem), 4px 테두리, 모서리 1.25rem, 안쪽 여백 1.5rem, 안의 것들은 1rem 간격.
- **알림:** 3px 경고 빨강 테두리에 경고 빨강 글자, 모서리 0.75rem. 바탕은 칠하지 않는다.

### Inputs / Fields
- **이름표:** 옵션 위의 1.0625rem 굵은 글자. 범위 같은 덧말은 회색 400으로 옆에 붙는다.
- **옵션 버튼:** 2열에서 5열 격자, 간격 0.5rem, 최소 높이 3.75rem, 모서리 0.75rem. 고른 것은 판 노랑 바탕(글자는 먹 그대로). 작은 것은 2.875rem.
- **맞붙은 고르기 줄:** 무엇을 뽑을지 고르는 2열. 테두리가 겹치게 맞붙고 직각이다. 고른 것은 먹 바탕에 흰 글자.
- **숫자 고르기:** 빼기 버튼(3.75rem 정사각), 값, 더하기 버튼. 한계에 닿은 버튼은 30%로 흐려진다. 숫자는 tabular-nums.
- **글 입력칸:** 최소 높이 3.75rem, 모서리 0.75rem, 1.375rem. 자리표시 글자는 회색 400. 포커스는 3px 남색 외곽선. 틀리면 테두리가 경고 빨강이 되고 바로 아래에 알림이 붙는다.
- **비밀번호 점:** 1.125rem 동그라미, 3px 테두리, 채워지면 먹.

### Navigation
- **머리띠:** 빨간 바탕, 아래 6px 먹선. 왼쪽에 던파 비트비트체 이름, 오른쪽에 알약들. 이름을 길게 누르면 관리자 비밀번호가 열린다.
- **아래 띠:** 먹 바탕에 흰 글자(1.3125rem, 400). 지금 프린터가 하는 일을 한 줄로 말한다. 앞에 붙는 상태 말은 굵은 노랑.

### 뽑기판 (Signature)
3열 격자. 흰 칸마다 왼쪽에 빨간 던파 비트비트체 번호, 오른쪽에 굵은 고딕 이름. 칸 사이는 3px 점선, 판 가장자리는 3px 실선이다.
- **눌린 순간:** 줄무늬 노랑 바탕.
- **고른 칸:** 남색 바탕에 흰 글자, 번호는 노랑.
- **뜯긴 칸:** 뽑는 중인 칸. 판 노랑과 줄무늬 노랑의 135도 줄무늬가 드러나고 글자와 번호는 `torn-ink`. 고른 상태보다 우선한다.
- **뜯기는 순간:** 뽑기를 누르면 흰 덮개가 왼쪽에서 오른쪽으로 걷힌다(`scaleX` 1에서 0, 0.28s, `cubic-bezier(0.16, 1, 0.3, 1)`). 화면의 유일한 연출이다.

### 종이 조각 (Signature)
뽑는 중 패널에 장 수만큼 늘어서는 3.5rem x 4.5rem 직각 조각(여덟 장이 넘으면 2.5rem x 3.25rem). 아직 안 나온 장은 점선 테두리에 회색 번호, 지금 나오는 장은 실선에 판 노랑, 다 나온 장은 실선에 남색 바탕과 흰 체크 선 그림. 바탕색은 0.18s에 걸쳐 바뀐다.

### 안내 순서와 목록
첫 화면 패널의 순서 안내는 던파 비트비트체 번호(1.75rem)와 1.25rem 굵은 글, 줄 위에 3px 점선. 대기열 목록은 위에 실선 하나, 줄마다 아래 점선, 상태(6.5rem 고정 너비), 내용(400), 장 수(tabular-nums) 순서다.

`prefers-reduced-motion`에서는 모든 전환과 뜯기는 연출을 끈다.

## Do's and Don'ts

### Do:
- **Do** 색은 `var(--board)`, `var(--accent)` 같은 변수로만 쓴다. 새 색이 필요하면 `:root`에 이름을 붙여 더한다.
- **Do** 새 누르는 것은 흰 바탕, 3px 먹색 테두리, 눌린 순간 `board-shade`에서 시작한다.
- **Do** 판에서 고른 것은 남색, 패널에서 고른 옵션은 판 노랑, 맞붙은 줄에서 고른 것은 먹으로 칠한다.
- **Do** 낱개 버튼과 입력칸은 0.75rem 모서리, 맞붙은 것은 직각, 탭과 알약은 999px로 만든다.
- **Do** 크기는 rem으로 쓰고, 화면 크기 대응은 `html`의 글자 크기를 바꾸는 미디어 쿼리에 맡긴다.
- **Do** 못 누르는 버튼 옆에는 왜 못 누르는지를 글로 적는다.
- **Do** 아이콘은 굵기 3, 끝이 둥근 인라인 SVG 선 그림으로 그린다.
- **Do** 움직임을 더하면 `prefers-reduced-motion`에서 끈다.

### Don't:
- **Don't** `box-shadow`, 그라데이션 광택, 흐림 효과를 쓰지 않는다. 깊이는 색면과 선으로 만든다.
- **Don't** 판의 칸을 서로 떨어진 카드로 만들지 않는다. 칸은 절취선으로 맞붙는다.
- **Don't** 뽑기 빨강을 고른 상태나 꾸밈에 쓰지 않는다. 화면의 빨간 버튼은 뽑기 하나다.
- **Don't** 뽑기 빨강(`accent`)과 경고 빨강(`danger`)을 섞어 쓰지 않는다.
- **Don't** 던파 비트비트체를 옵션, 설명, 알림에 쓰지 않는다.
- **Don't** 호버에 기대지 않는다. 터치 전용이다.
- **Don't** `clamp()`, `:has()`, flex `gap`, `inset`, `aspect-ratio`를 쓰지 않는다.
- **Don't** 1rem보다 작은 글자나 2.75rem보다 낮은 누르는 대상을 만들지 않는다.
- **Don't** 상태를 색만으로 알리지 않는다.
