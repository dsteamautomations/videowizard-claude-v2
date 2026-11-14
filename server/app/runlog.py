"""design/142 R1 (SK, 2 Nov 2026): one decision log per run, for every stage, kept with the run (vw2_log). The server writes every write step under
/api/runs/{run}/ and every refusal (a middleware in main.py, on its own connection so a refused step's entry survives the rollback); the assistant adds its
judgement calls with `vw log`; core.output records each stage output. Only the step, the ids it was about and the operator's words are kept, never a body."""
import logging
import re

from .errors import Problem

ABOUT_KEYS = ('unit', 'stage', 'beat_id', 'shot_id', 'shot', 'gap_id', 'gap', 'element_id', 'reference_id', 'ref', 'sub_clip_id', 'clip_id', 'job_id', 'job', 'voice_id', 'voice_ids',
              'slide_no', 'slide', 'decision', 'key', 'value', 'kind')
WORD_KEYS = ('quote', 'accepted_quote', 'confirm_quote', 'note', 'notes', 'reason')
PATH = re.compile(r'^/api/runs/([0-9a-f-]{36})/([a-z_-]+)(?:/(.*))?$')
PAGE = re.compile(r'^/runs/([A-Za-z0-9_-]+)/(visuals|review|voices2)/act$')   # design/145 L1: the pages' buttons
PAGE_STAGE = {'visuals': 'visuals', 'review': 'master', 'voices2': 'voice'}
FILM_STAGE = {'category': 'intake', 'shape': 'media', 'colours': 'visuals', 'font': 'visuals'}   # design/139: where each choice is asked
SEGMENT_STAGE = {'voice': 'voice', 'analysis': 'analysis', 'options': 'options', 'master': 'master', 'visuals': 'visuals', 'motion': 'visuals', 'assembly': 'assembly',
                 'delivery': 'delivery', 'files': 'media'}
PLAIN_KINDS = ('step', 'question', 'answer')   # design/192 (intake 8, brief 7): the prepare of a text stage, a question asked with the question tool, its answer
SKIP = {'log', 'files'}   # the assistant's entries are written by their own endpoint; design/145 L4: upload signs and receipts (the media record says it)
log = logging.getLogger('vw2.runlog')


def _short(value, n=300):
    text = ' '.join(str(value).split())
    return text if len(text) <= n else text[:n - 1] + '…'


def stage_of(segment, body):
    if segment in ('output', 'revise', 'decide', 'jobs'):
        return str(body.get('stage') or '')
    if segment == 'film':
        return FILM_STAGE.get(body.get('key'), '')
    return SEGMENT_STAGE.get(segment, 'run')   # design/145 L4: a step outside a stage (a defect, a claim) is the run's


def entry_from(path, body, status, response):
    """The entry for one write under /api/runs/{run}/ or one page button (/runs/<code>/<page>/act), or None for paths that are not a run's step."""
    body, response = body if isinstance(body, dict) else {}, response if isinstance(response, dict) else {}
    page = PAGE.match(path or '')
    if page:   # design/145 L1: the run is found by its code when the entry is written
        stage = 'options' if page.group(2) == 'review' and body.get('action') == 'record' else PAGE_STAGE[page.group(2)]
        return _entry(None, stage, f"{page.group(2)} page: {body.get('action') or 'action'}", body, status, response, run_code=page.group(1))
    m = PATH.match(path or '')
    if not m or m.group(2) in SKIP:
        return None
    run_id, segment, rest = m.group(1), m.group(2), m.group(3) or ''
    return _entry(run_id, stage_of(segment, body), f"{segment}{('/' + rest) if rest else ''}", body, status, response)


def _entry(run_id, stage, step, body, status, response, run_code=None):
    about = ', '.join(f'{k} {_short(body[k], 80)}' for k in ABOUT_KEYS if body.get(k) not in (None, '', [], {}) and k != 'stage')
    words = next((_short(body[k], 1000) for k in WORD_KEYS if str(body.get(k) or '').strip()), '')
    entry = {'run_id': run_id, 'stage': stage, 'about': about, 'quote': words, 'request_id': body.get('request_id'),
             'by_kind': 'operator' if words or run_code else 'assistant', 'by_name': '', **({'run_code': run_code} if run_code else {})}
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
    kind = str(body.get('kind') or 'decision')
    plain = kind in PLAIN_KINDS   # design/192: a step, a question or an answer is a record of when, not a judgement call: it names no rule
    return {'run_id': run_id, 'stage': stage or '', 'kind': kind, 'about': _short(body.get('about') or '', 200),
            'rule': _short(body.get('rule') or '', 200) or ('' if plain else 'no rule'), 'entry': _short(text, 4000),
            'by_kind': 'operator' if kind == 'answer' else 'assistant', 'by_name': '', 'quote': '',
            'request_id': body.get('request_id')}


def write(conn, e):
    if not e.get('run_id') and e.get('run_code'):   # design/145 L1: a page names its run by code
        row = conn.execute('select id from vw2_runs where code=%s', (e['run_code'],)).fetchone()
        if not row:
            return
        e = {**e, 'run_id': row['id']}
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
