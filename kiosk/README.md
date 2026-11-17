# 키오스크

라즈베리파이가 영수증 프린터에 연결되어 웹 페이지를 띄우고, 아이패드에서 눌러 뽑는다. 이 폴더와 `deploy/`는 `kiosk` 브랜치에만 있다.

콘텐츠는 여기서 만들지 않는다. `receipt-contents` 브랜치에서 터미널로 만들어 가져온다 (아래 "새 콘텐츠 올리기").

## 화면에서 할 수 있는 것

| | 방문자 | 관리자 |
|---|---|---|
| 한 번에 뽑는 장 수 | 최대 4장 | 최대 20장 |
| 고르기, 숫자 옵션 | 전부 | 전부 |
| 같은 문제 여러 장 | 스도쿠, 부등호 스도쿠, 노노그램, 지뢰찾기, 미로, 낱말 찾기, 다른 그림 찾기 | 같음 (낱말 직접 넣기 포함) |
| 글자 입력 | 시드번호, maimai 아이디 | 낱말, 이름, 결과, 상품 문구 등 전부 |
| 사다리 타기 참가자 | 준비된 닉네임에서 고르기 | 이름 직접 입력 |
| 관리자 전용 메뉴 | 보이지 않음 | 빙고 빈 판·진행자용, 로또 추첨 결과, maimai 전부 찍기 등 |
| 대기 중인 인쇄 취소 | 못 함 | 가능 |

텍스트 인쇄는 키오스크에 없다. 터미널(`python main.py`)에서만 쓴다.

무엇이 방문자용이고 무엇이 관리자용인지는 각 콘텐츠의 `content.toml`에 적혀 있다 (`audience = "staff"`). 규칙은 맨 위 README의 "콘텐츠 설정 파일" 절에 있다.

## PC에서 띄워 보기 (프린터 없이)

```powershell
.venv\Scripts\pip install -r kiosk/requirements.txt
$env:KIOSK_PREVIEW = "1"      # 인쇄하지 않고 이미지만 만든다
$env:KIOSK_PIN = "1234"       # 관리자 비밀번호 (없으면 관리자 기능이 꺼진다)
.venv\Scripts\python -m kiosk
```

브라우저에서 `http://localhost:8080`을 연다. 뽑은 결과는 각 콘텐츠의 `output/` 폴더에 이미지로 생긴다.

## 라즈베리파이에 설치

Raspberry Pi OS Lite(64비트)에 SSH로 접속한 상태에서 한다. 프린터는 파이의 USB에 꽂는다.

```bash
sudo apt install -y git
git clone -b kiosk https://github.com/DJ-WALNUT/receipt-printer.git
cd receipt-printer
bash deploy/setup-pi.sh       # 중간에 관리자 비밀번호(숫자 4~8자리)를 묻는다
sudo reboot
```

재부팅하면 키오스크가 자동으로 뜬다. 같은 공유기에 연결된 기기에서 `http://<파이 호스트 이름>.local`로 접속한다 (예: `http://djwalnut.local`).

설치 스크립트가 하는 일: 패키지 설치, 가상환경, 프린터 권한(`dialout`), 프린터 고정 경로(`/dev/receipt`), 설정 파일(`/etc/receipt-kiosk.env`), 자동 실행 서비스(`receipt-kiosk`).

작동확인
```
systemctl is-active receipt-kiosk
ls -l /dev/receipt
```

ip확인 및 와이파이 절전 확인
```
ip -br addr
iw dev wlan0 get power_save
```

## 밖에서 접속하기 (Cloudflare Tunnel + Access)

같은 공유기 밖에서도 `https://print.내도메인.com` 같은 주소로 열 수 있다. 파이가 Cloudflare로 먼저 연결을 걸기 때문에 공유기 설정이나 고정 IP가 필요 없다. 도메인이 Cloudflare 계정에 등록돼 있어야 한다 (네임서버가 Cloudflare).

키오스크는 누구나 인쇄할 수 있게 만들어져 있으므로, **주소를 열기 전에 먼저 잠근다.** 순서를 바꾸면 잠그기 전까지 아무나 인쇄할 수 있다.

**1. 잠그기 (Access)** — [Zero Trust 대시보드](https://one.dash.cloudflare.com)에서:

1. Access → Applications → Add an application → Self-hosted.
2. Application domain에 쓸 주소를 넣는다 (예: 하위 도메인 `print`, 도메인 `내도메인.com`). 경로는 비워 주소 전체를 잠근다.
3. Session Duration은 로그인을 다시 묻는 주기다. 자주 쓰면 `1 month`.
4. 정책을 하나 만든다: Action `Allow`, Include → `Emails`에 들어올 사람의 이메일을 적는다. 로그인 방법은 기본인 One-time PIN(이메일로 오는 6자리 숫자)이면 된다.

**2. 터널 만들기** — 같은 대시보드에서:

1. Networks → Tunnels → Create a tunnel → Cloudflared. 이름은 아무거나 (예: `receipt-kiosk`).
2. 설치 명령이 나오는 화면에서 `cloudflared service install` 뒤의 `eyJ...` 토큰만 복사한다.
3. 파이에서 실행하고 토큰을 붙여 넣는다.

   ```bash
   cd receipt-printer
   bash deploy/setup-tunnel.sh
   ```

4. 대시보드로 돌아와 Public Hostname을 더한다: 1번에서 잠근 것과 같은 주소, Service는 `HTTP` / `localhost:80` (`KIOSK_PORT`를 바꿨으면 그 포트).

**3. 확인** — 휴대폰의 와이파이를 끄고 주소를 연다. 키오스크가 아니라 Cloudflare의 이메일 입력 화면이 먼저 나와야 한다. 바로 키오스크가 뜨면 Access 주소와 Public Hostname 주소가 같은지 본다.

알아 둘 것:

- 같은 공유기 안에서는 전처럼 `http://djwalnut.local`로 로그인 없이 열린다. 현장의 아이패드는 이 주소를 그대로 쓴다.
- Access를 지나온 사람은 방문자와 같다. 관리자 기능은 여전히 관리자 비밀번호가 있어야 한다.
- 밖에서 여는 것을 멈추려면 파이에서 `sudo systemctl disable --now cloudflared`, 다시 열려면 `sudo systemctl enable --now cloudflared`.
- 토큰은 이 파이를 터널에 연결할 수 있는 열쇠다. 저장소나 메신저에 남기지 않는다. 새어 나갔으면 대시보드에서 터널을 지우고 새로 만든다.

## 새 콘텐츠 올리기

PC에서:

```powershell
git switch receipt-contents
# ... 콘텐츠 폴더와 content.toml 을 만들고 커밋 ...
git switch kiosk
git merge receipt-contents
git push
```

파이에서:

```bash
cd receipt-printer
bash deploy/update.sh
```

키오스크용 작업은 따로 없다. 병합이 충돌 없이 끝나도록 `kiosk` 브랜치에서는 `kiosk/`, `deploy/`, `tests/kiosk/` 밖의 파일을 고치지 않는다. 콘텐츠나 `hub.py`, `main.py`를 고칠 일이 있으면 `receipt-contents`에서 고치고 병합한다.

## 아이패드 설정

1. Safari에서 `http://djwalnut.local`을 연다.
2. 공유 버튼 → "홈 화면에 추가". 홈 화면의 아이콘으로 열면 주소창 없이 전체 화면으로 뜬다.
3. 설정 → 손쉬운 사용 → 사용법 유도를 켜고 암호를 정한다.
4. 키오스크를 연 상태에서 홈 버튼(또는 전원 버튼)을 세 번 눌러 사용법 유도를 시작한다. 다른 앱으로 나갈 수 없게 된다.
5. 설정 → 디스플레이 및 밝기 → 자동 잠금을 "안 함"으로 둔다.

## 관리자

- **들어가기**: 첫 화면의 제목을 2초 동안 길게 누르고 비밀번호를 넣는다.
- **자동으로 나가기**: 3분 동안 쓰지 않으면 방문자 화면으로 돌아간다.
- **비밀번호 바꾸기**: 파이에서 `sudo nano /etc/receipt-kiosk.env`로 `KIOSK_PIN`을 고치고 `sudo systemctl restart receipt-kiosk`.
- 비밀번호를 5번 틀리면 1분 동안 로그인이 막힌다.

### 관리 페이지 (`/admin`)

같은 네트워크의 PC나 아이패드에서 `http://<파이 주소>:8080/admin`을 연다 (키오스크 관리자 화면의 대기열 → "관리 페이지"로도 간다). 같은 관리자 비밀번호로 들어간다.

- **이용실적**: 기간(오늘, 최근 7일·30일, 이번 달, 지난 달, 직접 고르기)별 인쇄 장 수와 작업 수를 콘텐츠별·날짜별로 본다. "CSV 내려받기"는 엑셀에서 바로 열린다.
- **이미지**: 지금까지 만들어진 영수증 이미지를 콘텐츠·날짜로 골라 보고, 크게 보거나 지운다. `KIOSK_KEEP_DAYS`를 설정했으면 그보다 오래된 이미지는 자동으로 지워진다.
- 실적은 인쇄 작업이 끝날 때마다(성공·실패·취소) `kiosk/data/usage.csv`에 한 줄씩 쌓인다. 저장소에는 올라가지 않으니 필요하면 따로 백업한다.
- **지난 이력 지우기** (테스트 기록을 비울 때): 프로젝트 폴더에서 `python -m kiosk.reset`. 지울 개수를 보여 주고 확인을 받은 뒤 이용실적과 이미지를 모두 지운다. `--only usage` / `--only images`로 한쪽만, `--yes`로 확인 없이. 파이에서는 프로젝트 폴더에서 `.venv/bin/python -m kiosk.reset`처럼 가상환경의 파이썬으로 실행한다. 되돌릴 수 없다.

## 닉네임 바꾸기

사다리 타기에서 방문자가 고르는 이름은 `kiosk/nicknames.txt`에 한 줄에 하나씩 있다. 고친 뒤 서비스를 재시작한다. 이름은 8자까지, 사다리에 8명이 들어가도 겹치지 않으려면 세 글자 이하가 좋다.

## 안 될 때

| 증상 | 확인할 것 |
|---|---|
| 화면에 "프린터 연결을 확인해 주세요" | USB가 꽂혀 있는지, `ls -l /dev/receipt`에 경로가 보이는지. 안 보이면 `lsusb`에 `1cbe:0002`가 있는지 |
| 접속이 됐다 안 됐다 함, `.local` 주소만 안 열림 | 파이 와이파이의 절전이 켜져 있으면 생긴다. `iw dev wlan0 get power_save`가 `on`이면 `bash deploy/setup-pi.sh`를 다시 실행하거나 `sudo iw dev wlan0 set power_save off`로 끈다. 오래 켜 둘 키오스크는 랜선 연결이 가장 확실하다 |
| 아이패드에서 접속이 안 됨 | 아이패드와 파이가 같은 공유기에 있는지. `.local` 이름이 안 풀리면 `hostname -I`로 나온 IP로 접속한다. 공유기에서 파이 IP를 고정해 두면 편하다 |
| 센터 와이파이에서만 접속이 안 됨 | 기기끼리의 통신을 막아 둔 와이파이일 수 있다. 파이를 유선 랜으로 연결하거나 별도 공유기를 쓴다 |
| 밖에서 여는 주소만 안 열림 (502, 1033 오류) | 파이에서 `systemctl status cloudflared`, 로그는 `journalctl -u cloudflared -e`. 대시보드의 터널이 HEALTHY인지, Public Hostname의 Service가 `HTTP` / `localhost:80`인지 본다 |
| 화면이 "키오스크에 연결할 수 없습니다" | `systemctl status receipt-kiosk`, 로그는 `journalctl -u receipt-kiosk -e` |
| 새 콘텐츠가 화면에 안 보임 | 설정 파일에 오류가 있으면 그 콘텐츠만 빠진다. 로그에 "설정 오류로 뺀 콘텐츠"가 있는지 본다 |
| maimai 곡 제목의 한자가 빈 네모로 찍힘 | `fc-list | grep -i unifont`로 대체 글꼴이 설치됐는지 본다 (`sudo apt install fonts-unifont`) |
| 종이가 떨어짐 | 화면은 알지 못한다. 인쇄가 끝난 것으로 나오는데 종이가 안 나오면 용지를 확인한다 |

## 설정 (`/etc/receipt-kiosk.env`)

| 이름 | 뜻 |
|---|---|
| `RECEIPT_PORT` | 프린터 경로. 기본 `/dev/receipt` |
| `KIOSK_PORT` | 웹 포트. 80이면 주소에 포트 번호를 붙이지 않는다 |
| `KIOSK_PIN` | 관리자 비밀번호. 비우면 관리자 기능이 꺼진다 |
| `KIOSK_KEEP_DAYS` | 이 날수보다 오래된 출력 이미지를 지운다. 지우면 안 되면 이 줄을 뺀다 |
| `KIOSK_SECRET` | 로그인 세션 서명 키. 건드릴 일이 없다 |
| `KIOSK_PREVIEW` | `1`이면 인쇄하지 않고 이미지만 만든다 |

## 테스트

```powershell
.venv\Scripts\pip install -r requirements-dev.txt -r kiosk/requirements.txt
.venv\Scripts\python -m pytest
```
