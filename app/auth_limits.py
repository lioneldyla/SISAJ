"""Transactional admission limits for password verification; no raw identities in counters."""
import hashlib

WINDOW_SECONDS = 900
ACCOUNT_LIMIT = 5
PEER_LIMIT = 30

def buckets(username, peer):
    values = [('account', username.casefold(), ACCOUNT_LIMIT), ('peer', peer, PEER_LIMIT)]
    return [(scope, hashlib.sha256((scope+'|'+value).encode()).hexdigest(), limit)
            for scope,value,limit in values]

def reserve(c, username, peer, now, postgres=False):
    """Caller commits even a refusal so its audit entry survives HTTP 429."""
    entries = buckets(username,peer)
    if postgres:
        # Stable sorted locks protect count+insert across workers without deadlocks.
        for key in sorted(x[1] for x in entries):
            lock=int(key[:16],16) & ((1<<63)-1)
            c.execute('SELECT pg_advisory_xact_lock(?)',(lock,))
    c.execute('DELETE FROM login_attempts WHERE attempted_at<=?',(now-WINDOW_SECONDS,))
    for scope,key,limit in entries:
        row=c.execute('SELECT COUNT(*) n,MIN(attempted_at) oldest FROM login_attempts WHERE identity_hash=?',(key,)).fetchone()
        if row['n']>=limit:
            return {'scope':scope,'retry_after':max(1,row['oldest']+WINDOW_SECONDS-now)}
    for _,key,_ in entries:
        c.execute('INSERT INTO login_attempts(identity_hash,attempted_at) VALUES(?,?)',(key,now))
    return None

def clear_account(c,username):
    account=buckets(username,'')[0][1]
    # Peer attempts, including successful logins, remain bounded across usernames.
    c.execute('DELETE FROM login_attempts WHERE identity_hash=?',(account,))
