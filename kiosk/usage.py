"""이용실적 기록. 인쇄 작업이 끝날 때마다(성공·실패·취소 모두) CSV 파일에 한 줄씩 덧붙인다.

파일은 엑셀에서 바로 열리도록 UTF-8(BOM)로 쓴다. 지우거나 고치지 않고 덧붙이기만 한다.
관리 페이지(/admin)가 이 파일을 읽어 기간별·콘텐츠별·날짜별로 합계를 낸다.
"""
import csv
import datetime
import io
import threading
from pathlib import Path

COLUMNS = ["시각", "콘텐츠", "제목", "모드", "역할", "요청 장수", "인쇄 장수", "상태", "같은 문제", "메시지"]
KEYS = ["time", "content", "title", "mode", "role", "sheets", "done", "state", "same", "message"]
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class UsageLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def record(self, job, when: datetime.datetime | None = None):
        """끝난 작업 하나를 기록한다. 실패하면 예외가 나고, 삼킬지는 부른 쪽(대기열)이 정한다."""
        when = when or datetime.datetime.now()
        content = job.content
        row = [when.strftime(TIME_FORMAT), getattr(content, "name", ""), job.title, job.mode, job.role,
               job.sheets, job.done, job.state, "Y" if job.same else "", job.message]
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            new = not self.path.exists() or self.path.stat().st_size == 0
            with self.path.open("a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
                writer = csv.writer(f)
                if new:
                    writer.writerow(COLUMNS)
                writer.writerow(row)

    def rows(self, start: datetime.date | None = None, end: datetime.date | None = None) -> list:
        """start~end(둘 다 포함) 날짜의 기록을 dict 목록으로. 깨진 줄은 건너뛴다."""
        with self._lock:
            try:
                text = self.path.read_text(encoding="utf-8-sig")
            except FileNotFoundError:
                return []
        out = []
        reader = csv.reader(io.StringIO(text))
        next(reader, None)   # 머리줄
        for raw in reader:
            if len(raw) != len(KEYS):
                continue
            row = dict(zip(KEYS, raw))
            try:
                day = datetime.datetime.strptime(row["time"], TIME_FORMAT).date()
                row["sheets"], row["done"] = int(row["sheets"]), int(row["done"])
            except ValueError:
                continue
            if (start and day < start) or (end and day > end):
                continue
            row["date"] = day.isoformat()
            out.append(row)
        return out

    def csv_text(self, start=None, end=None) -> str:
        """기간 안의 기록을 엑셀용 CSV 문자열(BOM 포함)로."""
        buf = io.StringIO()
        buf.write("﻿")
        writer = csv.writer(buf)
        writer.writerow(COLUMNS)
        for row in self.rows(start, end):
            writer.writerow([row[k] for k in KEYS])
        return buf.getvalue()


def summarize(rows: list, start: datetime.date, end: datetime.date) -> dict:
    """합계: 전체, 콘텐츠별(인쇄 장수 많은 순), 날짜별(기록 없는 날도 0으로)."""
    def empty():
        return {"jobs": 0, "sheets": 0, "visitor_sheets": 0, "staff_sheets": 0, "failed": 0}

    def add(bucket, row):
        bucket["jobs"] += 1
        bucket["sheets"] += row["done"]
        bucket["staff_sheets" if row["role"] == "staff" else "visitor_sheets"] += row["done"]
        if row["state"] == "failed":
            bucket["failed"] += 1

    total, contents, days = empty(), {}, {}
    day = start
    while day <= end:
        days[day.isoformat()] = empty()
        day += datetime.timedelta(days=1)
    for row in rows:
        add(total, row)
        key = row["content"] or row["title"]
        if key not in contents:
            contents[key] = {"name": row["content"], "title": row["title"], **empty()}
        add(contents[key], row)
        if row["date"] in days:
            add(days[row["date"]], row)
    by_content = sorted(contents.values(), key=lambda c: (-c["sheets"], -c["jobs"], c["title"]))
    by_date = [{"date": d, **v} for d, v in days.items()]
    return {"from": start.isoformat(), "to": end.isoformat(), "total": total,
            "by_content": by_content, "by_date": by_date}
