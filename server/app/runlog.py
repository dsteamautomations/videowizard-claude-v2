"""design/142 R1 (SK, 2 Nov 2026): one decision log per run, for every stage, kept with the run (vw2_log). The server writes every write step under
/api/runs/{run}/ and every refusal (a middleware in main.py, on its own connection so a refused step's entry survives the rollback); the assistant adds its
judgement calls with `vw log`; core.output records each stage output. Only the step, the ids it was about and the operator's words are kept, never a body."""
import logging
import re

from .errors import Problem

ABOUT_KEYS = ('unit', 'stage', 'beat_id', 'shot_id', 'gap_id', 'element_id', 'reference_id', 'sub_clip_id', 'clip_id', 'job_id', 'voice_id', 'slide_no', 'key', 'value', 'kind')
WORD_KEYS = ('quote', 'accepted_quote', 'confirm_quote', 'note', 'notes', 'reason')
PATH = re.compile(r'^/api/runs/([0-9a-f-]{36})/([a-z_-]+)(?:/(.*))?$')
FILM_STAGE = {'category': 'brief', 'shape': 'media', 'colours': 'visuals', 'font': 'visuals'}   # design/139: where each choice is asked
SEGMENT_STAGE = {'voice': 'voice', 'analysis': 'analysis', 'options': 'options', 'master': 'master', 'visuals': 'visuals', 'motion': 'visuals', 'assembly': 'assembly',
                 'delivery': 'delivery', 'files': 'media'}
SKIP = {'log'}   # the assistant's entries are written by their own endpoint
log = logging.getLogger('vw2.runlog')


def _short(value, n=300):
    text = ' '.join(str(value).split())
    return text if len(text) <= n else text[:n - 1] + '…'


def stage_of(segment, body):
    if segment in ('output', 'revise', 'decide', 'jobs'):
        return str(body.get('stage') or '')
    if segment == 'film':
        return FILM_STAGE.get(body.get('key'), '')
    return SEGMENT_STAGE.get(segment, segment)


def entry_from(path, body, status, response):
    """The entry for one write under /api/runs/{run}/, or None for paths that are not a run's step."""
    m = PATH.match(path or '')
    if not m or m.group(2) in SKIP:
        return None
    body, response = body if isinstance(body, dict) else {}, response if isinstance(response, dict) else {}
    run_id, segment, rest = m.group(1), m.group(2), m.group(3) or ''
    about = ', '.join(f'{k} {_short(body[k], 80)}' for k in ABOUT_KEYS if body.get(k) not in (None, '', [], {}) and k != 'stage')
    words = next((_short(body[k], 1000) for k in WORD_KEYS if str(body.get(k) or '').strip()), '')
    step = f"{segment}{('/' + rest) if rest else ''}"
    entry = {'run_id': run_id, 'stage': stage_of(segment, body), 'about': about, 'quote': words, 'request_id': body.get('request_id'),
             'by_kind': 'operator' if words else 'assistant', 'by_name': ''}
    if status >= 400:
        return {**entry, 'kind': 'refusal', 'rule': str(response.get('code') or status), 'entry': f"{step} refused: {_short(response.get('message') or '', 1500)}"}
    if response.get('status') == 'rejected' or response.get('act_on'):
        said = list(response.get('refusals') or []) + list(response.get('act_on') or []) + ([response['error']] if response.get('error') else [])
        return {**entry, 'kind': 'refusal', 'rule': 'check', 'entry': f"{step} rejected: " + _short('; '.join(map(str, said)), 1500)}
    made = ', '.join(f'{k} {response[k]}' for k in ('reference_id', 'job_id', 'version', 'status') if isinstance(response.get(k), (str, int)))
    return {**entry, 'kind': 'step', 'rule': '', 'entry': step + (f' ({made})' if made else '')}


def assistant_entry(run_id, stage, body):
    text = ' '.join(str(body.get('text') or '').split())
    if not text:
        raise Problem(422, 'LOG_ENTRY', 'Say what was decided and why (the text of the entry).')
    return {'run_id': run_id, 'stage': stage or '', 'kind': str(body.get('kind') or 'decision'), 'about': _short(body.get('about') or '', 200),
            'rule': _short(body.get('rule') or '', 200) or 'no rule', 'entry': _short(text, 4000), 'by_kind': 'assistant', 'by_name': '', 'quote': '',
            'request_id': body.get('request_id')}


def write(conn, e):
    conn.execute('insert into vw2_log(run_id, stage, kind, about, rule, entry, by_kind, by_name, quote, request_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                 'on conflict do nothing', (e['run_id'], e['stage'], e['kind'], e['about'], e['rule'], e['entry'], e['by_kind'], e['by_name'], e['quote'], e.get('request_id')))


def write_apart(e):
    """On its own connection: a refused step rolls back its own work, never its log entry. A failure here never fails the step (the log is a record)."""
    try:
        from .db import connect
        with connect() as conn:
            write(conn, e)
    except Exception as exc:   # noqa: BLE001
        log.warning('decision log not written for run %s: %s', e.get('run_id'), exc)


def rows(conn, run_id):
    return conn.execute('select * from vw2_log where run_id=%s order by at, id', (run_id,)).fetchall()


def markdown(code, entries):
    """The log as one story: by stage in the order it first appears, each entry by time."""
    out, order = [f'# Decision log: {code}', ''], []
    for r in entries:
        if r['stage'] not in order:
            order.append(r['stage'])
    for st in order:
        out += [f"## {st or 'run'}", '']
        for r in (x for x in entries if x['stage'] == st):
            who = r['by_kind'] + (f" {r['by_name']}" if r.get('by_name') else '')
            line = f"- {str(r['at'])[:19].replace('T', ' ')} · {r['kind']}" + (f" · {r['about']}" if r.get('about') else '') + (f" · rule: {r['rule']}" if r.get('rule') else '')
            out.append(line + f" · {who}: {r['entry']}" + (f' (their words: "{r["quote"]}")' if r.get('quote') else ''))
        out.append('')
    return '\n'.join(out)
