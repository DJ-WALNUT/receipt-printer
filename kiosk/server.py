"""키오스크 서버. 메뉴를 내려주고, 인쇄 요청을 검사해 대기열에 넣는다.

화면(static/)은 /api/catalog 가 주는 메뉴만으로 그려진다. 콘텐츠를 추가해도 이 파일과 화면은 고치지 않는다.
무엇을 뽑을 수 있는지는 전부 hub.py 가 정한다. 여기서는 요청을 hub 에 넘기고 결과를 돌려줄 뿐이다.
"""
import datetime
import hmac
import logging
import re
import secrets
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory, session

import hub
from kiosk.jobs import Busy, JobQueue
from kiosk.theme import load_theme, theme_css
from kiosk.usage import UsageLog, summarize

HERE = Path(__file__).resolve().parent
STAFF_IDLE = 5 * 60        # 운영자 세션이 이만큼 쉬면 방문자로 돌아간다 (초)
LOGIN_TRIES = 5            # 비밀번호를 이만큼 틀리면
LOGIN_LOCK = 60            # 이만큼 로그인을 막는다 (초)
USAGE_PATH = HERE / "data" / "usage.csv"   # 이용실적 기록 (저장소에 올리지 않는다)
STATS_DAYS = 30            # 관리 페이지에서 기간을 안 고르면 최근 이만큼
IMAGE_PAGE = 60            # 이미지 목록 한 번에 보여 줄 개수
IMAGE_NAME = re.compile(r"(\d{8})_(\d{6})(?:_(.+))?\.png")   # receipt.save_output 이 만드는 이름

log = logging.getLogger("kiosk")


def output_images(root: Path) -> list:
    """콘텐츠 폴더들의 output/ 에 있는 이미지 경로 전부."""
    # 콘텐츠 폴더는 깊이 1~2 에만 있다. 저장소 전체(.git, .venv)를 훑지 않는다.
    found = list(Path(root).glob("*/output/*.png")) + list(Path(root).glob("*/*/output/*.png"))
    return [p for p in found if not p.parts[len(Path(root).parts)].startswith(".")]


def cleanup_outputs(root: Path, days: float) -> int:
    """콘텐츠 폴더의 output/ 에 쌓인 이미지 중 days일보다 오래된 것을 지운다 (0이면 전부). 지운 개수를 돌려준다."""
    cutoff = time.time() - days * 86400
    removed = 0
    for path in output_images(root):
        try:
            if days <= 0 or path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def create_app(queue: JobQueue | None = None, pin: str | None = None, root: Path = hub.ROOT,
               secret: str | None = None, theme_path: Path | None = None,
               usage_path: Path | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")
    app.secret_key = secret or secrets.token_hex(32)
    app.json.ensure_ascii = False

    queue = queue or JobQueue()
    usage = UsageLog(usage_path or USAGE_PATH)
    if queue.on_finish is None:
        queue.on_finish = usage.record
    catalog = hub.load(root)
    nicknames = hub.load_nicknames(HERE / "nicknames.txt")
    theme = load_theme(theme_path or HERE / "theme.toml")
    for error in catalog.errors:
        log.warning("설정 오류로 뺀 콘텐츠 - %s", error)
    login = {"fails": 0, "locked_until": 0.0}
    version = secrets.token_hex(4)   # 서버가 다시 뜨면 바뀐다. 화면이 새 메뉴와 새 화면 파일을 받아 가는 신호

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
        described["version"] = version
        if described["role"] == hub.STAFF:
            described["errors"] = list(catalog.errors)   # 설정 오류로 빠진 콘텐츠와 이유
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
            same = hub.check_same(mode, body.get("same")) and sheets > 1   # 한 장이면 보통 작업과 같다
        except hub.HubError as e:
            return jsonify({"error": str(e), "field": e.field}), 400
        try:
            job = queue.submit(content, args, sheets, who, same=same, mode=mode_id)
        except Busy:
            return error("지금 다른 인쇄가 진행 중이에요. 잠시만 기다려 주세요.", 409)
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
            return error("여러 번 틀렸어요. 1분 뒤에 다시 해 주세요.", 429)
        if isinstance(given, str) and hmac.compare_digest(given.encode(), pin.encode()):
            login["fails"] = 0
            session["staff_seen"] = time.time()
            return jsonify({"role": hub.STAFF})
        login["fails"] += 1
        if login["fails"] >= LOGIN_TRIES:
            login["fails"], login["locked_until"] = 0, time.time() + LOGIN_LOCK
        return error("비밀번호가 맞지 않아요.", 403)

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

    # ------------------------------------------------------------ 관리 페이지

    @app.get("/admin")
    def admin_page():
        return send_from_directory(app.static_folder, "admin.html")

    @app.get("/api/admin/me")
    def admin_me():
        return jsonify({"role": role(), "admin_enabled": bool(pin), "name": theme["name"]})

    def period():
        """?from=YYYY-MM-DD&to=YYYY-MM-DD. 없으면 최근 STATS_DAYS일. 잘못되면 400."""
        today = datetime.date.today()
        try:
            end = datetime.date.fromisoformat(request.args.get("to") or today.isoformat())
            start = datetime.date.fromisoformat(request.args.get("from")
                                                or (end - datetime.timedelta(days=STATS_DAYS - 1)).isoformat())
        except ValueError:
            abort(400)
        if start > end or (end - start).days > 366 * 3:
            abort(400)
        return start, end

    @app.get("/api/admin/stats")
    def admin_stats():
        staff_only()
        start, end = period()
        return jsonify(summarize(usage.rows(start, end), start, end))

    @app.get("/api/admin/usage.csv")
    def admin_usage_csv():
        staff_only()
        start, end = period()
        name = f"usage_{start:%Y%m%d}-{end:%Y%m%d}.csv"
        return Response(usage.csv_text(start, end), mimetype="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    def output_dir(name):
        content = catalog.contents.get(name)
        if content is None:
            abort(404)
        return content.script.parent / "output"

    def image_info(content, path):
        match = IMAGE_NAME.fullmatch(path.name)
        if not match:
            return None
        day, clock, tag = match.groups()
        try:
            when = datetime.datetime.strptime(day + clock, "%Y%m%d%H%M%S")
        except ValueError:
            return None
        return {"content": content.name, "title": content.title, "file": path.name, "tag": tag or "",
                "time": when.strftime("%Y-%m-%d %H:%M:%S"), "date": when.date().isoformat()}

    @app.get("/api/admin/images")
    def admin_images():
        """?content=이름&date=YYYY-MM-DD&offset=0. 최근 것부터 IMAGE_PAGE개씩."""
        staff_only()
        wanted, day = request.args.get("content") or None, request.args.get("date") or None
        try:
            offset = max(0, int(request.args.get("offset") or 0))
        except ValueError:
            abort(400)
        found, counts = [], {}
        for content in catalog.contents.values():
            folder = content.script.parent / "output"
            if not folder.is_dir():
                continue
            for path in folder.glob("*.png"):
                info = image_info(content, path)
                if info is None or (day and info["date"] != day):
                    continue
                counts[content.name] = counts.get(content.name, 0) + 1
                if wanted is None or wanted == content.name:
                    found.append(info)
        found.sort(key=lambda i: (i["time"], i["file"]), reverse=True)
        contents = [{"name": c.name, "title": c.title, "count": counts.get(c.name, 0)}
                    for c in sorted(catalog.contents.values(), key=lambda c: c.title)]
        return jsonify({"total": len(found), "offset": offset, "images": found[offset:offset + IMAGE_PAGE],
                        "contents": contents})

    @app.get("/api/admin/images/<name>/<file>")
    def admin_image(name, file):
        staff_only()
        if not IMAGE_NAME.fullmatch(file):
            abort(404)
        return send_from_directory(output_dir(name), file, max_age=3600)

    @app.delete("/api/admin/images/<name>/<file>")
    def admin_image_delete(name, file):
        staff_only()
        if not IMAGE_NAME.fullmatch(file):
            abort(404)
        path = output_dir(name) / file
        if not path.is_file():
            abort(404)
        try:
            path.unlink()
        except OSError:
            return error("이미지를 지우지 못했어요. 잠시 뒤에 다시 해 주세요.", 409)
        return jsonify({"deleted": file})

    @app.errorhandler(400)
    def bad_request(e):
        return error("요청 값이 올바르지 않습니다.", 400)

    @app.errorhandler(403)
    @app.errorhandler(404)
    def plain_error(e):
        return error("요청한 것을 찾을 수 없거나 권한이 없습니다.", e.code)

    return app
