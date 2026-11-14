"""design/188 (SK, 12 Nov 2026): the visuals stage in the operator chat. One decision at a time.

`next_item` hands out exactly one thing the operator must decide (where it is, the question, what to show, the buttons), or says that nothing is
needed and what is being made. `answer` records the operator's choice on that item and on no other, through the decision functions that exist
(`visuals_stage`, `guide`): the same ones the visuals page's buttons call. Nothing about what is approved changes here, only where and in what
order the operator answers.

The gate: the item handed out is kept in the session (`chat_item`); an answer naming any other item is refused by name, so the assistant cannot
choose the order, show two things at once or skip one.

The order: the treatment (one line), the plan (one gap), the reference round (one element, then one set), then everything `waiting()` lists
(an open question, a picture, a sheet, a spec, a take), an AI video shot's still and its word to shoot, then the gaps ready to record."""
import hashlib
import json
import re
from datetime import datetime, timezone
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from . import visuals_stage as V

NOTHING = 'Nothing is needed from you now.'
NEEDED = 'Your answer is needed.'
LETTERS = 'ABCDEFGH'
ROUTE_WORDS = {'footage': 'footage', 'image': 'a still picture', 'still': 'a still picture', 'video': 'AI video', 'diagram': 'a diagram', 'animation': 'an animated graphic',
               'drawn': 'a drawn graphic', 'graphic_sequence': 'an animated graphic'}
MAKING = {'guide': 'its guide is being drawn', 'guide-still': 'its still is being made', 'video': 'its take is being made', 'drawn': 'its drawing is being rendered',
          'motion': 'a helper is checking its drawing'}
LOOK_ONLY = 'do not study them yourself unless the operator asks you to'


def _button(label, choice, words=False, tell=''):
    """One button: its label, what it records, whether the operator's own words are needed with it, and what to ask for when they are missing."""
    return {'label': label, 'choice': choice, **({'needs_words': True} if words else {}), **({'tell': tell} if tell else {})}


def _item(ident, kind, position, question, run, buttons, text='', show=(), more=()):
    return {'id': ident, 'kind': kind, 'position': position, 'question': question, 'text': text, 'show': list(show), 'buttons': list(buttons)[:4],
            **({'other_choices': list(more)} if more else {}), '_run': run}


def _ref_key(run, ref_id):
    return f"{run['id']}/visuals/references/{ref_id}.png"


def _pic(run, ref_id, name):
    return {'key': _ref_key(run, ref_id), 'name': name + '.png'}


# ---------- the treatment and the plan ----------

def _changes(changes, n=10):
    """design/191: the first lines of what changed, then how many more there are."""
    changes = list(changes or [])
    return changes[:n] + ([f'and {len(changes) - n} more'] if len(changes) > n else [])


def _changed_text(changes):
    rows = _changes(changes)
    return ('**What changed:**\n' + '\n'.join('- ' + r for r in rows) + '\n\n') if rows else ''


def _treatment_items(ctx):
    session, draft = ctx['session'], ctx['session'].get('treatment_draft')
    if not draft:
        return [], '', []
    lines = draft.get('lines') or {}
    entries = {e['gap_id']: e for e in draft.get('gaps') or []}
    order = (['direction'] if 'direction' in lines else []) + [k for k in lines if k != 'direction']   # the direction first, then every gap (VW-22: it was asked last)
    totals = draft.get('totals') or {}
    summary = (f"{totals.get('gaps', len(entries))} gaps, {totals.get('images', 0)} picture(s) to make; estimate ₹{draft.get('estimate_inr', 0):g} of the ₹{V.cap_of(session):g} limit"
               + (f"; kept aside for takes made again: ₹{draft['rerun_allowance_inr']:g}" if draft.get('rerun_allowance_inr') else '')
               + (f". Warnings: {'; '.join(str(w.get('message') if isinstance(w, dict) else w) for w in (draft.get('warnings') or [])[:4])}" if draft.get('warnings') else ''))
    items = []
    if (lines.get('direction') or {}).get('state') == 'sent_back':   # design/190: every gap line is written again from the direction; none is asked until it is back
        return [], summary, ['direction']
    for n, key in enumerate(order, 1):
        st = lines[key]
        if st['state'] != 'to_accept':
            continue
        if key == 'direction':
            head, body, rows = 'The direction of the film', str(draft.get('direction') or ''), None
        else:
            e = entries.get(key) or {}
            head = f'Gap {key}'
            rows = [('The picture', e.get('picture')), ('Made as', ', '.join(ROUTE_WORDS.get(r, r) for r in e.get('routes') or [])), ('Length', f"{float(e.get('seconds') or 0):g} s"),
                    ('Pictures to make', e.get('images')), ('Shows', '; '.join(e.get('depicts') or [])),
                    ('Held still for', f"{float(e['frozen_seconds']):g} s" if e.get('frozen_seconds') else ''), ('Why', e.get('why') or e.get('reason') or '')]
            body = '\n'.join(f'- **{k}:** {v}' for k, v in rows if v not in (None, '', []))   # a list: plain line breaks run together in the chat

        def run(choice, quote, words, key=key):
            return V.treatment(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], None, quote, accept=[key] if choice == 'accept' else [],
                               send_back=[key] if choice == 'change' else [], notes=words if choice == 'change' else '')
        items.append(_item(f"treatment:{key}:{st['digest'][:10]}", 'treatment line', f'Treatment, line {n} of {len(order)}',
                           f"{head}{' (changed since you last saw it)' if st.get('changed') else ''}. Do you accept this line?", run,
                           [_button('Accept', 'accept'), _button('Change this', 'change', words=True, tell='Ask the operator what to change in this line.')],
                           text=_changed_text(st.get('changes')) + body))
        items[-1].update(_key=key, _summary=summary, _card={'n': head, 'c': 1 if st.get('changed') else 0, **({'ch': _changes(st['changes'])} if st.get('changes') else {}),
                                          **({'t': body} if rows is None else {'r': [[k, str(v)] for k, v in rows if v not in (None, '', [])]})})
    return items, summary, [k for k in order if lines[k]['state'] == 'sent_back']


def _seconds(shot, fps):
    return float(Fraction(shot['end_frame'] - shot['start_frame']) / Fraction(str(fps)))


GAP_COLS = ['#', 'Shot', 'Made as', 'Length', 'What it shows', 'Over the words']


def _gap_rows(session, gap):
    """A gap's shots as rows of GAP_COLS, and its totals line: the same for the chat's table and for the card."""
    fps, rows, total = session['source'].get('fps') or 25, [], 0.0
    cell = lambda v: ' '.join(str(v or '').split()).replace('|', '/')   # one line, no column break
    for sc in V.chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])):
        for s in sc['shots']:
            kind = ROUTE_WORDS.get(V.route_of(s), V.route_of(s))
            rows.append([str(len(rows) + 1), cell(s.get('title') or s['id']), kind, f'{_seconds(s, fps):.1f} s', cell(s.get('purpose')), cell(s.get('narration'))[:220]])
            total += _seconds(s, fps)
    return rows, f'{len(rows)} shots, {total:.1f} s in all.'


def _gap_text(session, gap):
    rows, total = _gap_rows(session, gap)
    return '\n'.join(['| ' + ' | '.join(GAP_COLS) + ' |', '|---|---|---|---|---|---|'] + [f'| {r[0]} | **{r[1]}** | ' + ' | '.join(r[2:]) + ' |' for r in rows]) + f'\n\n{total}'


def _plan_items(ctx):
    session, plan = ctx['session'], ctx['plan']
    if not plan:
        return [], []
    gaps, items, revising, cache = plan['gaps'], [], [], {}
    pending, unread = session.get('shared_pending') or {}, False
    try:   # design/191: gaps whose own shots are as accepted while the part every gap shares changed wait behind ONE question
        shared = V.shared_change(ctx['store'], session, plan, cache)
    except (V.Problem, StopIteration, KeyError, TypeError, ValueError):
        shared, unread = None, True   # the earlier version cannot be read: each gap is asked by itself, as before, and says so
    if shared and (session.get('shared_revision') or {}).get('shared') == V.shared_digest(plan):
        revising.append("the film's shared rules")   # the operator asked for a change there: the assistant's turn
    elif shared:
        many = len(shared['gaps']) != 1

        def run_shared(choice, quote, words):
            if choice == 'accept':
                return V.accept_shared(ctx['conn'], ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], quote)
            return V.revise_shared(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], words, quote)
        items.append(_item(f"shared:{V.shared_digest(plan)[:10]}", 'plan shared', 'Plan, the shared rules',
                           f"The film's shared rules changed. {len(shared['gaps'])} gap{'s have' if many else ' has'} the same shots as you accepted. Accept the change for {'all of them' if many else 'it'}?",
                           run_shared, [_button('Accept', 'accept'), _button('Change this', 'change', words=True, tell='Ask the operator what to change in the shared rules.')],
                           text=_changed_text(shared['changes']) + f"**Gaps with the same shots as you accepted:** {', '.join(shared['gaps'])}\n\nUntil you answer, the work on these gaps' shots waits."))
    for n, gap in enumerate(gaps, 1):
        gid = gap['gap_id']
        if gid in session['accepted'] or (gid in pending and not unread):
            continue
        if gid in (session.get('revisions') or {}):
            revising.append('gap ' + gid)
            continue
        where = f'Plan, gap {n} of {len(gaps)}'
        title = f'Gap {gid}' + (f" · {gap['title']}" if gap.get('title') else '')
        if gap.get('choices') and not session['choice_selections'].get(gid):
            choices = gap['choices'][:4]
            text = '\n\n'.join(f"{c['title']}\n{c['description']}\nWhy: {c['why']}\nThe cost of it: {c['tradeoff']}" for c in choices)
            items.append(_item(f"choice:{gid}:{V.gap_digest(plan, gap)[:10]}", 'plan choice', where, f'{title}. Which way should this gap be made?',
                               lambda choice, quote, words, gid=gid: V.select_choice(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], {gid: choice}),
                               [_button(c['title'][:34] + (' (advised)' if c['id'] == gap.get('recommended_choice') else ''), c['id'])
                                for c in sorted(choices, key=lambda c: c['id'] != gap.get('recommended_choice'))], text=text))
        else:
            def run(choice, quote, words, gid=gid):
                if choice == 'accept':
                    return V.accept(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], [gid], quote)
                return V.revise_gap(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], gid, words, quote)
            changes = (["The earlier plan version could not be read, so each gap is asked by itself. Only the film's shared rules changed; this gap's shots are as you accepted."] if gid in pending
                       else V.gap_changes(ctx['store'], session, plan, gap, cache))   # design/191: a gap asked again says what changed since the operator accepted it
            again = bool(changes) and gid not in pending
            items.append(_item(f"gap:{gid}:{V.gap_digest(plan, gap)[:10]}", 'plan gap', where, f"{title}{' (changed since you accepted it)' if again else ''}. Do you accept the shots planned for this gap?", run,
                               [_button('Accept', 'accept'), _button('Change this', 'change', words=True, tell='Ask the operator what to change in this gap.')],
                               text=_changed_text(changes) + _gap_text(session, gap)))
            rows, total = _gap_rows(session, gap)
            items[-1].update(_key=gid, _card={'n': title, 'c': 1 if again else 0, **({'ch': _changes(changes)} if changes else {}), 'tot': total, 'tb': rows})
    items.sort(key=lambda i: {'plan shared': 0, 'plan choice': 1}.get(i['kind'], 2))   # design/191: the shared change first; design/190: then a gap's offered choice, one at a time; the gaps then come on one card
    return items, revising


# ---------- the reference round: one element, then one set ----------

def _names(plan):
    return {e['id']: (e.get('name') or e['id']) for e in (plan or {}).get('elements') or []}


def _kinds(plan):
    return {e['id']: e.get('kind') for e in (plan or {}).get('elements') or []}


def sheet_of(store, run, rows):
    """One picture of a set, side by side, a large letter on each: stored with the run, so the chat can show it. Its key, or None when it cannot be made."""
    key = f"{run['id']}/visuals/chat/set-{hashlib.sha256(''.join(r['id'] + str(r.get('sha256')) for r in rows).encode()).hexdigest()[:16]}.jpg"
    try:
        if rows and store.exists(key):
            return key
        from PIL import Image, ImageDraw
        tiles = []
        for letter, r in zip(LETTERS, rows):
            im = Image.open(BytesIO(store.get(_ref_key(run, r['id'])))).convert('RGB')
            im.thumbnail((640, 640))
            tile = Image.new('RGB', (660, 720), (24, 24, 24))
            tile.paste(im, ((660 - im.width) // 2, 70 + (640 - im.height) // 2))
            d = ImageDraw.Draw(tile)
            d.rectangle((10, 8, 70, 62), fill=(255, 196, 61))
            d.text((28, 12), letter, fill=(0, 0, 0), font_size=44)
            tiles.append(tile)
        if not tiles:
            return None
        sheet = Image.new('RGB', (660 * len(tiles), 720), (24, 24, 24))
        for i, t in enumerate(tiles):
            sheet.paste(t, (660 * i, 0))
        buf = BytesIO()
        sheet.save(buf, 'JPEG', quality=88)
        store.put(key, buf.getvalue(), 'image/jpeg')
        return key
    except Exception:   # noqa: BLE001: the single pictures are shown all the same
        return None


def _round_kept(held, stamps):
    """The first-step answers that still stand: the thing is in the round and its footage pictures are the ones the operator answered about."""
    return {e: v for e, v in (held or {}).items() if isinstance(v, dict) and e in stamps and v.get('frames') == stamps[e]}


def _round_items(ctx):
    session, plan, run = ctx['session'], ctx['plan'], ctx['run']
    rd = session.get('round')
    if not (rd and plan and rd.get('kept')):
        return []
    step, names, kinds, items = V._round_pass(session, rd), _names(plan), _kinds(plan), []
    everything = list(rd['elements'].items())
    elements = [(eid, row) for eid, row in everything if eid in kinds]   # what the operator is asked about: the things the plan names
    if step == 1:
        frames_of = {eid: row.get('frames') or [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
                     for eid, row in elements}
        stamps = {eid: ','.join(map(str, f)) for eid, f in frames_of.items()}
        held = _round_kept(session.get('chat_round'), stamps)   # design/191 section 11, B4: kept through a round posted again, while that thing's footage pictures are the same
        open_ = [(eid, row) for eid, row in elements if eid not in held]
        for eid, row in open_[:1]:
            n = len(elements) - len(open_) + 1
            frames = frames_of[eid]
            person = kinds.get(eid) == 'person'
            if frames:
                q = (f"{names[eid]}: this is how {'this person' if person else 'it'} looks in your footage. "
                     + ('Use these pictures to make the reference set?' if person else 'Use this picture from your footage as the reference?'))
                yes = 'Yes, use it'
            else:
                q, yes = f"{names[eid]}: your footage has no picture of {'this person' if person else 'it'}. Have a reference set made (paid)?", 'Yes, make one'

            def run_(choice, quote, words, eid=eid):
                s = V.session_of(ctx['store'], run, ctx['outputs'])
                got = {**held, eid: {'verdict': choice, 'quote': quote, 'frames': stamps[eid]}}
                s['chat_round'] = got
                V.save_session(ctx['store'], run, s)
                left = [e for e, _ in elements if e not in got]
                if left:
                    return {'stored': eid, 'left': len(left)}
                # the server records the first step for every element of the round at once; one the plan no longer names is left out
                verdicts = {e: {'verdict': got[e]['verdict'] if e in got else 'ignore'} for e, _ in everything}
                out = V.round_done(ctx['store'], ctx['user'], run, ctx['outputs'], verdicts, quote, conn=ctx['conn'])
                s = V.session_of(ctx['store'], run, ctx['outputs'])
                s.pop('chat_round', None)
                V.save_session(ctx['store'], run, s)
                return {**out, 'tell': (f"{len(out.get('queued') or [])} reference set(s) are now being made, about ₹{out.get('cost_inr', 0):g}. " if out.get('queued') else '') + NOTHING}
            items.append(_item(f'round1:{eid}', 'reference', f'References, {n} of {len(elements)}', q, run_,
                               [_button(yes, 'approve'), _button('Leave it out', 'ignore')], show=[_pic(run, f, f'{eid}-footage-{i + 1}') for i, f in enumerate(frames[:4])]))
        return items
    if step not in (2, 'making'):
        return []
    budget = V._set_budget(run, session, V.visuals_spend(ctx['conn'], run))
    todo = [(eid, row) for eid, row in elements if eid in kinds and not row.get('ignored') and not row.get('from_footage')]
    for n, (eid, row) in enumerate(todo, 1):
        rows = sorted(V._set_rows(session, eid, row.get('set')), key=lambda r: int(r.get('set_n') or 1))
        where = f'Reference sets, {n} of {len(todo)}'
        if rows and not V._answered(session, kinds, eid, row):
            person = kinds.get(eid) == 'person'
            show = [_pic(run, r['id'], f'{eid}-{LETTERS[i]}') for i, r in enumerate(rows[:len(LETTERS)])]
            sheet = sheet_of(ctx['store'], run, rows[:len(LETTERS)]) if not items else None
            if sheet:
                show.insert(0, {'key': sheet, 'name': f'{eid}-side-by-side.jpg'})

            def run_(choice, quote, words, eid=eid):
                if choice.startswith('use:'):
                    ans = {'verdict': 'yes', 'golden': choice[4:], 'words': ''}
                elif choice == 'yes':
                    ans = {'verdict': 'yes', 'golden': None, 'words': ''}
                else:
                    ans = {'verdict': choice, 'golden': None, 'words': words if choice == 'correct' else ''}
                V.set_answer(ctx['store'], ctx['user'], run, ctx['outputs'], eid, ans['verdict'], ans['golden'], ans['words'])
                out = flush_sets(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], quote)
                return out if out is not None else {'tell': 'Your answer is kept. It is recorded as soon as the sets still being made are back.'}
            if person:
                buttons = [_button('Yes', 'yes'), _button('No', 'no'), _button('Correct it', 'correct', words=True, tell='Ask the operator what to correct.')]
                more, q = [], f'{names[eid]}: is this set right for this person?'
            else:
                uses = [_button(f'Use {LETTERS[i]}', 'use:' + r['id']) for i, r in enumerate(rows[:len(LETTERS)])]
                buttons = uses[:3] + [_button('None of these', 'no')]
                more = uses[3:] + [_button('Correct it', 'correct', words=True, tell='Ask the operator what to correct.')]
                q = f'{names[eid]}: which picture is the reference?'
            items.append(_item(f"set:{eid}:{row.get('set')}", 'reference set', where, q, run_, buttons, show=show, more=more))
        elif not rows and not V._set_rows(session, eid, row.get('set'), ('generating', 'approved')):
            if V.set_cause(session, plan, eid, budget):
                continue   # something stands in its way (a spec to approve first, the spend limit): that comes in its own turn

            def run_(choice, quote, words, eid=eid):
                if choice == 'make':
                    return {**V.set_make(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], eid), 'tell': 'The set is being made. ' + NOTHING}
                return V.set_aside(ctx['store'], ctx['user'], run, ctx['outputs'], eid, words or quote)
            items.append(_item(f'setmake:{eid}', 'reference set to make', where, f'{names[eid]}: its reference set was not made. Make it now (paid)?', run_,
                               [_button('Make it', 'make'), _button('Leave it out', 'aside')]))
    return items


# ---------- everything else that waits: questions, pictures, specs, takes ----------

def _spec_text(spec):
    rows = []
    for k, v in (spec or {}).items():
        if isinstance(v, list):
            rows += [f'{k}: ' + (', '.join(f'{a}: {b}' for a, b in x.items() if b not in (None, '', [])) if isinstance(x, dict) else str(x)) for x in v]
        elif v not in (None, '', []):
            rows.append(f'{k}: {v}')
    return '\n'.join(rows)[:6000]


def _drawing_items(ctx):
    """design/194: a thing's drawing set that waits for the operator: its labelled sheets, the facts with their sources, the sizes that are assumed.
    Approved by its exact content, before any paid picture uses it."""
    from . import drawings
    session, plan, run, store, user, outputs, conn = ctx['session'], ctx['plan'], ctx['run'], ctx['store'], ctx['user'], ctx['outputs'], ctx['conn']
    rows = [(eid, r) for eid, r in (session.get('drawings') or {}).items() if r.get('status') == 'proposed']
    names = _names(plan) if plan else {}
    items = []
    for n, (eid, r) in enumerate(rows, 1):
        def run_(choice, quote, words, eid=eid, sha=r['sha256']):
            return drawings.verdict(conn, store, user, run, outputs, eid, sha, choice == 'yes', quote, words)
        lines = ['Each sheet says what it shows and what it is for. These drawings go to the picture AI as references, so check them against what you know of the thing.']
        if r.get('sourced'):
            lines += ['Sizes and facts with a source:'] + [f'- {x}' for x in r['sourced'][:12]]
        if r.get('assumed'):
            lines += ['ASSUMED, with no source (say if any is wrong):'] + [f'- {x}' for x in r['assumed'][:12]]
        items.append(_item(f"drawing:{eid}:{r['sha256'][:10]}", 'drawing', f'Reference drawings, {n} of {len(rows)}', f"{names.get(eid) or r.get('name') or eid}: are these reference drawings right?", run_,
                           [_button('Yes', 'yes'), _button('Correct it', 'correct', words=True, tell='Ask the operator what is wrong in the drawings.')],
                           text=chr(10).join(lines), show=[{'key': v['labelled_key'], 'name': f"drawing-{eid}-{v['id']}.png"} for v in r['views']]))
    if plan and session.get('guides'):   # Area B: the drawing of an AI video shot, before its still
        from . import guide
        shots = {sh['id']: sh for _, sh in V._accepted_shots(plan, session)}
        for sid, g in session['guides'].items():
            d = g.get('drawing') or {}
            if sid not in shots or d.get('status') != 'proposed' or d.get('sha256') != g['sha256']:
                continue

            def run_(choice, quote, words, sid=sid, sha=g['sha256']):
                return guide.drawing_verdict(conn, store, user, run, outputs, sid, sha, choice == 'yes', quote, words)
            lines = ["Each person's pale side with the dark stripe is the chest, the purple side is the back, the orange arm is the right arm, the arm that works. "
                     'Check that each person faces what they do and that the working hand can reach it.']
            lines += (['Changed from the plan to make the shot possible:'] + [f'- {c}' for c in d['changes']]) if d.get('changes') else []
            lines += (['Notes:'] + [f'- {c}' for c in d['notes']]) if d.get('notes') else []
            items.append(_item(f"shot-drawing:{sid}:{g['sha256'][:10]}", 'drawing', 'AI video, the layout drawing of the shot', f"{shots[sid].get('title') or sid}: is the shot laid out right in these two drawings?", run_,
                               [_button('Yes', 'yes'), _button('Correct it', 'correct', words=True, tell='Ask the operator what is wrong in the drawing of the shot.')],
                               text=chr(10).join(lines), show=[{'key': v['labelled_key'], 'name': f"{sid}-drawing-{v['id']}.png"} for v in d['views']]))
    return items


def _waiting_items(ctx):
    session, plan, run, store, user, outputs, conn = ctx['session'], ctx['plan'], ctx['run'], ctx['store'], ctx['user'], ctx['outputs'], ctx['conn']
    if not plan:
        return []
    from . import motion
    names = _names(plan)
    take_rows = V.take_jobs(conn, run)
    rows = V.waiting(session, plan, run.get('code'), take_rows, V._set_budget(run, session, V.visuals_spend(conn, run)))
    rows = [w for w in rows if w['kind'] not in ('set to judge', 'set to make')]   # the round's own items, above
    shots = {sh['id']: sh for _, sh in V._accepted_shots(plan, session)}
    title = lambda sid: (shots.get(sid) or {}).get('title') or sid
    items = []
    for n, w in enumerate(rows, 1):
        kind, group, it = w['kind'], w['group'], w['item']
        where = f'{n} of {len(rows)} waiting'
        ref = session['references'].get(it)
        if kind == 'question to answer':
            q = session['questions'][it]
            choices = [str(c) for c in (q.get('choices') or [])]
            buttons = [_button(c[:40], f'c{i + 1}') for i, c in enumerate(choices)]   # a question always has two or more (the server refuses fewer)
            items.append(_item(f'question:{it}', 'question', where, q['question'],
                               lambda choice, quote, words, it=it, choices=choices: V.answer(store, user, run, outputs, it, words or choices[int(choice[1:]) - 1]), buttons[:4],
                               text='\n'.join(f'- {c}' for c in choices) if len(choices) > 4 or any(len(c) > 40 for c in choices) else '', more=buttons[4:],
                               show=[_pic(run, it, f'question-{it}')] if ref and ref.get('sha256') else []))
        elif kind in ('style sheet to approve', 'sheet to approve', 'picture to answer') and ref:
            what = 'The style sheet of the graphics' if kind.startswith('style') else names.get(ref.get('element_id')) or w['label']

            def run_(choice, quote, words, ref=ref):
                if choice == 'yes':
                    return V.approve_reference(store, user, run, outputs, ref['id'], ref['sha256'], quote, conn)
                return V.reject_reference(store, user, run, outputs, ref['id'], words, quote)
            items.append(_item(f"picture:{ref['id']}:{str(ref.get('sha256'))[:10]}", 'picture', where, f'{what}: is this picture right?', run_,
                               [_button('Yes', 'yes'), _button('No', 'no'), _button('Correct it', 'correct', words=True, tell='Ask the operator what to correct.')],
                               text='\n'.join('- ' + str((x.get('line') or x.get('check') or x.get('text') or '') if isinstance(x, dict) else x) for x in (ref.get('checklist') or [])[:6]),
                               show=[_pic(run, ref['id'], f"picture-{ref['id']}")]))
        elif kind == 'graphics to approve':
            chain = V.state_chain(session, group) or []

            def run_(choice, quote, words, group=group, chain=chain):
                if choice == 'yes':
                    return V.sequence(store, user, run, outputs, group, [r['id'] for r in chain], quote)
                return V.reject_reference(store, user, run, outputs, chain[-1]['id'], words, quote)
            items.append(_item(f'graphics:{group}:{len(chain)}', 'graphics', where, f'{title(group)}: are these {len(chain)} steps of the graphic right?', run_,
                               [_button('Yes', 'yes'), _button('Correct it', 'correct', words=True, tell='Ask the operator what to correct.')],
                               show=[_pic(run, r['id'], f'{group}-step-{i + 1}') for i, r in enumerate(chain)]))
        elif kind in ('drawing spec to approve', 'material spec to approve'):
            if kind.startswith('material'):
                key = 'element:' + group
                spec = next((e.get('material_spec') for e in plan['elements'] if e['id'] == group), None)
                what = f'{names.get(group, group)}: the facts of this material'
            else:
                key, spec, what = group, (shots.get(group) or {}).get('drawing_spec'), f'{title(group)}: the parts and sizes of this drawing'

            def run_(choice, quote, words, key=key):
                if choice == 'yes':
                    return V.approve_spec(store, user, run, outputs, key, quote)
                return V.correct_spec(store, user, run, outputs, key, words)
            items.append(_item(f"spec:{key}:{V.spec_digest(spec)[:10] if spec else ''}", 'spec', where, f'{what}. Are they right?', run_,
                               [_button('Yes', 'yes'), _button('Correct it', 'correct', words=True, tell='Ask the operator which value is wrong and what it should be.')], text=_spec_text(spec)))
        elif kind == 'reuse to approve':
            p = (session.get('reuse_pending') or {}).get(group) or {}
            if (session.get('chat_asked') or {}).get(f'reuse:{group}') == str(p):
                continue   # the operator said no to this very proposal: the assistant plans another picture; it is not asked twice

            def run_(choice, quote, words, group=group, p=p):
                if choice == 'yes':
                    return V.approve_reuse(store, user, run, outputs, group, quote)
                _asked(store, run, outputs, f'reuse:{group}', str(p))
                return {'for_the_assistant': words, 'tell': 'Another picture will be planned for this shot.'}
            items.append(_item(f'reuse:{group}', 'reuse', where, f'{title(group)}: the same picture is shown a second time here. Allow it?', run_,
                               [_button('Yes, reuse it', 'yes'), _button('No, another picture', 'no', words=True, tell='Ask the operator what they want there instead.')],
                               text='\n'.join(f'{k}: {v}' for k, v in p.items() if k in ('reason', 'considered') and v)))
        elif kind == 'take to select':
            job = next((j for j in take_rows if str(j['id']) == str(it)), None)
            if not job:
                continue
            res = job.get('result') or {}
            fin = (res.get('finish') or []) if (job.get('request') or {}).get('kind') == 'motion' else []
            check = (session.get('take_checks') or {}).get(str(job['id'])) or {}
            lines = [f"{l.get('line')}: {l.get('state')}" + (f" ({l.get('seen')})" if l.get('seen') else '') for l in (check.get('scorecard') or [])][:8]
            watch = check.get('watch') or {}
            look = [f"Look at: {watch.get('what')}" + (f" at {watch['at_s']} s" if watch.get('at_s') is not None else '')] if watch.get('what') else []
            if check.get('blocked'):   # the guide came back unedited, or the wrong length: not a take, nothing to select; the word to send it again is asked with the shot
                continue
            fact = ((session.get('motion_checks') or {}).get(group) or [None])[-1] if (job.get('request') or {}).get('kind') == 'motion' else None
            fact_line = [f"Fact check: {'passed' if fact.get('pass') else 'not passed'}" + (f" ({str(fact.get('notes'))[:160]})" if fact.get('notes') else '')] if isinstance(fact, dict) else []
            ev = res.get('evidence') or {}
            failed = [str(c.get('check')) for c in (check.get('must_failed') or [])] + [str(l.get('line')) for l in (check.get('scorecard') or []) if l.get('state') == 'Fail']
            hold = bool(failed or check.get('not_read') or (isinstance(fact, dict) and fact.get('pass') is False) or ev.get('timing_matches_placement') is False)
            why_hold = ('The checks did not pass it (' + ', '.join(dict.fromkeys(failed)) + ')' if failed else 'It was not checked' if check.get('not_read')
                        else 'Its fact check did not pass' if isinstance(fact, dict) and fact.get('pass') is False else 'It is shorter than its place in the film' if hold else '')
            text = '\n'.join('- ' + x for x in ([motion.finish_words(fin)] if fin else []) + fact_line + lines + look
                             + ([why_hold + ': to select it all the same, the operator says why.'] if hold else []) if x)

            def run_(choice, quote, words, job=job, group=group):
                if choice == 'select':   # a held take is selected only with the operator's own reason (never a note written for them)
                    return V.select_take(conn, store, user, run, outputs, str(job['id']), quote, words if hold else (words or 'selected in the chat'), words if hold else '', None)
                if choice == 'no-effect':
                    out = V.motion_finish(conn, store, user, run, outputs, group, False)
                    V.review_take(conn, store, user, run, outputs, str(job['id']), 'rejected', "made again without the effect, at the operator's word", '', quote)   # the drawing with the effect is not asked about again
                    return {**out, 'tell': 'The drawing is being made again without the effect. ' + NOTHING}
                return V.review_take(conn, store, user, run, outputs, str(job['id']), 'rejected', words, '', quote)
            drawn = job.get('provider') == 'drawn'
            show = [{'key': res['key'], 'name': f"{group}-{'drawing' if drawn else 'take'}.mp4"}] if res.get('key') else []
            sheet_key = res.get('sheet_key') or check.get('sheet_key')
            show += [{'key': sheet_key, 'name': f'{group}-frames.jpg'}] if sheet_key else []
            items.append(_item(f"take:{job['id']}", 'take', where, f"{title(group)}: is this {'drawing' if drawn else 'take'} right for the film?", run_,
                               [_button('Select', 'select', words=hold, tell=why_hold + ': ask the operator why it is right for the film all the same.'),
                                _button('Reject', 'reject', words=True, tell='Ask the operator what is wrong with it.')] + ([_button('Take the effect away', 'no-effect')] if fin else []),
                               text=text, show=show))
    return items


def _guide_items(ctx):
    """An AI video shot: its still on the overlay, then the word to shoot. Both are the operator's."""
    session, plan, run, store, user, outputs, conn = ctx['session'], ctx['plan'], ctx['run'], ctx['store'], ctx['user'], ctx['outputs'], ctx['conn']
    if not plan or not session.get('guides'):
        return []
    from . import guide
    shots, items = {sh['id']: sh for _, sh in V._accepted_shots(plan, session)}, []
    for sid, g in session['guides'].items():
        if sid not in shots:
            continue
        title = shots[sid].get('title') or sid
        still = next((s for s in g.get('stills') or [] if s.get('status') == 'candidate' and s.get('guide_sha256') == g['sha256'] and s.get('key')), None)
        if still:
            def run_(choice, quote, words, sid=sid, still=still):
                if choice == 'approve':
                    return guide.approve_still(conn, store, user, run, outputs, sid, still['id'], still['sha256'], quote)
                return guide.reject_still(conn, store, user, run, outputs, sid, still['id'], words, quote)
            show = ([{'key': still['overlay_key'], 'name': f'{sid}-still-on-the-guide.png'}] if still.get('overlay_key') else []) + [{'key': still['key'], 'name': f'{sid}-still.png'}]
            items.append(_item(f"still:{sid}:{still['id']}", 'still', 'AI video, the still',
                               f'{title}: this still starts the shot. On the first picture, does every person and thing sit on the red outlines?', run_,
                               [_button('Approve', 'approve'), _button('Reject', 'reject', words=True, tell='Ask the operator what is wrong with the still.')], show=show))
            continue
        if not g.get('take_prompt') or sid in session['selections']:
            continue
        card = guide.ready_card(session, sid, V.prices()['video_inr_per_s'])
        stamp = g['sha256'] + str((g.get('take_prompt') or {}).get('at') or (g.get('take_prompt') or {}).get('prompt'))
        takes = [j for j in V.take_jobs(conn, run, sid) if j['provider'] == 'video']
        checks = session.get('take_checks') or {}
        rejected = lambda j: (session['reviews'].get(str(j['id'])) or [{}])[-1].get('decision') == 'rejected'
        unusable = lambda j: bool((checks.get(str(j['id'])) or {}).get('blocked'))
        open_take = any(j['status'] in ('queued', 'running', 'storage_pending') or (j['status'] == 'ready' and not rejected(j) and not unusable(j)) for j in takes)
        last = takes[-1] if takes else None
        again = bool(last and last['status'] == 'ready' and not rejected(last) and unusable(last))   # the clip that came back is not a take: the same request may go once more, on the operator's word
        stamp = stamp + (':again:' + str(last['id']) if again else '')
        if card['ready'] and not open_take and (g.get('shoot_asked') or {}).get('stamp') != stamp:
            def run_(choice, quote, words, sid=sid, stamp=stamp, again=again):
                out = guide.shoot(conn, store, user, run, outputs, sid, quote, again) if choice == 'shoot' else {'for_the_assistant': words}
                s = V.session_of(store, run, outputs)
                s['guides'][sid]['shoot_asked'] = {'stamp': stamp, 'answer': 'shoot' if choice == 'shoot' else 'not yet', **({'words': words} if choice != 'shoot' else {})}   # asked once for this state of the shot
                V.save_session(store, run, s)
                return {**out, **({'tell': 'The take is being made. ' + NOTHING} if choice == 'shoot' else {})}
            show = [{'key': k, 'name': n} for k, n in ((card.get('guide_key'), f'{sid}-guide.mp4'), ((card.get('still') or {}).get('overlay_key'), f'{sid}-still-on-the-guide.png')) if k]
            why = str((checks.get(str(last['id'])) or {}).get('blocked')) if again else ''
            items.append(_item(f"shoot:{sid}:{hashlib.sha256(stamp.encode()).hexdigest()[:10]}", 'shoot', 'AI video, the take',
                               (f"{title}: the clip that came back cannot be used ({why}). Send the same request once more? It costs about ₹{card['cost_inr']:g}." if again
                                else f"{title}: make the take now? It is {card['seconds']} s and costs about ₹{card['cost_inr']:g}."), run_,
                               [_button('Send it again' if again else 'Shoot', 'shoot'), _button('Not yet', 'wait', words=True, tell='Ask the operator what should change first.')],
                               text=str(card.get('look_for') or ''), show=show))
    return items


def _record_items(ctx):
    session, plan = ctx['session'], ctx['plan']
    if not plan:
        return []
    asked, items = session.get('chat_record_wait') or {}, []
    for gap in plan['gaps']:
        gid = gap['gap_id']
        if gid not in session['accepted'] or gid in session['recorded_gaps'] or gid in asked:
            continue
        shots = V.shots_of(plan, session, gid)
        if shots and all(s['id'] in session['selections'] or s['id'] in session['assets'] for s in shots):
            def run_(choice, quote, words, gid=gid):
                if choice == 'record':
                    return V.record_gaps(ctx['conn'], ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], [gid], quote)
                s = V.session_of(ctx['store'], ctx['run'], ctx['outputs'])
                s.setdefault('chat_record_wait', {})[gid] = words
                V.save_session(ctx['store'], ctx['run'], s)
                return {'for_the_assistant': words}
            items.append(_item(f'record:{gid}', 'record', 'Recording', f"Gap {gid}{' · ' + gap['title'] if gap.get('title') else ''}: every shot of it is chosen. Record it into the film?", run_,
                               [_button('Record it', 'record'), _button('Not yet', 'wait', words=True, tell='Ask the operator what should change first.')]))
    return items


def _asked(store, run, outputs, key, value):
    """Remember that the operator answered this, where the server keeps no state of its own for the answer, so it is not asked twice."""
    s = V.session_of(store, run, outputs)
    s.setdefault('chat_asked', {})[key] = value
    V.save_session(store, run, s)


def flush_sets(conn, store, user, run, outputs, quote=''):
    """Record every whole answer kept on a reference set (the operator gave each one in the chat). None while a set is still being made, or when
    there is nothing to record: the answers stay kept. Any other refusal of the server is raised as it is."""
    s = V.session_of(store, run, outputs)
    rd = s.get('round')
    if not (rd and rd.get('kept') and s.get('current')):
        return None
    kinds = _kinds(V.current_plan(store, s))
    kept = {e: a for e, r in rd['elements'].items() if e in kinds and not r.get('ignored') for a in [V._answered(s, kinds, e, r)] if a and V._set_rows(s, e, r.get('set'))}
    if not kept:
        return None
    try:
        return V.round_sets(store, user, run, outputs, kept, quote, conn=conn, partial=True)
    except V.Problem as exc:
        if 'still being made' in str(getattr(exc, 'message', '') or exc):
            return None
        raise


def _candidates(ctx):
    """Every decision that waits for the operator, in the order it is asked; a summary for the treatment; and what is with the assistant meanwhile."""
    t_items, summary, back = _treatment_items(ctx)
    if t_items or back:
        none_yet = not any(v['state'] == 'accepted' for v in ((ctx['session'].get('treatment_draft') or {}).get('lines') or {}).values())
        return t_items, (summary if t_items and (none_yet or len(t_items) == 1) else ''), ([f"Treatment: the assistant is revising {', '.join('the direction' if k == 'direction' else 'gap ' + k for k in back)}."] if back else [])
    p_items, revising = _plan_items(ctx)
    note = [f"Plan: the assistant is revising {', '.join(revising)}."] if revising else []
    if p_items:
        return p_items, '', note
    for step in (_drawing_items, _round_items, _waiting_items, _guide_items, _record_items):   # design/194: a drawing set is approved before the pictures made from it
        items = step(ctx)
        if items:
            return items, '', note
    return [], '', note


def working(conn, run):
    """One line per shot or thing something is being made for, in plain words: what the operator is waiting on."""
    rows = conn.execute("select unit, provider, status from vw2_jobs where run_id=%s and stage='visuals' and status in ('queued','running','storage_pending') order by created_at", (run['id'],)).fetchall()
    seen, out = set(), []
    for r in rows:
        key = (r['unit'], r['provider'])
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{r['unit'] or 'the film'}: {MAKING.get(r['provider'], 'a picture is being made')}" + (' (waiting its turn)' if r['status'] == 'queued' else ''))
    return out


# ---------- the two calls ----------

def _ctx(conn, store, user, run, outputs):
    session = V.session_of(store, run, outputs)
    plan = V.current_plan(store, session) if session.get('current') else None
    return {'conn': conn, 'store': store, 'user': user, 'run': run, 'outputs': outputs, 'session': session, 'plan': plan}


def _split(question):
    """(what the decision is about, the short question itself). 'Gap G1 (changed). Do you accept this line?' -> ('Gap G1 (changed)', 'Do you accept this line?')."""
    m = re.match(r'^(.*?)(?:\. |: )(?=[^.:]*\?)(.*)$', question, re.S)
    if not m:
        return '', question
    ask = m.group(2).strip()
    return m.group(1).strip(), ask[:1].upper() + ask[1:]


def _paragraphs(text):
    """A long paragraph as one line per sentence, so it can be read; text that already has its own lines is left as it is."""
    text = str(text or '').strip()
    if not text or '\n' in text or len(text) < 240:
        return text
    return '\n'.join('- ' + s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\u201c])', text) if s.strip())


SAYS = {'Accept': 'Take it as it is', 'Change this': 'I will ask you what to change', 'Yes': 'It is right', 'No': 'It is wrong; another is made', 'Correct it': 'I will ask you what to correct',
        'None of these': 'None is right; the set is made again', 'Select': 'Use it in the film', 'Reject': 'I will ask you what is wrong with it', 'Approve': 'It is right; go on',
        'Shoot': 'Make the take now (paid)', 'Send it again': 'Send the same request once more (paid)', 'Not yet': 'I will ask you what should change first', 'Record it': 'Put this gap into the film',
        'Leave it out': 'This thing gets no reference', 'Make it': 'Make the set now (paid)', 'Yes, use it': 'Use the footage picture', 'Yes, make one': 'Have a set made (paid)',
        'Take the effect away': 'Make the drawing again without the added effect', 'Yes, reuse it': 'Show the same picture again here', 'No, another picture': 'I will ask you what you want there'}


def _says(label):
    return SAYS.get(label) or ('This one becomes the reference' if label.startswith('Use ') else '')


def _typed(item):
    """The choice a typed answer is recorded as: the first button that takes the operator's own words (Change this, Correct it, Reject, Not yet)."""
    return next((b['choice'] for b in item['buttons'] + list(item.get('other_choices') or []) if b.get('needs_words')), None)


def _message(item, summary):
    """What the operator reads above the question: where it is, what it is about, the content laid out, the totals, and how to ask for a change
    in one step. The question itself comes after, short."""
    subject, _ask = _split(item['question'])
    hint = '> To ask for a change in one step, choose **Other** and type what should change.' if _typed(item) else ''
    parts = [f"**{item['position']}**", f'### {subject}' if subject else '', _paragraphs(item.get('text')), f'*{summary}*' if summary else '', hint]
    return '\n\n'.join(x for x in parts if x)


def _public(item, summary, n_waiting, one=False):
    out = {k: v for k, v in item.items() if not k.startswith('_')}
    out['buttons'] = [{**b, 'description': _says(b['label'])} for b in out['buttons']]   # the line under each button, the same for every operator
    typed = _typed(item)
    return {**out, 'message': _message(item, summary), 'ask': _split(item['question'])[1], **({'typed_answer': typed} if typed else {}),
            'waiting_after_this': max(0, n_waiting - 1), **({'summary': summary} if summary else {}), 'needed': True, 'say_last': NEEDED,
            'how': ('The tool saved the files of `show` in the run folder: show them to the operator in this order (' + LOOK_ONLY + '). ' if item.get('show') else '')
                   + 'Post `message` as your own text, exactly as it is laid out (its heading, its lines, its totals); add nothing to it. '
                   + 'Then ask with the question tool: the question is `ask` and nothing else (never the text of `message` again); each button is an option with its `label` and its '
                   + '`description`, in this order, and no others. The panel adds "Other" by itself: it is the operator\'s box for typing. '
                   + (f"A typed answer that asks for a change is recorded as `--choice {typed}` with their words as `--notes`, at once, without a further question; " if typed else 'A typed answer is recorded with their words as `--quote`; ')
                   + 'a typed answer that plainly accepts is recorded as the accepting button. '
                   f"Record the reply: `vw visuals decide{' --one' if one else ''} --item {item['id']} --choice <the button's choice> --quote \"<their words>\"` (`--notes` for what to change). Say nothing about what you did."}


# ---------- design/190 (SK, 13 Nov 2026): the treatment's lines, and the plan's gaps, on one card; one submit ----------

CARD_KINDS = ('treatment line', 'plan gap')
CARD_ALL, CARD_PART = 12, 10   # up to 12 entries on one card; a longer step comes as cards of 10
CARD_SAY = ('What to do: read each {what} and choose Accept or Change this. The numbers at the top show where you are: green is accepted, amber has a change. '
            'When every number is coloured, press Submit all. Nothing is recorded until then.')


def _lit(value):
    """A string for the card's script, in pieces of at most 1200 characters, so no line of the card is too long to be read back whole."""
    s = str(value)
    return '+\n'.join(json.dumps(s[i:i + 1200], ensure_ascii=False) for i in range(0, len(s), 1200)) or '""'


def _card_code(card_id, items, summary):
    """The card as the chat shows it: the fixed page (chat_card.html) with this card's entries written into it, one row to a line."""
    plan = items[0]['kind'] == 'plan gap'
    entries = []
    for it in items:
        c = it['_card']
        body = (f"t:{_lit(c['t'])}" if 't' in c else 'r:[\n' + ',\n'.join(f'[{_lit(k)},{_lit(v)}]' for k, v in c['r']) + ']' if 'r' in c
                else f"tot:{_lit(c['tot'])},tb:[\n" + ',\n'.join('[' + ','.join(_lit(x) for x in row) + ']' for row in c['tb']) + ']')
        ch = f"ch:[{','.join(_lit(x) for x in c['ch'])}]," if c.get('ch') else ''
        entries.append(f"{{n:{_lit(c['n'])},c:{c['c']},{ch}{body}}}")
    data = ('{' + f"id:{_lit(card_id)},say:{_lit(CARD_SAY.format(what='gap' if plan else 'line'))},sum:{_lit(summary or '')},auto:1,"
            + f"dir:{1 if items[0]['id'].startswith('treatment:direction:') else 0},cols:{json.dumps(GAP_COLS)},w:[5,19,13,9,27,27],e:[\n" + ',\n'.join(entries) + ']}')
    data = data.replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')   # nothing in an entry can end the script or break a line of it
    return Path(__file__).with_name('chat_card.html').read_text(encoding='utf-8').replace('__DATA__', data, 1)


def _card(session, items, summary):
    """The card for these entries, and the session's note of it. A card shown again keeps its number; a new set of entries gets a new one."""
    ids = [i['id'] for i in items]
    held = session.get('chat_card') or {}
    if held.get('items') == ids:
        card_id, changed = held['id'], False
    else:
        at = datetime.now(timezone.utc).isoformat()
        card_id = 'card-' + hashlib.sha256(('|'.join(ids) + at).encode()).hexdigest()[:10]
        session['chat_card'], changed = {'id': card_id, 'items': ids, 'at': at}, True
    plan = items[0]['kind'] == 'plan gap'
    what = 'gaps of the plan' if plan else 'lines of the treatment'
    return {'id': card_id, 'step': 'Plan' if plan else 'Treatment', 'entries': len(items), 'widget_code': _card_code(card_id, items, summary),
            'say_before': f'Here are {len(items)} {what} on one card. Answer each one, then press Submit all.',
            'answers_file': f'work/chat/{card_id}.answers.json'}, changed


CARD_HOW = ('The tool saved the card in the run folder (`card_file`). Post `say_before` as your own one line. Then read `card_file` and show it with the card tool '
            '(`mcp__visualize__show_widget`): `widget_code` is the whole text of that file, character for character, nothing added, changed or left out; `title` is the card\'s id; '
            'one loading message, "Laying out the card". Do not call `read_me` for it and do not post the entries as text as well. Then wait for the operator. '
            'Submit all puts one message into the chat: "Card answers: {…}". Write the part from { to } as it is into the file `answers_path` and run '
            '`vw visuals card --file <answers_file>` (`answers_file` as it is given, the path inside the run folder): one call records every answer and brings what comes next. If the operator answers in words instead, write the same file yourself: '
            '{"card": "<id>", "answers": [{"n": 1, "choice": "accept"}, {"n": 2, "choice": "change", "notes": "<their words>"}]} (n is the entry\'s number on the card). '
            'If the card tool is not there or fails, run `vw visuals next --one`: the same decisions, one at a time. Say nothing about what you did.')


def card_answer(conn, store, user, run, outputs, card_id, answers, one=False):
    """Every answer of a card, recorded in one call through the same decision functions as one at a time. A card is recorded once: the same card
    sent again changes nothing. An entry that is no longer open (recorded before, or changed since the card) is named and left as it is."""
    session = V.session_of(store, run, outputs)
    if card_id in (session.get('chat_cards_done') or []):
        return {'answered_card': card_id, 'already': True, 'recorded': [], **next_item(conn, store, user, run, outputs, one),
                'then': 'This card was recorded before: nothing was changed. What comes next is in this answer.'}
    handed = session.get('chat_card') or {}
    V.need(handed.get('id') == card_id, f'{card_id} is not the card that is open. Run `vw visuals next` and show the card it gives; an older card higher in the chat is not answered.')
    ids, seen = handed['items'], {}
    V.need(answers, 'The card has no answers: each is {"n": <entry number>, "choice": "accept" or "change", "notes": "<what to change>"}.')
    for a in answers:
        n, choice, words = a['n'], a['choice'], str(a.get('notes') or '').strip()
        V.need(1 <= n <= len(ids), f'The card has {len(ids)} entries; there is no entry {n}.')
        V.need(n not in seen, f'Entry {n} is answered twice.')
        V.need(choice == 'accept' or words, f'Entry {n}: say what should change (notes).')
        seen[n] = (choice, words)
    open_ = {i['id']: i for i in _candidates(_ctx(conn, store, user, run, outputs))[0] if i['kind'] in CARD_KINDS}
    direction_changes = ids[0].startswith('treatment:direction:') and ids[0] in open_ and seen.get(1, ('', ''))[0] == 'change'
    todo, not_open, held, before = [], [], [], []
    lines, key_of = (session.get('treatment_draft') or {}).get('lines') or {}, lambda iid: iid.split(':')[1]
    for n in sorted(seen):
        iid, choice = ids[n - 1], seen[n][0]
        if direction_changes and n != 1:
            held.append(n)   # every gap line is written again from the changed direction
        elif iid not in open_ and (((lines.get(key_of(iid)) or {}).get('state') == ('accepted' if choice == 'accept' else 'sent_back')) if iid.startswith('treatment:')
                                   else key_of(iid) in ((session.get('accepted') or {}) if choice == 'accept' else (session.get('revisions') or {}))):
            before.append(n)   # an earlier attempt to send this card recorded it, with this same answer
        elif iid not in open_:
            not_open.append(n)
        else:
            todo.append((n, open_[ids[n - 1]], *seen[n]))
    treatment = bool(todo) and todo[0][1]['kind'] == 'treatment line'
    recorded = list(before)
    for n, it, choice, words in todo:   # the changes first, each with its own words; then every accepted entry in one record
        if choice == 'change':
            if treatment:
                V.treatment(store, user, run, outputs, None, words, send_back=[it['_key']], notes=words)
            else:
                V.revise_gap(store, user, run, outputs, it['_key'], words, words)
            recorded.append(n)
    accepted = [(n, it['_key']) for n, it, choice, _ in todo if choice == 'accept']
    if accepted:
        quote, keys = f'Accepted on the card ({card_id})', [k for _, k in accepted]
        if treatment:
            V.treatment(store, user, run, outputs, None, quote, accept=keys)
        else:
            V.accept(store, user, run, outputs, keys, quote)
        recorded += [n for n, _ in accepted]
    session = V.session_of(store, run, outputs)
    session['chat_cards_done'] = ((session.get('chat_cards_done') or []) + [card_id])[-30:]   # the card is spent: it is never taken up again
    session.pop('chat_card', None)
    V.save_session(store, run, session)
    nxt = next_item(conn, store, user, run, outputs, one)
    changed = sorted([n for n, _, choice, _ in todo if choice == 'change'] + [n for n in before if seen[n][0] == 'change'])
    return {'answered_card': card_id, 'recorded': sorted(recorded), 'not_open': not_open, 'held': held, **nxt,
            'then': f'{len(recorded)} answer(s) recorded. '
                    + (f"Not recorded, because the direction changes and every line is written again from it: entries {', '.join(map(str, held))}. " if held else '')
                    + (f"Not recorded, no longer open (recorded before, or changed since the card): entries {', '.join(map(str, not_open))}; any still open are asked again. " if not_open else '')
                    + (f"The operator asked for a change in entries {', '.join(map(str, changed))}: make only those changes, send them again, and they return in their turn. " if changed else '')
                    + ('What comes next is in this answer: show it now; do not run `vw visuals next` for it.' if nxt.get('item') or nxt.get('card') else 'No decision waits now: give the `working` lines and the last line.')}


def next_item(conn, store, user, run, outputs, one=False):
    """The one decision the operator takes now; or, for the treatment's lines and the plan's gaps, all of them on one card (design/190; `one` asks
    them one at a time, the older way, kept for a machine that cannot show the card); or that nothing is needed and what is being made."""
    try:
        flush_sets(conn, store, user, run, outputs)
    except V.Problem:
        pass   # said again when the operator next answers a set
    items, summary, with_assistant = _candidates(_ctx(conn, store, user, run, outputs))
    session = V.session_of(store, run, outputs)
    if items and not one and len(items) >= 2 and items[0]['kind'] in CARD_KINDS:
        on_card = items if len(items) <= CARD_ALL else items[:CARD_PART]
        card, changed = _card(session, on_card, items[0].get('_summary') or '')
        if changed or session.pop('chat_item', None):
            session.pop('chat_item', None)
            V.save_session(store, run, session)
        return {'item': None, 'card': card, 'waiting_after_this': len(items) - len(on_card), 'needed': True, 'say_last': NEEDED, 'how': CARD_HOW}
    if items:
        item = items[0]
        if (session.get('chat_item') or {}).get('id') != item['id'] or session.get('chat_card'):
            session['chat_item'] = {'id': item['id'], 'at': datetime.now(timezone.utc).isoformat()}
            session.pop('chat_card', None)   # one at a time now: a card shown before is not answered any more
            V.save_session(store, run, session)
        return {'item': _public(item, summary, len(items), one)}
    if session.pop('chat_item', None) or session.pop('chat_card', None):
        session.pop('chat_card', None)
        V.save_session(store, run, session)
    lines = with_assistant + working(conn, run)
    return {'item': None, 'needed': False, 'working': lines, 'say_last': NOTHING,
            'how': 'Tell the operator the `working` lines as they are' + ('' if lines else ' (there are none: say in one line what you are doing next)') + f', then "{NOTHING}"'}


def answer(conn, store, user, run, outputs, item_id, choice, quote='', notes='', one=False):
    """The operator's answer to the item that was handed out. Any other item is refused by name."""
    ctx = _ctx(conn, store, user, run, outputs)
    items, _summary, _ = _candidates(ctx)
    current = items[0] if items else None
    handed = (ctx['session'].get('chat_item') or {}).get('id')
    V.need(current, 'Nothing waits for an answer now: run `vw visuals next`.')
    V.need(item_id == current['id'] and handed == current['id'],
           f"{item_id} is not the decision that is open. The open one is {current['id']} ({current['position']}): show it with `vw visuals next` and record the operator's answer to it. One decision at a time, in the server's order.")
    choices = current['buttons'] + list(current.get('other_choices') or [])
    button = next((b for b in choices if b['choice'] == choice), None)
    V.need(button, f"Not an answer to this item: {choice!r}. Its answers are: " + ', '.join(f"{b['choice']} ({b['label']})" for b in choices) + '.')
    words = str(notes or '').strip() or str(quote or '').strip()
    words = '' if words.lower() == button['label'].lower() else words
    V.need(not button.get('needs_words') or words, button.get('tell') or 'Ask the operator what to change, in their own words.')
    out = current['_run'](choice, str(quote or '').strip() or button['label'], words)
    session = V.session_of(store, run, outputs)
    session.pop('chat_item', None)
    V.save_session(store, run, session)
    out = out if isinstance(out, dict) else {}
    done = {k: out[k] for k in ('recorded', 'accepted', 'revise', 'for_the_assistant', 'held', 'pass', 'queued', 'errors') if k in out}
    nxt = next_item(conn, store, user, run, outputs, one)   # SK, 12 Nov 2026: record and fetch in one step, so the operator waits once per answer, not twice
    return {'answered': item_id, 'choice': choice, **done, **nxt,
            'then': (str(out['tell']) + ' ' if out.get('tell') else '')
                    + ('The next decision is in `item`: show it now; do not run `vw visuals next` for it.' if nxt.get('item')
                       else 'What comes next is a card (`card`): show it now, as `how` says.' if nxt.get('card') else 'No decision waits now: give the `working` lines and the last line.')
                    + (' The operator asked for a change: make only that change, send it again, and it returns in its turn.' if button.get('needs_words') else '')}
