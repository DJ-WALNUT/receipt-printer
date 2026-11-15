#!/usr/bin/env bash
# 키오스크를 Cloudflare Tunnel 로 인터넷에 연다. 저장소 폴더에서 실행: bash deploy/setup-tunnel.sh
# 먼저 Cloudflare 대시보드에서 터널을 만들고 토큰을 받아 둔다 (kiosk/README.md 의 "밖에서 접속하기").
# 여러 번 실행해도 된다. 이미 연결돼 있으면 토큰을 바꿀지 묻는다.
set -euo pipefail

SERVICE=cloudflared
KEYRING=/usr/share/keyrings/cloudflare-main.gpg

echo "== 1/2 cloudflared 설치"
if command -v cloudflared > /dev/null; then
    echo "이미 있습니다: $(cloudflared --version)"
else
    sudo apt-get update -qq
    sudo apt-get install -y curl
    sudo mkdir -p --mode=0755 /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee "$KEYRING" > /dev/null
    echo "deb [signed-by=$KEYRING] https://pkg.cloudflare.com/cloudflared any main" \
        | sudo tee /etc/apt/sources.list.d/cloudflared.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y cloudflared
fi

echo "== 2/2 터널 연결"
if systemctl cat "$SERVICE" > /dev/null 2>&1; then
    read -r -p "이미 터널이 연결돼 있습니다. 새 토큰으로 바꿀까요? [y/N] " ANSWER
    if [[ ! "$ANSWER" =~ ^[yY]$ ]]; then
        sudo systemctl restart "$SERVICE"
        echo "그대로 두고 다시 띄웠습니다."
        exit 0
    fi
    sudo cloudflared service uninstall
fi

while true; do
    read -r -s -p "터널 토큰 (대시보드에서 복사한 eyJ... 로 시작하는 긴 글자): " TOKEN; echo
    [[ "$TOKEN" =~ ^eyJ[A-Za-z0-9_=-]+$ ]] && break
    echo "토큰 모양이 아닙니다. 'cloudflared service install' 뒤에 붙은 글자만 붙여 넣어 주세요."
done
sudo cloudflared service install "$TOKEN"
sleep 3

echo
if systemctl is-active --quiet "$SERVICE"; then
    echo "터널이 떴습니다. 대시보드의 터널 상태가 HEALTHY 인지 확인하세요."
    echo "밖에서 열기 전에 Cloudflare Access 로 잠갔는지 꼭 확인하세요 (kiosk/README.md)."
else
    echo "터널이 뜨지 않았습니다. 아래 명령으로 이유를 확인하세요."
fi
echo "  상태: systemctl status $SERVICE"
echo "  로그: journalctl -u $SERVICE -e"
echo "  끊기: sudo cloudflared service uninstall"
