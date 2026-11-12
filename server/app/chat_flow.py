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
from datetime import datetime, timezone
from fractions import Fraction
from io import BytesIO

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

def _treatment_items(ctx):
    session, draft = ctx['session'], ctx['session'].get('treatment_draft')
    if not draft:
        return [], '', []
    lines = draft.get('lines') or {}
    entries = {e['gap_id']: e for e in draft.get('gaps') or []}
    order, totals = list(lines), draft.get('totals') or {}
    summary = (f"{totals.get('gaps', len(entries))} gaps, {totals.get('images', 0)} picture(s) to make; estimate ₹{draft.get('estimate_inr', 0):g} of the ₹{V.cap_of(session):g} limit"
               + (f"; kept aside for takes made again: ₹{draft['rerun_allowance_inr']:g}" if draft.get('rerun_allowance_inr') else '')
               + (f". Warnings: {'; '.join(str(w.get('message') if isinstance(w, dict) else w) for w in (draft.get('warnings') or [])[:4])}" if draft.get('warnings') else ''))
    items = []
    for n, key in enumerate(order, 1):
        st = lines[key]
        if st['state'] != 'to_accept':
            continue
        if key == 'direction':
            head, body = 'The direction of the film', str(draft.get('direction') or '')
        else:
            e = entries.get(key) or {}
            head = f'Gap {key}'
            rows = [('The picture', e.get('picture')), ('Made as', ', '.join(ROUTE_WORDS.get(r, r) for r in e.get('routes') or [])), ('Length', f"{float(e.get('seconds') or 0):g} s"),
                    ('Pictures to make', e.get('images')), ('Shows', '; '.join(e.get('depicts') or [])),
                    ('Held still for', f"{float(e['frozen_seconds']):g} s" if e.get('frozen_seconds') else ''), ('Why', e.get('why') or e.get('reason') or '')]
            body = '\n'.join(f'{k}: {v}' for k, v in rows if v not in (None, '', []))

        def run(choice, quote, words, key=key):
            return V.treatment(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], None, quote, accept=[key] if choice == 'accept' else [],
                               send_back=[key] if choice == 'change' else [], notes=words if choice == 'change' else '')
        items.append(_item(f"treatment:{key}:{st['digest'][:10]}", 'treatment line', f'Treatment, line {n} of {len(order)}',
                           f"{head}{' (changed since you last saw it)' if st.get('changed') else ''}. Do you accept this line?", run,
                           [_button('Accept', 'accept'), _button('Change this', 'change', words=True, tell='Ask the operator what to change in this line.')], text=body))
    return items, (summary if items else ''), [k for k in order if lines[k]['state'] == 'sent_back']


def _seconds(shot, fps):
    return float(Fraction(shot['end_frame'] - shot['start_frame']) / Fraction(str(fps)))


def _gap_text(session, gap):
    fps, out = session['source'].get('fps') or 25, []
    for sc in V.chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])):
        for s in sc['shots']:
            kind = ROUTE_WORDS.get(V.route_of(s), V.route_of(s))
            out.append(f"{len(out) + 1}. {s.get('title') or s['id']} · {kind} · {_seconds(s, fps):.1f} s\n   {str(s.get('purpose') or '').strip()}"
                       + (f"\n   Over the words: \"{' '.join(str(s.get('narration') or '').split())[:300]}\"" if s.get('narration') else ''))
    return '\n'.join(out)


def _plan_items(ctx):
    session, plan = ctx['session'], ctx['plan']
    if not plan:
        return [], []
    gaps, items, revising = plan['gaps'], [], []
    for n, gap in enumerate(gaps, 1):
        gid = gap['gap_id']
        if gid in session['accepted']:
            continue
        if gid in (session.get('revisions') or {}):
            revising.append(gid)
            continue
        where = f'Plan, gap {n} of {len(gaps)}'
        title = f'Gap {gid}' + (f" · {gap['title']}" if gap.get('title') else '')
        if gap.get('choices') and not session['choice_selections'].get(gid):
            choices = gap['choices'][:4]
            text = '\n\n'.join(f"{c['title']}\n{c['description']}\nWhy: {c['why']}\nThe cost of it: {c['tradeoff']}" for c in choices)
            items.append(_item(f"choice:{gid}:{V.gap_digest(plan, gap)[:10]}", 'plan choice', where, f'{title}. Which way should this gap be made?',
                               lambda choice, quote, words, gid=gid: V.select_choice(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], {gid: choice}),
                               [_button(c['title'][:40], c['id']) for c in choices], text=text))
        else:
            def run(choice, quote, words, gid=gid):
                if choice == 'accept':
                    return V.accept(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], [gid], quote)
                return V.revise_gap(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], gid, words, quote)
            items.append(_item(f"gap:{gid}:{V.gap_digest(plan, gap)[:10]}", 'plan gap', where, f'{title}. Do you accept the shots planned for this gap?', run,
                               [_button('Accept', 'accept'), _button('Change this', 'change', words=True, tell='Ask the operator what to change in this gap.')], text=_gap_text(session, gap)))
    return items, revising


# ---------- the reference round: one element, then one set ----------

def _names(plan):
    return {e['id']: (e.get('name') or e['id']) for e in (plan or {}).get('elements') or []}


def _kinds(plan):
    return {e['id']: e.get('kind') for e in (plan or {}).get('elements') or []}


def sheet_of(store, run, rows):
    """One picture of a set, side by side, a large letter on each: stored with the run, so the chat can show it. Its key, or None when it cannot be made."""
    try:
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
        key = f"{run['id']}/visuals/chat/set-{hashlib.sha256(''.join(r['id'] + str(r.get('sha256')) for r in rows).encode()).hexdigest()[:16]}.jpg"
        store.put(key, buf.getvalue(), 'image/jpeg')
        return key
    except Exception:   # noqa: BLE001: the single pictures are shown all the same
        return None


def _round_items(ctx):
    session, plan, run = ctx['session'], ctx['plan'], ctx['run']
    rd = session.get('round')
    if not (rd and plan and rd.get('kept')):
        return []
    step, names, kinds, items = V._round_pass(session, rd), _names(plan), _kinds(plan), []
    elements = [(eid, row) for eid, row in rd['elements'].items() if eid in kinds]
    if step == 1:
        held = session.get('chat_round') or {}
        open_ = [(eid, row) for eid, row in elements if eid not in held]
        for eid, row in open_[:1]:
            n = len(elements) - len(open_) + 1
            frames = row.get('frames') or [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
            person = kinds.get(eid) == 'person'
            if frames:
                q = (f"{names[eid]}: this is how {'this person' if person else 'it'} looks in your footage. "
                     + ('Use these pictures to make the reference set?' if person else 'Use this picture from your footage as the reference?'))
                yes = 'Yes, use it'
            else:
                q, yes = f"{names[eid]}: your footage has no picture of {'this person' if person else 'it'}. Have a reference set made (paid)?", 'Yes, make one'

            def run_(choice, quote, words, eid=eid):
                s = V.session_of(ctx['store'], run, ctx['outputs'])
                s.setdefault('chat_round', {})[eid] = {'verdict': choice, 'quote': quote}
                V.save_session(ctx['store'], run, s)
                left = [e for e, _ in elements if e not in s['chat_round']]
                if left:
                    return {'stored': eid, 'left': len(left)}
                verdicts = {e: {'verdict': s['chat_round'][e]['verdict']} for e, _ in elements}
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
    todo = [(eid, row) for eid, row in elements if not row.get('ignored') and not row.get('from_footage')]
    for n, (eid, row) in enumerate(todo, 1):
        rows = sorted(V._set_rows(session, eid, row.get('set')), key=lambda r: int(r.get('set_n') or 1))
        where = f'Reference sets, {n} of {len(todo)}'
        if rows and not V._answered(session, kinds, eid, row):
            person = kinds.get(eid) == 'person'
            show = [_pic(run, r['id'], f'{eid}-{LETTERS[i]}') for i, r in enumerate(rows[:len(LETTERS)])]
            sheet = sheet_of(ctx['store'], run, rows[:len(LETTERS)])
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
                return V.round_sets(ctx['store'], ctx['user'], run, ctx['outputs'], {eid: ans}, quote, conn=ctx['conn'], partial=True)
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
            choices = [str(c) for c in (q.get('choices') or [])][:4]
            buttons = ([_button(c[:40], c) for c in choices] if len(choices) >= 2
                       else [_button('Answer in my words', 'words', words=True, tell='Ask the operator for their answer.')])
            items.append(_item(f'question:{it}', 'question', where, q['question'], lambda choice, quote, words, it=it: V.answer(store, user, run, outputs, it, words or choice), buttons,
                               show=[_pic(run, it, f'question-{it}')] if ref and ref.get('sha256') else []))
        elif kind in ('style sheet to approve', 'sheet to approve', 'picture to answer') and ref:
            what = 'The style sheet of the graphics' if kind.startswith('style') else names.get(ref.get('element_id')) or w['label']

            def run_(choice, quote, words, ref=ref):
                if choice == 'yes':
                    return V.approve_reference(store, user, run, outputs, ref['id'], ref['sha256'], quote, conn)
                return V.reject_reference(store, user, run, outputs, ref['id'], words, quote)
            items.append(_item(f"picture:{ref['id']}:{str(ref.get('sha256'))[:10]}", 'picture', where, f'{what}: is this picture right?', run_,
                               [_button('Yes', 'yes'), _button('No', 'no'), _button('Correct it', 'correct', words=True, tell='Ask the operator what to correct.')],
                               text='\n'.join(str(x) for x in (ref.get('checklist') or [])[:6]), show=[_pic(run, ref['id'], f"picture-{ref['id']}")]))
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
            items.append(_item(f'reuse:{group}', 'reuse', where, f'{title(group)}: the same picture is shown a second time here. Allow it?',
                               lambda choice, quote, words, group=group: (V.approve_reuse(store, user, run, outputs, group, quote) if choice == 'yes'
                                                                           else {'for_the_assistant': words, 'tell': 'Another picture will be planned for this shot.'}),
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
            text = '\n'.join(x for x in ([motion.finish_words(fin)] if fin else []) + lines + look if x)

            def run_(choice, quote, words, job=job, group=group):
                if choice == 'select':
                    return V.select_take(conn, store, user, run, outputs, str(job['id']), quote, words or 'selected in the chat', '', None)
                if choice == 'no-effect':
                    return {**V.motion_finish(conn, store, user, run, outputs, group, False), 'tell': 'The drawing is being made again without the effect. ' + NOTHING}
                return V.review_take(conn, store, user, run, outputs, str(job['id']), 'rejected', words, '', quote)
            drawn = job.get('provider') == 'drawn'
            show = [{'key': res['key'], 'name': f"{group}-{'drawing' if drawn else 'take'}.mp4"}] if res.get('key') else []
            sheet_key = res.get('sheet_key') or check.get('sheet_key')
            show += [{'key': sheet_key, 'name': f'{group}-frames.jpg'}] if sheet_key else []
            items.append(_item(f"take:{job['id']}", 'take', where, f"{title(group)}: is this {'drawing' if drawn else 'take'} right for the film?", run_,
                               [_button('Select', 'select'), _button('Reject', 'reject', words=True, tell='Ask the operator what is wrong with it.')] + ([_button('Take the effect away', 'no-effect')] if fin else []),
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
        open_take = any(j['status'] in ('queued', 'running', 'storage_pending') or (j['status'] == 'ready' and ((session['reviews'].get(str(j['id'])) or [{}])[-1].get('decision') != 'rejected')) for j in takes)
        if card['ready'] and not open_take and (g.get('shoot_asked') or {}).get('stamp') != stamp:
            def run_(choice, quote, words, sid=sid, stamp=stamp):
                if choice == 'shoot':
                    return {**guide.shoot(conn, store, user, run, outputs, sid, quote), 'tell': 'The take is being made. ' + NOTHING}
                s = V.session_of(store, run, outputs)
                s['guides'][sid]['shoot_asked'] = {'stamp': stamp, 'answer': 'not yet', 'words': words}
                V.save_session(store, run, s)
                return {'for_the_assistant': words}
            show = [{'key': k, 'name': n} for k, n in ((card.get('guide_key'), f'{sid}-guide.mp4'), ((card.get('still') or {}).get('overlay_key'), f'{sid}-still-on-the-guide.png')) if k]
            items.append(_item(f"shoot:{sid}:{hashlib.sha256(stamp.encode()).hexdigest()[:10]}", 'shoot', 'AI video, the take',
                               f"{title}: make the take now? It is {card['seconds']} s and costs about ₹{card['cost_inr']:g}.", run_,
                               [_button('Shoot', 'shoot'), _button('Not yet', 'wait', words=True, tell='Ask the operator what should change first.')], text=str(card.get('look_for') or ''), show=show))
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


def _candidates(ctx):
    """Every decision that waits for the operator, in the order it is asked; a summary for the treatment; and what is with the assistant meanwhile."""
    t_items, summary, back = _treatment_items(ctx)
    if t_items or back:
        return t_items, summary, ([f"Treatment: the assistant is revising {', '.join('the direction' if k == 'direction' else 'gap ' + k for k in back)}."] if back else [])
    p_items, revising = _plan_items(ctx)
    note = [f"Plan: the assistant is revising gap {', '.join(revising)}."] if revising else []
    if p_items:
        return p_items, '', note
    for step in (_round_items, _waiting_items, _guide_items, _record_items):
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


def _public(item, summary, n_waiting):
    out = {k: v for k, v in item.items() if not k.startswith('_')}
    return {**out, 'waiting_after_this': max(0, n_waiting - 1), **({'summary': summary} if summary else {}), 'needed': True, 'say_last': NEEDED,
            'how': ('The tool saved the files of `show` in the run folder: show them to the operator in this order (' + LOOK_ONLY + '). ' if item.get('show') else '')
                   + 'Post `position` and `question`' + (', then `text` as it is' if item.get('text') else '') + (', with `summary` under it' if summary else '')
                   + '. Ask with the buttons given, in this order, and no others; the operator may answer in their own words instead. '
                   f"Record the reply: `vw visuals decide --item {item['id']} --choice <the button's choice> --quote \"<their words>\"` (`--notes` for what to change). Say nothing about what you did."}


def next_item(conn, store, user, run, outputs):
    """The one decision the operator takes now, or that nothing is needed and what is being made."""
    items, summary, with_assistant = _candidates(_ctx(conn, store, user, run, outputs))
    session = V.session_of(store, run, outputs)
    if items:
        item = items[0]
        if (session.get('chat_item') or {}).get('id') != item['id']:
            session['chat_item'] = {'id': item['id'], 'at': datetime.now(timezone.utc).isoformat()}
            V.save_session(store, run, session)
        return {'item': _public(item, summary, len(items))}
    if session.pop('chat_item', None):
        V.save_session(store, run, session)
    lines = with_assistant + working(conn, run)
    return {'item': None, 'needed': False, 'working': lines, 'say_last': NOTHING,
            'how': 'Tell the operator the `working` lines as they are' + ('' if lines else ' (there are none: say in one line what you are doing next)') + f', then "{NOTHING}"'}


def answer(conn, store, user, run, outputs, item_id, choice, quote='', notes=''):
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
    done = {k: out[k] for k in ('recorded', 'accepted', 'revise', 'next', 'for_the_assistant', 'held', 'pass', 'queued', 'errors') if k in out}
    return {'answered': item_id, 'choice': choice, **done,
            'then': (str(out['tell']) + ' ' if out.get('tell') else '') + 'Run `vw visuals next` for the next decision.'
                    + (' The operator asked for a change: make only that change, send it again, and it returns in its turn.' if button.get('needs_words') else '')}
