"""design/204 (SK, 15 Nov 2026): the treatment answered on a Claude artifact page.

`page` gives the page its lines as data: the Direction alone until it is accepted, then every gap line, each built by the same function the chat
asks from (`chat_flow._treatment_items`), plus the lines already recorded and the ones back with the assistant. `page_record` records the answers
the operator gave on the page, in one call, through the same decision functions as one answer at a time.

The server stays the record. The page is a form: an answer counts only when the operator says "done" in the chat and the assistant sends it here.
An answer names the item it was given to; an item's id holds its text's digest, so an answer to an older text of a line is ignored by name."""
import json
from collections import Counter
from datetime import datetime, timezone

from . import chat_flow as CF
from . import film as F
from . import runlog
from . import visuals_stage as V
from .errors import Problem

HOW = ('The operator answers this step on a page, not on a card. '
       '1. If `url` is empty, publish the page with the Artifact tool: `file_path` is `page_file`, the title is `title`, `capabilities` exactly as given, an icon of your choice; '
       'then run `vw visuals page --url "<the link it gives>"`. If there is no Artifact tool, or it fails, run `vw visuals next` and show the card instead, and say once that the page is not available. '
       'If `republish` is true, the page at the link was published by an older tool: publish it again to the same link (the Artifact tool with `file_path` `page_file` and `url` the link), '
       'then run `vw visuals page --url` with that link. '
       '2. Write this round to the page with the ArtifactData tool: action "set", `url` the page\'s link, collection "rounds", doc_id `round`, file_path `round_file`. Type none of its content. '
       '3. Say to the operator, as your own one line: "Open this page, answer each line, then tell me you are done:" and the link. Then wait. Do not post the lines in the chat as well. '
       '4. When the operator says done: ArtifactData, action "list", collection `answers_collection`, out_dir `answers_dir`; then run `vw visuals page --record`. '
       '5. It prints what was recorded and writes the next round: do step 2 again with the new `round` and `round_file`, then follow `then`. '
       'An answer the operator gives in the chat instead is recorded with `vw visuals decide`, as before.')
CAPABILITIES = {'db': {'rules': [{'path': 'rounds', 'read': 'view', 'write': 'owner'}]}, 'user': {}}   # only the page's owner writes: the lines and the answers


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
        cost = f"; estimate ₹{V.plan_estimate(ctx['run'], V.routes(plan, V._fps(session) or 25)):g} of the ₹{V.cap_of(session):g} limit"
    except (Problem, KeyError, TypeError, ValueError):
        cost = ''
    return {**base, 'step': 'Plan', 'open': bool(left), 'lines': lines,
            'summary': f"{len(plan['gaps'])} gaps: {count('open')} to answer, {count('recorded')} recorded, {count('with_assistant')} with the assistant"
                       + (f", {len(waits)} behind the shared rules" if waits else '') + (f", {held} more after these" if held else '') + cost + '.',
            'note': f'This plan is long: {held} more gap(s) appear here after you answer these and say done in the chat.' if held else
                    'Answer each line, then say done in the chat.' if left else 'The assistant is changing the lines you sent back; they will appear here.' if plan_open
                    else 'Every gap of the plan is accepted. Nothing more to answer here.'}


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
    """What the page shows now, for the treatment and then for the plan (design/206, `_plan_page`): `lines` in the film's order, each `open` (with its rows or text and its buttons), `recorded`
    (accepted; `reopen` while the treatment is still a draft) or `with_assistant` (sent back, with the operator's words). A new `round` each call."""
    ctx = CF._ctx(conn, store, user, run, outputs)
    session, draft = ctx['session'], ctx['session'].get('treatment_draft')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    base = {'step': 'Treatment', 'round': 'r' + stamp, 'how': HOW, 'capabilities': CAPABILITIES, 'title': f"VideoWizard decisions {run.get('code') or ''}".strip()}
    if _at_plan(ctx):
        return _plan_page(ctx, base)
    motion = _motion_line(run, draft)
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
    for n, a in enumerate(answers):
        key, choice, words = str(a.get('key') or ''), str(a.get('choice') or ''), ' '.join(str(a.get('notes') or '').split())
        ctx = CF._ctx(conn, store, user, run, outputs)   # the session as the answer before left it
        draft = ctx['session'].get('treatment_draft') or {}
        state = (draft.get('lines') or {}).get(key, {}).get('state')
        said = words
        try:
            if _at_plan(ctx):   # design/206: a plan line
                got = _plan_answer(ctx, key, choice, words, a.get('item'))
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
    session = V.session_of(store, run, outputs)
    session['page_refused'] = {r['key']: r['message'] for r in refused}   # shown on the line until it is answered again
    V.save_session(store, run, session)
    now = page(conn, store, user, run, outputs)
    left = len([l for l in now['lines'] if l['state'] == 'open'])
    draft = session.get('treatment_draft') or {}
    alone_accepted = bool(draft.get('direction_only')) and (draft.get('lines') or {}).get('direction', {}).get('state') == 'accepted'
    at_plan = now['step'] == 'Plan'
    then = ('Nothing was answered on the page. ' if not answers else '') + (
        f"{left} line(s) still wait for the operator on the page: write the new round to the page and give them the link again." if at_plan and left else
        PLAN_BACK if at_plan and any(l['state'] == 'with_assistant' for l in now['lines']) else PLAN_NEXT if at_plan else
        'The treatment is recorded: write the plan to it.' if session.get('treatment') and not draft else
        f"{left} line(s) still wait for the operator on the page: write the new round to the page and give them the link again." if left else
        V.DIRECTION_ACCEPTED if alone_accepted else
        'Write the Direction alone, send it (`vw visuals treatment --file out/visual-treatment.json`, no `gaps` in it), then `vw visuals page`.' if not draft else
        'No line waits for the operator now: revise the lines that are back with you (their words are on each), send the draft again, then `vw visuals page`.')
    said = '; '.join(f"{name} {', '.join(keys)}" for name, keys in (('recorded', recorded), ('stale', stale), ('refused', [r['key'] for r in refused]), ('dropped', dropped)) if keys)
    return {'recorded': recorded, 'stale': stale, 'refused': refused, 'dropped': dropped, 'open': left, **({'tell': tell} if tell else {}), 'then': (tell + ' ' if tell else '') + then, 'page': now,
            'log': said or 'nothing answered'}   # design/205: the record call's own log line
