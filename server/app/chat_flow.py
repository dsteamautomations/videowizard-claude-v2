"""design/188 (SK, 12 Nov 2026): the visuals stage in the operator chat. One decision at a time.

`next_item` hands out exactly one thing the operator must decide (where it is, the question, what to show, the buttons), or says that nothing is
needed and what is being made. `answer` records the operator's choice on that item and on no other, through the decision functions that exist
(`visuals_stage`, `guide`): the same ones the visuals page's buttons call. Nothing about what is approved changes here, only where and in what
order the operator answers.

The gate: the item handed out is kept in the session (`chat_item`); an answer naming any other item is refused by name, so the assistant cannot
choose the order, show two things at once or skip one.

The order: the treatment (one line), the plan (one gap), the reference round (one element, then one set), then everything `waiting()` lists
(an open question, a picture, a sheet, a spec, a take), an AI video shot's still and its word to shoot, then the gaps ready to record.

design/222 (SK, 19 Nov 2026): the finished AI video takes are no longer asked here one by one: they are judged on the page (`takes`), all together, once
every take is made and checked. The shot's layout drawing, the still, the word to make the first take and "send it again" stay cards here; the word for
a second take is "Make another" on the page."""
import hashlib
import json
import re
from datetime import datetime, timezone
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from . import pictures as P
from . import takes as T
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


def _mark(refs, ref_id):
    """Defect 55 (VW-24): the content's mark of a reference's picture, its sha256: the page knows a picture by its key and this mark."""
    return str((refs.get(ref_id) or {}).get('sha256') or '')


# ---------- the treatment and the plan ----------

def _changes(changes, n=10):
    """design/191: the first lines of what changed, then how many more there are."""
    changes = list(changes or [])
    return changes[:n] + ([f'and {len(changes) - n} more'] if len(changes) > n else [])


def _changed_text(changes, asked=False):
    """design/202: a line the operator sent back and the assistant rewrote says it was changed as they asked."""
    rows = _changes(changes)
    return (('**Changed as you asked:**\n' if asked else '**What changed:**\n') + '\n'.join('- ' + r for r in rows) + '\n\n') if rows else ''


DIRECTION_HELP = ('The direction says what the viewer should understand by the end, and how the film will show it. Every gap\'s line is written from it; '
                  'no gap is shown until you accept it.')


SECOND_DIRECTION_TELL = ('Write a second Direction that differs in viewpoint or approach, not in wording. Keep the first as it is in `direction_parts`; put the second in '
                         '`direction_alternative` (its six parts, `answers_brief` and `risk`); give the first its own two lines (`direction_answers_brief`, `direction_risk`); '
                         'send the draft again. The operator then sees both and takes one.')


def _direction_rows(draft, outputs):
    """design/203: the Direction as the operator reads it: from the brief its purpose, audience and tone (so a departure shows at once), then the
    six headed parts, a part not given reading 'not given'. With a second Direction beside it, both are shown, each with how it answers the brief
    and what it risks. Empty for a Direction sent as the older paragraph: that one is shown as its text."""
    parts = draft.get('direction_parts')
    if not parts:
        return []
    rows = []
    try:
        brief = next((o for o in outputs or [] if o.get('stage') == 'brief' and o.get('unit') is None), None)
        if brief:
            s = brief.get('summary') or {}
            rows = [(f'From the brief · {k}', ' '.join(str(s.get(k) or '').split()) or 'not recorded') for k in ('purpose', 'audience', 'tone')]
    except Exception:   # the brief's record cannot be read: its rows are left out; the Direction is still shown
        rows = []
    second = draft.get('direction_alternative')
    if not second:
        return rows + [(h, parts.get(k) or 'not given') for k, h, _ in V.DIRECTION_PARTS]
    notes = draft.get('direction_notes') or {}
    for name, p, lines in (('First', parts, notes), ('Second', second.get('parts') or {}, second)):
        rows += [(f'{name} · {h}', p.get(k) or 'not given') for k, h, _ in V.DIRECTION_PARTS]
        rows += [(f'{name} · {what}', lines.get(k) or 'not given') for k, what in V.SECOND_LINES]
    return rows


def _shot_rows(e, reasons_asked=True):
    """design/202: each shot of a treatment line as the operator reads it: how it is made and for how long, what the viewer sees, why the picture
    fits the words, why it is made this way. A reason that was not written reads 'not given'; on a draft saved before the reasons were asked
    (`reasons_asked` false) the row is left out. A gap of one way with no shots carries them itself."""
    shots = [s for s in e.get('shots') or [] if isinstance(s, dict)]
    why = lambda row, k: V.reason_text(row, k) or ('not given' if reasons_asked else '')
    if not shots:
        return [('Why it fits the words', why(e, 'fits_why')), ('Why this way', why(e, 'way_why'))]
    rows = []
    for n, s in enumerate(shots, 1):
        route = s.get('route') if isinstance(s.get('route'), str) else ''
        way = ROUTE_WORDS.get(route, route)
        rows += [(f'Shot {n}', ', '.join(x for x in (way, f"{float(s['seconds']):g} s" if isinstance(s.get('seconds'), (int, float)) else '') if x)),
                 (f'Shot {n} · the viewer sees', s.get('picture')), (f'Shot {n} · why it fits the words', why(s, 'fits_why')), (f'Shot {n} · why this way', why(s, 'way_why'))]
    return rows


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
               + (f"; moving {totals['moving_seconds']:g} s, still {totals['still_seconds']:g} s" if 'still_seconds' in totals else '')   # design/202
               + (f"; {len(draft['reasons_missing'])} shot(s) with a reason not given" if draft.get('reasons_missing') else '')
               + (f". Warnings: {'; '.join(str(w.get('message') if isinstance(w, dict) else w) for w in (draft.get('warnings') or [])[:4])}" if draft.get('warnings') else ''))
    items = []
    if (lines.get('direction') or {}).get('state') == 'sent_back':   # design/190: every gap line is written again from the direction; none is asked until it is back
        return [], summary, ['direction']
    for n, key in enumerate(order, 1):
        st = lines[key]
        if st['state'] != 'to_accept':
            continue
        if key == 'direction':
            head, rows = 'The direction of the film', _direction_rows(draft, ctx.get('outputs'))   # design/203: six headed rows, the brief above them
            body = DIRECTION_HELP + '\n\n' + ('\n'.join(f'- **{k}:** {v}' for k, v in rows) if rows else str(draft.get('direction') or ''))   # design/202: named, explained, in full
        else:
            e = entries.get(key) or {}
            head = f'Gap {key}'
            rows = [('The picture', e.get('picture')), ('Made as', ', '.join(ROUTE_WORDS.get(r, r) for r in e.get('routes') or [])), ('Length', f"{float(e.get('seconds') or 0):g} s"),
                    ('Pictures to make', e.get('images')), ('Shows', '; '.join(e.get('depicts') or [])),
                    ('Held still for', f"{float(e['frozen_seconds']):g} s" if e.get('frozen_seconds') else ''), ('Why', e.get('why') or e.get('reason') or ''),
                    *_shot_rows(e, 'reasons_missing' in draft)]   # design/202: each shot's two reasons; the gap's own why stays (a long graphics run gives its reason there)
            body = '\n'.join(f'- **{k}:** {v}' for k, v in rows if v not in (None, '', []))   # a list: plain line breaks run together in the chat

        def run(choice, quote, words, key=key):
            if key == 'direction' and choice == 'different':   # design/203: the same path as Change this, with fixed words
                out = V.treatment(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], None, quote, send_back=[key], different=True)
                return {**out, 'tell': SECOND_DIRECTION_TELL}
            return V.treatment(ctx['store'], ctx['user'], ctx['run'], ctx['outputs'], None, quote, accept=[key] if choice in ('accept', 'accept_second') else [],
                               send_back=[key] if choice == 'change' else [], notes=words if choice == 'change' else '', use_second=choice == 'accept_second')
        change = _button('Change this', 'change', words=True, tell='Ask the operator what to change in this line.')
        another = _button(V.DIFFERENT_DIRECTION, 'different')
        buttons = ([_button('Accept', 'accept'), change] if key != 'direction'
                   else [_button('Use the first', 'accept'), _button('Use the second', 'accept_second'), change, another] if draft.get('direction_alternative')
                   else [_button('Accept', 'accept'), change, another])
        items.append(_item(f"treatment:{key}:{st['digest'][:10]}", 'treatment line', f'Treatment, line {n} of {len(order)}',
                           f"{head}{' (changed as you asked)' if st.get('asked') else ' (changed since you last saw it)' if st.get('changed') else ''}. "
                           + ('Do you accept the direction of the film?' if key == 'direction' else 'Do you accept this line?'), run,   # design/202: the Direction is asked by its name
                           buttons, text=_changed_text(st.get('changes'), bool(st.get('asked'))) + body))
        items[-1].update(_key=key, _summary=summary, _card={'n': head, 'c': 1 if st.get('changed') else 0, **({'a': 1} if st.get('asked') else {}), **({'ch': _changes(st['changes'])} if st.get('changes') else {}),
                                          **({'t': body} if not rows else {'r': [[k, str(v)] for k, v in rows if v not in (None, '', [])]})})
    return items, summary, [k for k in order if lines[k]['state'] == 'sent_back']


def _seconds(shot, fps):
    return float(Fraction(shot['end_frame'] - shot['start_frame']) / Fraction(str(fps)))


GAP_COLS = ['#', 'Shot', 'Made as', 'Length', 'What it shows', 'Over the words']


def _gap_rows(session, gap, selection=None):
    """A gap's shots as rows of GAP_COLS, and its totals line: the same for the chat's table, the card and the page. `selection` names one
    offered way (design/206: the page shows the shots of each way before one is taken)."""
    fps, rows, total = session['source'].get('fps') or 25, [], 0.0
    cell = lambda v: ' '.join(str(v or '').split()).replace('|', '/')   # one line, no column break
    for sc in V.chosen_scenes(gap, selection or session['choice_selections'].get(gap['gap_id'])):
        for s in sc['shots']:
            kind = ROUTE_WORDS.get(V.route_of(s), V.route_of(s))
            rows.append([str(len(rows) + 1), cell(s.get('title') or s['id']), kind, f'{_seconds(s, fps):.1f} s', cell(s.get('purpose')), cell(s.get('narration'))[:220]])
            total += _seconds(s, fps)
    return rows, f'{len(rows)} shots, {total:.1f} s in all.'


def _world_rows(plan, n=400):
    """design/207 (SK, 16 Nov 2026): the world of the film as [label, text] rows, read only, the same for the page and the chat: the look, each
    rule of the world, what is not shown, each specification, the graphic style, then each person, place, thing and material with its
    description and known sizes. The Direction is left out (accepted at the treatment); so is a graphic (it is a shot's drawing). A long cell
    is cut at `n` characters. A plan with nothing written about the world gives no rows."""
    f = (plan or {}).get('foundation') or {}
    style = f.get('graphic_style') or {}
    rows = ([['The look', f.get('appearance')]]
            + [[label, r.get('statement')] for label, k in (('The world', 'world'), ('Not shown', 'exclusions'), ('Specification', 'specifications')) for r in f.get(k) or []]
            + [['The graphic style', '; '.join(f"{k.replace('_', ' ')}: {v}" for k, v in ((k, style.get(k)) for k in ('palette', 'line_weight', 'labels', 'background', 'frame_fill')) if v)]])
    rows = [r for r in rows if r[1]]
    if not rows:
        return []
    for e in plan.get('elements') or []:
        if e.get('kind') == 'graphic':
            continue
        name = e.get('name') or e.get('id')
        sizes = V.size_sentence({'name': name, 'size': (e.get('size') or []) + ((e.get('material_spec') or {}).get('dimensions') or [])})
        text = ' '.join(str(e.get('description') or e.get('requirements') or '').split()).rstrip('.')
        rows.append([f"{str(e.get('kind') or 'thing').capitalize()} · {name}", '. '.join(x for x in (text, 'Known sizes: ' + sizes[len(str(name)) + 2:] if sizes else '') if x)])
    return [[label, V._short_text(text, n)] for label, text in rows]


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
                               text=_changed_text(changes) + ''.join(f'**Read before you answer:** {w}\n\n' for w in V.warning_lines(session, gap, plan)) + _gap_text(session, gap)))   # design/207: the plain lines, in the chat too
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
    return {e: v for e, v in (held or {}).items() if isinstance(v, dict) and e in stamps and v.get('frames') == stamps[e] and not v.get('confirm')}   # design/212 review: an answer that waits for a look at a new picture is not an answer yet


def _round1(session, plan):
    """Step 1 of the round: every row of it, the rows of the things the plan names (what the operator is asked about), each thing's footage
    pictures, their stamps, and the answers kept so far that still stand."""
    kinds = _kinds(plan)
    everything = list(session['round']['elements'].items())
    elements = [(eid, row) for eid, row in everything if eid in kinds]
    frames_of = {eid: row.get('frames') or [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
                 for eid, row in elements}
    if V.round_v2(session):   # design/211: the looked frames that stand, in view order (a frame the operator marked "not this picture" is out)
        from . import ref_find
        frames_of = {eid: [f['ref'] for f in ref_find.frames_of(session, eid)] for eid, _ in elements}
    stamps = {eid: ','.join(map(str, f)) for eid, f in frames_of.items()}
    return everything, elements, frames_of, stamps, _round_kept(session.get('chat_round'), stamps)   # design/191 section 11, B4: kept through a round posted again, while that thing's footage pictures are the same


def round_close(conn, store, user, run, outputs, quote):
    """Step 1 recorded, once, when every thing of the round has its answer: the server records the first step for every element of the round at
    once (one the plan no longer names is left out) and the sets are queued. None while a thing is unanswered, or when the round is not at
    step 1: nothing is recorded. design/210: a thing answered with the operator's own picture (the page) takes that picture as its reference:
    its footage pictures are set aside first, and put back if the server refuses the step."""
    s = V.session_of(store, run, outputs)
    rd = s.get('round')
    if not (rd and rd.get('kept') and rd.get('pass') == 1 and s.get('current')):
        return None
    plan = V.current_plan(store, s)
    everything, elements, frames_of, _stamps, held = _round1(s, plan)
    if V.round_v2(s):   # design/212: a person the footage does not show is answered here, not by the operator
        held = _auto_held(store, run, s, plan, elements, _stamps, held)
    if not elements or any(e not in held for e, _ in elements):
        return None
    kinds = _kinds(plan)
    owns = {e: held[e]['own'] for e, _ in elements if held[e].get('own') and kinds.get(e) != 'person' and held[e]['verdict'] == 'approve'}
    aside = [f for e in owns for f in frames_of[e] if (s['references'].get(f) or {}).get('status') == 'candidate']
    # design/212 review: a footage picture left unticked is not used: set aside here, at "done", with no search for another (never "not this picture")
    unticked = [f for e, _ in elements if e not in owns and held[e].get('verdict') in ('approve', 'clean') for f in frames_of[e]
                if (held[e].get('pics') or {}).get(f) == 'off' and (s['references'].get(f) or {}).get('status') == 'candidate'] if V.round_v2(s) else []
    for f in aside + unticked:
        s['references'][f].update(status='rejected', rejection={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'quote': quote,
                                                                'notes': WORDS['aside'] if f in unticked else "the operator's own picture is used instead"})
    aside = aside + unticked
    if aside:
        V.save_session(store, run, s)
    verdicts = {e: {'verdict': held[e]['verdict'] if e in held else 'ignore'} for e, _ in everything}
    if V.round_v2(s):   # design/211: the operator's words of step 1 go into the request of the set
        verdicts = {e: {**v, 'words': str((held.get(e) or {}).get('words') or '')} for e, v in verdicts.items()}
    try:
        out = V.round_done(store, user, run, outputs, verdicts, quote, conn=conn)
    except (ValueError, V.Problem):
        s = V.session_of(store, run, outputs)
        for f in aside:
            s['references'][f]['status'] = 'candidate'
            s['references'][f].pop('rejection', None)
        if aside:
            V.save_session(store, run, s)
        raise
    s = V.session_of(store, run, outputs)
    s.pop('chat_round', None)
    for e, mine in owns.items():
        if s['round']['elements'][e].get('from_footage'):
            s.setdefault('golden', {})[e] = mine   # the picture the operator gave on this line, not an older one of theirs
    V.save_session(store, run, s)
    if out.get('then'):   # design/211: a v2 round says what comes next in the server's own sentence
        return {**out, 'tell': str(out['then'])}
    return {**out, 'tell': (f"{len(out.get('queued') or [])} reference set(s) are now being made, about ₹{out.get('cost_inr', 0):g}. " if out.get('queued') else '') + NOTHING}


def _round_items(ctx, every=False):
    """The reference round's questions. The chat asks one at a time and leaves out what is answered or waits on something else. `every`
    (design/210, the page): every thing of step 1, the answered ones too, each answer only kept (the page closes the step once, after the last
    answer of a visit: `round_close`); at step 2 every set that is back, an answered one too, and every set that was not made, one a cause
    holds too. An item then says what the page shows beside it: `_eid`, `_person`, `_frames`, `_makes` (a paid set follows a yes), `_kept`
    (the answer kept so far), `_rows` (a set's pictures), `_cause`."""
    session, plan, run = ctx['session'], ctx['plan'], ctx['run']
    rd = session.get('round')
    if not (rd and plan and rd.get('kept')):
        return []
    step, names, kinds, items = V._round_pass(session, rd), _names(plan), _kinds(plan), []
    if V.round_v2(session):   # design/211: a round made after the references step was rebuilt; an older round runs the code below, unchanged
        return _round_v2(ctx, every, step)
    elements = [(eid, row) for eid, row in rd['elements'].items() if eid in kinds]   # what the operator is asked about: the things the plan names
    if step == 1:
        _everything, elements, frames_of, stamps, held = _round1(session, plan)
        open_ = [(eid, row) for eid, row in elements if eid not in held]
        for eid, row in (elements if every else open_[:1]):
            n = (elements.index((eid, row)) if every else len(elements) - len(open_)) + 1
            frames = frames_of[eid]
            person = kinds.get(eid) == 'person'
            mine = not frames and not person and bool(V._own_pictures(session, eid))   # the operator's own approved picture is its reference, as a footage picture is
            makes = person or (session.get('drawings') or {}).get(eid, {}).get('status') == 'approved' or not (frames or mine)   # as `visuals_stage._from_footage` decides
            if frames:
                q = (f"{names[eid]}: this is how {'this person' if person else 'it'} looks in your footage. "
                     + ('Use these pictures to make the reference set?' if person else 'Use this picture from your footage as the reference?'))
                yes = 'Yes, use it'
            elif mine:
                q, yes = f"{names[eid]}: your own picture is its reference. Use it?", 'Yes, use it'
            else:
                q, yes = f"{names[eid]}: your footage has no picture of {'this person' if person else 'it'}. Have a reference set made (paid)?", 'Yes, make one'

            def run_(choice, quote, words, eid=eid, own=None):
                s = V.session_of(ctx['store'], run, ctx['outputs'])
                got = {**held, eid: {'verdict': choice, 'quote': quote, 'frames': stamps[eid], **({'own': own} if own else {})}}
                s['chat_round'] = got
                V.save_session(ctx['store'], run, s)
                out = None if every else round_close(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], quote)
                return out if out is not None else {'stored': eid, 'left': len([e for e, _ in elements if e not in got])}
            items.append(_item(f'round1:{eid}', 'reference', f'References, {n} of {len(elements)}', q, run_,
                               [_button(yes, 'approve'), _button(WORDS['leave'], 'ignore')], show=[_pic(run, f, f'{eid}-footage-{i + 1}') for i, f in enumerate(frames[:4])]))
            items[-1].update(_eid=eid, _person=person, _frames=frames, _makes=makes, _kept=held.get(eid))
        return items
    if step not in (2, 'making'):
        return []
    budget = V._set_budget(run, session, V.visuals_spend(ctx['conn'], run))
    todo = [(eid, row) for eid, row in elements if eid in kinds and not row.get('ignored') and not row.get('from_footage')]
    for n, (eid, row) in enumerate(todo, 1):
        rows = sorted(V._set_rows(session, eid, row.get('set')), key=lambda r: int(r.get('set_n') or 1))
        where = f'Reference sets, {n} of {len(todo)}'
        person = kinds.get(eid) == 'person'
        if rows and (every or not V._answered(session, kinds, eid, row)):
            show = [_pic(run, r['id'], f'{eid}-{LETTERS[i]}') for i, r in enumerate(rows[:len(LETTERS)])]
            sheet = sheet_of(ctx['store'], run, rows[:len(LETTERS)]) if not items and not every else None   # the page shows each picture alone
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
            items[-1].update(_eid=eid, _person=person, _rows=rows[:len(LETTERS)], _kept=V._answered(session, kinds, eid, row))
        elif not rows and not V._set_rows(session, eid, row.get('set'), ('generating', 'approved')):
            cause = V.set_cause(session, plan, eid, budget)
            if cause and not every:
                continue   # something stands in its way (a spec to approve first, the spend limit): that comes in its own turn
            refused = V._set_state(session, plan, step, eid, row, budget).get('next')   # design/207 (D1): the picture service refused this person's photo
            if refused:
                def run_(choice, quote, words, eid=eid, refused=refused):
                    if choice == 'photo':
                        return {'for_the_assistant': refused, 'tell': 'Ask the operator for another photo of this person.'}
                    V.likeness(ctx['store'], ctx['user'], run, ctx['outputs'], eid, words or quote, conn=ctx['conn'], stand_in=True)
                    return {**V.set_make(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], eid), 'tell': 'This person is a stand-in now: the set is being made from the description. ' + NOTHING}
                items.append(_item(f'likeness:{eid}:{row.get("set")}', 'reference set to make', where, f"{names[eid]}: the picture service refused this person's photo. Give another photo, or make them a stand-in (made from the description, paid)?", run_,
                                   [_button('Another photo', 'photo'), _button('A stand-in', 'standin', words=True, tell='Ask the operator to say in their own words that this person is a stand-in now.')]))
                items[-1].update(_eid=eid, _person=person)
                continue

            def run_(choice, quote, words, eid=eid):
                if choice == 'make':
                    return {**V.set_make(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], eid), 'tell': 'The set is being made. ' + NOTHING}
                return V.set_aside(ctx['store'], ctx['user'], run, ctx['outputs'], eid, words or quote)
            items.append(_item(f'setmake:{eid}', 'reference set to make', where, f'{names[eid]}: its reference set was not made. Make it now (paid)?', run_,
                               [_button('Make it', 'make'), _button(WORDS['leave_failed'], 'aside')]))   # design/216 (B6): was "Leave it out"
            items[-1].update(_eid=eid, _person=person, _cause=(cause or {}).get('text'), _error=row.get('error'))
    return items


# ---------- design/211 part C (17 Nov 2026): the reference round of a v2 round ----------
# One builder, two front ends: each item carries `_line`, the fields the page draws (design/211 section 3.10); the chat says the same
# sentences as text (`_told`). Every sentence the operator reads is in WORDS. The facts come from parts A and B (`ref_find`, `ref_sets`).

ACCEPT_NONE = 'No routine thing is left to accept: answer the open lines one by one.'
PIC_UNKNOWN = '{pic} is not a picture on this line: nothing was marked. Open the page again and mark the picture there.'
GROUP_SETS_DOUBT = 'Doubtful: look at these first'   # design/213: no longer said; the four groups below are
# design/213 (17 Nov 2026): the four groups of step 2, in the order both front ends show them
STEP2_GROUPS = ['To judge', 'Could not be made', 'Waiting to be made', 'Settled']
# design/212 (SK, 17 Nov 2026): the five groups of step 1, in the order both front ends show them. They replace "Doubtful: answer these yourself"
# and the groups by kind for a v2 round at step 1 (step 2 keeps its groups).
STEP1_GROUPS = ['Routine: accept together', 'With footage pictures', 'No picture: a set is suggested', 'No picture: no reference suggested', 'No action needed']
GROUPS = {'person': 'People', 'object': 'Things', 'material': 'Materials', 'place': 'Places', 'technique': 'Ways of working', 'process': 'Ways of working'}
GROUP_ORDER = ['People', 'Things', 'Materials', 'Places', 'Ways of working']
SIZE_WORDS = {'ECU': 'an extreme close-up', 'CU': 'a close-up', 'MCU': 'a medium close-up', 'MS': 'a medium shot', 'MWS': 'a medium wide shot', 'WS': 'a wide shot',
              'EWS': 'an extreme wide shot'}
REC_DOES = {'footage': 'footage', 'clean': 'set', 'set': 'set', 'no_set': 'none', 'leave': 'none'}   # what a proposal does: the button accepted for it must do the same
WORDS = {
    # design/212 (SK, 17 Nov 2026): no cost is named at the references, on the page or in the chat; the server keeps the limit and records the spend
    # a thing: where the film uses it, what the footage has
    'used': 'Used in {shots}; the closest is {size} ({where}).',
    'shot': 'shot {n} of gap {gap}',   # design/212: the gap by its number in the film's order, as the plan's page lists them; never its code name
    'shot_unnumbered': 'a shot of gap {gap}',
    'used_short': 'Used in {shots} · closest: {size}',
    'used_short_none': 'In no shot',
    'no_shot': 'No shot of the plan names it.',
    'found': 'From your footage: {pictures}.',
    'nothing_close': 'Nothing close was seen.',
    'not_in': 'Not in your footage.',   # design/212: short; the reason is behind "why"
    'not_in_closest': 'Not in your footage. The closest picture is shown.',
    'searched': 'Searched: {clips}{names}.',
    'auto': 'Not in your footage. A set will be made from the description when you say done in the chat. No answer is needed; you may add words or your own photo.',
    'auto_kept': 'A set will be made',
    'auto_people': '{people} not in your footage {get} a set from the description without being asked: {names}.',
    'no_analysis': 'Not searched for any thing, because they have no analysis: {names}.',
    'own_is': 'Your own picture is its reference.',
    'closest_label': 'The closest: {view}',
    # step 1: the answers
    'set': 'Make a set',   # design/212: one word, "set", for every kind of thing, people included
    # design/215: the answer that was "Leave out" does three jobs, so it has three labels; each comes with the line naming the shots made without a reference
    'leave': 'No reference needed',                # step 1, and a thing that is back with the operator
    'leave_failed': 'Go on without a reference',   # step 2: a set that could not be made, or was made the most times
    'fix_all': 'Correct every picture of it',      # design/215 (change 5): the chat's own button for the page's tick
    'all_tick': 'This applies to every picture of this thing',
    'say_fix_all': 'Make it again with your words: "{words}". They are kept for every later picture of this thing. Claude rewrites the request first; the new set comes back to you.',
    'corrections': "The operator's corrections: {words}",
    # design/215 (change 3): what the picture model searched, each state in its own words
    'web_yes': 'The picture model searched the web: {n}.',
    'web_yes_bare': 'The picture model searched the web. It gave no list of pages.',
    'web_no': 'The picture model did not search the web.',
    'web_no_footage': "The picture model did not search the web. It was asked to search only for what the film's picture does not show.",
    'web_not_asked': "No search was asked: a person's set is made from the description and the film's own pictures.",
    'web_unknown': 'Searched: not known.',
    'fix1': 'Make a set with words',            # step 1 (W1): it makes a new set with the operator's words; it corrects no picture
    'go_set': 'Make a set with these words',       # the button of the words box
    'go_fix': 'Make it again with these words',
    'set_hint': 'Picture not good? Make a set instead.',   # beside "Make a set", only where a footage picture exists and may be used as it is
    # design/220 (SK, 19 Nov 2026): the check decides whether the others follow; before: 'Up to {m} sets are made first, to check the method; after you judge them, any others are made in one go.'
    'goes': ' Up to {m} sets are made and checked first; when the check passes them all, the others are made at once, and when it does not, you see that set first and the others wait for your word. '
            'A set you ask to change is made again, at most {x} times.',
    # design/212: the buttons of step 1, short and plain; which of them a thing gets follows its case
    'approve': 'Approve',
    'fix': 'Minor corrections',
    'add_words': 'Add words for the picture',
    'upload': 'Upload my own',
    'tag_use': 'Use footage',
    'tick_use': 'Tick at least one picture first.',
    'tick_closest': 'Tick the picture first, if that is it.',
    'tick_set': 'Tick at least one picture first: the set is made from it.',
    'fix_words': 'Write what should change first.',
    'fix_tell': 'Ask the operator what should change, in their own words.',
    'no_answer': 'This thing cannot be answered that way now: choose one of its buttons.',
    'made_note': 'Nothing is made until you say done in the chat.',
    'came': 'A new picture was found for this thing. Look at it, then confirm or change your answer.',
    'kept_pictures': 'from the {n} ticked picture{s}',
    'kept_words': 'from the description; the footage pictures are not used',
    'aside': 'not ticked by the operator: not used',
    'help': 'Choose a thing in the list. Tick the pictures to keep, then choose an answer under them; you can undo it. Nothing is made until you say done in the chat. '
            'A set is three pictures of one thing, which become its reference; for a person, their three views; a place gets one picture. '
            'Up to 3 sets are made and checked first; when the check passes them all, the others are made at once, and when it does not, you see that set first and the others wait for your word. '
            'A set you ask to change is made again, at most 3 times.',
    'not_this': 'Not this picture',
    'that_is_it': 'That is it',
    'ask_footage': 'Use the footage picture as the reference?',
    'ask_footages': 'Use the footage pictures as the reference?',
    'ask_mine': 'Use your own picture as the reference?',
    'ask_set': 'Make a set?',
    'ask_person': 'Make a set of this person?',
    'hint': 'Words for the picture (optional): what it must show. They go into the request when a set is made; with any other answer they are not used.',
    'cost': 'These shots are then made with no reference of it: {ids}.',
    'cost_none': 'No made shot uses it: nothing is lost.',
    'warn_person': 'This is a real, named person and no photo of them is recorded: the set is made from the description alone.',
    'warn_exact': 'This is one exact, real thing: a made picture must match it.',
    'warn_cause': 'A set cannot be made now: {cause}.',
    'warn_stale': 'The plan changed since the footage was searched for it.',
    'proposes': 'Claude suggests: {label}. {reason}',
    'read_first': 'Read before you answer: {warning}',
    # step 1: "Accept the proposals"
    'all_title': "Claude's proposals",
    'all_ask': 'Accept the proposals for the routine things?',
    'all_head': "Accept Claude's proposals for the {n} routine things",
    'all_show': 'Show the {n}',
    'all_text': '{n} have a proposal from Claude. Accepting the {r} routine ones asks for {s}, takes the footage pictures of {f} as they are, and makes no reference for {l}.{goes} '
                'A thing you answer yourself keeps your answer.',
    'accept': 'Accept all {n}',
    'each': 'Ask me each one',
    # step 2: the sets
    'rest_title': 'The other sets',
    'rest_ask': 'Make the other sets now?',
    'rest_text': 'These are the first {k}. {r} not ordered yet: {names}. Look at these first: a fault here would repeat in all of them.',
    'rest_make': 'Make the other {sets}',
    'rest_out': 'Do not make {them}',
    'rest_out_make': 'Do not make {them}; make the other {m}',
    'rest_people': '{names}: a person shown in a made picture always gets a set, so this does not cover {them}.',
    'rest_cost': 'Without {them}, these shots are made with no reference: {things}.',
    'rest_cost_none': 'Without {them}, no made shot loses a reference.',
    'earlier': 'The set before is shown too: {labels}.',
    'made_max_unmade': 'Its set was made {n} times, which is the most: add your own picture, or go on without a reference.',
    'ask_person_set': 'Is this set right for this person?',
    'ask_thing_set': 'Which picture is the reference?',
    'ask_one_set': 'Is this picture right as the reference?',
    'set_made_max': 'This set was made {n} times, which is the most: use it, or add your own picture.',
    'set_made_max_one': 'This picture was made {n} times, which is the most: use it, add your own, or go on without a reference.',
    'set_made_max_thing': 'This set was made {n} times, which is the most: use one of these pictures, add your own, or go on without a reference.',
    'set_changed': 'The plan changed since this set was made.',
    'remake': 'Make it again from the changed plan',
    'rec_use': 'Use this set',
    'rec_use_one': 'Use this picture',
    'rec_remake': 'Make it again',
    'rec_doubt': 'Look closely',
    'tag_rec_use': 'Use it',
    'tag_rec_remake': 'Make again',
    'tag_rec_doubt': 'Look closely',
    'from_footage': 'From your footage: {view}',
    'drawing': 'Drawing',
    'photo': 'Their photo',
    'picture': '{letter} · {view}',
    'before': 'Before: {letter}',
    'check_by': "Claude's check",   # design/214: the check of a set is Claude's look, line by line; no model checks a set of a v2 round
    'check_line': '{pic}: {seen}',
    'check_off': '{pic} was not checked',
    'check_size': '{pic} is not the size asked for.',
    'check_parent': '{pic} was made from a picture that is not approved.',
    'pic_n': 'Picture {letter}',
    'pic_one': 'The picture',
    'chip_fail': "Claude's check found {faults}",
    'chip_pass': "Claude's check passed",
    'chip_none': "Claude's check: not checked",
    'by_fail': "Claude's check found:",
    'by_pass': "Claude's check passed: no fault found.",
    'by_none': "Claude's check: not checked.",
    'model_chose': 'The image model chose: {words}',
    'model_aside': 'It set aside: {words}',
    'partial': '{made} of {asked} pictures came back; missing: {missing}.',
    'asked': 'Made again as you asked: "{words}"',
    'not_made': 'Its reference set was not made.',
    'not_made_cause': 'Its reference set was not made: {cause}. It can be made when that is settled.',
    'ask_make': 'Make it now?',
    'ask_standin': 'Give another photo, or make them a stand-in (made from the description)?',
    'make': 'Make it',
    'reopen_new': 'It is new in the plan, so it is back with you. Nothing was made.',
    'reopen_left': 'You said it needs no reference and asked for it again, so it is back with you. Nothing was made.',
    'reopen_changed': 'You said it needs no reference; its entry in the plan changed since, so it is back with you. Nothing was made.',
    # step 2: the lines with nothing to answer (the page)
    'making': 'Its set is being made.',
    'looking': 'Claude is looking at it.',
    'rewriting': 'The assistant is writing its request again from your words.',
    'waiting': 'Not ordered yet: it is offered when the first sets are judged.',
    'tag_looking': 'Claude is looking',
    'tag_rewriting': 'Being rewritten',
    'tag_waiting': 'Waiting',
    # design/213 (17 Nov 2026): the sets screen in the new layout; the chat says the same words and offers the same answers
    'again_set': 'Make again',
    'again_ask': 'Make this set again? Claude rewrites the request from what the checks found.',
    'approve_pic': 'Approve {letter}',
    'pick': 'Choose the picture that is the reference first.',
    'rule_person': 'For a person, picture A is the reference and the face goes with it',
    'made_twice': 'made twice',
    'made_n': 'made {n} times',
    'added': 'Claude added for the picture: {words}',
    'say_yes': 'Approve: this set is right. Picture A is the reference and the face goes with it.',
    'say_use': 'Approve: picture {letter} is the reference; pictures of this thing start from it.',
    'say_use_one': 'Approve: this picture is the reference; pictures of this thing start from it.',
    'say_fix': 'Make it again with your words: "{words}". Claude rewrites the request first; the new set comes back to you.',
    'say_again': 'Make it again. Claude rewrites the request from what the checks found. The new set comes back to you.',
    'say_remake': 'Make it again from the changed plan. The new set comes back to you.',
    'say_leave': '{label}. {shots} will be made with no reference of it.',
    'say_leave_none': '{label}. No made shot loses it.',
    'say_make': 'Make it. The set comes back to you to judge.',
    'say_set': 'Make a set. It comes back to you to judge.',
    'say_words': 'Make a set, with your words: "{words}". It comes back to you to judge.',
    'say_photo': 'Another photo: give it to the assistant in the chat.',
    'say_standin': 'A stand-in: the set is made from the description. Your words: "{words}".',
    'say_own': 'My own picture: it becomes the reference; pictures of this thing start from it.',
    'say_own_person': 'My own photo: the set is made from it.',
    'own_set': 'When none of these is right, add your own picture, {file}: it becomes the reference, and pictures of this thing start from it.',
    'loss': 'These {shots} are then made with no reference of it:',
    'loss_one': 'This 1 shot is then made with no reference of it:',
    'not_made_head': 'This set could not be made.',
    'not_made_wait': 'It can be made when this is settled: {cause}.',
    'photo_refused': "The picture service refused this person's photo.",
    'standin_hint': 'Say in your own words that this person is a stand-in now.',
    'words_hint': 'What must the picture show?',
    'rest_head': '{sets} for your word',
    'rest_why': 'Judge the first sets first: a fault here would repeat in all of them.',
    # design/220: why the others were not made by themselves, said on the line of the other sets
    'rest_held_fault': "Claude's check did not pass {names}: look at {it} first. A fault here would repeat in the others, so they wait for your word.",
    'rest_held_unmade': '{names} could not be made, so the others wait for your word.',
    'rest_held_unchecked': '{names} could not be checked, so the others wait for your word.',
    'rest_show': 'Show the {n}',
    'rest_list': 'The {sets} waiting to be made',
    'rest_list_note': 'None of these is made yet. They are made together, in one go, when you choose to make them.',   # design/216: no button is named here (A12)
    'rest_say': 'The other {sets} will be made.',
    'rest_out_say': '{made} will be made. {out} not made.',
    'rest_out_say_none': '{out} not made. No other set waits.',
    'loss_head': 'Without {them}',
    'loss_intro': 'These shots are then made with no reference of the thing named. Nothing changes until you choose it below.',
    'loss_cols': ['Not made', 'Shots', 'Which shots lose it'],
    'loss_people': '{people} always {get} a set: {names}. Not making the others also has {their} made, on the same word, when you say done in the chat.',
    'rest_first': 'Judge the first sets first: a fault here would repeat in all of them. Nothing was changed and nothing was made.',
    'wait_person': 'A person: always gets a set.',
    'wait_loss': 'If not made, {shots} would have no reference of it.',
    'wait_none': 'Made with the others.',
    'wait_head': 'Not made yet. It is made with the other sets when you choose to make them.',
    'tag_making': 'Being made',
    'tag_not_made': 'Not made',
    'tag_back': 'Back with you',
    'tag_settled': 'Settled',
    'settled_footage': 'Settled at the step before: its footage pictures are the reference. Nothing to do here.',
    'settled': 'Settled: its reference is recorded. Nothing to do here.',
    'help_set': 'A set is the pictures made of one person or thing: up to three. The one you approve becomes its reference: pictures of this thing start from it.',
    'help_rest': 'Judge the first sets, then say whether the others are made. The settled ones need no answer. Only what you do here counts: nothing is chosen for you.',
    # design/216 (SK, 18 Nov 2026): the sets screen as on the trial SK corrected. One answer for the whole set; the words that count the set's pictures are the server's
    'approve_all': 'Approve all {n}',
    'again_all': 'Make all {n} again',
    'say_all': 'All {n} pictures approved as one set. Later pictures start from picture {letter}.',
    'answer_all': 'Your answer for the whole set (pictures {letters})',
    'answer_one': 'Your answer',
    'answer_all_note': 'One answer covers all {n} pictures. You do not answer them one by one.',
    'answer_one_note': 'This one picture is the reference.',
    'strip_all': 'The set: {n} pictures, answered together',
    'strip_one': 'The picture that was made',
    'sure_ask': "Claude's check found {faults} in this set. Approve it all the same?",
    'sure_ask_none': 'Claude recommends making this set again. Approve it all the same?',
    'sure_copy': 'Every later picture of it would copy this.',
    'sure_go': 'Approve the set all the same',
    'sure_back': 'Go back',
    'rec_head': 'Claude recommends: {label}',
    'set_cap': 'The set: {pic}',
    'check_of': "Claude's check of {pic}:",
    'no_fault': 'no fault found.',
    'not_checked_pic': 'Claude could not check this picture.',
    'main_link': 'Make {letter} the main picture',
    'cmp_cap': 'Your footage, to compare: {view}',
    'own_instead': 'Use my own picture instead',
    'rest_name': 'The other {sets}',
    'rest_some': 'Make only some of them',
    'place_waits': 'It will be made{again} after the {sets} of {names} {are} approved, so that it shows the real {what}.',   # design/216 (the critic's point 2): before, "answer that first"
    'held': 'Waits for {names}: it is made when their sets are approved.',
    'tag_held': 'Waits',
    'things_due_line': "Waits for Claude to name the film's things shown in this place; then it is made.",   # design/216b
    'things_head': "The film's things shown in this place",
    'things_none': 'none',
    'rest_now': '{sets} {are} made now.',
    'rest_held': '{places} {wait} for {names}: made when their sets are approved.',
    # design/216 (B1, B2): what the assistant posts with the page's link, and before the pictures are prepared; it adds nothing to them
    'say_page': 'Open this page, answer each line, then tell me you are done:',
    'say_need': '{things} your answer:',
    'say_rest': 'Then choose whether the other {sets} are made.',
    'say_rest_only': 'Choose whether the other {sets} are made.',
    'say_done': 'Then say done here.',
    'say_nothing': 'Nothing needs your answer on this page now.',
    'preparing': 'Preparing {pictures} for the page, about {minutes}.',
    # fix set (SK, 20 Nov 2026): what the page itself says while its pictures are sent, and when the load is late (`page_flow.late_after`)
    'loading': 'The pictures of this step are being loaded: {lines}, about {minutes}. This page fills itself: there is no need to reload it.',
    'loading_late': 'This is taking longer than expected. Nothing is lost and the page still fills itself: wait a little longer, or ask the assistant once its turn in the chat has ended.',
    # design/213: a person the footage shows (step 1): the permission is asked, nothing else
    'likeness_ask': 'Your footage shows this person. Do you have their permission to make pictures of them?',
    'likeness_ask_child': 'Your footage shows this person, a child. Do you have the permission of a parent or guardian to make pictures of them?',
    'permit': 'I have their permission',
    'permit_hint': 'Write in your own words that you have the permission.',
    'permit_words': 'Write in your own words that you have the permission first.',
    'standin': 'Make a stand-in',
    'say_permit': 'I have their permission: "{words}". The set is made from the {pictures} of this person.',
    'say_standin1': 'Make a stand-in: the set is made from the description. The made person will differ from the person in your clips.',
    'g_back': 'Back with you',
    'g_not_made': 'Not made',
    'g_wait': 'Not ready yet',
    'g_done': 'Recorded',
}
# design/216: the words of the sets screen itself (its list, its bottom bar, its end card), sent with the layout (`page_flow.page_words`); the page holds none
SETS_PAGE = {
    'todo': 'Needs your answer', 'settled': 'Settled earlier, nothing to do', 'busy': 'Being made or looked at, nothing to answer yet', 'suggested': 'Suggested', 'against': 'Against advice', 'against_say': "This goes against Claude's advice.",
    'done': {'approve': 'Approved', 'fix': 'Made again, your words', 'again': 'Made again', 'remake': 'Made again', 'own': 'Your picture', 'make': 'Will be made',
             'set': 'Will be made', 'leave': 'No reference', 'rest': 'Will be made', 'rest_out': 'Some not made', 'photo': 'Another photo', 'standin': 'A stand-in'},
    'more': 'more', 'main': 'Main picture', 'compare': 'Compare with your footage', 'stop': 'Stop comparing', 'footage_head': 'Your footage: click one to see it beside the set',
    'answer': 'Your answer: ', 'kept': 'Kept from before: ', 'undo': 'Undo', 'cancel': 'Cancel', 'details': 'Details', 'fix_ask': 'What should change?', 'fix_need': WORDS['fix_words'],
    'again_go': 'Make the set again', 'no_large': 'The large picture is not available.', 'loading': 'Loading…', 'missing': 'Not available',
    'gate_wait': 'The buttons work when every picture has shown.', 'gate_bad': 'A picture is missing: {pics}. This set cannot be answered here: tell the assistant in the chat.',
    'left_one': '1 answer still needed', 'left_many': '{n} answers still needed', 'left_note': 'Choose one from the list on the left.',
    'end_head': 'All answered', 'end_note': 'Go back to the chat and say done. This is what will happen then:', 'end_foot': 'Nothing is recorded or made before you say done.',
    'foot': '{n} of {m} answered.', 'foot_wait': 'When all are answered, say done in the chat. Nothing is made before that.', 'foot_done': 'Go back to the chat and say done.',
    'help': 'How this works', 'keys': 'Keys: the left and right arrows move between the things that need an answer. Escape closes what is open.', 'close': 'Close',
    'rest_kind': 'Not made yet. They are made together, in one go, after you say done in the chat.', 'rest_before': 'Answer the first sets before this.',
    'rest_before_why': 'A fault in the first sets would repeat in all of these.', 'rest_more': 'More, if you want it', 'rest_names': 'Which sets these are',
}


def _n(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _and(words):
    """'A', 'A and B', 'A, B and C'."""
    words = list(words)
    return ', '.join(words[:-1]) + ' and ' + words[-1] if len(words) > 1 else ''.join(words)


def _first(text):
    """The first sentence of a text (design/216: Claude's reason, its first sentence on the coloured line, the rest behind "more")."""
    m = re.match(r'^.*?[.!?](?:\s|$)', str(text or ''))
    return m.group(0).strip() if m else str(text or '')


def rec_of(label, do, reason):
    """Claude's recommendation on a set's line: the label and the reason as before; design/216 (A5): its heading, the first sentence of the reason and the rest."""
    first = _first(reason)
    return {'do': do, 'label': label, 'reason': reason, 'head': WORDS['rec_head'].format(label=label[:1].lower() + label[1:]), 'first': first, 'more': reason[len(first):].strip()}


def _shot_words(session, plan):
    """Each shot as the operator knows it from the plan's page: its number in its gap's table, and the gap (design/211 review: no shot code name)."""
    out = {}
    for number, gap in enumerate((plan or {}).get('gaps') or [], 1):
        gid = gap.get('gap_id')
        try:
            chosen = [s['id'] for sc in V.chosen_scenes(gap, (session.get('choice_selections') or {}).get(gid)) for s in sc.get('shots') or []]
        except (KeyError, TypeError, ValueError, StopIteration):
            chosen = []
        for sc in gap.get('scenes') or []:
            for s in sc.get('shots') or []:
                out[s.get('id')] = WORDS['shot'].format(n=chosen.index(s['id']) + 1, gap=number) if s.get('id') in chosen else WORDS['shot_unnumbered'].format(gap=number)
    return out


def _gap_numbers(plan):
    return {g.get('gap_id'): n for n, g in enumerate((plan or {}).get('gaps') or [], 1)}


def _used(facts, where, short=False):
    """Where the film uses a thing: how many shots, and the closest of them. `short` (design/212): the same in a few words, for a chip."""
    shots = facts.get('shots') or []
    if not shots:
        return WORDS['used_short_none' if short else 'no_shot']
    near = next((s for s in shots if s.get('size') == facts.get('closest')), shots[0])
    size = SIZE_WORDS.get(near.get('size'), near.get('size') or 'of no stated size')
    if short:
        return WORDS['used_short'].format(shots=_n(len(shots), 'shot'), size=size)
    return WORDS['used'].format(shots=_n(len(shots), 'shot'), size=size, where=where.get(near.get('shot')) or WORDS['shot_unnumbered'].format(gap=where.get('#', {}).get(near.get('gap'), '?')))


def _search_words(found, frames):
    """What the footage has of a thing, from the search record (`ref_find.found_all`) and the pictures that stand: (the sentence, its reason).
    design/212: a thing the footage does not show is said in three words, "Not in your footage.", with the reason behind "why". The clips
    with no analysis are named once for the step (`_unread`), not on every line."""
    if frames:
        return WORDS['found'].format(pictures=_n(len(frames), 'picture')), ''
    if not found:
        return '', ''
    if found.get('result') == 'not_searched':
        return WORDS['not_in'], str(found.get('note') or 'No reason was recorded').rstrip('.') + '.'
    names, n = list(found.get('clip_names') or []), int(found.get('clips') or 0)
    searched = WORDS['searched'].format(clips=_n(n, 'clip'), names=f" ({', '.join(names)}{'…' if n > len(names) else ''})" if names else '')
    return (WORDS['not_in_closest'], searched) if found.get('closest') else (WORDS['not_in'], searched + ' ' + WORDS['nothing_close'])


def _unread(found):
    """The clips nobody could search, said once for the step: the page's summary and the chat's first question."""
    missed = next((list(f.get('not_searched') or []) for f in (found or {}).values()), [])
    return WORDS['no_analysis'].format(names=', '.join(missed)) if missed else ''


def unread_words(ctx):
    from . import ref_find
    return _unread(ref_find.found_all(ctx['store'], ctx['run'], ctx['session'], ctx['plan'])) if ctx.get('plan') and V.round_v2(ctx['session']) else ''


def _made_shots(facts, where):
    return [where.get(s['shot']) or WORDS['shot_unnumbered'].format(gap=where.get('#', {}).get(s.get('gap'), '?')) for s in facts.get('shots') or [] if s.get('way') != 'footage']


def _cost(facts, where):
    made = _made_shots(facts, where)
    return WORDS['cost'].format(ids=', '.join(made)) if made else WORDS['cost_none']


def _told(line):
    """A line's page fields as the chat's text: the same sentences, in the order the page shows them."""
    check = line.get('check') or {}
    parts = [line.get('text') or ''] + [(line.get('likeness') or {}).get('ask') or ''] + [line.get('differs') or ''] + [line.get('partial') or ''] + [WORDS['read_first'].format(warning=w) for w in line.get('warnings') or []]
    parts += [f"{p['label']}: {p['note']}" + (' (weak)' if p.get('weak') else '') for p in line.get('pics') or [] if p.get('note')]
    parts += [check['by']] if check else []
    parts += list(check.get('lines') or []) + ([check['na']['head'] + ': ' + ' '.join(check['na']['lines'])] if check.get('na') else []) + list(line.get('changes') or [])   # release 1, A5
    parts += [WORDS['model_' + k].format(words=v) for k, v in (line.get('look') or {}).items() if v]   # design/213: the image model's notes as Claude's two plain lines; the raw notes stay in the record
    parts += [line['searched']['text']] if line.get('searched') else []   # design/215
    parts += [line['asked']] if isinstance(line.get('asked'), str) else []
    parts += [WORDS['earlier'].format(labels=', '.join(p['label'] for p in line['earlier']))] if line.get('earlier') else []   # design/211 review, S14: the chat shows the set before too
    parts += [WORDS['corrections'].format(words='; '.join(line['corrections']))] if line.get('corrections') else []   # design/215
    parts += [WORDS['proposes'].format(**line['rec'])] if line.get('rec') else []
    return '\n'.join(p for p in [line.get('note') or ''] + parts + [line.get('cost') or ''] if p)   # design/212 review: first, that a new picture came for the thing


def _v2_item(ident, kind, position, name, ask, run, buttons, line, more=(), **marks):
    """One question of a v2 round: the chat's item, with the page's line beside it."""
    named = lambda p, n, tag='': f"{marks.get('_eid') or 'round'}{tag}-{n}.{'jpg' if p['_key'].endswith('.jpg') else 'png'}"
    item = _item(ident, kind, position, f'{name}: {ask[:1].lower()}{ask[1:]}', run, buttons, text=_told(line), more=more,
                 show=[{'key': p['_key'], 'name': named(p, n)} for n, p in enumerate(line.get('pics') or [], 1)]
                      + [{'key': p['_key'], 'name': named(p, n, '-before')} for n, p in enumerate(line.get('earlier') or [], 1)])
    item.update({'_v2': True, '_line': line, '_eid': '', '_person': False, '_kept': None, '_frames': [], '_makes': False, **marks})
    return item


def round_marks(ctx, eid, marks, quote):
    """The pictures of a step-1 line answered on their own: "Not this picture" (`ref_find.not_this`) and "That is it" on the closest picture
    (`ref_find.that_is_it`). A mark that names a picture not on that line is refused (PIC_UNKNOWN) before anything is changed. Returns the
    pictures the operator has not seen that came in place of a rejected one."""
    from . import ref_find
    session, run = ctx['session'], ctx['run']
    frames = {f['ref'] for f in ref_find.frames_of(session, eid)}
    found = ref_find.found_all(ctx['store'], run, session, ctx['plan']).get(eid) or {}
    closest = None if frames else (found.get('closest') or {}).get('trial')
    for pid, mark in marks.items():
        V.need((mark in ('not', 'on', 'off') and pid in frames) or (mark == 'use' and pid == closest), PIC_UNKNOWN.format(pic=pid))
    came = []   # design/212 review: the pictures that came in place of a rejected one; a tick on a picture ('on', 'off') changes nothing here
    for pid, mark in marks.items():
        if mark == 'not':
            came += [x for x in [(ref_find.not_this(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], eid, pid, quote) or {}).get('next')] if x]
        elif mark == 'use':   # the frame it becomes is the operator's own choice: remembered, so that it starts ticked (the frame's record does not say who kept it)
            took = (ref_find.that_is_it(ctx['conn'], ctx['store'], ctx['user'], run, ctx['outputs'], eid, pid, quote) or {}).get('ref')
            s = V.session_of(ctx['store'], run, ctx['outputs'])
            s['refs_taken'] = [*(s.get('refs_taken') or []), *([took] if took else [])]
            V.save_session(ctx['store'], run, s)
    return came


def _auto(kinds, eid, row, frames, fnd):
    """design/212 (SK, 17 Nov 2026): a person the footage does not show, for whom a set is proposed: nothing is to be decided, every such
    person gets a set from the description. Not asked on the page or in the chat; answered by the server at "done"."""
    return kinds.get(eid) == 'person' and not frames and not (fnd or {}).get('closest') and row.get('rec') == 'set'


def _auto_held(store, run, session, plan, elements, stamps, held):
    """The step-1 answers kept, with the answer of every thing that needs none (`_auto`) and has none of the operator's: a set is made.
    Nothing is stored for them: the same answer is found again until the step is recorded."""
    from . import ref_find
    kinds, found = _kinds(plan), ref_find.found_all(store, run, session, plan)
    auto = {eid: {'verdict': 'approve', 'quote': WORDS['auto_kept'], 'frames': stamps[eid], 'words': '', 'pics': {}, 'auto': True}
            for eid, row in elements if eid not in held and _auto(kinds, eid, row, ref_find.frames_of(session, eid), found.get(eid))}
    return {**auto, **held}


def round_accept(ctx, quote):
    """"Accept the proposals", for the page and the chat: every routine thing with no answer yet gets its proposal as its kept answer. Never a
    doubtful thing, never a real person's likeness; ACCEPT_NONE when none is left. A line the operator answers afterwards keeps their answer."""
    todo = [i for i in _round_items(ctx, every=True) if i.get('_routine') and not i['_kept']]
    V.need(todo, ACCEPT_NONE)
    s = V.session_of(ctx['store'], ctx['run'], ctx['outputs'])
    s['chat_round'] = {**(s.get('chat_round') or {}), **{i['_eid']: {'verdict': i['_routine'], 'quote': quote, 'frames': i['_stamp'], 'words': '', 'pics': {r: 'off' for r in i['_off']}} for i in todo}}   # the pictures the proposal does not use stay unused
    V.save_session(ctx['store'], ctx['run'], s)
    return {'accepted': [i['_eid'] for i in todo]}


def _rest_held_why(rd, names):
    """design/220: why the other sets wait for the operator's word, from what the check found of the first sets (`ref_sets.rest_by_check`); '' when it kept nothing."""
    from . import ref_sets
    held, out = rd.get('rest_held') or {}, []
    for k in ('fault', 'unmade', 'unchecked'):
        if held.get(k):
            out.append(WORDS['rest_held_' + k].format(names=_and(names.get(e, e) for e in held[k]), it='it' if len(held[k]) == 1 else 'them'))
    return ' '.join(out) or (ref_sets.LIMIT_PLAIN if held.get('limit') else '')


def _round_v2(ctx, every, step):
    """The questions of a v2 round (design/211 section 3.10), in the order both front ends show them. `every` as in `_round_items`."""
    from . import ref_find, ref_sets
    session, plan, run, conn, store, user, outputs = ctx['session'], ctx['plan'], ctx['run'], ctx['conn'], ctx['store'], ctx['user'], ctx['outputs']
    rd, names, kinds = session['round'], _names(plan), _kinds(plan)
    by_id = {e['id']: e for e in plan['elements']}
    budget = V._set_budget(run, session, V.visuals_spend(conn, run))
    facts = lambda eid: ref_sets.thing_facts(plan, session, by_id[eid])
    where = {**_shot_words(session, plan), '#': _gap_numbers(plan)}
    about = lambda eid, f: '\n'.join(x for x in (str(f.get('description') or by_id[eid].get('description') or ''), _used(f, where)) if x)
    if step == 1:
        _everything, elements, _frames, stamps, held = _round1(session, plan)
        elements = sorted(elements, key=lambda row: list(by_id).index(row[0]))   # the plan's order: a saved session keeps no order of its own
        found = ref_find.found_all(store, run, session, plan)
        held = _auto_held(store, run, session, plan, elements, stamps, held)   # design/212: a person the footage does not show counts as answered from the start
        things = []
        for eid, row in elements:
            f, person = facts(eid), kinds.get(eid) == 'person'
            frames = ref_find.frames_of(session, eid)
            fnd = found.get(eid) or {}
            mine = not frames and not person and bool(V._own_pictures(session, eid))
            drawn = (session.get('drawings') or {}).get(eid, {}).get('status') == 'approved'
            makes = person or drawn or not (frames or mine)   # as `visuals_stage._from_footage` decides
            closest = None if frames else fnd.get('closest')
            auto = _auto(kinds, eid, row, frames, fnd)
            shown = ref_sets.footage_person(session, plan, eid) if person and frames else {}   # design/213: a person whose kept footage picture shows the face: the permission is asked, nothing else
            permit = shown.get('state') == 'ask'
            # what the server records, as before design/212: (its older label, the stored choice, what it does). The stored round keeps these choices.
            opts = [('Have a set made', 'approve', 'set') if makes else ('Use my picture as the reference' if mine else 'Use it as the reference', 'approve', 'footage')]
            if frames and not makes:
                opts.append(('Make a clean set from it', 'clean', 'set'))
            if not (person and f.get('shots_made')):   # a person shown in a made picture always gets a set
                opts.append(('No set needed' if row.get('rec') == 'no_set' else WORDS['leave'], 'ignore', 'none'))   # design/216 (B6): was "Leave it out"
            rec = row.get('rec')
            match = next((o for o in opts if o[1] == ref_sets.REC_VERDICT.get(rec) and o[2] == REC_DOES.get(rec)), None)
            cause = V.set_cause(session, plan, eid, budget)
            warnings = ([WORDS['warn_person']] if f.get('real_person') and not V.likeness_of(session, eid) else []) + ([WORDS['warn_exact']] if f.get('identity') == 'exact' else []) \
                + ([WORDS['warn_cause'].format(cause=cause['text'])] if cause and cause.get('kind') != 'cap' else []) + ([WORDS['warn_stale']] if fnd.get('stale') else [])   # a size that is not known is no warning here: nothing is decided by it; design/212: the limit is named only in a refusal after "done"
            doubt = bool(permit or row.get('doubt') or any(p.get('weak') for p in frames) or not match or f.get('real_person') or fnd.get('stale'))   # design/211 review, M3: a weak frame that came in since the round was sent counts too
            # design/212 review (17 Nov 2026): which pictures start ticked follows the proposal, not the weak mark: the pictures the proposal uses. "Use the footage" and a
            # set that can only come from the footage: every picture. A set of a person, or of a thing with approved drawings (made with or without footage): the pictures
            # that are not weak; with only weak ones the set is from the description. "Leave out": none. A picture left unticked is not used; it is never "not this picture".
            starts = lambda p: rec in ('footage', 'clean') or (rec == 'set' and not (makes and p.get('weak'))) or p['ref'] in (session.get('refs_taken') or [])   # the closest picture the operator took ("that is it") is theirs: ticked
            pics = [{'_key': _ref_key(run, p['ref']), '_mark': _mark(session['references'], p['ref']), 'label': str(p.get('view') or 'Footage picture'), 'note': str(p.get('seen') or ''), **({'weak': True} if p.get('weak') else {}),
                     **({'on': True} if starts(p) else {}), 'choice': 'not:' + p['ref'], 'choice_label': WORDS['not_this']} for p in frames]
            start_off = [p['ref'] for p in frames if not starts(p)]
            waits = (session.get('chat_round') or {}).get(eid) or {}
            waits = waits if waits.get('confirm') and waits.get('frames') == stamps[eid] else {}   # an answer held for a look at a picture that came in place of a rejected one
            if closest:
                pics.append({'_key': closest['key'], '_mark': str(closest.get('sha256') or ''), 'label': WORDS['closest_label'].format(view=closest.get('view') or 'not said'), 'note': str(closest.get('seen') or ''),
                             'choice': 'use:' + closest['trial'], 'choice_label': WORDS['that_is_it']})
            # design/212: the case of the thing, and the buttons that case allows: (the label, the choice both front ends send, needs the operator's words, a small link)
            case = 'auto' if auto else 'footage' if frames else 'closest' if closest else 'none'
            does = {o[1]: o[2] for o in opts}
            can_use, can_set, can_leave = 'footage' in does.values(), 'set' in does.values(), 'ignore' in does
            acts = []
            if not auto and (can_use or (case == 'closest' and not person and not drawn)):   # the closest picture, once ticked, is its footage picture
                acts.append((WORDS['approve'], 'use', False, False))
            if not auto and can_set:
                acts.append((WORDS['set'], 'set', False, False))
            if case == 'footage' and can_set:   # only where a picture exists: the set is made with the operator's words
                acts.append((WORDS['fix1'], 'fix', True, False))
            if not auto and can_leave:
                acts.append((WORDS['leave'], 'ignore', False, False))
            if case in ('none', 'auto') and can_set:
                acts.append((WORDS['add_words'], 'fix', True, case == 'none'))
            if permit:   # the two answers of the permission, then "Leave out" where the thing may be left out
                acts = [(WORDS['permit'], 'permit', True, False), (WORDS['standin'], 'standin', False, False)] + [x for x in acts if x[1] == 'ignore']
            want = {'footage': 'use', 'clean': 'set', 'set': 'set', 'no_set': 'ignore', 'leave': 'ignore'}.get(rec)
            want = 'set' if want == 'use' and not can_use and can_set else want   # approved drawings, or a person: its footage picture is used through a set
            sug = next((x[1] for x in acts if x[1] == want and not x[3] and x[0] != WORDS['add_words']), None)
            acts.sort(key=lambda x: not (sug and x[1] == sug and x[0] != WORDS['add_words']))   # the suggested answer first
            tick = {}   # the answers that need a picture kept, with what the click is told when none is
            if permit:
                case, tick = 'likeness', {'permit': WORDS['tick_set']}
            elif case == 'footage' and not makes:
                tick = {'use': WORDS['tick_use'], 'set': WORDS['tick_set'], 'fix': WORDS['tick_set']}
            elif case == 'closest' and any(x[1] == 'use' for x in acts):
                tick = {'use': WORDS['tick_closest']}
            said, why = (WORDS['own_is'], '') if mine else (WORDS['auto'], _search_words(fnd, frames)[1]) if auto else _search_words(fnd, frames)
            tag = {'use': WORDS['tag_use'], 'set': WORDS['set'], 'ignore': WORDS['leave']}.get(sug or want, str(rec))
            group = STEP1_GROUPS[4] if auto else STEP1_GROUPS[0] if not doubt else STEP1_GROUPS[1] if pics else STEP1_GROUPS[3] if rec in ('leave', 'no_set') else STEP1_GROUPS[2]
            desc = str(f.get('description') or by_id[eid].get('description') or '')
            line = {'group': group, 'case': case, 'text': '\n'.join(x for x in (desc, _used(f, where), ' '.join(x for x in (said, why) if x)) if x),
                    'desc': desc, 'used': _used(f, where), 'shots': _used(f, where, short=True),
                    **({'search': {'text': said, 'why': why}} if not frames and said and not mine else {}),
                    **({'rec': {'do': rec, 'label': tag, 'reason': str(row.get('reason') or ''), **({'choice': sug} if sug else {})}} if rec else {}),
                    **({'warnings': warnings} if warnings else {}), **({'pics': pics} if pics else {}), **({'tick': tick} if tick else {}),
                    **({'likeness': {'ask': WORDS['likeness_ask_child' if shown.get('child') else 'likeness_ask']}} if permit else {}),
                    **({'differs': WORDS['added'].format(words=row['prompt'])} if frames and row.get('prompt') else {}),   # design/213: where the plan and the footage differ, said openly
                    **({'corrections': ref_sets.corrections_shown(session, plan, eid)} if ref_sets.corrections_shown(session, plan, eid) else {}),   # design/215
                    **({'cost': _cost(f, where)} if can_leave else {}),
                    **({'note': WORDS['came'], 'again': {'choice': waits.get('choice'), 'notes': str(waits.get('words') or '')}} if waits else {})}

            def run_(choice, quote, words, eid=eid, own=None, pics=None, does=does, opts=opts, marked=None, tick=tick, frames=frames, closest=closest, start_off=start_off, waits=waits, permit=permit):
                marks = dict(pics or {})
                if permit and choice in ('permit', 'standin'):   # design/213: recorded through the likeness path both front ends share; a set is made either way
                    V.need(choice == 'standin' or words, WORDS['permit_words'])
                    kept_ = [p['ref'] for p in frames if marks.get(p['ref']) not in ('not', 'off') and not (p['ref'] in start_off and marks.get(p['ref']) != 'on')]
                    V.need(choice == 'standin' or kept_, WORDS['tick_set'])   # the permission is for the pictures ticked: with none there is nothing to make the set from
                    V.likeness(store, user, run, outputs, eid, words or quote, conn=conn, stand_in=choice == 'standin')
                    if choice == 'permit':   # design/213 review: the ticks are kept exactly as "Make a set" keeps them: only the ticked frames feed the likeness; the words of permission are not words for the picture
                        again = next(i for i in _round_items(_ctx(conn, store, user, run, outputs), every=True) if i.get('_eid') == eid)
                        return again['_run']('set', quote, '', own=own, pics=marks)
                    s = V.session_of(store, run, outputs)
                    s['chat_round'] = {**(s.get('chat_round') or {}), eid: {'verdict': 'approve', 'quote': quote, 'frames': stamps[eid], 'words': '',
                                                                           'pics': {p['ref']: 'off' for p in frames}}}   # a stand-in: nothing of the footage person is used
                    V.save_session(store, run, s)
                    out = None if every else round_close(conn, store, user, run, outputs, quote)
                    return out if out is not None else {'stored': eid}
                if choice.startswith(('not:', 'use:')):   # the chat: one picture answered on its own
                    marks, choice = {choice[4:]: 'not' if choice.startswith('not:') else 'use'}, 'pics'
                new = choice in ('use', 'set', 'fix')   # design/212: the buttons say what the operator wants; the stored choice is found below
                V.need(choice != 'fix' or words, WORDS['fix_words'])
                # design/212 review: the pictures not used: one the operator unticked ('not': also "not this picture"), and one that started unticked and was not ticked ('on').
                # An answer in the shape of before design/212 (approve, clean, ignore) knew no ticks: every picture not marked "not" is used
                unused = lambda ms: [p['ref'] for p in frames if ms.get(p['ref']) in ('not', 'off') or (new and p['ref'] in start_off and ms.get(p['ref']) != 'on')]
                if choice in tick and marked is None:   # an answer that needs a picture kept: refused before anything is marked
                    V.need(len(unused(marks)) < len(frames) or (closest and marks.get(closest['trial']) == 'use'), tick[choice])
                if marked is None and any(m in ('not', 'use') for m in marks.values()):   # the pictures first: "not this picture", "that is it"
                    came = round_marks(ctx, eid, marks, quote)
                    again = next(i for i in _round_items(_ctx(conn, store, user, run, outputs), every=True) if i.get('_eid') == eid)
                    if choice == 'pics':
                        return {'marked': eid}
                    mine_ = next((o[0] for o in opts if o[1] == choice), None)
                    if not new and not any(o[1] == choice and o[0] == mine_ for o in again['_opts']):
                        return {'marked': eid}   # the older answer would now mean something else: the line is asked again
                    if came and not waits:   # design/212 review: a picture the operator has not seen came: their answer and words are kept, and wait once for their look at it
                        s = V.session_of(store, run, outputs)
                        s['chat_round'] = {**(s.get('chat_round') or {}), eid: {'confirm': True, 'choice': choice, 'words': words, 'quote': quote, 'frames': again['_stamp'], 'pics': {}}}
                        V.save_session(store, run, s)
                        return {'stored': eid, 'came': came}
                    # once per thing: a picture that comes after the operator has confirmed is not used, and the answer stands
                    return again['_run'](choice, quote, words, own=own, marked={**marks, **{c: 'off' for c in came}})
                if marked is None:
                    bad = [k for k in marks if k not in {p['ref'] for p in frames}]
                    V.need(not bad, PIC_UNKNOWN.format(pic=bad[0] if bad else ''))
                    if choice == 'pics':
                        return {'marked': eid}
                    marked = marks
                verdict = choice
                if new:   # Approve: the ticked footage pictures as the reference. Make a set, Minor corrections, Add words: a set, from the ticked pictures; from the description where none is ticked
                    verdict = next((o[1] for o in opts if o[2] == ('footage' if choice == 'use' else 'set')), None)
                    V.need(verdict, WORDS['tick_use'] if choice == 'use' else WORDS['no_answer'])
                off = unused(marked)
                V.need(not (verdict == 'clean' or does.get(verdict) == 'footage') or len(off) < len(frames) or not frames, tick.get(choice) or WORDS['tick_use'])
                s = V.session_of(store, run, outputs)
                s['chat_round'] = {**(s.get('chat_round') or {}), eid: {'verdict': verdict, 'quote': quote, 'frames': stamps[eid], 'words': words if does.get(verdict) == 'set' else '',
                                                                       'pics': {**{k: v for k, v in marked.items() if v != 'on'}, **{r: 'off' for r in off if marked.get(r) != 'not'}},
                                                                       **({'own': own} if own else {})}}
                V.save_session(store, run, s)
                out = None if every else round_close(conn, store, user, run, outputs, quote)
                return out if out is not None else {'stored': eid}
            ask = WORDS['likeness_ask_child' if shown.get('child') else 'likeness_ask'] if permit else WORDS['ask_person'] if person else WORDS['ask_set'] if makes else WORDS['ask_mine'] if mine else WORDS['ask_footages' if len(frames) > 1 else 'ask_footage']
            said = {'permit': (WORDS['say_permit'], WORDS['permit_hint']), 'standin': (WORDS['say_standin1'], '')}
            button = lambda x: {**_button(x[0], x[1], words=x[2], tell=(WORDS['permit_hint'] if x[1] == 'permit' else WORDS['fix_tell']) if x[2] else ''), **({'small': True} if x[3] else {}),
                                **({'go': WORDS['go_set']} if x[1] == 'fix' else {}),   # design/215: the words box's own button, sent by the server
                                **({'note': WORDS['set_hint']} if x[1] == 'set' and case == 'footage' and can_use else {}),   # only where a picture exists and may be used as it is
                                **({'say': said[x[1]][0], **({'hint': said[x[1]][1]} if said[x[1]][1] else {})} if x[1] in said else {})}
            things.append(_v2_item(f'round1:{eid}', 'reference', '', names[eid], ask, run_, [button(x) for x in acts if not x[3]], line,
                                   more=[button(x) for x in acts if x[3]] + [_button(f"{p['choice_label']}: {p['label']}", p['choice']) for p in pics],
                                   _key=f'ref:{eid}', _eid=eid, _person=person, _frames=[p['ref'] for p in frames], _makes=makes, _kept=held.get(eid), _does=does, _stamp=stamps[eid],
                                   _opts=opts, _off=start_off, _routine=None if doubt or auto else ref_sets.REC_VERDICT[rec]))
        items = sorted(things, key=lambda i: STEP1_GROUPS.index(i['_line']['group']))   # design/212: the five groups in their order; the plan's order inside
        routine_all = [i for i in things if i['_routine']]
        routine = [i for i in routine_all if not i['_kept']]
        if routine and (every or session.get('round_each') != rd.get('at')):
            does = [i['_does'][i['_routine']] for i in routine]
            n_sets = does.count('set')
            # design/211 review, C4: the truth about the sets: three are made first, the others are asked after. design/212: no cost is named
            goes = WORDS['goes'].format(m=ref_sets.FIRST_MAX, x=ref_sets.MAKES_MAX) if n_sets else ''
            line = {'text': WORDS['all_text'].format(n=_n(len(things), 'thing'), r=len(routine), s=_n(n_sets, 'set'), goes=goes, f=_n(does.count('footage'), 'thing'), l=does.count('none')),
                    'head': WORDS['all_head'].format(n=len(routine_all)), 'show': WORDS['all_show'].format(n=len(routine_all)), 'covers': [i['_key'] for i in routine_all]}   # design/212: the routine things, to be seen before they are accepted together

            def run_(choice, quote, words):
                if choice == 'each':   # the chat: the operator answers every line; not offered again in this round
                    s = V.session_of(store, run, outputs)
                    s['round_each'] = rd.get('at')
                    V.save_session(store, run, s)
                    return {}
                out = round_accept(_ctx(conn, store, user, run, outputs), quote)
                return (None if every else round_close(conn, store, user, run, outputs, quote)) or out
            items.insert(0, _v2_item('round1:all', 'reference', '', WORDS['all_title'], WORDS['all_ask'], run_,
                                     [_button(WORDS['accept'].format(n=len(routine_all)), 'accept_all')] + ([] if every else [_button(WORDS['each'], 'each')]),
                                     line, _key='refs:proposals', _title=WORDS['all_title']))
        if not every:
            fresh = not [e for e, v in held.items() if not v.get('auto')] and session.get('round_each') != rd.get('at')
            people = [names[i['_eid']] for i in things if (i['_kept'] or {}).get('auto')]
            items = [i for i in items if not i['_kept']]
            if items and fresh:   # said once, with the first question of the step
                items[0]['_summary'] = ' '.join(x for x in (_unread(found), WORDS['auto_people'].format(
                    people=_n(len(people), 'person') if len(people) == 1 else f'{len(people)} people', get='gets' if len(people) == 1 else 'get', names=', '.join(people)) if people else '') if x)
        for n, i in enumerate(items, 1):
            i['position'] = f'References, {n} of {len(items)}'
        return items
    if step not in (2, 'making', 'looking', 'rewrite'):
        return []
    # design/213 (17 Nov 2026): step 2 in the new layout. One builder for both front ends: the group, the case, the order, the buttons and every
    # sentence are decided here. A line carries `buttons` for the page (each with its `act`, the slot it takes, and `say`, what will happen);
    # the chat's item carries the same answers with the same words (a thing's "Approve" is one button per picture there: the chat has no ticks).
    rows = {eid: rd['elements'][eid] for eid in by_id if eid in rd['elements']}   # the plan's order
    waiting = [e for e in rows if e in (rd.get('rest') or []) and not any(rows[e].get(k) for k in ('ignored', 'set', 'reopened'))]   # the second go: not ordered yet
    back, sets, unmade = [], [], []
    make = lambda eid, quote: V.set_make(conn, store, user, run, outputs, eid, quote=quote)   # paid: the operator's words travel with it (design/211, MAKE_NO_QUOTE)

    def answers():
        """The answers of one line, twice: the chat's buttons and the page's (`add`), in the order given."""
        chat, page = [], []

        def add(label, choice, act, say, words=False, tell='', **more):
            chat.append(_button(label, choice, words=words, tell=tell))
            page.append({'label': label, 'choice': choice, 'needs_words': words, 'act': act, 'say': say, **more})
        return chat, page, add

    def head(eid, f, group, case, tag):
        """What every line of a thing says of it: the group, the case, and where the film uses it."""
        kept = ref_sets.corrections_shown(session, plan, eid)   # design/215: the operator's corrections of the thing, on its line
        return {'group': group, 'case': case, 'tag': tag, 'desc': str(f.get('description') or by_id[eid].get('description') or ''), 'used': _used(f, where), 'shots': _used(f, where, short=True),
                **({'corrections': kept} if kept else {})}

    def leaving(f, label):
        """What a thing with no reference loses: (the sentence of the answer, under the label pressed; the page's list)."""
        lost = _made_shots(f, where)
        return (WORDS['say_leave'].format(label=label, shots=_n(len(lost), 'shot')) if lost else WORDS['say_leave_none'].format(label=label),
                {'text': WORDS['loss_one'] if len(lost) == 1 else WORDS['loss'].format(shots=_n(len(lost), 'shot')) if lost else WORDS['cost_none'], 'shots': lost})

    for eid, row in rows.items():
        person = kinds.get(eid) == 'person'
        if row.get('reopened'):   # back after the round was sent again: the operator's word orders its set, or leaves it out
            f = facts(eid)
            why = WORDS[{'new': 'reopen_new', 'changed': 'reopen_changed'}.get(row['reopened'], 'reopen_left')]
            chat, page, add = answers()
            say, loss = leaving(f, WORDS['leave'])
            add(WORDS['set'], 'approve', 'set', WORDS['say_set'], sug=True)
            add(WORDS['add_words'], 'words', 'fix', WORDS['say_words'], words=True, tell=WORDS['fix_tell'], hint=WORDS['words_hint'], go=WORDS['go_set'])
            add(WORDS['leave'], 'ignore', 'leave', say)
            line = {**head(eid, f, STEP2_GROUPS[0], 'back', WORDS['tag_back']), 'text': about(eid, f) + '\n' + why, 'head': why, 'cost': _cost(f, where), 'loss': loss, 'buttons': page}
            back.append(_v2_item(f'reopen:{eid}', 'reference set to make', '', names[eid], WORDS['ask_set'],
                                 lambda choice, quote, words, eid=eid: ref_sets.round_reopen(conn, store, user, run, outputs, eid, 'approve' if choice == 'words' else choice, words, quote),
                                 chat, line, _key=f'set:{eid}', _eid=eid, _person=person))
            continue
        if row.get('ignored') or row.get('from_footage') or row.get('rewrite_due') or row.get('held') or row.get('things_due') or eid in waiting:   # design/216: a held place is a line with nothing to answer
            continue
        live = V._set_rows(session, eid, row.get('set'))
        if live:
            sf = ref_sets.set_facts(session, plan, eid, row)
            shown = [p for p in sf.get('pictures') or [] if p['ref'] in {r['id'] for r in live}][:len(LETTERS)]
            if (row.get('set_look') or {}).get('set') != row.get('set') or not shown or not all(p.get('look') for p in shown) or not ref_sets.looked(session, eid, row):
                continue   # no set reaches the operator before its look is recorded
            if not every and V._answered(session, kinds, eid, row):
                continue
            f, letter, one = facts(eid), {p['ref']: LETTERS[n] for n, p in enumerate(shown)}, len(shown) == 1   # `one`: a set of one picture (a place, design/213): no A, B, C to choose from
            named = lambda p: WORDS['pic_one'] if one else WORDS['pic_n'].format(letter=letter[p['ref']])
            states = [(p.get('check') or {}).get('state') or 'none' for p in shown]
            state = 'fail' if 'fail' in states else 'none' if 'none' in states else 'pass'   # design/214: one result, Claude's check; a picture not checked is never counted as passed
            # design/211 review, S15: plain words, no size in pixels and no picture id. design/214: a failed line is said as what was seen; a picture not checked is named, with why
            plain = lambda p, x: WORDS['check_' + x['check']].format(pic=named(p)) if x.get('check') in ('size', 'parent') else str(x.get('seen') or x.get('check'))
            fault = lambda p, x: plain(p, x) if x.get('check') in ('size', 'parent') else WORDS['check_line'].format(pic=named(p), seen=plain(p, x))
            faults = [fault(p, x) for p in shown for x in (p.get('check') or {}).get('failed') or []]
            off = [WORDS['check_off'].format(pic=named(p)) + (': ' + str(p['check']['error']) if (p.get('check') or {}).get('error') else '.') for p, st in zip(shown, states) if st == 'none']
            na = [f"{named(p)}: {x['check']}: {x['seen']}" for p in shown for x in (p.get('check') or {}).get('na') or []]   # release 1, A5: the lines that did not apply, apart from the faults
            check = {'state': state, 'by': WORDS['by_' + state], 'chip': WORDS['chip_fail'].format(faults=_n(len(faults), 'fault')) if state == 'fail' else WORDS['chip_' + state], 'lines': faults + off,
                     **P.na_view(na)}
            proposed, again = sf.get('rec') or {}, int(sf.get('makes_left') or 0) > 0
            do = proposed.get('do') if proposed.get('do') in ('use', 'remake', 'doubt') else None
            chat, page, add = answers()
            say_out, loss = leaving(f, WORDS['leave_failed'])
            n_pics = len(shown)   # design/216: one answer covers the whole set; the labels count its pictures (A3)
            if person:
                add(WORDS['approve'] if one else WORDS['approve_all'].format(n=n_pics), 'yes', 'approve', WORDS['say_use_one'] if one else WORDS['say_all'].format(n=n_pics, letter=LETTERS[0]))
            elif one:
                add(WORDS['approve'], 'use:' + shown[0]['ref'], 'approve', WORDS['say_use_one'])
            else:   # the page: one "Approve all", which takes the main picture (A unless the operator makes another the main one); the chat: one per picture
                chat += [_button(WORDS['approve_pic'].format(letter=letter[p['ref']]), 'use:' + p['ref']) for p in shown]
                page.append({'label': WORDS['approve_all'].format(n=n_pics), 'choice': 'use', 'needs_words': False, 'act': 'approve', 'say': ''})
            if again:   # made the most times: no remake is offered (ref_sets.MAKES_LIMIT would hold it)
                add(WORDS['fix'], 'correct', 'fix', WORDS['say_fix'], words=True, tell=WORDS['fix_tell'], go=WORDS['go_fix'], all={'label': WORDS['all_tick'], 'choice': 'correct_all', 'say': WORDS['say_fix_all']})
                add(WORDS['again_set'] if one else WORDS['again_all'].format(n=n_pics), 'no', 'again', WORDS['say_again'], ask=WORDS['again_ask'])
            if sf.get('changed'):
                add(WORDS['remake'], 'remake', 'remake', WORDS['say_remake'])
            if not again and not person:   # made the most times: a thing may be left out (V.set_aside takes it then); a person shown in a made picture is never left out
                add(WORDS['leave_failed'], 'aside', 'leave', say_out)
            # the proposed answer first, on both front ends; the chat shows four buttons, the others follow
            gold = proposed.get('golden') if not person and not one else None
            want = {'use': 'use:' + str(gold) if gold else chat[0]['choice'], 'remake': 'no'}.get(do)
            chat.sort(key=lambda b: b['choice'] != want)
            if again:   # design/215 (change 5): the page's tick "applies to every picture of this thing" as the chat's own answer, after the others
                chat.append(_button(WORDS['fix_all'], 'correct_all', words=True, tell=WORDS['fix_tell']))
            page.sort(key=lambda b: b['act'] != {'use': 'approve', 'remake': 'again'}.get(do))
            if do in ('use', 'remake') and page[0]['act'] == {'use': 'approve', 'remake': 'again'}[do]:
                page[0]['sug'] = True
            refs = session['references']
            drawn = {v.get('id'): v.get('labelled_key') or v.get('plain_key') for v in ((session.get('drawings') or {}).get(eid) or {}).get('views') or []}
            drawn_mark = {v.get('id'): v.get('labelled_sha256' if v.get('labelled_key') else 'plain_sha256') for v in ((session.get('drawings') or {}).get(eid) or {}).get('views') or []}
            pics = []
            beside = [i for i in sf.get('inputs') or [] if i.get('role') != 'thing'] + [{**x, 'role': 'footage'} for x in sf.get('footage') or []]   # design/216 (B4): the references of a place's things are not its footage   # what the set was made from, then the film's other pictures of it: to compare with
            for i in beside:
                key = (refs.get(i['ref']) or {}).get('key') or drawn.get(i['ref']) or (_ref_key(run, i['ref']) if i['ref'] in refs else None)
                if key:
                    view = i.get('view') or (refs.get(i['ref']) or {}).get('view') or 'a footage picture'
                    pics.append({'_key': key, '_mark': _mark(refs, i['ref']) or str(drawn_mark.get(i['ref']) or ''), 'ref_only': True, 'view': view if i.get('role') == 'footage' else '',
                                 'label': WORDS['from_footage'].format(view=view) if i.get('role') == 'footage' else WORDS['photo' if i.get('role') == 'photo' else 'drawing'],
                                 'cmp_cap': WORDS['cmp_cap'].format(view=view) if i.get('role') == 'footage' else WORDS['photo' if i.get('role') == 'photo' else 'drawing']})   # design/216: under it, beside the set's picture
            flagged = {p['ref'] for p in shown if (p.get('check') or {}).get('failed')}
            low = lambda x: x[:1].lower() + x[1:]
            for p, st in zip(shown, states):
                view = p.get('view') or 'no view named'
                pics.append({'_key': _ref_key(run, p['ref']), '_mark': _mark(refs, p['ref']), 'label': view if one else WORDS['picture'].format(letter=letter[p['ref']], view=view),
                             'letter': '' if one else letter[p['ref']], 'view': view, 'note': str((p.get('look') or {}).get('seen') or ''),
                             **({'weak': True} if (p.get('look') or {}).get('verdict') == 'weak' else {}), **({'flag': True} if p['ref'] in flagged else {}),
                             # design/216 (A4): what belongs to this picture, under it: its own faults, or that it has none, or that Claude could not check it (never "no fault" then)
                             'name': named(p), 'set_cap': WORDS['set_cap'].format(pic=low(named(p))), 'faults': [plain(p, x) for x in (p.get('check') or {}).get('failed') or []],
                             **({'faults_n': _n(len((p.get('check') or {}).get('failed')), 'fault')} if (p.get('check') or {}).get('failed') else {}),   # design/216, the fit: "1 fault" under the small picture
                             'check_head': WORDS['check_of'].format(pic=low(named(p))) if st != 'none' else '', 'check_none': WORDS['no_fault'] if st != 'none' else WORDS['not_checked_pic'],
                             **({} if person or one else {'choice': 'use:' + p['ref'], 'choice_label': WORDS['approve_pic'].format(letter=letter[p['ref']]),
                                                          'say': WORDS['say_all'].format(n=n_pics, letter=letter[p['ref']]), 'main_label': WORDS['main_link'].format(letter=letter[p['ref']])})})
            old = (sf.get('history') or [{}])[-1].get('set')
            earlier = [{'_key': r['key'], '_mark': str(r.get('sha256') or ''), 'label': WORDS['before'].format(letter=LETTERS[n])} for n, r in enumerate(sorted(
                [r for r in refs.values() if old and r.get('kind') == 'sheet' and r.get('element_id') == eid and r.get('set') == old and r.get('key')], key=lambda r: int(r.get('set_n') or 1))[:len(LETTERS)])]
            part, n_made, model = sf.get('partial'), int(sf.get('makes') or 0), sf.get('model') or {}
            most = '' if again else WORDS['set_made_max' if person else 'set_made_max_one' if one else 'set_made_max_thing'].format(n=sf.get('makes'))
            added = str(row.get('prompt') or '') if any(i.get('role') == 'footage' for i in beside) else ''
            line = {**head(eid, f, STEP2_GROUPS[0], 'judge', WORDS['tag_rec_' + do] if do else ''),
                    'text': '\n'.join(x for x in (about(eid, f), most, WORDS['set_changed'] if sf.get('changed') else '') if x),
                    **({'rec': rec_of(WORDS['rec_use_one' if one and do == 'use' else 'rec_' + do], do, str(proposed.get('reason') or ''))} if do else {}),
                    # design/216: the answer column speaks of the whole set (A3); approving against a "make again" asks once (A6)
                    'answer_head': WORDS['answer_one'] if one else WORDS['answer_all'].format(letters=_and([letter[p['ref']] for p in shown])),
                    'answer_note': WORDS['answer_one_note'] if one else WORDS['answer_all_note'].format(n=n_pics), 'strip_head': WORDS['strip_one'] if one else WORDS['strip_all'].format(n=n_pics),
                    **({'sure': {'ask': WORDS['sure_ask'].format(faults=_n(len(faults), 'fault')) if faults else WORDS['sure_ask_none'],
                                 'text': ' '.join(x for x in (_first(str(proposed.get('reason') or '')), WORDS['sure_copy']) if x), 'go': WORDS['sure_go'], 'back': WORDS['sure_back']}} if do == 'remake' else {}),
                    **({'things_wait': waits_for} if (waits_for := ref_sets.place_waiting(plan, session, eid)) else {}),
                    'pics': pics, 'check': check, **({'look': {k: str(model.get(k) or '') for k in ('chose', 'aside')}} if model.get('chose') or model.get('aside') else {}),
                    **({'differs': WORDS['added'].format(words=added)} if added else {}),   # the plan against the footage, said openly (design/213)
                    **({'searched': sf['searched']} if sf.get('searched') else {}),   # design/215: what the picture model searched
                    **({'rule': WORDS['rule_person']} if person else {}), **({'pick': True} if not person and not one else {}),
                    **({'made_n': WORDS['made_twice'] if n_made == 2 else WORDS['made_n'].format(n=n_made)} if n_made > 1 else {}),
                    **({'most': most} if most else {}), **({'changed': WORDS['set_changed']} if sf.get('changed') else {}),
                    **({'partial': WORDS['partial'].format(made=part.get('made'), asked=part.get('asked'), missing=', '.join(part.get('missing') or []) or 'not named')} if part else {}),
                    **({'earlier': earlier} if earlier else {}), **({'asked': WORDS['asked'].format(words=sf['asked'])} if sf.get('asked') else {}),
                    **({'loss': loss, 'cost': _cost(f, where)} if any(b['act'] == 'leave' for b in page) else {}), 'buttons': page}

            def run_(choice, quote, words, eid=eid):
                if choice == 'remake':
                    return {**make(eid, quote), 'tell': 'The set is being made again. ' + NOTHING}
                if choice == 'aside':
                    return V.set_aside(store, user, run, outputs, eid, words or quote)
                golden = choice[4:] if choice.startswith('use:') else None
                every_pic = choice == 'correct_all'
                choice = 'correct' if every_pic else choice
                V.set_answer(store, user, run, outputs, eid, 'yes' if golden else choice, golden, words if choice == 'correct' else '', all=every_pic)
                out = flush_sets(conn, store, user, run, outputs, quote)
                return out if out is not None else {'tell': 'Your answer is kept. It is recorded as soon as the sets still being made are back.'}
            sets.append(_v2_item(f"set:{eid}:{row.get('set')}", 'reference set', '', names[eid], WORDS['ask_person_set' if person else 'ask_one_set' if one else 'ask_thing_set'], run_, chat[:4], line, more=chat[4:],
                                 _key=f'set:{eid}', _eid=eid, _person=person, _rows=sorted(live, key=lambda r: int(r.get('set_n') or 1))[:len(LETTERS)], _kept=V._answered(session, kinds, eid, row),
                                 _first=do != 'use'))
        elif not V._set_rows(session, eid, row.get('set'), ('generating', 'approved')):
            cause = V.set_cause(session, plan, eid, budget)
            if cause and not every:
                continue   # something stands in its way: that comes in its own turn
            refused = V._set_state(session, plan, 2, eid, row, budget).get('next')   # the picture service refused this person's photo
            f = facts(eid)
            chat, page, add = answers()
            if refused:
                def run_(choice, quote, words, eid=eid, refused=refused):
                    if choice == 'photo':
                        return {'for_the_assistant': refused, 'tell': 'Ask the operator for another photo of this person.'}
                    V.likeness(store, user, run, outputs, eid, words or quote, conn=conn, stand_in=True)
                    return {**make(eid, words or quote), 'tell': 'This person is a stand-in now: the set is being made from the description. ' + NOTHING}
                add('Another photo', 'photo', 'photo', WORDS['say_photo'])
                add('A stand-in', 'standin', 'standin', WORDS['say_standin'], words=True, tell='Ask the operator to say in their own words that this person is a stand-in now.', hint=WORDS['standin_hint'])
                line = {**head(eid, f, STEP2_GROUPS[1], 'photo', WORDS['tag_not_made']), 'text': about(eid, f) + '\n' + WORDS['photo_refused'], 'head': WORDS['photo_refused'], 'buttons': page}
                unmade.append(_v2_item(f'likeness:{eid}:{row.get("set")}', 'reference set to make', '', names[eid], WORDS['ask_standin'], run_, chat, line, _key=f'set:{eid}', _eid=eid, _person=person))
                continue
            fail = (ref_sets.set_facts(session, plan, eid, row).get('fail') or {}).get('text') if row.get('set') or row.get('error') else None
            most = ref_sets.makes(session, eid, row) >= ref_sets.MAKES_MAX   # design/211 review, M2: made the most times: no paid button
            limit = (cause or {}).get('kind') == 'cap' or ref_sets.is_limit(row.get('error'))   # design/213: the limit is said with no amount, openly on the line
            retired = fail == V.RULE_RETIRED and not cause   # design/216 (B3): held by a rule that no longer applies: the plain sentence alone
            said = WORDS['made_max_unmade'].format(n=ref_sets.MAKES_MAX) if most else ref_sets.LIMIT_PLAIN if limit else V.RULE_RETIRED if retired else WORDS['not_made_head']
            why = '' if most or limit or retired else WORDS['not_made_wait'].format(cause=cause['text']) if cause else fail or ''
            say_out, loss = leaving(f, WORDS['leave_failed'])
            if not most:
                add(WORDS['make'], 'make', 'make', WORDS['say_make'])
            add(WORDS['leave_failed'], 'aside', 'leave', say_out)
            line = {**head(eid, f, STEP2_GROUPS[1], 'notmade', WORDS['tag_not_made']), 'cost': _cost(f, where), 'loss': loss, 'head': said, **({'why': why} if why else {}),
                    **({'things_wait': waits_for} if (waits_for := ref_sets.place_waiting(plan, session, eid)) else {}),
                    'text': '\n'.join(x for x in (about(eid, f), said, why) if x), 'buttons': page}
            if line.get('things_wait'):   # not made yet: "It will be made after ...", not "made again"
                line['things_wait'] = ref_sets.place_waiting(plan, session, eid, again=False)

            def run_(choice, quote, words, eid=eid):
                if choice == 'make':
                    return {**make(eid, quote), 'tell': 'The set is being made. ' + NOTHING}
                return V.set_aside(store, user, run, outputs, eid, words or quote)
            unmade.append(_v2_item(f'setmake:{eid}', 'reference set to make', '', names[eid], WORDS['ask_make'], run_, chat, line, _key=f'set:{eid}', _eid=eid, _person=person))
    items = back + sorted(sets, key=lambda i: not i['_first']) + unmade   # "To judge": the sets Claude suggests making again or is unsure of first; then "Could not be made"
    if waiting and step in (2, 'rewrite'):   # (also while a sent-back set waits for its rewrite: ref_sets.round_rest takes it then, the operator answers both in one visit) the first sets are judged before the others are ordered
        many = len(waiting) != 1
        # design/211 review, C5: a person shown in a made picture always gets a set, so "Leave out" never covers one; the line names the shots that lose a reference
        wf = {e: facts(e) for e in waiting}
        people = [e for e in waiting if kinds.get(e) == 'person' and wf[e].get('shots_made')]
        out_ = [e for e in waiting if e not in people]
        them = f'these {len(out_)} sets' if len(out_) != 1 else 'this set'
        lose = [f"{names[e]}: {', '.join(_made_shots(wf[e], where))}" for e in out_ if _made_shots(wf[e], where)]
        sets_n = lambda n: _n(n, 'set')
        said_people = WORDS['rest_people'].format(names=', '.join(names[e] for e in people), them='them' if len(people) != 1 else 'this one') if people and out_ else ''
        chat, page, add = answers()
        later = {e: [t.get('name') or t['id'] for t in ref_sets.pending_things(plan, session, e)] for e in waiting}
        later = {e: n for e, n in later.items() if n}   # design/216 (the critic's point 1): a place waits for its things' sets
        made_now = len(waiting) - len(later)
        rest_said = WORDS['rest_say'].format(sets=sets_n(len(waiting))) if not later else ' '.join(
            [WORDS['rest_now'].format(sets=sets_n(made_now), are='is' if made_now == 1 else 'are')] + [
                WORDS['rest_held'].format(places=_and(names[e] for e in later if later[e] == n), wait='waits' if sum(later[e] == n for e in later) == 1 else 'wait', names=_and(n))
                for n in [list(x) for x in dict.fromkeys(tuple(v) for v in later.values())]])
        add(WORDS['rest_make'].format(sets=len(waiting) if many else 'set'), 'rest', 'rest', rest_said)   # design/216 (A12): one label, on the page and in the chat
        page[0].update(big=page[0]['label'])
        if out_:   # design/213: what is left out is left out, and the others (the people, who always get a set) are made on the same word
            out_say = (WORDS['rest_out_say'].format(made=sets_n(len(people)), out=f"{len(out_)} {'are' if len(out_) != 1 else 'is'}") if people else
                       WORDS['rest_out_say_none'].format(out=f"{len(out_)} {'are' if len(out_) != 1 else 'is'}"))
            add(WORDS['rest_out_make'].format(them=them, m=len(people)) if people else WORDS['rest_out'].format(them=them), 'rest_out', 'rest_out', out_say)
            page[1].update(label=WORDS['rest_some'], loss={
                'head': WORDS['loss_head'].format(them=them), 'intro': WORDS['loss_intro'], 'cols': WORDS['loss_cols'],
                'rows': [[names[e], len(_made_shots(wf[e], where)), ', '.join(_made_shots(wf[e], where))] for e in out_],
                **({'people': WORDS['loss_people'].format(people='This person' if len(people) == 1 else f'The {len(people)} people', get='gets' if len(people) == 1 else 'get',
                                                          names=', '.join(names[e] for e in people), their='their set' if len(people) == 1 else f'their {len(people)} sets')} if people else {}),
                'button': chat[1]['label']})   # design/213 review: the words pressed are the words recorded, the same on the page and in the chat
        line = {'text': '\n'.join(x for x in (
                    WORDS['rest_text'].format(k=_n(len([r for r in rows.values() if r.get('set')]), 'set'), r=f"{len(waiting)} more {'are' if many else 'is'}", names=', '.join(names[e] for e in waiting)), said_people) if x),   # design/212: no money is named here
                **({'cost': WORDS['rest_cost'].format(them=them, things='; '.join(lose)) if lose else WORDS['rest_cost_none'].format(them=them)} if out_ else {}),
                'head': WORDS['rest_head'].format(sets=f"{len(waiting)} more set{'s wait' if many else ' waits'}"), 'why': _rest_held_why(rd, names) or WORDS['rest_why'], 'show': WORDS['rest_show'].format(n=len(waiting)),
                'name': WORDS['rest_name'].format(sets=sets_n(len(waiting))),   # design/216 (A10): the last row of the list
                'list_head': WORDS['rest_list'].format(sets=sets_n(len(waiting))), 'list_note': WORDS['rest_list_note'], 'covers': [f'set:{e}' for e in waiting],
                'waits': {f'set:{e}': {'note': WORDS['wait_person'] if e in people else WORDS['wait_loss'].format(shots=_n(len(_made_shots(wf[e], where)), 'shot')) if _made_shots(wf[e], where) else WORDS['wait_none'],
                                       'out': e in out_} for e in waiting},
                'buttons': page}

        def run_(choice, quote, words):
            if choice == 'rest':
                return ref_sets.round_rest(conn, store, user, run, outputs, quote)
            s = V.session_of(store, run, outputs)   # design/213 review: all or nothing: refused before anything is left out
            V.need(not any(V._set_rows(s, e, r.get('set')) and not V._answered(s, kinds, e, r) for e, r in s['round']['elements'].items() if e in kinds and not r.get('ignored')), WORDS['rest_first'])
            spent, cap, one = V._set_budget(run, s, V.visuals_spend(conn, run))
            V.need(not people or spent + one * len(people) <= cap + 1e-9, ref_sets.LIMIT_PLAIN)
            for eid in out_:
                V.set_aside(store, user, run, outputs, eid, words or quote)
            return {'aside': out_, **(ref_sets.round_rest(conn, store, user, run, outputs, quote) if people else {})}   # the people are made on the same word; the limit refuses it in its plain sentence
        rest = _v2_item(f"rest:{rd.get('at')}", 'reference set to make', '', WORDS['rest_title'], WORDS['rest_ask'], run_, chat, line, _key='sets:rest', _title=WORDS['rest_title'])
        # the page shows it first; the chat asks it once the first sets are answered. design/220: held by the check, it comes after the sets on the page too: the set that did not pass is seen first
        items = [rest] + items if every and not rd.get('rest_held') else items + [rest]
    for n, i in enumerate(items, 1):
        i['position'] = f'Reference sets, {n} of {len(items)}'
    return items


# ---------- everything else that waits: questions, pictures, specs, takes ----------

VIEW_WORDS = {'cutaway': 'a cutaway', 'plan': 'seen from above', 'side': 'from the side', 'elevation': 'from the front'}
SPEC_FACTS = (('How it is laid', 'laid'), ('Joints', 'joint'), ('Pattern', 'pattern'))


def _leaves(x):
    """Every plain value of a record, without its field names."""
    if isinstance(x, dict):
        return [s for v in x.values() for s in _leaves(v)]
    if isinstance(x, (list, tuple)):
        return [s for v in x for s in _leaves(v)]
    return [] if x is None or isinstance(x, bool) or not str(x).strip() else [' '.join(str(x).split())]


def _spec_parts(spec, view=None):
    """design/209 (SK, 16 Nov 2026): a drawing spec or a material spec as plain parts, the one function the page and the chat both show: what it
    is drawn as and why, the words it carries, its parts, how they sit, its proportions, a material's facts, the sizes that are known (part,
    measure, size, where it came from in one short line) and the names of the sizes that are not. The assistant's working notes (`tried`) are
    not shown, and no field name is. A record of a shape this does not know is listed as its plain values (`other`), never an error."""
    def listed(x):
        if x is not None and not isinstance(x, list):
            raise TypeError('not a list')
        return x or []
    short = lambda s: s if len(s) <= 100 else s[:99].rstrip() + '…'
    try:
        dims = listed(spec.get('dimensions'))
        known = [d for d in dims if d.get('value') is not None]
        v, why = view or (spec.get('view') or '', str(spec.get('view_reason') or '').strip())
        label = ' '.join(str(spec.get('label') or '').split())
        out = {'drawn_as': VIEW_WORDS[v] + (f' ({why})' if why else '') if v in VIEW_WORDS else '',
               'words': ' '.join(x for x in ('Not to scale.' if spec.get('illustrative') else '', f'It carries the words "{label}".' if label else '') if x),
               'parts': [str(p) for p in listed(spec.get('parts'))], 'sits': [str(p) for p in listed(spec.get('relationships'))],
               'proportions': [str(p) for p in listed(spec.get('proportions'))], 'facts': [[name, str(spec[k])] for name, k in SPEC_FACTS if spec.get(k)],
               'sizes': [[str(d['part']), str(d['measure']), f"{d['value']:g} {d.get('unit') or ''}".strip(), short(' '.join(str(d.get('source') or '').split()))] for d in known],
               'unknown': ', '.join(f"{d['part']} {d['measure']}" for d in dims if d.get('value') is None), 'known': len(known)}
        return {k: x for k, x in out.items() if x}
    except (AttributeError, KeyError, TypeError, ValueError):
        return {'other': _leaves(spec)}


def _spec_text(parts):
    """The plain parts of a spec (`_spec_parts`) as the lines the chat shows above its question."""
    c = parts or {}
    rows = [f"Drawn as: {c['drawn_as']}"] if c.get('drawn_as') else []
    rows += [c['words']] if c.get('words') else []
    rows += ['Parts: ' + ', '.join(c['parts'])] if c.get('parts') else []
    rows += [f'{k}: {v}' for k, v in c.get('facts') or []]
    rows += (['How they sit:'] + [f'- {x}' for x in c['sits']]) if c.get('sits') else []
    rows += ['Proportions: ' + '; '.join(c['proportions'])] if c.get('proportions') else []
    rows += (['Sizes to confirm:'] + [f'- {p} {m}: {size}' + (f' (from {src})' if src else '') for p, m, size, src in c['sizes']]) if c.get('sizes') else []
    rows += [f'Note: {x}' for x in c.get('differs') or []]
    rows += [f"Already confirmed: {c['confirmed']}"] if c.get('confirmed') else []
    rows += [f"Not known, so no figure is shown: {c['unknown']}"] if c.get('unknown') else []
    rows += [f'- {x}' for x in c.get('other') or []]
    return '\n'.join(rows)[:6000]


def _spec_views(ctx):
    """design/209: every material spec and drawing spec of the film as the operator reads it, the materials first, then the drawings in the
    film's order: its title, its state (`open`, `recorded` when approved as it is now, `with_assistant` with the operator's words), the question
    it asks and its plain parts. Each fact is asked once: a known size that is the same part, measure and size as one the operator has approved
    in this film, or as one on an earlier line still to answer, is on the one line `confirmed` and not among the `sizes` to confirm (so a
    material's unit sizes are asked at the material). The same part and measure with another size on another line stays in full on both, with a
    `differs` remark. A line that is back with the assistant confirms nothing."""
    session, plan = ctx['session'], ctx['plan']
    names, approved, corrections = _names(plan), session.get('spec_approvals') or {}, session.get('spec_corrections') or {}
    rows = [(V.material_key(e['id']), names[e['id']], e['material_spec'], None) for e in plan.get('elements') or [] if e.get('material_spec')]
    rows += [(sh['id'], sh.get('title') or sh['id'], sh['drawing_spec'], V.spec_view(sh)) for _, sh in V._accepted_shots(plan, session) if sh.get('drawing_spec')]
    views = []
    for key, title, spec, view in rows:
        digest = V.spec_digest(spec)
        state = 'with_assistant' if V.correction_pending(session, key, spec) else 'recorded' if (approved.get(key) or {}).get('digest') == digest else 'open'
        parts = _spec_parts(spec, view)
        views.append({'key': key, 'title': title, 'state': state, 'item': f'spec:{key}:{digest[:10]}', 'spec': parts, 'note': (corrections.get(key) or {}).get('words') or '',
                      'ask': 'Are these facts right?' if view is None else 'Are the parts and the known sizes right?' if parts.get('known') else 'Are the parts right?'})
    sizes = [{(p.strip().lower(), m.strip().lower()): size for p, m, size, _ in v['spec'].get('sizes') or []} for v in views]
    live = [n for n, v in enumerate(views) if v['state'] != 'with_assistant']
    for n in live:
        v, keep, same, differs = views[n], [], {}, []
        for row in v['spec'].get('sizes') or []:
            k = (row[0].strip().lower(), row[1].strip().lower())
            other = [f'{row[0]} {row[1]}: differs from {views[m]["title"]}: {sizes[m][k]}' for m in live if m != n and sizes[m].get(k, row[2]) != row[2]]
            asked = any(sizes[m].get(k) == row[2] for m in live if m != n and (m < n if views[m]['state'] == v['state'] else views[m]['state'] == 'recorded' and v['state'] == 'open'))
            if other or not asked:
                keep.append(row)
                differs += other
            else:
                same.setdefault(row[0], []).append(f'{row[1]} {row[2]}')
        v['spec'] = {**{k: x for k, x in v['spec'].items() if k != 'sizes'}, **({'sizes': keep} if keep else {}), **({'differs': differs} if differs else {}),
                     **({'confirmed': '; '.join(f"{part}: {', '.join(xs)}" for part, xs in same.items())} if same else {})}
    return views


def _drawing_items(ctx):
    """design/200: a thing's drawing set that waits for the operator: its labelled sheets, the facts with their sources, the sizes that are assumed.
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
            items.append(_item(f"shot-drawing:{sid}:{g['sha256'][:10]}", 'drawing', 'Step 7, AI video: the layout drawing of the shot', f"{shots[sid].get('title') or sid}: is the shot laid out right in these two drawings?", run_,
                               [_button('Yes', 'yes'), _button('Correct it', 'correct', words=True, tell='Ask the operator what is wrong in the drawing of the shot.')],
                               text=chr(10).join(lines), show=[{'key': v['labelled_key'], 'name': f"{sid}-drawing-{v['id']}.png"} for v in d['views']]))
    return items


FRAMES_ON_PAGE = ('The footage pictures are not asked here: the operator answers them with the references, on the page. Write out/reference-round.json and send it '
                  '(`vw visuals round --file out/reference-round.json`), then run `vw visuals page`. ')


def _round_frames(ctx):
    """design/210 review: the footage pictures that step 1 of the reference round will ask, while no round exists yet on a film whose
    references are made as sets. The chat does not ask them one by one before the round: the operator would answer each twice. Once the round
    is sent, the chat asks each thing with its pictures (`_round_items`) where the page cannot be shown."""
    session, plan = ctx['session'], ctx['plan']
    if not plan or session.get('round') or not V.is_kept(session, ctx['run']):
        return set()
    things = {e['id'] for e in plan.get('elements') or [] if e['id'] != V.STYLE and e.get('kind') not in ('graphic', 'animal', 'style')}   # what the round takes
    return {r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('status') == 'candidate' and r.get('element_id') in things}


def _decided(conn, run, user, about, rule, entry, words):
    """design/221 (A6): the operator's answer on a step-6 card (the shared parts, a still end-frame, a held drawing) is a line of the run's log, as
    their decision with their words (as the other answers that decide a thing are written)."""
    if conn is not None:
        from . import runlog
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': about, 'rule': rule, 'entry': entry,
                            'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': words, 'request_id': None})


def _waiting_items(ctx):
    session, plan, run, store, user, outputs, conn = ctx['session'], ctx['plan'], ctx['run'], ctx['store'], ctx['user'], ctx['outputs'], ctx['conn']
    if not plan:
        return []
    from . import motion
    names = _names(plan)
    briefs = {}   # design/221 (the critic's A2): each drawn shot's brief lines worked out once in this call

    def brief_now(sid):
        if sid not in briefs:
            briefs[sid] = V.motion_brief(store, run, outputs, sid, session=session)['lines']
        return briefs[sid]
    take_rows = V.take_jobs(conn, run)
    rows = V.waiting(session, plan, run.get('code'), take_rows, V._set_budget(run, session, V.visuals_spend(conn, run)), **({'gate': False} if ctx.get('page') else {}))   # design/221: the page's answers are never held back
    frames = _round_frames(ctx)
    rows = [w for w in rows if w['kind'] not in ('set to judge', 'set to make') and w['item'] not in frames]   # the round's own items, above; the round's footage pictures, at its step 1
    shots = {sh['id']: sh for _, sh in V._accepted_shots(plan, session)}
    title = lambda sid: (shots.get(sid) or {}).get('title') or sid
    items, specs = [], None
    for n, w in enumerate(rows, 1):
        kind, group, it = w['kind'], w['group'], w['item']
        where = f'{n} of {len(rows)} waiting'
        ref = session['references'].get(it)
        if kind == 'question to answer':
            q = session['questions'][it]
            choices = [str(c) for c in (q.get('choices') or [])]
            line = P.question_line(session, plan, it, q, ref) if w.get('step') != 'references' and len(choices) <= 4 and not (ref and P.video_shot(session, plan, ref)) else None
            shown = [b['label'] for b in line['buttons']] if line else choices   # the critic's review (6): the chat says the page's words, with no amount
            buttons = [_button(c[:40], f'c{i + 1}') for i, c in enumerate(shown)]   # a question always has two or more (the server refuses fewer)
            item = _item(f'question:{it}', 'question', where, line['ask'] if line else q['question'],
                         lambda choice, quote, words, it=it, choices=choices: V.answer(store, user, run, outputs, it, words or choices[int(choice[1:]) - 1]), buttons[:4],
                         text='\n'.join(f'- {c}' for c in shown) if len(shown) > 4 or any(len(c) > 40 for c in shown) else '', more=buttons[4:],
                         show=[_pic(run, it, f'question-{it}')] if ref and ref.get('sha256') else [])
            if line:   # design/217: a question about a made picture is a line of step 6; a size or fact question stays in the chat
                item['_line'] = line
            items.append(item)
        elif kind in ('style sheet to approve', 'sheet to approve', 'picture to answer') and ref:
            line = P.picture_line(store, session, plan, ref, style=kind.startswith('style')) if kind.startswith('style') or (kind == 'picture to answer' and w.get('step') == 'pictures') else None
            what = 'The style sheet of the graphics' if kind.startswith('style') else names.get(ref.get('element_id')) or w['label']

            def run_(choice, quote, words, ref=ref):
                if choice == 'yes':
                    out = V.approve_reference(store, user, run, outputs, ref['id'], ref['sha256'], quote, conn)
                    if ref.get('parent_wanted'):   # fix set A2.2: one answer, the operator's: approved, and allowed as the parent of new pictures
                        view = P.check_view(session, ref, plan)
                        faults = view['faults']
                        _decided(conn, run, user, f"picture {ref['id']}", 'fix set A2.2 (a picture another picture is made from, approved in the chat)',
                                 'approved, also as the parent of new pictures' + (P._named(", although Claude's check failed a must line: ", view.get('who')) + ' '.join(faults) if faults else ''), quote)   # release 1, A2: who checked
                    elif kind != 'sheet to approve':   # release 1, B1 (SK, 20 Nov 2026): one click against the check: no second box; the run's log keeps the fact
                        faults = P.check_view(session, ref, plan)['faults']
                        if faults:
                            _decided(conn, run, user, f"picture {ref['id']}", 'release 1, B1 (approved against the check, one click)', P.W['log_against'].format(faults=' '.join(faults)), quote)
                    return out
                return V.reject_reference(store, user, run, outputs, ref['id'], '' if choice == 'no' else words, quote)   # design/217 (F4): a bare No carries no reason
            if line:   # design/217: the style sheet and a still say the page's words in the chat too (F1: the check from Claude's look and the program's lines)
                faults = line['check']['faults'] if ref.get('parent_wanted') else None   # fix set A2.2: the card says plainly what its Yes carries
                early = '' if faults is None else '- ' + (P._named(P.W['parent_card_failed'].format(lines=' '.join(faults)), line['check'].get('who')) if faults else P.W['parent_card']) + '\n'
                item = _item(f"picture:{ref['id']}:{str(ref.get('sha256'))[:10]}", 'picture', where, f"{line['name']}: {line['ask'][0].lower()}{line['ask'][1:]}", run_,
                             [_button(b['label'], b['choice'], words=b['needs_words'], tell='Ask the operator what to correct.' if b['needs_words'] else '') for b in line['buttons']],
                             text=early + P.chat_text(line), show=[_pic(run, ref['id'], f"picture-{ref['id']}")])
                item['_line'] = line
            else:
                item = _item(f"picture:{ref['id']}:{str(ref.get('sha256'))[:10]}", 'picture', where, f'{what}: is this picture right?', run_,
                             [_button('Yes', 'yes'), _button('No', 'no'), _button('Correct it', 'correct', words=True, tell='Ask the operator what to correct.')],
                             text=P.chat_text({'check': P.check_view(session, ref, plan)}), show=[_pic(run, ref['id'], f"picture-{ref['id']}")])
            items.append(item)
        elif kind == 'graphics to approve':
            chain = V.state_chain(session, group) or []
            line = P.steps_line(store, session, plan, group, chain)

            def run_(choice, quote, words, group=group, chain=chain, faults=line['check']['faults']):
                if choice == 'yes':
                    out = V.sequence(store, user, run, outputs, group, [r['id'] for r in chain], quote)
                    if faults:   # release 1, B1: approved against the check with one click: the run's log keeps the fact
                        _decided(conn, run, user, f'shot {group}', 'release 1, B1 (approved against the check, one click)', P.W['log_against'].format(faults=' '.join(faults)), quote)
                    return out
                k = int(choice.split(':')[1]) if choice.startswith('correct:') else len(chain)   # design/217 (F2): the step the operator named; "correct" alone is the last, as before
                V.need(1 <= k <= len(chain), f'{title(group)}: there is no step {k}.')
                out = V.reject_reference(store, user, run, outputs, chain[k - 1]['id'], words, quote)
                for later in chain[k:]:   # each later step was made from the one before it: made again from the corrected one
                    if (V.session_of(store, run, outputs)['references'].get(later['id']) or {}).get('status') in ('candidate', 'approved'):
                        V.reject_reference(store, user, run, outputs, later['id'], '', 'No')   # the critic's review (4): no reason, so nothing reaches the feedback or the library (as F4)
                        s_ = V.session_of(store, run, outputs)
                        s_['references'][later['id']]['rejection']['cause'] = P.W['later_step']   # shown with the earlier try, never a reason
                        V.save_session(store, run, s_)
                return out
            buttons = [_button(b['label'], b['choice'], words=b['needs_words'], tell='Ask the operator what to correct in this step.' if b['needs_words'] else '') for b in line['buttons']]
            item = _item(f'graphics:{group}:{len(chain)}', 'graphics', where, f"{line['name']}: {line['ask'][0].lower()}{line['ask'][1:]}", run_, buttons[:4], more=buttons[4:],
                         text=P.chat_text(line), show=[_pic(run, r['id'], f'{group}-step-{i + 1}') for i, r in enumerate(chain)])
            item['_line'] = line
            items.append(item)
        elif kind == 'shared parts to approve':   # design/221 row 1: the film's shared parts, drawn once: their picture, Approve or Reject with the operator's words
            up = session['motion_parts']
            els = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or []}

            def run_(choice, quote, words, sha=up['sha256']):
                out = V.parts_answer(store, user, run, outputs, sha, choice == 'approve', quote, words)
                _decided(conn, run, user, 'the shared parts', 'design/221 row 1 (the shared parts, approved in the chat)',
                         'the shared parts approved' if choice == 'approve' else f'the shared parts rejected: "{words}"', words or quote)
                return out
            items.append(_item(f"parts:{up['sha256'][:10]}", 'parts', where, f"The shared parts of the drawn graphics ({len(up['parts'])}): each is drawn once and every drawing uses it. Are they right?", run_,
                               [_button('Approve', 'approve'), _button('Reject', 'reject', words=True, tell='Ask the operator what to change in the parts, in their words.')],
                               text='\n'.join(f"- {p['id']}: {p['title']}" + (f" ({els.get(p['element'], p['element'])})" if p.get('element') else '') for p in up['parts']),
                               show=[{'key': up['picture_key'], 'name': 'shared-parts' + ('.svg' if up['picture_key'].endswith('.svg') else '.png')}]))
        elif kind == 'still end-frame to approve':   # design/221 row 3: the drawing as it stands at the end of the shot, before the motion: Approve or Reject with the words
            ids = it.split(',')
            sts = [session['motion_stills'][sid] for sid in ids]

            def run_(choice, quote, words, ids=ids):
                out = V.still_answer(store, user, run, outputs, ids, choice == 'approve', quote, words)
                _decided(conn, run, user, 'shot ' + ', '.join(ids), 'design/221 row 3 (the still end-frame, approved in the chat)',
                         'the still end-frame approved' if choice == 'approve' else f'the still end-frame rejected: "{words}"', words or quote)
                return out
            ask = (f"{ids[0]}: this is the drawing as it stands at the end of the shot, before any motion is added. Is it right?" if len(ids) == 1 else
                   f"{', '.join(ids)}: the drawing as it stands at the end of each of these shots, in order, before any motion is added. Are they right?")
            items.append(_item(f"still-end:{it}:{hashlib.sha256(''.join(st['png'] for st in sts).encode()).hexdigest()[:10]}", 'still end-frame', where, ask, run_,
                               [_button('Approve', 'approve'), _button('Reject', 'reject', words=True, tell='Ask the operator what to change in the still, in their words.')],
                               show=[{'key': st['frame_key'], 'name': f'{sid}-still-end.png'} for sid, st in zip(ids, sts)]))
        elif kind == 'held drawing':   # design/221 row 18: a must still fails after the last round: its frames, the open musts in full, three answers
            job, rec = next((j for j in take_rows if str(j['id']) == str(it)), None), V.held_drawing(session, group)
            if not job or not rec:
                continue
            musts, res = V.held_rules(rec), job.get('result') or {}

            def run_(choice, quote, words, job=job, group=group):
                out = V.held_answer(conn, store, user, run, outputs, group, str(job['id']), choice, quote, words)
                _decided(conn, run, user, f'shot {group}', 'design/221 row 18 (a held drawing, decided in the chat)',
                         f'the held drawing selected anyway: "{words}"' if choice == 'select' else "one more round, at the operator's word" if choice == 'more'
                         else 'the held drawing rejected' + (f': "{words}"' if words else ''), words or quote)
                return out
            buttons = [_button('Select it anyway', 'select', words=True, tell='The drawing is held: ask the operator why it is right for the film all the same.'),
                       _button('Reject it', 'reject')] + ([] if (session.get('motion_more') or {}).get(group) else [_button('One more round', 'more')])
            items.append(_item(f"held:{group}:{str(rec.get('sha256'))[:10]}:{rec.get('round')}", 'held drawing', where,
                               f"{title(group)}: held after round {rec.get('round')}: {len(musts)} must rule{' still fails' if len(musts) == 1 else 's still fail'}. What do you decide?",
                               run_, buttons, text='\n'.join('- ' + m for m in musts),
                               show=[{'key': k, 'name': f'{group}-{n}'} for k, n in ((res.get('key'), 'drawing.mp4'), (res.get('sheet_key'), 'frames.jpg')) if k]))
        elif kind in ('drawing spec to approve', 'material spec to approve'):
            key = V.material_key(group) if kind.startswith('material') else group
            specs = specs or {v['key']: v for v in _spec_views(ctx)}   # design/209: the plain words the page shows, a size the operator approved earlier in the film said once
            view = specs.get(key)
            if not view:
                continue

            def run_(choice, quote, words, key=key):
                if choice == 'yes':
                    return V.approve_spec(store, user, run, outputs, key, quote)
                return V.correct_spec(store, user, run, outputs, key, words)
            items.append(_item(view['item'], 'spec', where, f"{view['title']}: {view['ask'][0].lower()}{view['ask'][1:]}", run_,
                               [_button('Yes', 'yes'), _button('Correct it', 'correct', words=True, tell='Ask the operator which value is wrong and what it should be.')], text=_spec_text(view['spec'])))
        elif kind == 'take to select':   # design/207 (D2): the reuse question is retired; a reuse that passes the checks is kept without the operator
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
            motion_take = (job.get('request') or {}).get('kind') == 'motion'
            drawn = job.get('provider') == 'drawn'
            if not drawn and V.round_v2(session):   # design/222: an AI video take: one item per shot (its newest take), the page's own line, words and answers
                found = next(((g_, sh, k, of) for g_, sh, k, of in T.video_shots(plan, session) if sh['id'] == group), None)
                if not found:
                    continue
                left = V.cap_of(session) - V.visuals_spend(conn, run)['spent_inr']
                line = T.line(store, session, plan, *found, take_rows, left_inr=left, price_inr_per_s=V.prices()['video_inr_per_s'])
                if line['takes'][-1]['job'] != str(job['id']):
                    continue   # an earlier take of the shot: it is on the newest take's line

                def run_(choice, quote, words, group=group):
                    out = T.answer(conn, store, user, run, outputs, group, V.take_jobs(conn, run), choice, quote, words)
                    if choice == 'again' and not ctx.get('page'):   # the critic's S7: answered in the chat, the one line with the amount is said here (on the page: once, after done)
                        s_ = V.session_of(store, run, outputs)
                        said = T.ordered(s_, V.current_plan(store, s_), V.prices()['video_inr_per_s'])
                        V.save_session(store, run, s_)
                        return {**(out or {}), 'tell': said}
                    return out
                buttons = [_button(b['label'], b['choice'], words=b['needs_words'], tell=b.get('hint') or '') for b in line['buttons']]
                item = _item(T.item_id(session, job), 'take', where, f"{line['name']}: {line['ask'][0].lower()}{line['ask'][1:]}", run_, buttons[:4], more=buttons[4:], text=T.chat_text(line),   # the id carries the check as shown: an answer to an older view is stale
                             show=[{'key': res['key'], 'name': f'{group}-take.mp4'}] if res.get('key') else [])
                item['_line'] = line
                items.append(item)
                continue
            ev = res.get('evidence') or {}
            line = P.drawn_line(store, session, plan, job, check, fin, motion_take, brief_now) if drawn else None
            if line:   # design/217 (F3): held as select_take holds it: the fact check of the project it was rendered from, no fact check yet, the server's lines, the timing
                hold, why_hold = bool(line['held']), line['held'].split(':')[0] if line['held'] else ''
                text = P.chat_text(line)
            else:
                failed = [str(c.get('check')) for c in (check.get('must_failed') or [])] + [str(l.get('line')) for l in (check.get('scorecard') or []) if l.get('state') == 'Fail']
                hold = bool(failed or check.get('not_read') or ev.get('timing_matches_placement') is False)
                why_hold = ('The checks did not pass it (' + ', '.join(dict.fromkeys(failed)) + ')' if failed else 'It was not checked' if check.get('not_read')
                            else 'It is shorter than its place in the film' if hold else '')
                text = '\n'.join('- ' + x for x in lines + look + ([why_hold + ': to select it all the same, the operator says why.'] if hold else []) if x)
            short = ev.get('timing_matches_placement') is False

            def run_(choice, quote, words, job=job, group=group, hold=hold, short=short, line=line):
                if choice == 'select':   # an older film's held take is selected only with the operator's own reason
                    if not hold:   # nothing holds it: the accepted review carries the operator's click, no words
                        V.review_take(conn, store, user, run, outputs, str(job['id']), 'accepted', '', '', quote)
                    note = (words or (P.W['against_note'] if line else '')) if hold else ''   # release 1, B1 (SK, 20 Nov 2026): a drawn graphic of step 6 is selected with one click against its check: no reason asked (one typed on an older page is kept)
                    out = V.select_take(conn, store, user, run, outputs, str(job['id']), quote, note, note if short else '', None)
                    if hold and line:   # the run's log keeps that it went against the check
                        _decided(conn, run, user, f'shot {group}', 'release 1, B1 (selected against the check, one click)',
                                 P.W['log_against_drawn'].format(why=': '.join([line['held'].split('.')[0]] + ['; '.join(line['check']['faults'])] * bool(line['check']['faults']))), words or quote)
                    return out
                if choice in ('plain', 'no-effect'):   # design/217: "plain" on the page; "no-effect", the chat's older word, kept
                    out = V.motion_finish(conn, store, user, run, outputs, group, False)
                    V.review_take(conn, store, user, run, outputs, str(job['id']), 'rejected', "made again without the effect, at the operator's word", '', quote)   # the drawing with the effect is not asked about again
                    return {**out, 'tell': 'The drawing is being made again without the effect. ' + NOTHING}
                return V.review_take(conn, store, user, run, outputs, str(job['id']), 'rejected', words, '', quote)
            show = [{'key': res['key'], 'name': f"{group}-{'drawing' if drawn else 'take'}.mp4"}] if res.get('key') else []
            sheet_key = res.get('sheet_key') or check.get('sheet_key')
            show += [{'key': sheet_key, 'name': f'{group}-frames.jpg'}] if sheet_key else []
            if line:
                buttons = [_button(b['label'], b['choice'], words=b['needs_words'], tell='Ask the operator what is wrong with it.' if b['needs_words'] else '') for b in line['buttons']]   # release 1, B1: Select asks no reason
            else:
                buttons = [_button('Select', 'select', words=hold, tell=why_hold + ': ask the operator why it is right for the film all the same.'),
                           _button('Reject', 'reject', words=True, tell='Ask the operator what is wrong with it.')] + ([_button('Take the effect away', 'no-effect')] if fin else [])
            item = _item(f"take:{job['id']}", 'take', where, f"{title(group)}: is this {'drawing' if drawn else 'take'} right for the film?", run_, buttons, text=text, show=show)
            if line:
                item['_line'] = line
            items.append(item)
    return items


def _guide_items(ctx):
    """An AI video shot: its still on the overlay, then the word to shoot. Both are the operator's."""
    session, plan, run, store, user, outputs, conn = ctx['session'], ctx['plan'], ctx['run'], ctx['store'], ctx['user'], ctx['outputs'], ctx['conn']
    if not plan or not session.get('guides'):
        return []
    from . import guide
    # release 1, D2 (SK, 20 Nov 2026): the early cards in batches, in film order: every still's card first (`items`), then every word to shoot (`words`).
    # (Until this release: per shot, in the order the guides were written: a still, a word to shoot, the next shot's still; design/35 row 277.)
    shots, items, words, checking = {sh['id']: sh for _, sh in V._accepted_shots(plan, session)}, [], [], False
    for sid in [sid for sid in shots if sid in session['guides']]:
        g = session['guides'][sid]
        title = shots[sid].get('title') or sid
        still = next((s for s in g.get('stills') or [] if s.get('status') == 'candidate' and s.get('guide_sha256') == g['sha256'] and s.get('key')), None)
        if still and not P.start_offered(session, still):
            checking = True   # a still is with Claude's look: its card comes first, so the words to shoot wait for it (30 minutes at most: then it is shown as not checked)
            continue   # release 1, A1: step 7's still is checked by Claude's look first; its card comes with the look, or after 30 minutes as not checked
        if still:
            def run_(choice, quote, words, sid=sid, still=still):
                if choice == 'approve':
                    return guide.approve_still(conn, store, user, run, outputs, sid, still['id'], still['sha256'], quote)
                return guide.reject_still(conn, store, user, run, outputs, sid, still['id'], words, quote)
            show = ([{'key': still['overlay_key'], 'name': f'{sid}-still-on-the-guide.png'}] if still.get('overlay_key') else []) + [{'key': still['key'], 'name': f'{sid}-still.png'}]
            items.append(_item(f"still:{sid}:{still['id']}", 'still', 'Step 7, AI video: the still',
                               f'{title}: this still starts the shot. On the first picture, does every person and thing sit on the red outlines?', run_,
                               [_button('Approve', 'approve'), _button('Reject', 'reject', words=True, tell='Ask the operator what is wrong with the still.')], show=show,
                               text=P.chat_text({'check': P.look_view(still)}) if V.round_v2(session) else ''))   # the check's line and its warnings: the operator may approve against them
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
        if card['ready'] and not open_take and (g.get('shoot_asked') or {}).get('stamp') != stamp and not T.again_pending(g):   # design/222: "Make another" on the page gave the word: no second Shoot card
            def run_(choice, quote, words, sid=sid, stamp=stamp, again=again):
                out = guide.shoot(conn, store, user, run, outputs, sid, quote, again) if choice == 'shoot' else {'for_the_assistant': words}
                s = V.session_of(store, run, outputs)
                s['guides'][sid]['shoot_asked'] = {'stamp': stamp, 'answer': 'shoot' if choice == 'shoot' else 'not yet', **({'words': words} if choice != 'shoot' else {})}   # asked once for this state of the shot
                V.save_session(store, run, s)
                return {**out, **({'tell': 'The take is being made. ' + NOTHING} if choice == 'shoot' else {})}
            show = [{'key': k, 'name': n} for k, n in ((card.get('guide_key'), f'{sid}-guide.mp4'), ((card.get('still') or {}).get('overlay_key'), f'{sid}-still-on-the-guide.png')) if k]
            why = str((checks.get(str(last['id'])) or {}).get('blocked')) if again else ''
            words.append(_item(f"shoot:{sid}:{hashlib.sha256(stamp.encode()).hexdigest()[:10]}", 'shoot', 'Step 7, AI video: the take',
                               (f"{title}: the clip that came back cannot be used ({why}). Send the same request once more? It costs about ₹{card['cost_inr']:g}." if again
                                else f"{title}: make the take now? It is {card['seconds']} s and costs about ₹{card['cost_inr']:g}."), run_,
                               [_button('Send it again' if again else 'Shoot', 'shoot'), _button('Not yet', 'wait', words=True, tell='Ask the operator what should change first.')],
                               text=str(card.get('look_for') or ''), show=show))
    return items + ([] if checking else words)


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


def flush_sets(conn, store, user, run, outputs, quote=''):
    """Record every whole answer kept on a reference set (the operator gave each one in the chat). None while a set is still being made, or when
    there is nothing to record: the answers stay kept. Any other refusal of the server is raised as it is. With no answer kept and no set left
    to judge at step 2, the round is completed here: the chat (`next_item`) and the page (`page_flow._page`) both pass through this."""
    s = V.session_of(store, run, outputs)
    rd = s.get('round')
    if not (rd and rd.get('kept') and s.get('current')):
        return None
    kinds = _kinds(V.current_plan(store, s))
    from . import ref_sets
    if V.round_v2(s) and any(r.get('held') for r in rd['elements'].values()) and ref_sets.release(conn, store, user, run, outputs):   # design/216: a held place whose things are approved now
        s = V.session_of(store, run, outputs)
        rd = s['round']
    kept = {e: a for e, r in rd['elements'].items() if e in kinds and not r.get('ignored') for a in [V._answered(s, kinds, e, r)] if a and V._set_rows(s, e, r.get('set'))}
    if not kept:
        if V.round_v2(s) and rd.get('pass') != 'complete' and V._round_pass(s, rd) == 'complete':   # design/211: nothing is left with the operator (the others were left out): the state says complete; it is stored here, once, for both front ends
            rd['pass'] = 'complete'
            V.save_session(store, run, s)
            return {'pass': 'complete', 'queued': [], 'errors': {}, 'approved': [], 'held': {}}
        if V._round_pass(s, rd) != 2:
            return None
        try:   # design/210 review: the last answer was "Leave it out" or the operator's own picture, so no set is left to judge: the round completes by the server's own test, as after a Yes
            return V.round_sets(store, user, run, outputs, {}, quote or rd.get('quote') or '', conn=conn, partial=True)
        except (ValueError, V.Problem):
            return None   # a set still waits for its answer
    try:
        return V.round_sets(store, user, run, outputs, kept, quote, conn=conn, partial=True)
    except (ValueError, V.Problem) as exc:   # a refusal written with `need` is a ValueError until the API wraps it
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
    for step in (_drawing_items, _round_items, _waiting_items, _guide_items, _record_items):   # design/200: a drawing set is approved before the pictures made from it
        items = step(ctx)
        if items:
            return items, str(items[0].get('_summary') or '') if items[0].get('_v2') else '', note   # design/211 review: a v2 round's first question says once what holds for the whole step
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
        'Leave it out': 'This thing gets no reference', 'No reference needed': 'No reference of it; its shots are made without one',
        'Go on without a reference': 'No set of it; its shots are made without a reference',
        'Correct every picture of it': 'The set is made again with your words, and they go into every later picture of this thing', 'Make again': 'The set is made again; Claude rewrites the request first', 'Make a set with words': 'A set is made with your words; it comes back to you to judge',
        'Make it': 'Make the set now (paid)', 'Yes, use it': 'Use the footage picture', 'Yes, make one': 'Have a set made (paid)',
        'Take the effect away': 'Make the drawing again without the added effect',
        'Select it anyway': 'Use it in the film; I will ask you why', 'Reject it': 'It is rebuilt from the start', 'One more round': 'The helpers try once more (allowed once)',
        'Use it as the reference': 'Take the footage picture; nothing is made', 'Make a clean set from it': 'A set is made from the footage picture', 'Have a set made': 'A set of three pictures is made',
        'No set needed': 'Its words carry it; nothing is made', 'Ask me each one': 'I ask you every thing in turn',
        'Make a set': 'A set is made of it; it comes back to you to judge', 'Minor corrections': 'The set is made again with your words', 'Leave out': 'This thing gets no reference',
        'Add words for the picture': 'A set is made with your words'}


def _says(label):
    label = label.split(' (paid')[0]   # design/211: a paid button carries its price
    return SAYS.get(label) or ('This one becomes the reference' if label.startswith('Use ') else 'The whole set is right' if label.startswith('Approve all ') else   # design/216
                               SAYS['Make again'] if label.startswith('Make all ') else 'Use this picture as the reference' if label.startswith('Approve ') else
                               'No set of them; their shots are made without a reference' if label.startswith('Do not make ') else
                               'The sets that wait are made now, in one go' if label.startswith('Make the other ') else '')


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
    says = (lambda label: ('Use the ticked footage pictures as the reference; nothing is made' if item['id'].startswith('round1:') else 'Use this as the reference') if label == WORDS['approve'] else   # design/215 (W2)
            _says(label).replace(' (paid)', '')) if item.get('_v2') else _says   # design/212: no cost at the references
    out['buttons'] = [{**b, 'description': says(b['label'])} for b in out['buttons']]   # the line under each button, the same for every operator
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
            'When every number is coloured, press Submit all: your answers appear in the message box below. Press Enter to send them. Nothing is recorded until you send them.')


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
        entries.append(f"{{n:{_lit(c['n'])},c:{c['c']},{'a:1,' if c.get('a') else ''}{ch}{body}}}")
    data = ('{' + f"id:{_lit(card_id)},say:{_lit(CARD_SAY.format(what='gap' if plan else 'line'))},sum:{_lit(summary or '')},auto:1,"
            + f"cols:{json.dumps(GAP_COLS)},w:[5,19,13,9,27,27],e:[\n" + ',\n'.join(entries) + ']}')
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
            'Submit all puts one line into the message box and the operator sends it: "Card answers (press Enter to send; do not edit or delete): {…}". Write the part from { to } as it is into the file `answers_path` and run '
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
    # a card from before 14 Nov 2026 held the direction with the gap lines: its changed direction is still taken once, the old way
    direction_changes = ids[0].startswith('treatment:direction:') and ids[0] in open_ and seen.get(1, ('', ''))[0] == 'change'
    unanswered = [n for n in range(1, len(ids) + 1) if n not in seen]
    V.need(direction_changes or not unanswered, f"Answer every entry of the card first; still to answer: {', '.join(map(str, unanswered))}. Nothing was recorded.")
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
    """design/217 (C2): the pictures that wait for Claude's check are said first, in `then`: the duty is never silent."""
    out = _next_item(conn, store, user, run, outputs, one)
    try:
        session = V.session_of(store, run, outputs)
        plan = V.current_plan(store, session) if session.get('current') and V.round_v2(session) else None
    except (ValueError, V.Problem):
        plan = None
    if plan:
        if P.stamp(session, plan) | P.asked(session, plan):   # a picture that waited for the model's check at the deploy is given to Claude's check; C3: Claude is asked from now
            V.save_session(store, run, session)
        looks = P.waits_words(session, plan)
        if looks:
            out['then'] = looks + (' ' + out['then'] if out.get('then') else '')
        rows = V.take_jobs(conn, run)
        if T.asked(session, plan, rows):   # design/222: Claude is asked to check the takes from now
            V.save_session(store, run, session)
        more = ' '.join(x for x in (T.waits_words(session, plan, rows), T.starts(session, plan, rows), T.again_due(session, plan, rows), T.rejected_due(session, plan, rows)) if x)   # the takes that wait for Claude's check; release 1, D1: what can start now, together; a take ordered on the page; a shot left with no take
        if more:
            out['then'] = more + (' ' + out['then'] if out.get('then') else '')
        six = P.expected(session, plan, rows)
        due = ' '.join(x for x in (P.drawn_due(six), P.starts(six), P.stills_due(six)) if x)   # design/221 row 19: the stills are ordered at the start of step 6; a failed or stale render is said; fix set A1.4: what can start now
        if due:
            out['then'] = (out['then'] + ' ' if out.get('then') else '') + due
        show = _finished({'session': session, 'store': store}, six) if out.get('item') or out.get('card') else []   # fix set A3.4: a finished drawing is shown with the next answer too (with nothing waiting: `_next_item`), once
        if show:
            V.save_session(store, run, session)
            out['show'], out['show_how'] = show, SHOW_FIRST
    return out


SHOW_FIRST = ('First, before the decision: the tool saved the files of the top-level `show` in the run folder (finished drawn graphics): show each to the operator with its '
              '`say` line, as it is; ask nothing about it. ')
STATUS_HOW = ' (the first is the count of step 6: say it each time it changes, as it is, and ask nothing with it)'
SHOW_HOW = 'The tool saved the files of `show` in the run folder: show each to the operator with its `say` line, as it is; ask nothing about it. '


def _step6(ctx):
    """design/221 row 18: step 6's things (`pictures.expected`), on a film whose step 6 is answered on the page; else []."""
    return P.expected(ctx['session'], ctx['plan'], V.take_jobs(ctx['conn'], ctx['run'])) if ctx['plan'] and V.round_v2(ctx['session']) else []


def _finished(ctx, six):
    """design/221 row 18: each drawn graphic whose render is ready, shown in the chat once (by its render job), to look at early; nothing is asked."""
    shown, out = ctx['session'].setdefault('drawings_shown', {}), []
    for i in six:
        res = (i.get('job') or {}).get('result') or {}
        if i['kind'] == 'drawn' and i['state'] == P.STATE['done'] and res.get('key') and shown.get(i['id']) != str(i['job']['id']):
            n = len(P.fact_view(ctx['session'], ctx['store'], i['job'], i['id']).get('notes') or [])
            out.append({'key': res['key'], 'name': f"{i['id']}-drawing.mp4", 'say': P.W['shown'].format(name=i['name'], notes=f"{n} note{'' if n == 1 else 's'}" if n else 'no notes')})
            shown[i['id']] = str(i['job']['id'])
    return out


def _next_item(conn, store, user, run, outputs, one=False):
    """The one decision the operator takes now; or, for the treatment's lines and the plan's gaps, all of them on one card (design/190; `one` asks
    them one at a time, the older way, kept for a machine that cannot show the card); or that nothing is needed and what is being made."""
    try:
        flush_sets(conn, store, user, run, outputs)
    except V.Problem:
        pass   # said again when the operator next answers a set
    ctx = _ctx(conn, store, user, run, outputs)
    items, summary, with_assistant = _candidates(ctx)
    session = V.session_of(store, run, outputs)
    # SK, 14 Nov 2026: the direction is asked first and alone; every gap line is written from it, so none is shown until it is accepted
    if items and not one and len(items) >= 2 and items[0]['kind'] in CARD_KINDS and not items[0]['id'].startswith('treatment:direction:'):
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
        pub = _public(item, summary, len(items), one)
        if item.get('_line') and P.complete(_step6(ctx)):   # design/221 row 18: everything of step 6 is made: the page offers it, in one visit
            pub['how'] = (T.W['page_now'] if item['_line'].get('kind') == 'take' else P.W['page_now']) + pub['how']   # design/222: a take is answered on the page of step 7
        return {'item': pub}
    if session.pop('chat_item', None) or session.pop('chat_card', None):
        session.pop('chat_card', None)
        V.save_session(store, run, session)
    six = _step6(ctx)
    seven = T.expected(session, ctx['plan'], V.take_jobs(conn, run)) if ctx['plan'] and V.round_v2(session) else []   # design/222: step 7's line of counts
    count = ' '.join(x for x in (P.status_line(six), T.status_line(seven)) if x)
    show = _finished({**ctx, 'session': session}, six)
    if show:
        V.save_session(store, run, session)
    lines = ([count] if count else []) + with_assistant + working(conn, run)
    # design/211: a v2 round that waits for Claude (the looks at the made sets, a rewrite): the server's own sentence, as every status gives it; design/211 review, N6: and with the plan accepted and no round, what comes next
    turn = V.round_due(session, ctx['plan']) if V.round_v2(session) or (V.ROUND_V == 2 and not session.get('round')) else None
    return {'item': None, 'needed': False, 'working': lines, 'say_last': NOTHING, **({'then': turn} if turn else {}), **({'show': show} if show else {}),
            'how': (FRAMES_ON_PAGE if _round_frames(ctx) else '') + (SHOW_HOW if show else '') + 'Tell the operator the `working` lines as they are'
                   + (STATUS_HOW if count else '') + ('' if lines else ' (there are none: say in one line what you are doing next)') + f', then "{NOTHING}"'}


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
    said = out.get('tell') or (out.get('then') if V.round_v2(session) else None)   # design/211: an answer of a v2 round carries the server's own "what next" (the second go ordered, a set made)
    nxt = next_item(conn, store, user, run, outputs, one)   # SK, 12 Nov 2026: record and fetch in one step, so the operator waits once per answer, not twice
    return {'answered': item_id, 'choice': choice, **done, **nxt,
            'then': (str(said) + ' ' if said else '')
                    + ('The next decision is in `item`: show it now; do not run `vw visuals next` for it.' if nxt.get('item')
                       else 'What comes next is a card (`card`): show it now, as `how` says.' if nxt.get('card') else 'No decision waits now: give the `working` lines and the last line.')
                    + (' ' + nxt['then'] if nxt.get('then') and nxt['then'] != said else '')
                    + (' The operator asked for a change: make only that change, send it again, and it returns in its turn.' if button.get('needs_words') else '')}
