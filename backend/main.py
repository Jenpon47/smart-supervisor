from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smart_supervision.db"
TH_TZ = timezone(timedelta(hours=7))

Role = Literal["supervisor", "admin", "viewer"]

app = FastAPI(title="Smart Supervision API", version="0.1.0")
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:4173,http://localhost:4173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_iso() -> str:
    return datetime.now(TH_TZ).isoformat()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              name TEXT NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('supervisor','admin','viewer')),
              school_id INTEGER,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schools (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              district TEXT,
              flag TEXT DEFAULT 'gray',
              red INTEGER DEFAULT 0,
              prev INTEGER DEFAULT 0,
              min15 INTEGER DEFAULT 0,
              adjust INTEGER DEFAULT 0,
              sim TEXT DEFAULT '->',
              supervisor_id INTEGER,
              payload_json TEXT DEFAULT '{}',
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS screening_imports (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              imported_by INTEGER,
              source_name TEXT,
              summary_json TEXT NOT NULL,
              errors_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS coaching_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              school_id INTEGER NOT NULL,
              teacher TEXT NOT NULL,
              supervisor_id INTEGER,
              log_type TEXT NOT NULL,
              next_step TEXT,
              followup TEXT,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              channel TEXT NOT NULL,
              recipient TEXT,
              message TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO users(id,email,name,role,created_at) VALUES (1,?,?,?,?)",
            ("admin@demo.local", "ผอ.กลุ่มนิเทศ Demo", "admin", now_iso()),
        )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class CurrentUser(BaseModel):
    id: int
    email: str
    name: str
    role: Role
    school_id: int | None = None


def current_user(x_demo_role: str = Header(default="admin")) -> CurrentUser:
    # Development auth scaffold. Replace with Google Workspace OAuth/JWT verification.
    role = x_demo_role if x_demo_role in {"supervisor", "admin", "viewer"} else "viewer"
    return CurrentUser(id=1, email="admin@demo.local", name="Demo User", role=role)  # type: ignore[arg-type]


def require_role(*roles: Role):
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dep


class SchoolIn(BaseModel):
    id: int
    name: str
    district: str | None = None
    flag: str = "gray"
    red: int = Field(ge=0, le=100)
    prev: int = Field(default=0, ge=0, le=100)
    min15: int | None = Field(default=None, ge=0, le=100)
    adjust: int | None = Field(default=None, ge=0, le=100)
    sim: str | None = None
    supervisor_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CoachingLogIn(BaseModel):
    school_id: int
    teacher: str
    log_type: str = "coaching"
    next_step: str
    followup: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    notify: bool = True


class ScreeningImportIn(BaseModel):
    source_name: str | None = None
    schools: list[SchoolIn]
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class InsightIn(BaseModel):
    district_name: str = "เขตพื้นที่การศึกษา"
    priority_schools: list[dict[str, Any]]
    district_stats: dict[str, Any]
    recent_logs: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": now_iso()}


@app.get("/me")
def me(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    return user


@app.get("/schools")
def list_schools(user: CurrentUser = Depends(current_user)) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM schools ORDER BY name").fetchall()
    if user.role == "viewer" and user.school_id:
        rows = [r for r in rows if r["id"] == user.school_id]
    return [dict(r) | {"payload": json.loads(r["payload_json"] or "{}")} for r in rows]


@app.post("/schools/bulk")
def upsert_schools(payload: list[SchoolIn], user: CurrentUser = Depends(require_role("supervisor", "admin"))) -> dict[str, Any]:
    with db() as conn:
        for school in payload:
            conn.execute(
                """
                INSERT INTO schools(id,name,district,flag,red,prev,min15,adjust,sim,supervisor_id,payload_json,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name, district=excluded.district, flag=excluded.flag, red=excluded.red,
                  prev=excluded.prev, min15=excluded.min15, adjust=excluded.adjust, sim=excluded.sim,
                  supervisor_id=excluded.supervisor_id, payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (
                    school.id,
                    school.name,
                    school.district,
                    school.flag,
                    school.red,
                    school.prev,
                    school.min15,
                    school.adjust,
                    school.sim,
                    school.supervisor_id,
                    json.dumps(school.payload, ensure_ascii=False),
                    now_iso(),
                ),
            )
    return {"updated": len(payload)}


@app.post("/screening/imports")
def create_screening_import(payload: ScreeningImportIn, user: CurrentUser = Depends(require_role("admin"))) -> dict[str, Any]:
    if payload.validation_errors:
        raise HTTPException(status_code=422, detail={"message": "Import rejected by validation", "errors": payload.validation_errors})
    upsert_schools(payload.schools, user)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO screening_imports(imported_by,source_name,summary_json,errors_json,created_at) VALUES (?,?,?,?,?)",
            (user.id, payload.source_name, json.dumps(payload.summary, ensure_ascii=False), "[]", now_iso()),
        )
    return {"import_id": cur.lastrowid, "updated": len(payload.schools)}


@app.post("/coaching-logs")
async def create_coaching_log(payload: CoachingLogIn, user: CurrentUser = Depends(require_role("supervisor", "admin"))) -> dict[str, Any]:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO coaching_logs(school_id,teacher,supervisor_id,log_type,next_step,followup,payload_json,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                payload.school_id,
                payload.teacher,
                user.id,
                payload.log_type,
                payload.next_step,
                payload.followup,
                json.dumps(payload.payload, ensure_ascii=False),
                now_iso(),
            ),
        )
    if payload.notify and payload.next_step:
        await send_line_message(f"Next Step: {payload.next_step}\nกำหนดติดตาม: {payload.followup or 'ภายใน 1 สัปดาห์'}")
    return {"log_id": cur.lastrowid}


@app.post("/ai/strategic-insight")
async def strategic_insight(payload: InsightIn, user: CurrentUser = Depends(require_role("supervisor", "admin"))) -> dict[str, str]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    prompt = build_prompt(payload)
    if not api_key:
        return {"mode": "fallback", "text": local_fallback_insight(payload)}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(url, json=body)
        res.raise_for_status()
    data = res.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return {"mode": "gemini", "text": text}


def build_prompt(payload: InsightIn) -> str:
    return (
        "คุณคือผู้ช่วยวิเคราะห์ยุทธศาสตร์การนิเทศการศึกษาไทย ให้ตอบเป็นภาษาไทย กระชับ ใช้ข้อมูลจริงเท่านั้น "
        "แบ่งเป็น: สถานการณ์, โรงเรียนเร่งด่วน, แผน 30/60/90 วัน, ความเสี่ยง, next action สำหรับ ศน.\n\n"
        + json.dumps(payload.model_dump(), ensure_ascii=False, indent=2)
    )


def local_fallback_insight(payload: InsightIn) -> str:
    urgent = payload.priority_schools[:5]
    names = ", ".join([str(s.get("name", "-")) for s in urgent]) or "ยังไม่มีข้อมูล"
    avg_red = payload.district_stats.get("avgRed", "-")
    return (
        f"**สถานการณ์**\nค่าเฉลี่ยนักเรียนกลุ่มแดงของเขตอยู่ที่ {avg_red}% ควรใช้ Priority List เพื่อกำหนดพื้นที่นิเทศเร่งด่วน\n\n"
        f"**โรงเรียนเร่งด่วน**\n{names}\n\n"
        "**แผน 30/60/90 วัน**\n"
        "- 30 วัน: ยืนยันข้อมูลและลงพื้นที่โรงเรียน Priority 5 อันดับแรก\n"
        "- 60 วัน: ทำ Coaching Cycle และติดตาม Next Step รายครู\n"
        "- 90 วัน: เทียบผลก่อน-หลังและถอดบทเรียนโรงเรียนที่ขยับดีขึ้น"
    )


async def send_line_message(message: str) -> None:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    recipient = os.getenv("LINE_DEFAULT_TO", "")
    status = "skipped"
    if token and recipient:
        # LINE Messaging API push message. For LINE Notify legacy setups, replace this function only.
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Authorization": f"Bearer {token}"}
        body = {"to": recipient, "messages": [{"type": "text", "text": message}]}
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, headers=headers, json=body)
        status = "sent"
    with db() as conn:
        conn.execute(
            "INSERT INTO notifications(channel,recipient,message,status,created_at) VALUES (?,?,?,?,?)",
            ("line", recipient, message, status, now_iso()),
        )
