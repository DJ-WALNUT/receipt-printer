"""키오스크 서버. 메뉴를 내려주고, 인쇄 요청을 검사해 대기열에 넣는다.

화면(static/)은 /api/catalog 가 주는 메뉴만으로 그려진다. 콘텐츠를 추가해도 이 파일과 화면은 고치지 않는다.
무엇을 뽑을 수 있는지는 전부 hub.py 가 정한다. 여기서는 요청을 hub 에 넘기고 결과를 돌려줄 뿐이다.
"""
import hmac
import logging
import secrets
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory, session

import hub
from kiosk.jobs import Busy, JobQueue
from kiosk.theme import load_theme, theme_css

HERE = Path(__file__).resolve().parent
STAFF_IDLE = 5 * 60        # 운영자 세션이 이만큼 쉬면 방문자로 돌아간다 (초)
LOGIN_TRIES = 5            # 비밀번호를 이만큼 틀리면
LOGIN_LOCK = 60            # 이만큼 로그인을 막는다 (초)

log = logging.getLogger("kiosk")


def cleanup_outputs(root: Path, days: float) -> int:
    """콘텐츠 폴더의 output/ 에 쌓인 이미지 중 days일보다 오래된 것을 지운다. 지운 개수를 돌려준다."""
    cutoff = time.time() - days * 86400
    removed = 0
    for path in Path(root).glob("**/output/*.png"):
        if ".venv" in path.parts:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def create_app(queue: JobQueue | None = None, pin: str | None = None, root: Path = hub.ROOT,
               secret: str | None = None, theme_path: Path | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")
    app.secret_key = secret or secrets.token_hex(32)
    app.json.ensure_ascii = False

    queue = queue or JobQueue()
    catalog = hub.load(root)
    nicknames = hub.load_nicknames(HERE / "nicknames.txt")
    theme = load_theme(theme_path or HERE / "theme.toml")
    for error in catalog.errors:
        log.warning("설정 오류로 뺀 콘텐츠 - %s", error)
    login = {"fails": 0, "locked_until": 0.0}

    def role():
        """요청한 사람의 역할. 운영자 세션은 쓰는 동안 연장되고, 오래 쉬면 끝난다."""
        seen = session.get("staff_seen")
        if pin and seen is not None and time.time() - seen < STAFF_IDLE:
            session["staff_seen"] = time.time()
            return hub.STAFF
        session.pop("staff_seen", None)
        return hub.VISITOR

    def error(message, status):
        return jsonify({"error": message}), status

    def staff_only():
        if role() != hub.STAFF:
            abort(403)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/fonts/<name>")
    def font(name):
        if not name.endswith(".ttf"):
            abort(404)
        return send_from_directory(hub.ROOT / "Galmuri-v2.40.4", name, max_age=86400)

    @app.get("/theme.css")
    def get_theme():
        return Response(theme_css(theme), mimetype="text/css")

    @app.get("/api/catalog")
    def get_catalog():
        described = hub.describe(catalog, role(), nicknames)
        described["admin_enabled"] = bool(pin)
        described["name"] = theme["name"]
        return jsonify(described)

    @app.post("/api/print")
    def post_print():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return error("요청을 읽을 수 없습니다.", 400)
        who = role()
        name, mode_id = body.get("content"), body.get("mode")
        content = catalog.contents.get(name) if isinstance(name, str) else None
        if content is None or not content.kiosk or not isinstance(mode_id, str):
            return error("없는 콘텐츠입니다.", 400)
        try:
            args = hub.build_args(content, mode_id, body.get("values"), who, nicknames)
            mode = next(m for m in content.modes if m.id == mode_id)
            sheets = hub.check_sheets(mode, body.get("sheets"), who)
        except hub.HubError as e:
            return error(str(e), 400)
        try:
            job = queue.submit(content, args, sheets, who)
        except Busy:
            return error("지금 다른 인쇄가 진행 중입니다. 잠시만 기다려 주세요.", 409)
        return jsonify(job.to_dict()), 202

    @app.get("/api/jobs/<job_id>")
    def get_job(job_id):
        job = queue.get(job_id)
        if job is None:
            abort(404)
        return jsonify(job.to_dict())

    @app.post("/api/admin/login")
    def admin_login():
        body = request.get_json(silent=True)
        given = body.get("pin") if isinstance(body, dict) else None
        if not pin:
            return error("관리자 기능이 꺼져 있습니다.", 403)
        if time.time() < login["locked_until"]:
            return error("여러 번 틀렸습니다. 1분 뒤에 다시 시도해 주세요.", 429)
        if isinstance(given, str) and hmac.compare_digest(given.encode(), pin.encode()):
            login["fails"] = 0
            session["staff_seen"] = time.time()
            return jsonify({"role": hub.STAFF})
        login["fails"] += 1
        if login["fails"] >= LOGIN_TRIES:
            login["fails"], login["locked_until"] = 0, time.time() + LOGIN_LOCK
        return error("비밀번호가 맞지 않습니다.", 403)

    @app.post("/api/admin/logout")
    def admin_logout():
        session.pop("staff_seen", None)
        return jsonify({"role": hub.VISITOR})

    @app.get("/api/admin/jobs")
    def admin_jobs():
        staff_only()
        return jsonify([job.to_dict() for job in queue.jobs()])

    @app.post("/api/admin/cancel")
    def admin_cancel():
        staff_only()
        return jsonify({"cancelled": queue.cancel_all()})

    @app.errorhandler(403)
    @app.errorhandler(404)
    def plain_error(e):
        return error("요청한 것을 찾을 수 없거나 권한이 없습니다.", e.code)

    return app
