#!/usr/bin/env bash
# 저장소의 새 내용을 받아 키오스크를 다시 띄운다. 저장소 폴더에서 실행: bash deploy/update.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "== $(git branch --show-current) 브랜치의 새 내용 받기"
git pull --ff-only
.venv/bin/pip install --quiet -r kiosk/requirements.txt
sudo systemctl restart receipt-kiosk
sleep 2
if systemctl is-active --quiet receipt-kiosk; then
    echo "업데이트 완료: $(git log -1 --format='%h %s')"
else
    echo "서비스가 뜨지 않았습니다: journalctl -u receipt-kiosk -e"
    exit 1
fi
