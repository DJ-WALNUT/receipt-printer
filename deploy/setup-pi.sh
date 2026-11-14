#!/usr/bin/env bash
# 라즈베리파이에 키오스크를 설치한다. 저장소 폴더에서 실행: bash deploy/setup-pi.sh
# 여러 번 실행해도 된다. 이미 있는 비밀번호 설정은 건드리지 않는다.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/receipt-kiosk.env
SERVICE=receipt-kiosk
cd "$DIR"

echo "== 1/5 필요한 패키지 설치"
sudo apt-get update -qq
sudo apt-get install -y python3-venv fonts-unifont

echo "== 2/5 파이썬 가상환경"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r kiosk/requirements.txt

echo "== 3/5 프린터 권한과 고정 경로(/dev/receipt), 와이파이 절전 끄기"
sudo usermod -aG dialout "$USER"
sudo cp deploy/99-receipt-printer.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty

# 와이파이 절전을 끈다. 켜져 있으면 파이가 무선 기기(아이패드)의 요청과 이름 찾기(.local)를
# 놓쳐서 됐다 안 됐다 한다. 모든 와이파이 연결에 적용되므로 다른 공유기에 붙여도 유지된다.
if [ -d /etc/NetworkManager/conf.d ]; then
    printf '[connection]\nwifi.powersave = 2\n' | sudo tee /etc/NetworkManager/conf.d/wifi-powersave-off.conf > /dev/null
    if command -v iw > /dev/null && iw dev wlan0 info > /dev/null 2>&1; then
        sudo iw dev wlan0 set power_save off || true
    fi
fi

echo "== 4/5 설정 파일 ($ENV_FILE)"
if sudo test -f "$ENV_FILE"; then
    echo "이미 있습니다. 그대로 둡니다."
else
    while true; do
        read -r -s -p "관리자 비밀번호 (숫자 4~8자리): " PIN; echo
        [[ "$PIN" =~ ^[0-9]{4,8}$ ]] && break
        echo "숫자 4~8자리로 입력해 주세요."
    done
    SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    printf 'RECEIPT_PORT=/dev/receipt\nKIOSK_PORT=80\nKIOSK_PIN=%s\nKIOSK_KEEP_DAYS=7\nKIOSK_SECRET=%s\n' "$PIN" "$SECRET" \
        | sudo tee "$ENV_FILE" > /dev/null
    sudo chown "$USER" "$ENV_FILE"
    sudo chmod 600 "$ENV_FILE"
fi

echo "== 5/5 자동 실행 서비스"
sed -e "s|__USER__|$USER|g" -e "s|__DIR__|$DIR|g" deploy/receipt-kiosk.service \
    | sudo tee /etc/systemd/system/$SERVICE.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" > /dev/null
sudo systemctl restart "$SERVICE"
sleep 2

echo
if systemctl is-active --quiet "$SERVICE"; then
    echo "설치 완료. 아이패드 Safari에서 http://$(hostname).local 로 접속하세요."
else
    echo "서비스가 뜨지 않았습니다. 아래 명령으로 이유를 확인하세요."
fi
echo "  상태: systemctl status $SERVICE"
echo "  로그: journalctl -u $SERVICE -e"
ls -l /dev/receipt 2>/dev/null || echo "  프린터가 아직 /dev/receipt 로 보이지 않습니다. USB를 꽂았는지 확인하고, 처음 설치했다면 한 번 재부팅하세요 (sudo reboot)."
