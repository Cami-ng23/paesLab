"""Capa de base de datos: Postgres (Supabase) si existe DATABASE_URL; SQLite local si no."""
import os, sqlite3
from pathlib import Path

URL = os.environ.get('DATABASE_URL')
PG = bool(URL)
SQLITE = Path(os.environ.get('DATA_DIR', Path(__file__).parent)) / 'paeslab.db'
_PK = 'serial primary key' if PG else 'integer primary key'
SCHEMA = [
    f'create table if not exists usuarios(id {_PK},username text unique not null,pw_hash text not null,created text)',
    f'create table if not exists intentos(id {_PK},user_id int,unit text,mode text,ts text,correct int,hints int,gaveup int,skill text)',
    'create table if not exists estado(user_id int,unit text,status text,approved_at text,reviews int default 0,next_review text,primary key(user_id,unit))',
    f'create table if not exists sesiones(id {_PK},user_id int,unit text,mode text,ts text,score int,total int,passed int)',
]

def _conn():
    if PG:
        import psycopg
        from psycopg.rows import dict_row
        # prepare_threshold=None: compatible con el pooler de Supabase
        return psycopg.connect(URL, row_factory=dict_row, prepare_threshold=None, connect_timeout=15)
    c = sqlite3.connect(SQLITE); c.row_factory = sqlite3.Row; return c

def run(q, p=(), fetch=None):
    """Escribe las consultas con ? como marcador; aquí se adaptan a cada motor."""
    c = _conn()
    try:
        cur = c.execute(q.replace('?', '%s') if PG else q, p)
        out = cur.fetchone() if fetch == 'one' else cur.fetchall() if fetch == 'all' else None
        c.commit(); return out
    finally:
        c.close()

def init():
    for s in SCHEMA: run(s)
