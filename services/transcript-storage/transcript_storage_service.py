import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time

DB_PATH = Path("/data/transcripts.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Transcript Storage Service")

class Transcript(BaseModel):
    session_id: str
    content: str


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS transcripts (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, content TEXT, ts REAL)")
    conn.commit()
    conn.close()

init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/transcripts")
async def write_transcript(t: Transcript):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO transcripts (session_id, content, ts) VALUES (?,?,?)", (t.session_id, t.content, time.time()))
    conn.commit()
    conn.close()
    return {"status": "stored"}

@app.get("/transcripts/{session_id}")
async def read_transcripts(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT content, ts FROM transcripts WHERE session_id=? ORDER BY ts", (session_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"content": r[0], "ts": r[1]} for r in rows] 