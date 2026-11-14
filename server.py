"""Shared travel board. Run with python3 server.py."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("TRAVEL_DATA", ROOT / "data"))
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css")}


class Problem(Exception):
    def __init__(self, status, label):
        self.status, self.label = status, label


def connect():
    db = sqlite3.connect(DATA / "board.sqlite", timeout=8)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(connect()) as db, db:
        db.executescript("""
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, secret BLOB NOT NULL);
          CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL);
          CREATE TABLE IF NOT EXISTS guests (token TEXT PRIMARY KEY, project INTEGER NOT NULL, name TEXT);
          CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY, project INTEGER NOT NULL,
            request TEXT NOT NULL, title TEXT NOT NULL, note TEXT NOT NULL, author TEXT NOT NULL,
            UNIQUE(project, request));
          CREATE TABLE IF NOT EXISTS attempts (client TEXT PRIMARY KEY, since REAL, count INTEGER);
        """)
        db.execute("INSERT OR IGNORE INTO settings VALUES (1, ?)", (secrets.token_bytes(32),))


def field(body, key, limit, required=True):
    value = body.get(key, "")
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise Problem(400, "invalid")
    return value.strip()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def access(db, body, create, client):
    code = field(body, "code", 128).strip().upper()
    if not re.fullmatch("[A-Z0-9-]{8,32}", code, flags=re.ASCII) or not body["code"].isascii():
        raise Problem(400, "codeFormat")
    now = time.time()
    with db:
        db.execute("DELETE FROM attempts WHERE since < ?", (now - 60,))
        db.execute("""INSERT INTO attempts VALUES (?, ?, 1)
                   ON CONFLICT(client) DO UPDATE SET count=count+1""", (client, now))
        count = db.execute("SELECT count FROM attempts WHERE client=?", (client,)).fetchone()[0]
    if count > 30:
        raise Problem(429, "limited")
    secret = db.execute("SELECT secret FROM settings").fetchone()[0]
    digest = hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()
    with db:
        if create:
            try:
                db.execute("INSERT INTO projects(code) VALUES (?)", (digest,))
            except sqlite3.IntegrityError:
                raise Problem(409, "taken")
        project = db.execute("SELECT id FROM projects WHERE code=?", (digest,)).fetchone()
        if project is None:
            raise Problem(404, "missing")
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO guests VALUES (?, ?, NULL)", (hash_token(token), project[0]))
    return {"token": token}


def dispatch(db, path, body, token, client):
    if path in ("/api/create", "/api/join"):
        return access(db, body, path.endswith("create"), client)
    guest = db.execute("SELECT project,name FROM guests WHERE token=?", (hash_token(token),)).fetchone()
    if guest is None:
        raise Problem(401, "expired")
    project, name = guest
    if path == "/api/name":
        name = field(body, "name", 60)
        db.execute("UPDATE guests SET name=? WHERE token=?", (name, hash_token(token)))
        return {"name": name}
    if path == "/api/board":
        cards = db.execute("SELECT title,note,author FROM cards WHERE project=? ORDER BY id", (project,))
        return {"name": name, "cards": [dict(row) for row in cards] if name else []}
    if path == "/api/card" and name:
        title = field(body, "title", 160)
        note = field(body, "note", 6000, False)
        request = field(body, "request", 64)
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM cards WHERE project=? AND request=?", (project, request)).fetchone():
            if db.execute("SELECT count(*) FROM cards WHERE project=?", (project,)).fetchone()[0] >= 100:
                raise Problem(409, "full")
            db.execute("INSERT INTO cards VALUES(NULL,?,?,?,?,?)", (project, request, title, note, name))
        return {"saved": True}
    raise Problem(404, "invalid")


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, kind, data):
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        asset = ASSETS.get(self.path)
        if not asset:
            return self.reply(404, "text/plain", b"Not found")
        self.reply(200, asset[1], (ROOT / "web" / asset[0]).read_bytes())

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536 or self.headers.get_content_type() != "application/json":
                raise Problem(400, "invalid")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise Problem(400, "invalid")
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            with closing(connect()) as db, db:
                result = dispatch(db, self.path, body, token, self.client_address[0])
            status = 200
        except Problem as e:
            status, result = e.status, {"error": e.label}
        except (ValueError, UnicodeError):
            status, result = 400, {"error": "invalid"}
        except sqlite3.Error:
            status, result = 503, {"error": "offline"}
        self.reply(status, "application/json", json.dumps(result).encode())


if __name__ == "__main__":
    initialize()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    print(f"Travel workspace: http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
