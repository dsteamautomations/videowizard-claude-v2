"""design/204 (SK, 15 Nov 2026): the treatment answered on a Claude artifact page.

`page` gives the page its lines as data: the Direction alone until it is accepted, then every gap line, each built by the same function the chat
asks from (`chat_flow._treatment_items`), plus the lines already recorded and the ones back with the assistant. `page_record` records the answers
the operator gave on the page, in one call, through the same decision functions as one answer at a time.

The server stays the record. The page is a form: an answer counts only when the operator says "done" in the chat and the assistant sends it here.
An answer names the item it was given to; an item's id holds its text's digest, so an answer to an older text of a line is ignored by name."""
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO

from PIL import Image

from . import chat_flow as CF
from . import film as F
from . import runlog
from . import visuals_stage as V
from .errors import Problem

HOW = ('The operator answers this step on a page, not on a card. '
       '1. If `url` is empty, publish the page with the Artifact tool: `file_path` is `page_file`, the title is `title`, `capabilities` exactly as given, an icon of your choice; '
       'then run `vw visuals page --url "<the link it gives>"`. If there is no Artifact tool, or it fails, run `vw visuals next` and show the card instead, and say once that the page is not available. '
       'If `republish` is true, the page at the link was published by an older tool: publish it again to the same link (the Artifact tool with `file_path` `page_file`, `url` the link '
       'and `capabilities` again, exactly as given), then run `vw visuals page --url` with that link. '
       '2. Send the pictures before the round, when there are any (design/210). For each batch in `picture_batches`: ArtifactData, action "batch", `url` the page\'s link, `writes` the batch, '
       'unchanged. If a batch fails, or a picture stays grey on the page, run `vw visuals page --pictures-again` and send what it gives; if that fails too, stop here, '
       'run `vw visuals next` and ask this step in the chat. Then for each list in `zoom_uploads`: the Artifact tool, '
       'action "publish", `url` the page\'s link, `asset` true, `file_paths` the list; save its answer, exactly as it came, to `uploaded_file` with the Write tool, and run '
       '`vw visuals page --uploaded "<that file>"`: it gives one more batch in `picture_batches`, sent the same way. If an upload fails, go on, and tell the operator that the large pictures '
       'are not available on the page. '
       '3. Write this round to the page with the ArtifactData tool: action "set", `url` the page\'s link, collection "rounds", doc_id `round`, file_path `round_file`. Type none of its content. '
       '4. Say to the operator, as your own one line: "Open this page, answer each line, then tell me you are done:" and the link. Then wait. Do not post the lines in the chat as well. '
       '5. When the operator says done: ArtifactData, action "list", collection `answers_collection`, out_dir `answers_dir`; then run `vw visuals page --record`. '
       'If it lists pictures the operator added on the page (`own_fetch`), fetch each one: the Artifact tool, action "read", `url` the page\'s link, `path` the picture\'s id, '
       '`out_dir` `own_dir`; then run `vw visuals page --record` again: their lines are recorded then (design/210). '
       '6. It prints what was recorded and writes the next round: do steps 2 and 3 again with the new `round` and `round_file`, then follow `then`. '
       'An answer the operator gives in the chat instead is recorded with `vw visuals decide`, as before.')
CAPABILITIES = {'db': {'rules': [{'path': path, 'read': 'view', 'write': 'owner'} for path in ('rounds', 'pics', 'zoom')]}, 'assets': {}, 'user': {}}   # only the page's owner writes: the lines, the answers and the pictures (design/210: `pics` the small pictures, `zoom` the links of the large ones in the file store)


# ---------- design/210 (SK, 16 Nov 2026): pictures on the page ----------
# A line names its pictures: `pics`, a list of `pic(key, label)` in the order to show. `page` then lists once, under `pictures`, the two sizes
# of every picture on the round's lines: a small one the page shows in a row and a large one it opens on a click. The tool fetches both by
# their storage keys and the assistant sends them to the page.

PIC_SIZES = {'thumb': ('.page-thumb.jpg', 360, 60), 'zoom': ('.page-zoom.jpg', 1600, 78)}   # per size: where it is stored beside the picture, its long side at most, its JPEG quality
_MADE = set()   # ponytail: the sizes this process knows are stored, so a page with many pictures asks the storage once each; a shared record if servers multiply
PIC_WORKERS = 8   # pictures whose sizes are made at one time: the storage reads and writes at once, as `analysis_jobs.REUSE_READS`


def pic_code(key):
    """A picture's code on the page: the same for the same storage key in every round, so a picture is sent once."""
    return 'p' + hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]


def pic(key, label):
    """One picture of a line: its code, the label shown under it and, until `page` answers, its storage key."""
    return {'code': pic_code(key), 'label': str(label), '_key': key}


def shrink(data, side, quality):
    """A picture as a JPEG whose long side is at most `side`: shrunk in its own shape, never cropped, never enlarged; a see-through one on white."""
    img = Image.open(BytesIO(data))
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGBA')
        white = Image.new('RGB', img.size, 'white')
        white.paste(img, mask=img.getchannel('A'))
        img = white
    img = img.convert('RGB')
    img.thumbnail((side, side))
    out = BytesIO()
    img.save(out, 'JPEG', quality=quality, optimize=True)
    return out.getvalue()


def sized(store, key, which):
    """The storage key of a picture's small (`thumb`) or large (`zoom`) size: made from the full picture once, stored beside it, reused after."""
    suffix, side, quality = PIC_SIZES[which]
    out = key + suffix
    if out not in _MADE:
        if not store.exists(out):
            store.put(out, shrink(store.get(key), side, quality), 'image/jpeg')
        _MADE.add(out)
    return out


def _with_pictures(store, page):
    """The page's answer with `pictures`: for every picture code on its lines, once, the storage keys of its two sizes. A picture that cannot
    be read or shrunk is marked `missing` on its line and named in `pictures_failed`; the rest of the page is built. A page with no picture
    is left as it is."""
    keys = {}   # each picture once, in the order of the lines
    for line in page['lines']:
        for p in line.get('pics') or []:
            keys.setdefault(p['code'], p.pop('_key', None))

    def both(item):
        code, key = item
        try:
            return {'code': code, 'thumb': sized(store, key, 'thumb'), 'zoom': sized(store, key, 'zoom')}
        except Exception:   # a broken or half-written picture never fails the page
            return None
    found, failed = {}, []
    if keys:   # ponytail: the sizes are made inside this call, PIC_WORKERS pictures at a time; a job if a film's first page of many pictures still takes too long
        with ThreadPoolExecutor(max_workers=PIC_WORKERS) as pool:
            found = dict(zip(keys, pool.map(both, keys.items())))
    named = set()
    for line in page['lines']:
        for p in line.get('pics') or []:
            if not found[p['code']]:
                p['missing'] = True
                if p['code'] not in named:   # named once, on the first line that shows it
                    named.add(p['code'])
                    failed.append(f"{line.get('title') or line.get('key')}: {p['label']}")
    if found:
        page['pictures'] = [v for v in found.values() if v]
    if failed:
        page['pictures_failed'] = failed
    return page


def _title(item):
    return CF._split(item['question'])[0].split(' (changed')[0]


def _motion_line(run, draft):
    """design/205 (SK, 15 Nov 2026): the film's motion style, asked on the page beside the Direction: every style the server holds, the one
    recommended for the film's category first with its reason, one button each, and what the page needs to play a sample of each. None for a
    film from before the film record; a recorded line once it is chosen."""
    if F.older(run):
        return None
    st, chosen, head = F.styles(), F.motion(run), {'line': 'l00', 'key': 'motion'}
    if chosen:
        return {**head, 'title': f"How things move in this film: {st.get(chosen, {}).get('title') or chosen}", 'state': 'recorded'}
    cat = F.category(run)
    order = F.recommend_styles(cat)
    first, label = st[order[0]], str(cat or 'not recorded').replace('-', ' ')
    why = (f"this film's category is {label}, and {first['title']} is the style filed for {first['for']}" if cat in first['first'] else
           f"no style is filed first for this film's category ({label}), and {first['title']} moves the least")
    idea = ((draft or {}).get('direction_parts') or {}).get('idea')
    return {**head, 'title': 'How things move in this film (the motion style)', 'state': 'open', 'item': 'motion:choose',
            'text': f"The motion style decides how drawn pictures, labels and figures appear and move in this film. It is asked once.\nRecommended: {first['title']}, because {why}. "
                    f"All {len(order)} styles are below; \"Show me\" plays a rough sample of each.",
            'rows': [[st[n]['title'] + (' (recommended)' if n == order[0] else ''), f"For {st[n]['for']}. {st[n]['text'].split(chr(10) + chr(10))[0]}"] for n in order],
            'buttons': [{'label': st[n]['title'], 'choice': n, 'needs_words': False} for n in order],
            'styles': [{'name': n, 'title': st[n]['title']} for n in order],
            'sample': {'title': str(run.get('title') or run.get('code') or 'This film'), 'words': str(idea or run.get('title') or run.get('code') or 'This film'), 'frame': F.frame(run) or '16:9'}}


def _log(conn, run, key, choice, words, refused=''):
    """design/205: each answer given on the page is a line of the run's log, by the operator, with their words (or the button they chose)."""
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'refusal' if refused else 'step', 'about': f'line {key}, choice {choice}', 'rule': 'page' if refused else '',
                        'entry': f'visuals/page/record refused: {refused}' if refused else 'visuals/page/record: answered on the page', 'by_kind': 'operator', 'by_name': '',
                        'quote': words, 'request_id': None})


PLAN_NEXT = 'Every gap of the plan is accepted. Go on with `vw visuals next`: it gives the next decision.'
PLAN_BACK = ('No line waits for the operator now: change the plan for the lines that are back with you (their words are on each), propose it again, '
             'then `vw visuals page`.')


ROUND_BYTES = 200_000   # one document of the page's database holds at most 256 KiB (the artifact runtime's contract); a round is one document


def _at_plan(ctx):
    """The page's step: the plan once one is proposed and no treatment draft is open."""
    return bool(ctx['plan']) and not ctx['session'].get('treatment_draft')


def _table(session, gap, selection=None):
    rows, total = CF._gap_rows(session, gap, selection)
    mix = Counter(r[2] for r in rows)
    return {'cols': CF.GAP_COLS, 'table': rows, 'total': total, 'mix': 'Made as: ' + ', '.join(f'{n} × {kind}' for kind, n in mix.items())}


def _buttons(item):
    return [{'label': b['label'], 'choice': b['choice'], 'needs_words': bool(b.get('needs_words'))} for b in item['buttons']]


def _plan_page(ctx, base):
    """design/206 (SK, 16 Nov 2026): the plan on the page. Every plan question is on this one round, so one "done" answers the step: the shared
    rules first (design/191), then the gaps in the film's order. A gap to accept shows its shots as a table, its totals and what changed since it
    was accepted, and above the table its `warnings`, the plain lines to read before answering (design/207; a film-wide one is on the gap it is
    attached to); a gap offered two ways shows each way with its own shots, and taking a way accepts the gap; an accepted gap is `recorded`
    (`reopen` while the plan is open); one sent back is `with_assistant` with the operator's words."""
    session, plan, store = ctx['session'], ctx['plan'], ctx['store']
    items, revising = CF._plan_items(ctx)
    pending, revisions = session.get('shared_pending') or {}, session.get('revisions') or {}
    waits = [g['gap_id'] for g in plan['gaps'] if g['gap_id'] in pending]
    treated = session.get('treatment') or {}
    agreed = {e.get('gap_id'): e for e in treated.get('gaps') or [] if isinstance(e, dict)}
    plan_open, lines = bool(items or revising), []
    for n in (400, 160, 80, 40):   # design/207: the world of the film first, read only; a very large one has its cells cut shorter, so the gaps keep their room in the round
        world = CF._world_rows(plan, n)
        if len(json.dumps(world, ensure_ascii=False).encode('utf-8')) <= ROUND_BYTES // 2:
            break
    if world:
        lines.append({'key': 'world', 'title': 'The world of this film', 'state': 'recorded', 'rows': world})
    shared = next((i for i in items if i['kind'] == 'plan shared'), None)
    if shared:
        try:
            changes = (V.shared_change(store, session, plan) or {}).get('changes') or []
        except (Problem, StopIteration, KeyError, TypeError, ValueError):
            changes = []
        many = len(waits) != 1
        lines.append({'key': 'shared', 'title': "The film's shared rules changed", 'state': 'open', 'item': shared['id'], 'changed': True, 'changes': CF._changes(changes), 'waits': waits,
                      'text': f"{len(waits)} gap{'s have' if many else ' has'} the same shots as you accepted: {', '.join(waits)}. One answer here covers {'all of them' if many else 'it'}. "
                              f"Until you answer, the work on {'their' if many else 'its'} shots waits.", 'buttons': _buttons(shared)})
    elif "the film's shared rules" in revising:
        lines.append({'key': 'shared', 'title': "The film's shared rules", 'state': 'with_assistant', 'note': (session.get('shared_revision') or {}).get('notes') or '', 'waits': waits})
    for gap in plan['gaps']:
        gid = gap['gap_id']
        head = {'key': gid, 'title': f'Gap {gid}' + (f" · {gap['title']}" if gap.get('title') else '')}
        ask = next((i for i in items if i['id'].startswith((f'gap:{gid}:', f'choice:{gid}:'))), None)
        entry = agreed.get(gid) or {}
        accepted = [[k, str(v)] for k, v in (CF._shot_rows(entry, 'reasons_missing' in treated) if entry else []) if v not in (None, '', [])]   # design/207: the shots and the two reasons accepted at the treatment
        seen = {**({'text': f"What you accepted in the treatment: {entry['picture']}"} if entry.get('picture') else {}), **({'rows': accepted} if accepted else {})}
        warned = V.warning_lines(session, gap, plan)   # design/207: the plain lines the operator reads before answering, from the function the server's page uses
        if warned:
            seen['warnings'] = warned
        if gid in revisions:
            lines.append({**head, 'state': 'with_assistant', 'note': revisions[gid].get('notes') or ''})
        elif ask and ask['kind'] == 'plan choice':
            ways = sorted(gap['choices'][:4], key=lambda c: c['id'] != gap.get('recommended_choice'))
            lines.append({**head, 'state': 'open', 'item': ask['id'], **seen, 'cols': CF.GAP_COLS,
                          'ways': [{'id': c['id'], 'title': c['title'], 'recommended': c['id'] == gap.get('recommended_choice'),
                                    'rows': [['What it is', c['description']], ['Why', c['why']], ['The cost of it', c['tradeoff']]], **_table(session, gap, {'choice_id': c['id']})} for c in ways],
                          'buttons': [{'label': 'Take ' + b['label'], 'choice': 'way:' + b['choice'], 'needs_words': False} for b in ask['buttons']]
                                     + [{'label': 'Change this', 'choice': 'change', 'needs_words': True}]})
        elif ask:
            card = ask['_card']
            lines.append({**head, 'state': 'open', 'item': ask['id'], **seen, 'changed': bool(card.get('c')), 'changes': card.get('ch') or [], **_table(session, gap), 'buttons': _buttons(ask)})
        elif gid in session['accepted'] and gid not in pending:
            lines.append({**head, 'state': 'recorded', **({'reopen': True} if plan_open else {})})
    held = 0   # ponytail: a round over the document's size shows the first gaps only and the rest after the next "done"; one document per line if plans grow this large
    while len(json.dumps(lines, ensure_ascii=False).encode('utf-8')) > ROUND_BYTES:
        last = next((i for i in range(len(lines) - 1, -1, -1) if lines[i]['state'] == 'open' and lines[i]['key'] != 'shared'), None)
        if last is None or len([l for l in lines if l['state'] == 'open' and l['key'] != 'shared']) == 1:
            break
        del lines[last]
        held += 1
    refused = session.get('page_refused') or {}
    lines = [{'line': f'l{n:02d}', **line, **({'refused': refused[line['key']]} if line['key'] in refused else {})} for n, line in enumerate(lines, 1)]
    count = lambda state: len([l for l in lines if l['state'] == state and l['key'] not in ('shared', 'world')])
    left = len([l for l in lines if l['state'] == 'open'])
    try:   # design/207: the plan's estimate against the film's limit, by the sum the check uses; left out when it cannot be worked out (a film with no picture AI named)
        sets = V.set_estimate(ctx['run'], session, plan)   # design/209: what the reference sets may cost, beside the shots
        cost = (f"; estimate ₹{V.plan_estimate(ctx['run'], V.routes(plan, V._fps(session) or 25)):g} "
                + (f"for the shots, and up to ₹{sets['inr']:g} for {sets['sets']} reference set{'' if sets['sets'] == 1 else 's'}, " if sets['sets'] else '') + f"of the ₹{V.cap_of(session):g} limit")
    except (Problem, KeyError, TypeError, ValueError):
        cost = ''
    return {**base, 'step': 'Plan', 'open': bool(left), 'lines': lines,
            'summary': f"{len(plan['gaps'])} gaps: {count('open')} to answer, {count('recorded')} recorded, {count('with_assistant')} with the assistant"
                       + (f", {len(waits)} behind the shared rules" if waits else '') + (f", {held} more after these" if held else '') + cost + '.',
            'note': f'This plan is long: {held} more gap(s) appear here after you answer these and say done in the chat.' if held else
                    'Answer each line, then say done in the chat.' if left else 'The assistant is changing the lines you sent back; they will appear here.' if plan_open
                    else 'Every gap of the plan is accepted. Nothing more to answer here.'}


SPEC_STEP = 'Drawings and materials'
SPEC_NEXT = 'Every drawing and material is approved. Go on with `vw visuals next`: it gives the next decision.'
SPEC_BACK = ('No line waits for the operator now: correct the drawings and materials that are back with you (their words are on each) in out/visual-plan.json, '
             'propose the plan again, then `vw visuals page`.')


def _spec_lines(ctx):
    """design/209 (SK, 16 Nov 2026): the lines of the step after the plan: once no plan line is open or back with the assistant, every material's
    facts and every drawing's parts and sizes, the materials first. An open line is the chat's own waiting item (the same id, the same buttons)
    with the plain parts of `chat_flow._spec_views`; an approved one is `recorded` and keeps its parts, to be read back; one sent back is
    `with_assistant` with the operator's words. Empty while the plan is open, or when the film has no such spec."""
    if any(CF._plan_items(ctx)):
        return []
    views = CF._spec_views(ctx)
    items = {i['id']: i for i in CF._waiting_items(ctx) if i['kind'] == 'spec'} if any(v['state'] == 'open' for v in views) else {}
    lines = []
    for v in views:
        head = {'key': v['key'], 'title': v['title']}
        if v['state'] == 'with_assistant':
            lines.append({**head, 'state': 'with_assistant', 'note': v['note']})
        elif v['state'] == 'recorded':
            lines.append({**head, 'state': 'recorded', 'spec': v['spec']})
        elif v['item'] in items:
            lines.append({**head, 'state': 'open', 'item': v['item'], 'ask': v['ask'], 'spec': v['spec'], 'buttons': _buttons(items[v['item']])})
    return lines


def _spec_page(ctx, base, lines):
    """The step's round: every line on one round, so one "done" answers the step. A round over the document's size first leaves out the parts of
    the recorded lines, then holds the later lines to answer for the next "done", as the plan does."""
    many = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    kinds = [many(n, word) for n, word in ((len([l for l in lines if l['key'].startswith('element:')]), 'material'),
                                           (len([l for l in lines if not l['key'].startswith('element:')]), 'drawing')) if n]
    held = 0
    while len(json.dumps(lines, ensure_ascii=False).encode('utf-8')) > ROUND_BYTES:
        read = next((l for l in reversed(lines) if l['state'] == 'recorded' and 'spec' in l), None)
        open_ = [i for i, l in enumerate(lines) if l['state'] == 'open']
        if read:
            del read['spec']
        elif len(open_) > 1:
            del lines[open_[-1]]
            held += 1
        else:
            break
    refused = ctx['session'].get('page_refused') or {}
    lines = [{'line': f'l{n:02d}', **line, **({'refused': refused[line['key']]} if line['key'] in refused and line['state'] == 'open' else {})} for n, line in enumerate(lines, 1)]
    count = lambda state: len([l for l in lines if l['state'] == state])
    left = count('open')
    return {**base, 'step': SPEC_STEP, 'open': bool(left), 'lines': lines,
            'summary': f"{' and '.join(kinds)}: {left} to answer, {count('recorded')} recorded, {count('with_assistant')} with the assistant" + (f', {held} more after these' if held else '') + '.',
            'note': f'This list is long: {held} more appear here after you answer these and say done in the chat.' if held else
                    'Answer each line, then say done in the chat.' if left else 'The assistant is correcting the lines you sent back; they will appear here.' if count('with_assistant')
                    else 'Every drawing and material is approved. Nothing more to answer here.'}


SPEC_REFUSED = ('The server refused an answer on the page; its reason is in `refused` and on the line. When the reason is about the drawing itself (a size with nothing '
                'tried, a missing "not to scale"), it is yours to fix, not the operator\'s: complete that drawing in the plan, check, propose again, then `vw visuals page`. '
                'When the reason is about the answer (no words for a correction), tell the operator and give them the link again.')


DRAW_STEP = 'Reference drawings'
DRAW_NEXT = 'Every reference drawing is approved. Go on with `vw visuals next`: it gives the next decision.'
DRAW_BACK = ('No line waits for the operator now: redraw the things that are back with you (their words are on each), one thing at a time, and send each set again '
             '(`vw drawing set --element E --file work/drawing/E/set.json`), then `vw visuals page`.')
DRAW_REFUSED = 'The server refused an answer on the page; its reason is in `refused` and on the line: tell the operator and give them the link again.'


def _drawing_lines(ctx):
    """design/210: the lines of the step after the drawings and materials: every thing's drawing set, while one waits for the operator or is back
    with the assistant. An open line is the chat's own item (`chat_flow._drawing_items`: the same id, the same buttons) with every labelled
    sheet as a picture, the facts with where each came from and the assumed sizes on one line; an approved set is `recorded` and keeps its
    pictures and facts; one sent back is `with_assistant` with the operator's words. Empty when no set waits."""
    rows = ctx['session'].get('drawings') or {}
    if not any(r.get('status') in ('proposed', 'rejected') for r in rows.values()):
        return []
    items = {i['id']: i for i in CF._drawing_items(ctx)}
    names = CF._names(ctx['plan'])
    order = {e['id']: n for n, e in enumerate(ctx['plan'].get('elements') or [])}
    lines = []
    for eid, r in sorted(rows.items(), key=lambda row: order.get(row[0], len(order))):   # the things in the plan's order
        head = {'key': f'drawing:{eid}', 'title': names.get(eid) or r.get('name') or eid}
        if r.get('status') == 'rejected':
            lines.append({**head, 'state': 'with_assistant', 'note': (r.get('verdict') or {}).get('notes') or ''})
            continue
        item = items.get(f"drawing:{eid}:{r['sha256'][:10]}")
        if r.get('status') != 'approved' and not item:
            continue
        n = len(r['views'])
        seen = {'pics': [pic(v['labelled_key'], v['name']) for v in r['views']],
                'facts': [[str(f.get('what') or ''), f"{f.get('value', '')} {f.get('unit') or ''}".strip(), str(f.get('source') or '')] for f in r.get('facts') or [] if not f.get('assumed')],
                'assumed': '; '.join(r.get('assumed') or [])}
        seen = {k: v for k, v in seen.items() if v}
        if item:
            lines.append({**head, 'state': 'open', 'item': item['id'], 'ask': 'Is the shape and arrangement right?', **seen, 'buttons': _buttons(item),
                          'text': f"{n} sheet{'' if n == 1 else 's'}. Each sheet says what it shows and what it is for. These drawings go to the picture AI as references, "
                                  'so check them against what you know of the thing. Choose a picture to see it large.'})
        else:
            lines.append({**head, 'state': 'recorded', **seen})
    return lines


def _drawing_page(ctx, base, lines):
    """The step's round: every thing on one round, so one "done" answers the step. Its pictures are not in the round (the page reads each by its
    code); a round whose text is over the document's size first leaves out the facts of the recorded lines, then holds the later lines to
    answer for the next "done", as the plan does."""
    held = 0
    while len(json.dumps(lines, ensure_ascii=False).encode('utf-8')) > ROUND_BYTES:
        read = next((l for l in reversed(lines) if l['state'] == 'recorded' and 'facts' in l), None)
        open_ = [i for i, l in enumerate(lines) if l['state'] == 'open']
        if read:
            del read['facts']
        elif len(open_) > 1:
            del lines[open_[-1]]
            held += 1
        else:
            break
    refused = ctx['session'].get('page_refused') or {}
    lines = [{'line': f'l{n:02d}', **line, **({'refused': refused[line['key']]} if line['key'] in refused and line['state'] == 'open' else {})} for n, line in enumerate(lines, 1)]
    count = lambda state: len([l for l in lines if l['state'] == state])
    left = count('open')
    return {**base, 'step': DRAW_STEP, 'open': bool(left), 'lines': lines,
            'summary': f"{len(lines)} thing{'' if len(lines) == 1 else 's'}: {left} to answer, {count('recorded')} recorded, {count('with_assistant')} with the assistant" + (f', {held} more after these' if held else '') + '.',
            'note': f'This list is long: {held} more appear here after you answer these and say done in the chat.' if held else
                    'Look at each picture, answer each line, then say done in the chat.' if left else 'The assistant is drawing again the things you sent back; they will appear here.'}


# ---------- design/210 part 2 (SK, 16 Nov 2026): the reference round on the page, in two screens ----------
# "References" is the round's step 1: every person, object and place in one visit; each answer is kept and the step is recorded once, when
# every thing has its answer (`chat_flow.round_close`). "References: the sets" is step 2: every set that is back, that was not made, that is
# being made and that is approved. Each open line is the chat's own item (`chat_flow._round_items(ctx, every=True)`): the same id, the same
# buttons, the same run function; a button that leads to a paid set says so with the price of one set, and that label is logged as the
# operator's word.

REFS_STEP, SETS_STEP = 'References', 'References: the sets'
REFS_START = ('The references come next: write out/reference-round.json and send it (`vw visuals round --file out/reference-round.json`), then run `vw visuals page`: '
              'the operator answers every person, object and place there, in one visit.')
REFS_GO = 'The references come next: run `vw visuals page`. The operator answers every person, object and place there, in one visit.'
REFS_KEPT = 'Kept, not recorded yet: the sets are made when every thing is answered. Choose again to change it.'
SETS_KEPT = 'Kept, not recorded yet: it is recorded when the sets still being made are back. Choose again to change it.'
SETS_HELD = 'Kept, not recorded yet: the reason is on this line. Choose again to change it.'
SETS_WAIT = 'The sets are being made. Wait for them (`vw visuals status --wait 900`), then run `vw visuals page`: the operator judges the sets there, in one visit.'
SETS_STAND = ('No set waits for the operator now, and none is being made: the answers kept wait, and the reason is on each line. Tell the operator; when it is settled, '
              'run `vw visuals page`.')
SETS_NONE = 'No set waits for the operator on the page now. Go on with `vw visuals next`: it gives the next decision.'
ROUND_NEXT ='The reference round is complete. Go on with `vw visuals next`: it gives the next decision (the stills and the graphics are not on the page yet).'
ROUND_REFUSED = 'The server refused an answer on the page; its reason is in `refused` and on the line: tell the operator and give them the link again.'
OWN_PERMISSION = "A real person's photo is used only with their permission. Write in the box on this line that you have it, then add the photo again."
OWN_MISSING = 'Your own picture did not reach VideoWizard. Add it again on this line, or give it to the assistant in the chat.'
KIND_WORDS = {'person': 'a person', 'place': 'a place', 'object': 'an object', 'material': 'a material', 'process': 'a process', 'technique': 'a technique'}
OWN_FILE = 'a PNG, JPEG or WebP file up to 15 MB'


def _money(ctx):
    """(spent, the film's limit, the price of one set) and the words a paid button carries."""
    budget = V._set_budget(ctx['run'], ctx['session'], V.visuals_spend(ctx['conn'], ctx['run']))
    return budget, f'paid, about ₹{budget[2]:,.0f}'


def _drawn(session, eid):
    return (session.get('drawings') or {}).get(eid, {}).get('status') == 'approved'


def _round_buttons(item, paid):
    """The chat item's own buttons, every one of them, for the page: one that leads to a paid set says so, with the price of one set."""
    def label(b):
        if b['choice'] in ('no', 'correct'):
            return f"{b['label']} ({paid}: the set is made again)"
        return f"{b['label']} ({paid})" if b['choice'] in ('make', 'standin') or (b['choice'] == 'approve' and item.get('_makes')) else b['label']
    return [{'label': label(b), 'choice': b['choice'], 'needs_words': bool(b.get('needs_words'))} for b in item['buttons'] + list(item.get('other_choices') or [])]


def _own_line(ctx, item, paid):
    """"Use my own picture" on a thing's line: its label (with the price when a set is made from the picture), whether the thing is a person,
    whether the permission is already recorded, and what the picture then does, in plain words."""
    session, eid, person, step1 = ctx['session'], item['_eid'], item['_person'], item['id'].startswith('round1:')
    drawn = step1 and _drawn(session, eid)
    text = (f"Add this person's own photo, {OWN_FILE}: their set is made from it. A real person's photo is used only with their permission: write first, in your own words, that you have it." if person else
            f'When the footage picture is not right, add your own, {OWN_FILE}: its set is made from your picture and the drawings.' if drawn else
            f'When the footage picture is not right, or there is none, add your own, {OWN_FILE}: it becomes the reference of this thing, and no picture is made.' if step1 else
            f'When none of these is right, add your own picture, {OWN_FILE}: every shot of this thing then starts from it.' if item['id'].startswith('set:') else
            f'Add your own picture, {OWN_FILE}: it becomes the reference of this thing, and no set is made.')
    return {'label': 'Use my own picture' + (f' ({paid}: the set is made from it)' if person or drawn else ''), 'person': person,
            'permitted': not person or bool(V.likeness_of(session, eid)), 'text': text}


def _thing(plan, eid):
    e = next(x for x in plan['elements'] if x['id'] == eid)
    return f"{e.get('name') or eid} ({KIND_WORDS.get(e.get('kind'), 'a thing')})"


def _ask(item):
    q = CF._split(item['question'])[1]
    return q[:1].upper() + q[1:]


def _refs_lines(ctx):
    """The lines of step 1, in the plan's order, and how many sets a yes to every thing would make: one line per thing, its footage pictures
    (up to four, as the chat shows them), what a yes does in plain words, the chat item's buttons, a comment box and "Use my own picture".
    A thing answered at an earlier "done" stays open, to be changed, and says what is kept."""
    session, plan, run = ctx['session'], ctx['plan'], ctx['run']
    items = {i['_eid']: i for i in CF._round_items(ctx, every=True)}
    _budget, paid = _money(ctx)
    lines = []
    for eid in [e['id'] for e in plan['elements'] if e['id'] in items]:
        item = items[eid]
        person, drawn = item['_person'], _drawn(session, eid)
        live = [f for f in item['_frames'] if (session['references'].get(f) or {}).get('status') in ('candidate', 'approved')][:4]
        seen = ('This is how {x} looks in your footage. ' if live else 'Your footage has no picture of {x}. ').format(x='this person' if person else 'it')
        text = (seen + f"A reference set is made for every person{', even with footage' if live else ''} ({paid}): from the description, or from their photo when you have their permission." if person else
                seen + f'It has approved reference drawings, so a reference set is made from them, even with footage ({paid}).' if drawn else
                seen + 'A yes takes the footage picture as its reference: no picture is made and nothing is paid.' if live else
                seen + f'A yes has a reference set of three pictures made ({paid}).' if item['_makes'] else
                'Your own picture is its reference: no picture is made and nothing is paid.')
        kept = item['_kept']
        lines.append({'key': f'ref:{eid}', 'title': _thing(plan, eid), 'state': 'open', 'item': item['id'], 'ask': _ask(item), 'text': text + (' Choose a picture to see it large.' if live else ''),
                      **({'pics': [pic(CF._ref_key(run, f), f'Footage picture {n}') for n, f in enumerate(live, 1)]} if live else {}),
                      'buttons': _round_buttons(item, paid), 'comment': True, 'own': _own_line(ctx, item, paid),
                      **({'kept': str(kept.get('quote') or kept.get('verdict')), 'kept_note': REFS_KEPT} if kept else {})})
    return lines, len([i for i in items.values() if i['_makes']])


def _sets_lines(ctx):
    """The lines of step 2, in the plan's order: a set that is back (its three pictures, each alone, lettered; a thing's picture carries the
    choice that takes it as the starting picture), a set that was not made (with the cause the server gives), a set being made, and an
    approved set, which keeps its pictures."""
    session, plan, run = ctx['session'], ctx['plan'], ctx['run']
    rd = session['round']
    items = {i['_eid']: i for i in CF._round_items(ctx, every=True)}
    _budget, paid = _money(ctx)
    by_n = lambda rows: sorted(rows, key=lambda r: int(r.get('set_n') or 1))
    lines = []
    for eid in [e['id'] for e in plan['elements'] if e['id'] in rd['elements']]:
        row, item = rd['elements'][eid], items.get(eid)
        if row.get('ignored') or row.get('from_footage'):
            continue
        head = {'key': f'set:{eid}', 'title': _thing(plan, eid)}
        if item and item['id'].startswith('set:'):
            person, buttons, a = item['_person'], _round_buttons(item, paid), item['_kept']
            choice = None if not a else ('use:' + a['golden']) if a.get('golden') else a['verdict']
            said = next((b['label'] for b in buttons if b['choice'] == choice), 'Use my own picture' if a and a.get('golden') else choice)
            lines.append({**head, 'state': 'open', 'item': item['id'], 'ask': _ask(item),
                          'text': (f"Three pictures of the same {'person' if person else 'thing'}. Choose a picture to see it large."
                                   + ('' if person else ' Choose the one every shot starts from: under the picture, or with a button below.')),
                          'pics': [{**pic(CF._ref_key(run, r['id']), CF.LETTERS[n]), **({} if person else {'choice': 'use:' + r['id']})} for n, r in enumerate(item['_rows'])],
                          'buttons': buttons, 'comment': True, 'own': _own_line(ctx, item, paid),
                          **({'kept': said, 'kept_note': SETS_KEPT if V._round_pass(session, rd) == 'making' else SETS_HELD} if a else {})})
        elif item:   # its set was not made, or the picture service refused a person's photo
            cause = item.get('_cause')
            lines.append({**head, 'state': 'open', 'item': item['id'], 'ask': _ask(item), 'buttons': _round_buttons(item, paid), 'comment': True, 'own': _own_line(ctx, item, paid),
                          'text': "The picture service refused this person's photo." if item['id'].startswith('likeness:') else
                                  'Its reference set was not made' + (f': {cause}. It can be made when that is settled.' if cause else
                                                                      f": {V._fail_words(item.get('_error')).rstrip('.').lower()}." if item.get('_error') else '.')})
        elif V._set_rows(session, eid, row.get('set'), ('generating',)):
            lines.append({**head, 'state': 'making', 'note': 'Its set is being made.'})
        else:
            done = by_n(V._set_rows(session, eid, row.get('set'), ('approved',)))
            if not done:
                continue
            gold = V.golden_of(session, eid)
            mine = session['references'].get(gold) if gold and not any(r['id'] == gold for r in done) else None
            lines.append({**head, 'state': 'recorded',
                          'pics': [pic(CF._ref_key(run, r['id']), CF.LETTERS[n] + (' (the starting picture)' if r['id'] == gold else '')) for n, r in enumerate(done[:len(CF.LETTERS)])]
                                  + ([pic(mine.get('key') or CF._ref_key(run, gold), 'Your own picture (the starting picture)')] if mine else [])})
    return lines


def _round_page(ctx, base, step):
    """One screen of the reference round as a round of the page. Its pictures are not in the round; a round whose text is over the document's
    size first leaves out the pictures of the approved sets, then the things already kept, then holds the later lines to answer for the next
    "done". Step 1 is recorded only when every thing of the round is answered, the held ones too, and the page says so."""
    session = ctx['session']
    (spent, cap, one), paid = _money(ctx)
    sets = 0
    if step == 'refs':
        lines, sets = _refs_lines(ctx)
    else:
        lines = _sets_lines(ctx)
    waits = lambda l: l['state'] == 'open' and not l.get('kept')
    count = lambda test: len([l for l in lines if test(l)])
    total, kept, making, done = len(lines), count(lambda l: bool(l.get('kept'))), count(lambda l: l['state'] == 'making'), count(lambda l: l['state'] == 'recorded')
    held = 0
    while len(json.dumps(lines, ensure_ascii=False).encode('utf-8')) > ROUND_BYTES:
        read = next((l for l in reversed(lines) if l['state'] == 'recorded' and 'pics' in l), None)
        old = next((i for i, l in enumerate(lines) if l.get('kept')), None)
        open_ = [i for i, l in enumerate(lines) if waits(l)]
        if read:
            del read['pics']
        elif old is not None and open_:
            del lines[old]
        elif len(open_) > 1:
            del lines[open_[-1]]
            held += 1
        else:
            break
    refused = session.get('page_refused') or {}
    lines = [{'line': f'l{n:02d}', **line, **({'refused': refused[line['key']]} if line['key'] in refused and line['state'] == 'open' else {})} for n, line in enumerate(lines, 1)]
    left = len([l for l in lines if waits(l)])
    more = f', {held} more after these' if held else ''
    many = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    if step == 'refs':
        stopped = refused.get('references')
        return {**base, 'step': REFS_STEP, 'open': bool(left), 'lines': lines,
                'summary': f"{many(total, 'thing')}: {total - kept} to answer, {kept} kept{more}; up to {many(sets, 'set')}, about ₹{sets * one:,.0f}, of the ₹{cap:,.0f} limit; spent so far ₹{spent:,.0f}.",
                'note': f'Not recorded: {stopped}' if stopped else
                        f'This list is long: {held} more things appear here after you answer these and say done in the chat. Nothing is made until after the last one.' if held else
                        'Look at each picture, answer each thing, then say done in the chat. Nothing is made until every thing is answered.' if left else
                        'Every thing is answered. Say done in the chat.'}
    return {**base, 'step': SETS_STEP, 'open': bool(left), 'lines': lines,
            'summary': f"{many(total, 'set')}: {total - kept - making - done} to answer, {kept} kept, {making} being made, {done} approved{more}. "
                       f'A set made again costs about ₹{one:,.0f}; spent so far ₹{spent:,.0f} of the ₹{cap:,.0f} limit.',
            'note': f'This list is long: {held} more sets appear here after you answer these and say done in the chat.' if held else
                    'Look at each set, answer each line, then say done in the chat.' if left else
                    'The sets are being made; they appear here when they are back.' if making else 'Nothing more to answer here now.',
            **({} if left or not making else {'then': SETS_WAIT})}


def _sets_asked(ctx, items):
    """How many paid sets the kept answers of step 1 ask for, as `visuals_stage._from_footage` will decide."""
    return len([i for i in items if i['_kept']['verdict'] == 'approve'
                and (i['_person'] or _drawn(ctx['session'], i['_eid']) if i['_kept'].get('own') else i['_makes'])])


def _round_close(ctx):
    """Step 1 recorded from the page, once every thing is answered: nothing half made. When the film's limit has no room for every set the
    answers ask for, the whole step is refused in a plain sentence and nothing is queued. None while a thing is unanswered."""
    items = CF._round_items(ctx, every=True)
    if not items or not items[0]['id'].startswith('round1:') or not all(i['_kept'] for i in items):
        return None
    n = _sets_asked(ctx, items)
    (spent, cap, one), _paid = _money(ctx)
    V.need(spent + n * one <= cap + 1e-9, f"The answers ask for {n} set{'' if n == 1 else 's'}, about ₹{n * one:,.0f}, and ₹{spent:,.0f} is spent of the ₹{cap:,.0f} limit of this film. "
                                          'Nothing was made and nothing is recorded: the answers are kept. Leave some things out, or ask the owner to set another limit for this film; then say done again.')
    return CF.round_close(ctx['conn'], ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], 'Done, on the page')


def _round_answer(ctx, a, choice, words):
    """One answer to a line of the reference round, through the run function of the chat's own item. Returns (what the operator said, the
    function's answer, whether the answer is only kept so far), or None when the line is no longer open with that content (stale: a set made
    again has a new id). The operator's own picture reached the server before this call (`own_ref`); a picture that did not is refused on
    its line (`own_error` is the tool's reason)."""
    session = ctx['session']
    item = next((i for i in CF._round_items(ctx, every=True) if i['id'] == a.get('item')), None)
    if not item:
        eid, mine = str(a.get('key') or '').split(':', 1)[-1], str(a.get('own_ref') or '')
        row = ((session.get('round') or {}).get('elements') or {}).get(eid) or {}
        if choice == 'own' and mine and row.get('own') and V.golden_of(session, eid) == mine:   # its set was not made: the server's own-picture path already took the picture as its reference
            return 'Use my own picture' + (f': {words}' if words else ''), {}, False
        return None
    eid, person, step1 = item['_eid'], item['_person'], item['id'].startswith('round1:')
    _budget, paid = _money(ctx)
    if choice == 'own':
        V.need(not (person and not V.likeness_of(session, eid)), OWN_PERMISSION)
        V.need(not a.get('own_error'), f"Your own picture was not used: {' '.join(str(a.get('own_error')).split())}")
        mine = str(a.get('own_ref') or '')
        V.need(V._own_golden(session, eid, mine), OWN_MISSING)
        label = _own_line(ctx, item, paid)['label']
        if step1:
            out = item['_run']('approve', label, words, own=mine)
        elif person:   # the sheet made before the photo is out of date: it is made again from the photo, as `vw visuals round --make` does
            out = V.set_make(ctx['conn'], ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], eid)
        elif item['id'].startswith('set:'):
            out = item['_run']('use:' + mine, label, '')
        else:
            out = {}
    else:
        buttons = _round_buttons(item, paid)
        button = next((b for b in buttons if b['choice'] == choice), None)
        V.need(button, f"Not an answer to this line: {choice!r}. Its answers are: " + ', '.join(b['label'] for b in buttons) + '.')
        V.need(not button['needs_words'] or words, 'Say what should change in this line, in your own words.')
        label = button['label']
        again = choice == 'no' and words and item['id'].startswith('set:')   # design/210 review: a paid remake asked for with words is made with them, as "Correct it" is; the log keeps the button pressed
        out = item['_run']('correct' if again else choice, label, words) or {}
    hold = (out.get('held') or {}).get(eid)   # the limit holds a set made again: the answer is kept and its line says why
    V.need(not hold, f'{hold[:1].upper()}{hold[1:]}.' if hold else '')
    return label + (f': {words}' if words else ''), out, step1 or (item['id'].startswith('set:') and 'pass' not in out)


def _round_due(ctx, now):
    """The reference round is the next thing and is not started: no line of the page waits or is back with the assistant, the film's
    references are made as sets, the plan names a thing the round takes, and no round exists."""
    if any(l['state'] in ('open', 'with_assistant') for l in now['lines']) or ctx['session'].get('round'):
        return False
    try:
        return V.set_estimate(ctx['run'], ctx['session'], ctx['plan'])['sets'] > 0
    except (Problem, KeyError, TypeError, ValueError):
        return False


def _plan_step(ctx):
    """Which step the page is at once a plan is proposed, with its lines: 'plan' while a gap is open or back with the assistant; 'spec' (the
    drawings and materials, design/209) until each is approved; then 'draw' (the reference drawings, design/210) while a drawing set waits;
    then the reference round: 'refs' at its step 1, 'sets' at its step 2 and while a set is being made (the lines are built by `_round_page`)."""
    specs = _spec_lines(ctx)
    quiet = not any(CF._plan_items(ctx)) and all(l['state'] == 'recorded' for l in specs)
    draws = _drawing_lines(ctx) if quiet else []
    if draws:
        return 'draw', draws
    rd = ctx['session'].get('round') or {}
    at = V._round_pass(ctx['session'], rd) if quiet and rd.get('kept') else None
    return ('refs', []) if at == 1 else ('sets', []) if at in (2, 'making') else ('spec', specs) if specs else ('plan', [])


def _spec_answer(ctx, key, choice, words, item_id, items=None):
    """One answer to a drawing's or a material's line (or, with `items`, to a reference drawing's), through the run function of the chat's own
    item: Yes approves it, Correct it sends it back with the operator's words. None when the line is no longer open with that content (stale)."""
    item = next((i for i in (items if items is not None else [i for i in CF._waiting_items(ctx) if i['kind'] == 'spec']) if i['id'] == item_id), None)
    if not item:
        return None
    button = next((b for b in item['buttons'] if b['choice'] == choice), None)
    V.need(button, f"Not an answer to this line: {choice!r}. Its answers are: " + ', '.join(b['label'] for b in item['buttons']) + '.')
    V.need(not button.get('needs_words') or words, 'Say what should change in this line, in your own words.')
    return words or button['label'], item['_run'](choice, button['label'], words)


def _plan_answer(ctx, key, choice, words, item_id):
    """One answer to a plan line, through the decision functions the chat uses. Returns (what the operator said, the function's answer), or None
    when the line is no longer open with that text (stale)."""
    store, user, run, outputs, session = ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], ctx['session']
    items, revising = CF._plan_items(ctx)
    if choice == 'reopen':
        if key not in session['accepted'] or key in (session.get('shared_pending') or {}):
            return None
        V.need(items or revising, f"{key}: the plan is accepted as a whole and the work has moved on. Ask for this change in the chat.")
        V.need(words, f"{key}: your words are needed to reopen a line: say what should change.")
        return words, V.revise_gap(store, user, run, outputs, key, words, 'Reopen')
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        return None
    if item['kind'] == 'plan choice':   # a way taken accepts the gap in the same answer; "Change this" sends the gap back with no way taken
        gid = item['id'][len('choice:'):].rsplit(':', 1)[0]
        if choice == 'change':
            V.need(words, 'Say what should change in this line, in your own words.')
            return words, V.revise_gap(store, user, run, outputs, gid, words, 'Change this')
        button = next((b for b in item['buttons'] if 'way:' + b['choice'] == choice), None)
        V.need(button, f"Not an answer to this line: {choice!r}. Its answers are: " + ', '.join('Take ' + b['label'] for b in item['buttons']) + ', Change this.')
        item['_run'](button['choice'], button['label'], '')
        return 'Take ' + button['label'], V.accept(store, user, run, outputs, [gid], 'Take ' + button['label'])
    button = next((b for b in item['buttons'] if b['choice'] == choice), None)
    V.need(button, f"Not an answer to this line: {choice!r}. Its answers are: " + ', '.join(b['label'] for b in item['buttons']) + '.')
    V.need(not button.get('needs_words') or words, 'Say what should change in this line, in your own words.')
    return words or button['label'], item['_run'](choice, button['label'], words)


def page(conn, store, user, run, outputs):
    """What the page shows now (`_page`), with the two sizes of every picture its lines name (design/210, `_with_pictures`)."""
    return _with_pictures(store, _page(conn, store, user, run, outputs))


def _page(conn, store, user, run, outputs):
    """What the page shows now, for the treatment and then for the plan (design/206, `_plan_page`): `lines` in the film's order, each `open` (with its rows or text and its buttons), `recorded`
    (accepted; `reopen` while the treatment is still a draft) or `with_assistant` (sent back, with the operator's words). A new `round` each call."""
    ended = False
    try:
        ended = (CF.flush_sets(conn, store, user, run, outputs, 'Answered on the page') or {}).get('pass') == 'complete'   # design/210: an answer kept on a set while others were being made is recorded once they are back, as `vw visuals next` does; a round with nothing left to judge ends here
    except (ValueError, Problem):
        pass   # said on its line when the operator next answers
    ctx = CF._ctx(conn, store, user, run, outputs)
    session, draft = ctx['session'], ctx['session'].get('treatment_draft')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    base = {'step': 'Treatment', 'round': 'r' + stamp, 'how': HOW, 'capabilities': CAPABILITIES, 'title': f"VideoWizard decisions {run.get('code') or ''}".strip()}
    if _at_plan(ctx):
        step, lines = _plan_step(ctx)   # design/209: after the plan, the drawings and the materials; design/210: then the reference drawings, then the reference round
        if step in ('refs', 'sets'):
            return _round_page(ctx, base, step)
        out = _drawing_page(ctx, base, lines) if step == 'draw' else _spec_page(ctx, base, lines) if step == 'spec' else _plan_page(ctx, base)
        if _round_due(ctx, out):
            out['then'] = REFS_START   # nothing waits on the page and the round is not started: what the assistant does next
        elif ended:
            out['then'] = ROUND_NEXT   # the round ended in this call: said once
        return out
    motion =_motion_line(run, draft)
    first = [motion] if motion else []
    if not draft:
        done = bool(session.get('treatment'))
        recorded = [{'line': f'l{n:02d}', 'key': k, 'title': 'The direction of the film' if k == 'direction' else f'Gap {k}', 'state': 'recorded'}
                    for n, k in enumerate(V._line_digests(session['treatment']), 1)] if done else []
        if motion and motion['state'] == 'open' and not done:   # asked as early as the preparation
            return {**base, 'open': True, 'lines': first, 'summary': '', 'note': 'Choose the motion style. The Direction appears here when the assistant has written it.'}
        return {**base, 'open': False, 'lines': first + recorded, 'summary': '',
                'note': 'The treatment is recorded: every line is accepted. Nothing more to answer here.' if done else 'No treatment draft yet: nothing to answer here.'}
    items, summary, _back = CF._treatment_items(ctx)
    by_key = {i['_key']: i for i in items}
    states = draft.get('lines') or {}
    direction_open = states.get('direction', {}).get('state') in ('to_accept', 'sent_back')
    lines = []
    film_order = [e.get('gap_id') for e in draft.get('gaps') or [] if e.get('gap_id') in states]   # the film's order, as the draft lists its gaps
    for n, key in enumerate((['direction'] if 'direction' in states else []) + film_order, 1):
        st, head = states[key], {'line': f'l{n:02d}', 'key': key, 'title': 'The direction of the film' if key == 'direction' else f'Gap {key}'}
        if key != 'direction' and direction_open:
            continue   # no gap is shown until the Direction is accepted
        if st['state'] == 'accepted':
            lines.append({**head, 'state': 'recorded', 'reopen': True})
        elif st['state'] == 'sent_back':
            lines.append({**head, 'state': 'with_assistant', 'note': st.get('note') or ''})
        elif key in by_key:
            i = by_key[key]
            lines.append({**head, 'state': 'open', 'item': i['id'], 'title': _title(i), 'rows': i['_card'].get('r') or [], 'text': i['_card'].get('t') or '',
                          'asked': bool(st.get('asked')), 'changed': bool(st.get('changed')), 'changes': CF._changes(st.get('changes')),
                          'buttons': [{'label': b['label'], 'choice': b['choice'], 'needs_words': bool(b.get('needs_words'))} for b in i['buttons']]})
    for line in lines:   # a refusal of the last "done" stays on its line until the line is answered again
        if line['key'] in (session.get('page_refused') or {}):
            line['refused'] = session['page_refused'][line['key']]
    hidden = len([k for k in states if k != 'direction']) if direction_open else 0
    alone = bool(draft.get('direction_only'))   # design/205: no gap line is written before the Direction is accepted
    return {**base, 'open': True, 'lines': first + lines, 'summary': '' if alone else summary,
            'note': f"The {hidden} gap lines appear after the Direction is accepted." if hidden else
                    'The gap lines are written after you accept the Direction.' if alone and direction_open else
                    'The Direction is accepted. The assistant writes the gap lines now; they will appear here.' if alone else 'Answer each line, then say done in the chat.'}


def page_record(conn, store, user, run, outputs, answers):
    """Every answer the operator gave on the page, recorded in one call. The Direction first: when it is not simply accepted, the gap answers sent
    with it are dropped (every gap is written again from the new Direction). An answer to an item that is no longer open, or whose text changed,
    is named as stale and changes nothing. A refusal is kept for its line and the other answers are still recorded."""
    answers = [a for a in answers or [] if isinstance(a, dict)]
    answers.sort(key=lambda a: {'motion': 0, 'direction': 1, 'shared': 1}.get(a.get('key'), 2))   # the motion style, then the Direction (or the plan's shared rules), then the gaps
    recorded, stale, refused, dropped, tell = [], [], [], [], ''
    kept = []   # design/210: the answers of the reference round that are kept and not recorded yet
    relies, corrected, was_draw, was_round = set(), False, False, False   # design/209: the lines that showed a size only as "Already confirmed", as the operator saw them
    try:
        first = CF._ctx(conn, store, user, run, outputs)
        was = _plan_step(first)[0] if _at_plan(first) else ''
        was_draw, was_round = was == 'draw', was in ('refs', 'sets')   # design/210: this "done" was said on the reference drawings, or on the reference round
        if _at_plan(first) and _spec_lines(first):
            relies = {v['key'] for v in CF._spec_views(first) if v['spec'].get('confirmed')}
            answers.sort(key=lambda a: str(a.get('choice') or '') == 'yes')   # the corrections first: a yes may rest on a size corrected in the same visit
    except Problem:
        pass
    for n, a in enumerate(answers):
        key, choice, words = str(a.get('key') or ''), str(a.get('choice') or ''), ' '.join(str(a.get('notes') or '').split())
        ctx = CF._ctx(conn, store, user, run, outputs)   # the session as the answer before left it
        draft = ctx['session'].get('treatment_draft') or {}
        state = (draft.get('lines') or {}).get(key, {}).get('state')
        said = words
        try:
            if _at_plan(ctx) and key.startswith(('ref:', 'set:')):   # design/210: a line of the reference round, whatever the page shows now
                got = _round_answer(ctx, a, choice, words)
                if not got:
                    stale.append(key)
                    continue
                said, out, waits = got
                tell = tell or str((out or {}).get('tell') or '')
                if waits:
                    kept.append(key)
                    _log(conn, run, key, choice, said)
                    continue
            elif _at_plan(ctx):   # design/206: a plan line; design/209: after the plan, a drawing's or a material's line
                step = _plan_step(ctx)[0]
                at_spec = step == 'spec'
                if at_spec and choice == 'yes' and corrected and key in relies:   # it rested on a size another line gave, and a line was corrected in this visit: asked again
                    stale.append(key)
                    continue
                got = (_spec_answer(ctx, key, choice, words, a.get('item'), [i for i in CF._drawing_items(ctx) if i['id'].startswith('drawing:')]) if step == 'draw' else   # design/210: a thing's drawing set
                       (_spec_answer if at_spec else _plan_answer)(ctx, key, choice, words, a.get('item')))
                corrected = corrected or (at_spec and bool(got) and choice != 'yes')
                if not got:
                    stale.append(key)
                    continue
                said, out = got
                tell = tell or str((out or {}).get('tell') or '')
            elif key == 'motion':   # design/205: the film's motion style, chosen on the page
                if F.older(run) or F.motion(run):
                    stale.append(key)
                    continue
                said = words or (F.styles().get(choice) or {}).get('title') or choice
                run['film'] = F.record(conn, user, run, 'motion', choice, said)
            elif choice == 'reopen':
                if state != 'accepted':
                    stale.append(key)
                    continue
                V.need(words, f"{key}: your words are needed to reopen a line: say what should change.")
                V.treatment(store, user, run, outputs, None, 'Reopen', send_back=[key], notes=words)
            else:
                item = next((i for i in CF._treatment_items(ctx)[0] if i['id'] == a.get('item')), None)
                if not item:
                    stale.append(key)
                    continue
                button = next((b for b in item['buttons'] if b['choice'] == choice), None)
                V.need(button, f"Not an answer to this line: {choice!r}. Its answers are: " + ', '.join(b['label'] for b in item['buttons']) + '.')
                V.need(not button.get('needs_words') or words, 'Say what should change in this line, in your own words.')
                said = words or button['label']
                out = item['_run'](choice, button['label'], words)
                tell = tell or str((out or {}).get('tell') or '')
        except (ValueError, Problem) as exc:
            refused.append({'key': key, 'message': str(getattr(exc, 'message', '') or exc)})
            _log(conn, run, key, choice, said, refused=refused[-1]['message'])
            continue
        recorded.append(key)
        _log(conn, run, key, choice, said or choice)
        if key == 'direction' and choice != 'accept':
            dropped = [str(x.get('key') or '') for x in answers[n + 1:]]
            break
    stopped = ''
    try:   # design/210: step 1 of the reference round is recorded once, when every thing has its answer and no drawing is in its way
        ctx = CF._ctx(conn, store, user, run, outputs)
        if _at_plan(ctx) and (_plan_step(ctx)[0] == 'refs' or any(k.startswith('ref:') for k in kept)):
            closed = _round_close(ctx)
            if closed:
                done = ['ref:' + e['id'] for e in ctx['plan']['elements'] if e['id'] in ctx['session']['round']['elements']]
                recorded, kept = recorded + [k for k in done if k not in recorded], [k for k in kept if k not in done]
                tell = tell or str(closed.get('tell') or '')
    except (ValueError, Problem) as exc:
        stopped = str(getattr(exc, 'message', '') or exc)
        refused.append({'key': 'references', 'message': stopped})
        _log(conn, run, 'references', 'done', 'Done, on the page', refused=stopped)
    session = V.session_of(store, run, outputs)
    session['page_refused'] = {r['key']: r['message'] for r in refused}   # shown on the line until it is answered again
    V.save_session(store, run, session)
    now = page(conn, store, user, run, outputs)
    left = len([l for l in now['lines'] if l['state'] == 'open' and not l.get('kept')])
    draft = session.get('treatment_draft') or {}
    alone_accepted = bool(draft.get('direction_only')) and (draft.get('lines') or {}).get('direction', {}).get('state') == 'accepted'
    at_plan, at_spec, at_draw = now['step'] == 'Plan', now['step'] == SPEC_STEP, now['step'] == DRAW_STEP
    at_refs, at_sets = now['step'] == REFS_STEP, now['step'] == SETS_STEP
    rd = V.session_of(store, run, outputs).get('round') or {}   # read again: `page` may have ended the round
    drawn = 'Every reference drawing is approved. '
    then = ('Nothing was answered on the page. ' if not answers else '') + (f'The references are not recorded yet: {stopped} ' if stopped else '') + (
        SPEC_REFUSED + ' ' if at_spec and refused else DRAW_REFUSED + ' ' if at_draw and refused else ROUND_REFUSED + ' ' if (at_refs or at_sets) and [r for r in refused if r['key'] != 'references'] else '') + (
        drawn + REFS_GO if at_refs and was_draw and not session.get('chat_round') else
        f"{left} thing(s) still wait for the operator on the page: write the new round to the page and give them the link again. The answers given are kept: nothing is made until every thing is answered." if at_refs and left else
        'Every thing is answered and kept. When what stands in the way is settled, run `vw visuals page --record` again: the step is recorded then.' if at_refs else
        f"{left} line(s) still wait for the operator on the page: write the new round to the page and give them the link again." if at_sets and left else
        SETS_WAIT if at_sets and any(l['state'] == 'making' for l in now['lines']) else SETS_STAND if at_sets and any(l.get('kept') for l in now['lines']) else SETS_NONE if at_sets else
        ROUND_NEXT if (was_round or kept or any(k.startswith(('ref:', 'set:')) for k in recorded)) and rd.get('kept') and rd.get('pass') == 'complete' else
        f"{left} line(s) still wait for the operator on the page: write the new round to the page and give them the link again." if (at_plan or at_spec or at_draw) and left else
        DRAW_BACK if at_draw else drawn + REFS_START if was_draw and _round_due(CF._ctx(conn, store, user, run, outputs), now) else DRAW_NEXT if was_draw else
        SPEC_BACK if at_spec and any(l['state'] == 'with_assistant' for l in now['lines']) else SPEC_NEXT if at_spec else
        PLAN_BACK if at_plan and any(l['state'] == 'with_assistant' for l in now['lines']) else PLAN_NEXT if at_plan else
        'The treatment is recorded: write the plan to it.' if session.get('treatment') and not draft else
        f"{left} line(s) still wait for the operator on the page: write the new round to the page and give them the link again." if left else
        V.DIRECTION_ACCEPTED if alone_accepted else
        'Write the Direction alone, send it (`vw visuals treatment --file out/visual-treatment.json`, no `gaps` in it), then `vw visuals page`.' if not draft else
        'No line waits for the operator now: revise the lines that are back with you (their words are on each), send the draft again, then `vw visuals page`.')
    said = '; '.join(f"{name} {', '.join(keys)}" for name, keys in (('recorded', recorded), ('kept', kept), ('stale', stale), ('refused', [r['key'] for r in refused]), ('dropped', dropped)) if keys)
    return {'recorded': recorded, 'kept': kept, 'stale': stale, 'refused': refused, 'dropped': dropped, 'open': left, **({'tell': tell} if tell else {}), 'then': (tell + ' ' if tell else '') + then, 'page': now,
            'log': said or 'nothing answered'}   # design/205: the record call's own log line
