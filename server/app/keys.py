"""design/114: a pool of API keys on the server. Keys come from server/.env (the old single key first, then the comma-separated list), are handed out
in turn, and one that answers a rate limit, a quota or a revocation is set aside for a while. Cooling is kept in this process's memory (SK's answer 2):
a sibling worker learns a cooling key on its own first failed call. No key ever leaves the server; records carry an index, never a key."""
import sys
import time

from .config import settings as _settings

COOL = {'rate': 60, 'quota': 600, 'revoked': 3600}   # seconds (SK's answer 1)
_cooling = {}   # (kind, index) -> monotonic time when the key is usable again
_turn = {}      # kind -> the next index to hand out


def pool(kind, s=None):
    """The keys of a kind, in order: the single key of the old setting, then the list; stripped, empty entries dropped, no duplicates."""
    s = s or _settings()
    name = 'OPENAI_API_KEY' if kind == 'openai' else 'GEMINI_API_KEY'
    single, many = getattr(s, name, None), getattr(s, name + 'S', None)   # a test's settings may carry the single key only
    out = []
    for k in [single.get_secret_value() if single else ''] + (many.get_secret_value() if many else '').split(','):
        k = k.strip()
        if k and k not in out:
            out.append(k)
    return out


def cooling(kind):
    """The indexes cooling right now."""
    now = time.monotonic()
    return sorted(i for (k, i), until in _cooling.items() if k == kind and until > now)


def cool(kind, index, reason='rate'):
    """Set a key aside: 60 s after a rate limit, 10 minutes after a quota or billing answer, an hour after a revocation."""
    _cooling[(kind, index)] = time.monotonic() + COOL[reason]
    print(f'{kind} key {index + 1} cooling {COOL[reason]} s ({reason})', file=sys.stderr, flush=True)


def each(kind, s=None):
    """(index, key) pairs to try, in turn from where the last call left off: the keys not cooling first; when every key is cooling, the one that
    comes back soonest, so the provider itself gives the answer the caller already handles (a requeue, an undecided check)."""
    keys = pool(kind, s)
    n = len(keys)
    if not n:
        return []
    start = _turn.get(kind, 0) % n
    order = [(start + i) % n for i in range(n)]
    _turn[kind] = start + 1
    cold = set(cooling(kind))
    ready = [i for i in order if i not in cold]
    if not ready:
        ready = [min(order, key=lambda i: _cooling.get((kind, i), 0))]
    return [(i, keys[i]) for i in ready]


def reason_of(http_status, category=None):
    """How long a failed call cools its key: None when the failure is not the key's."""
    if category in ('spending_or_billing_limit', 'quota_limit'):
        return 'quota'
    if http_status == 429:
        return 'rate'
    if http_status in (401, 403):
        return 'revoked'
    return None


def gemini(factory, model, use, s=None, **kw):
    """One Gemini call through the pool: factory(key, model, **kw) makes the transport, use(transport) makes the call(s). A 429, a quota answer or a
    revoked key cools that key and the call is made again on the next one; the last error is raised when every key failed. Returns (result, index)."""
    from .video_evidence.transport import GeminiTransportError, classify_failure
    last = None
    for idx, key in each('gemini', s):
        try:
            return use(factory(key, model, **kw)), idx
        except GeminiTransportError as exc:
            reason = reason_of(exc.http_status, classify_failure(exc).get('category')) if exc.code == 'http_error' else None
            if reason is None:
                raise
            cool('gemini', idx, reason)
            last = exc
    if last is None:
        raise RuntimeError('No Gemini key on the server.')
    raise last


def sizes(s=None):
    return {'openai': len(pool('openai', s)), 'gemini': len(pool('gemini', s))}


def reset():
    """Tests only."""
    _cooling.clear()
    _turn.clear()
