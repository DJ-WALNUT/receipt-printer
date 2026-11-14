"""키오스크 서버 실행: python -m kiosk

환경 변수:
    KIOSK_PORT       포트 (기본 8080)
    KIOSK_PIN        관리자 비밀번호. 없으면 관리자 기능이 꺼진다
    KIOSK_PREVIEW    1이면 인쇄하지 않고 이미지만 만든다 (프린터 없는 PC에서 개발할 때)
    KIOSK_SECRET     세션 서명 키. 없으면 시작할 때마다 새로 만든다 (재시작하면 관리자 로그인이 풀린다)
    KIOSK_KEEP_DAYS  설정하면 그 날수보다 오래된 output 이미지를 지운다 (파이에서만 설정한다)
    RECEIPT_PORT     프린터 시리얼 포트 (receipt.py 가 읽는다)
"""
import logging
import os
import threading

from waitress import serve

import hub
from kiosk.jobs import JobQueue
from kiosk.server import cleanup_outputs, create_app


def keep_clean(days):
    removed = cleanup_outputs(hub.ROOT, days)
    if removed:
        logging.getLogger("kiosk").info("오래된 이미지 %d개를 지웠습니다", removed)
    timer = threading.Timer(86400, keep_clean, [days])
    timer.daemon = True
    timer.start()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    preview = os.environ.get("KIOSK_PREVIEW") == "1"
    port = int(os.environ.get("KIOSK_PORT", "8080"))
    app = create_app(queue=JobQueue(preview=preview), pin=os.environ.get("KIOSK_PIN") or None,
                     secret=os.environ.get("KIOSK_SECRET") or None)
    if os.environ.get("KIOSK_KEEP_DAYS"):
        keep_clean(float(os.environ["KIOSK_KEEP_DAYS"]))
    logging.getLogger("kiosk").info("키오스크 시작: 포트 %d%s", port, " (미리보기 모드, 인쇄 안 함)" if preview else "")
    serve(app, host="0.0.0.0", port=port, threads=8)


if __name__ == "__main__":
    main()
