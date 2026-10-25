"""PostgreSQL adapter for the existing parameterized SQLite repository queries.
The adapter is deliberately narrow: no user-supplied SQL or placeholder translation.
"""
import re
import psycopg
from psycopg.rows import dict_row


class Cursor:
    def __init__(self, cursor, inserted_id=None):
        self.cursor = cursor
        self.lastrowid = inserted_id
        self.rowcount = cursor.rowcount

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class Connection:
    def __init__(self, url):
        self.raw = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)

    def execute(self, query, args=()):
        ignore = 'INSERT OR IGNORE INTO' in query
        query = query.replace('INSERT OR IGNORE INTO', 'INSERT INTO').replace('?', '%s')
        if ignore:
            query += ' ON CONFLICT DO NOTHING'
        table = re.match(r'\s*INSERT INTO (users|cases|case_events|audit_log)\b', query, re.I)
        if table:
            cursor = self.raw.execute(query + ' RETURNING id', args)
            row = cursor.fetchone()
            return Cursor(cursor, row['id'])
        return Cursor(self.raw.execute(query, args))

    def executescript(self, schema):
        self.raw.execute('SELECT pg_advisory_xact_lock(731024)')
        for statement in schema.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('PRAGMA '):
                self.raw.execute(re.sub(r'\bid INTEGER PRIMARY KEY\b', 'id SERIAL PRIMARY KEY', statement))

    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self): self.raw.close()
