"""design/211, part B: the reference sets of a v2 round. The facts of a thing, the request per kind, the views, the checks' lines,
the two goes of making, the looks at a set, the remake by rewrite.

Every name, signature and constant of the contract (design/211 section 3) is here. Nothing here is called for a round without `v == 2`
(`visuals_stage.round_v2`): `visuals_stage` branches into this file, and an older round runs the code of before, word for word. Parts A
and C read only the functions and constants named in design/211 section 4.

A refusal is a named constant (a format string): raised with `visuals_stage.need(False, NAME.format(...))`; a test asserts the message.
"""
import re
from datetime import datetime, timezone

from . import ref_find, visuals_stage as V
from .errors import Problem
from .visual_contract import SIZE_ORDER, all_scenes

RECS = ('footage', 'clean', 'set', 'no_set', 'leave')
REC_VERDICT = {'footage': 'approve', 'clean': 'clean', 'set': 'approve', 'no_set': 'ignore', 'leave': 'ignore'}   # "Accept the proposals": a proposal as a step-1 answer
STEP1_VERDICTS = ('approve', 'clean', 'ignore')
RECOMMENDS = ('use', 'remake', 'doubt')   # the look at a set
REASON_CHARS = 300
FIRST_MAX = 3      # the sets of the first go
MAKES_MAX = 3      # a set is made at most this many times
STATES = (1, 'making', 'looking', 'rewrite', 2, 'complete')   # what visuals_stage._round_pass gives for a v2 round

# ---------- "what next" (design/211 section 3.9): the answer carries one of these as `then`; the tool prints it and adds nothing ----------

ROUND_POSTED = ('The round is posted for {n} things, {d} of them doubtful. Run `vw visuals page`: the operator answers step 1 there, in one visit; in the chat '
                '(`vw visuals next`) only where the page cannot be shown.')
GO1_MAKING = "Step 1 is recorded. The first {k} sets are being made (about ₹{x}); {r} more wait for the operator's word. Wait: `vw visuals status --wait 900`."
ALL_MAKING = '{k} set(s) are being made (about ₹{x}). Wait: `vw visuals status --wait 900`.'
SETS_LOOK = ('The sets are back. Look at them before the operator does: `vw visuals round --looks` lists them and fetches the pictures. Start `vw-set-look` helpers, '
             'about 5 sets each (with 5 sets or fewer, look yourself); each records its looks: `vw visuals round --looks <file>`. No set is shown to the operator '
             'before its look is recorded.')
SETS_PAGE = 'Every set has its look. Run `vw visuals page`: the operator judges the sets there, in one visit.'
REWRITE_DUE = ("{n} set(s) wait for your rewrite. For each, write the request again from the operator's words, the check and your look: out/round-rewrites.json, "
               'rows {{element_id, prompt}}. Send it: `vw visuals round --rewrite out/round-rewrites.json`. The sets are made then, not before.')
REWRITE_MAKING = '{n} set(s) are being made again (about ₹{x}). Wait: `vw visuals status --wait 900`.'
MERGE_ASK = 'The round is past step 1: nothing was made. {n} thing(s) are back with the operator as open lines. Run `vw visuals page`.'

# ---------- refusals ----------

REC_MISSING = '{eid}: give its proposal (`rec`): footage, clean, set, no_set or leave.'
REC_UNKNOWN = '{eid}: {rec!r} is not a proposal: footage, clean, set, no_set or leave.'
REC_NO_FRAME = '{eid}: the proposal {rec} needs a footage picture with a recorded look; it has none.'
REC_PERSON = '{eid} is a person a picture is made of: every such person gets a set, so the proposal is set.'
REASON_MISSING = '{eid}: give the reason of its proposal in one line, at most {max} characters.'
FIRST_TOO_MANY = '{n} rows are marked `first`: at most {max} sets are made in the first go.'
CLEAN_NO_FRAME = '{eid} has no footage picture: a clean set is made from one. Have a set made, or leave it out.'
SET_NO_LOOK = '{eid}: its set has no recorded look yet: it is not shown or answered before (`vw visuals round --looks`).'
LOOK_SET_UNKNOWN = '{eid}: {set} is not its set now (it was made again, or never made): list the sets to look at again (`vw visuals round --looks`).'
LOOK_PICTURES = '{eid}: every picture of the set needs its look; missing: {missing}.'
LOOK_VERDICT = '{eid}: the verdict of a look is pass, weak or fail, and the recommendation is use, remake or doubt.'
LOOK_SEEN = '{eid}: a look says in one line what was seen, at most {max} characters, and the recommendation gives its reason.'
LOOK_GOLDEN = '{eid}: the picture proposed as the starting picture is not a picture of this set.'
REST_NOT_NOW = 'The other sets are ordered once the first sets are back and have their look: not now.'
REST_NONE = 'No set waits to be ordered.'
REST_CAP = ('The other {n} sets need about ₹{x}, and ₹{spent} is spent of the ₹{cap} limit of this film: none was ordered. Leave some things out, or ask the '
            'owner to set another limit for this film.')
REWRITE_NOT_DUE = '{eid}: no rewrite is asked for it now.'
REWRITE_EMPTY = '{eid}: the rewritten request is empty.'
REWRITE_SAME = '{eid}: the request is the same as before: the same words would buy the same picture. Change it from the operator\'s words, the check and your look.'
MAKES_LIMIT = '{eid}: its set was made {max} times. Use one of these, add your own picture, or leave it out.'
MAKE_NO_QUOTE = "{eid}: making a set is paid: give the operator's words (`--quote`)."
REOPEN_NOT_DUE = '{eid} is not back with the operator: there is nothing to answer for it here.'

# ---------- the fixed text of a set's request (design/211 section 3.6): generic, for every category of film ----------
# It keeps the two ideas of the owner's text of 4 Nov 2026 (visuals_stage.KEPT_PREAMBLE): a reference must be correct, and it shows one
# consistent real thing, never a mix of two. The older text stays in visuals_stage for the sets of an older round.

OPENING = ('I need a photograph-like image that will be used as a reference picture for an AI image model. Because it is a reference, correctness matters more than '
           'anything else: the AI will copy exactly what it sees, including any mistake.')
FROM_WEB = ("This film's own footage shows no picture of the subject, so the picture is made from real photographs: search Google Images for real photographs of the subject "
            'below, study what it really looks like, and build the picture from them. If anything I ask for below contradicts what the real photographs show, the photographs win.')
FROM_FOOTAGE = ("The film's own picture of the subject is attached. It is the truth about this subject: take the thing itself from it, its exact form, colour, material and wear. "
                "Search Google Images for real photographs too, but only for what the film's picture does not show (a side it hides, a detail too small to read). "
                "Where a web photograph differs from the film's picture, the film's picture wins.")
ONE_THING = ('One rule above all: show one real thing, as one real photograph would. Real photographs will show you more than one variant of the same subject. Do not combine them '
             'into a single picture, and do not add details of one variant to another. Choose the variant that appears most often in the photographs, or the one that fits the '
             'description below best, and show only that, exactly as it appears in those photographs, with nothing added. Everything in the picture must belong to one consistent '
             'real thing; if two details could not both be true of it at the same time, one of them does not belong. Mention the other variants you saw only in your notes, not in the picture.')
ONE_THING_FOOTAGE = ("One rule above all: show one real thing, as one real photograph would: the one in the film's picture. Real photographs will show you other variants of the same "
                     'subject. Do not combine them into a single picture, and do not add details of another variant to it. Everything in the picture must belong to one consistent '
                     'real thing; if two details could not both be true of it at the same time, one of them does not belong. Mention the other variants you saw only in your notes, not in the picture.')
SET_LINE = ("This is a set of three pictures of the same one subject, made one per turn: I name each picture's view in its turn; keep every detail the same across the set, each "
            'picture adding the view the others lack. Deliver each picture as one separate output image at full size, never as a collage, grid or split frame, with no borders, numbers '
            'or captions inside any picture. Say what each picture adds.')
FINISH = ('Natural colours, no filters, no stylisation, no illustration. The camera near enough that the subject is readable, the surroundings soft. No text, logos, watermarks, '
          "lettering of a picture library or maker's stamps; nothing in the picture that its sources do not justify.")
NOTES = ('With the pictures, tell me: (1) the one variant you chose and why, and the other variants you saw in the photographs but left out; (2) what you found in the real photographs '
         'and which findings you implemented; (3) anything in my request that the photographs contradicted and what you did instead; (4) the web pages and images you consulted, with URLs.')
NOTES_FOOTAGE = NOTES[:-1] + "; (5) what you took from the film's picture and what from the web."
FRAME_LINE = "Image {k} is the film's own picture of {name} ({view}): take the thing itself from it, its exact form, colour, material and wear."
FRAME_WEAK_LINE = ("Image {k} is the film's own picture of {name} ({view}); it is a weak picture (part of the thing is hidden, small or unsharp): take its form, colour and material "
                   'from it; show it whole and clean.')
SHEET_LINE = 'Image {k} is an approved drawing of {name} ({view}).'
ADDED_LINE = "Added by the film's writer; where this differs from the description, this wins: {words}"
OPERATOR_LINE = "The operator's words: {words}"
PERSON_SET = ('Make a set of three separate pictures of this one person, one per turn: 1, {a}; 2, {b}; 3, {c}. Deliver each as one separate output image at full size, never a collage, '
              'grid or split frame; the same person in every picture in every detail; alone on plain neutral ground, nothing else in the frame; no text, numbers or captions inside any picture.')
KIND_WORDS = {'person': 'a person', 'object': 'an object', 'material': 'a material', 'place': 'a place', 'technique': 'a way of working', 'process': 'a way of working'}
MAY_SHOW = {'object': 'What may be shown: the thing alone. No person and no face in any picture; a hand may hold it only in a picture whose view shows it in use.',
            'place': 'What may be shown: the place itself is the subject of every picture. No person as the subject.',
            'technique': 'What may be shown: the hands and forearms doing it, the tool and the material. No face.'}
MAY_SHOW.update(material=MAY_SHOW['object'], process=MAY_SHOW['technique'])
NO_PLACE = 'a plain real setting that fits the description'

PERSON_FRONT = {'name': 'full length, front', 'ask': 'a full-length front view, standing at ease'}
PERSON_SIDE = {'name': 'full length, side', 'ask': 'a full-length view from the side, standing at ease'}
PERSON_FACE = {'name': 'the face', 'ask': 'a close view of the face'}
THING = [{'name': 'whole and at rest', 'ask': 'the whole of {name}, at rest, filling the frame'},
         {'name': 'as the film uses it', 'ask': 'the same {name} as the film uses it; a hand may hold it, no face'},
         {'name': 'the detail that shows how it is made', 'ask': 'a close view of the detail of the same {name} that shows how it is made'}]
PLACE = [{'name': 'the whole place', 'ask': 'the whole of {name}, seen wide'},
         {'name': 'from the other side', 'ask': 'the same place seen from the other side'},
         {'name': 'its fixed things', 'ask': 'a nearer view of the things that always stand in the same place'}]
WAY = [{'name': 'the action at its key moment', 'ask': 'the action at its key moment: the hands and the tool doing it'},
       {'name': 'the result just after', 'ask': 'the result just after the action, in the same place, on the same material'},
       {'name': 'the tool meeting the material', 'ask': 'a close view of the tool meeting the material'}]
KIND_VIEWS = {'object': THING, 'material': THING, 'place': PLACE, 'technique': WAY, 'process': WAY}
VIEW_STOP = {'the', 'a', 'an', 'of', 'view', 'its', 'it', 'from', 'in', 'on', 'and', 'at', 'as', 'is', 'same', 'seen', 'shown'}

FAIL_TEXT = {'refused': '{who} refused the request.', 'no_picture': '{who} returned no picture.', 'timeout': '{who} did not answer in time.',
             'limit': '{who} is at its limit for now: too many requests.', 'other': '{who} could not make the picture.'}
PROVIDERS = {'gemini': 'Google', 'openai': 'OpenAI'}
UNUSED_REF = ('shot {shot} names {name} ({eid}), which has an approved reference, and none of its pictures is among the pictures this one is made from: '
              'add its reference to the parents, or leave it out on purpose')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _element(plan, eid):
    return next((e for e in plan.get('elements') or [] if e['id'] == eid), None)


def _inr(amount):
    return f'{amount:,.0f}'


def _price(run, n):
    return round(n * V.image_price_inr(run, provider='gemini') * V.SET_MAX, 2)


# ---------- the facts of a thing (parts A, B and C read this) ----------

def thing_facts(plan, session, element):
    """What the plan says of one thing and where the film uses it (design/211 section 3.5): {'id', 'name', 'kind', 'identity', 'real_person',
    'description', 'requirements', 'sizes': [{'part', 'measure', 'value', 'unit', 'status'}], 'views': [three view names], 'signs': [str],
    'shots': [{'gap', 'shot', 'size', 'way'}] (every shot of all_scenes(gap) naming it, film order), 'shots_made' (those not footage),
    'closest' (the tightest size among them, '' when none), 'scene': {'gap', 'scene', 'place'} of its first shot, or None}."""
    eid = element['id']
    seen = [(gap, sc, sh) for gap in plan.get('gaps') or [] for sc in all_scenes(gap) for sh in sc.get('shots') or [] if eid in (sh.get('element_ids') or [])]
    shots = [{'gap': gap.get('gap_id'), 'shot': sh.get('id'), 'size': sh.get('size') or '', 'way': sh.get('visual_type') or ''} for gap, sc, sh in seen]
    sizes = [s['size'] for s in shots if s['size'] in SIZE_ORDER]
    first = seen[0] if seen else None
    return {'id': eid, 'name': element.get('name') or eid, 'kind': element.get('kind'), 'identity': element.get('identity') or 'representative',
            'real_person': element.get('kind') == 'person' and bool(element.get('speaker')),
            'description': str(element.get('description') or ''), 'requirements': str(element.get('requirements') or ''),
            'sizes': [{k: d.get(k) for k in ('part', 'measure', 'value', 'unit', 'status')} for d in element.get('size') or []],
            'views': view_names(element), 'signs': [str(s.get('what') or s.get('sign') or '') for s in element.get('signs_of_use') or []],
            'shots': shots, 'shots_made': sum(1 for s in shots if s['way'] != 'footage'), 'closest': max(sizes, key=SIZE_ORDER.index) if sizes else '',
            'scene': {'gap': first[0].get('gap_id'), 'scene': first[1].get('id'), 'place': str(first[1].get('location_time') or '').strip()} if first else None}


def _reads(view):
    return frozenset(w.rstrip('s') for w in re.findall(r'[a-z]+', str(view).lower()) if w not in VIEW_STOP)


def _same_view(a, b):
    """Two views read the same: the same words, or the words of one all among the other's ("side" and "side view")."""
    a, b = _reads(a), _reads(b)
    return bool(a and b) and (a <= b or b <= a)


def views_for(element, plan):
    """The three views of a thing's set, always three: [{'name': short label, 'ask': the sentence of that turn}]. The plan's required_views
    first (two that read the same are one), then the kind's own, never one already present. A person's pictures 1 (full length, front)
    and 3 (the face) are fixed."""
    name = element.get('name') or element.get('id') or 'the subject'
    asked = []
    for v in element.get('required_views') or []:
        v = ' '.join(str(v or '').split())
        if v and not any(_same_view(v, x) for x in asked):
            asked.append(v)
    if element.get('kind') == 'person':   # later steps read pictures 1 and 3 by their position: the plan drives picture 2 only
        mine = next((v for v in asked if not _same_view(v, PERSON_FRONT['name']) and not _same_view(v, PERSON_FACE['name'])), None)
        return [dict(PERSON_FRONT), {'name': mine, 'ask': f'{mine}, the same person'} if mine else dict(PERSON_SIDE), dict(PERSON_FACE)]
    out = [{'name': v, 'ask': f'this view of the same {name}: {v}'} for v in asked[:V.SET_MAX]]
    for own in KIND_VIEWS.get(element.get('kind')) or THING:
        if len(out) < V.SET_MAX and not any(_same_view(own['name'], x['name']) for x in out):
            out.append({'name': own['name'], 'ask': own['ask'].format(name=name)})
    return out


def view_names(element):
    """The three view names of a thing, as `views_for` names them: for the helpers' brief and the labels of footage frames."""
    return [v['name'] for v in views_for(element, None)]


# ---------- the request and the checks ----------

def inputs_of(session, element):
    """The pictures a set is made from, in the order they are sent: the thing's approved footage frames that have a look (up to three, in view
    order; a frame the operator marked "not this" is rejected, so it is not among them), then its approved drawings. A person: their photo,
    only with the recorded permission. Returns ([{'ref', 'role', 'view'}], the ids of the weak frames)."""
    eid, refs = element['id'], session.get('references') or {}
    if element.get('kind') == 'person':
        photo = V.likeness_photo(session, eid)
        return ([{'ref': photo, 'role': 'photo', 'view': ''}] if photo else []), set()
    frames = [f for f in ref_find.frames_of(session, eid) if (refs.get(f['ref']) or {}).get('status') == 'approved'][:3]
    from . import drawings
    return ([{'ref': f['ref'], 'role': 'footage', 'view': f.get('view') or ''} for f in frames]
            + [{'ref': s['id'], 'role': 'drawing', 'view': s['view']} for s in drawings.approved_sheets(session, eid)]), {f['ref'] for f in frames if f.get('weak')}


def _sizes(element):
    """The plan's sizes with their status: confirmed and measured as numbers, proposed as "about …", unknown left out."""
    out = []
    for d in element.get('size') or []:
        if d.get('value') is None or d.get('status') == 'unknown':
            continue
        about = 'about ' if d.get('status') == 'proposed' else ''
        out.append(f"{d.get('part', '')} {d.get('measure', '')} {about}{d['value']:g} {d.get('unit') or ''}".strip())
    return out


def _drawn_facts(session, eid):
    from . import drawings
    row = (session.get('drawings') or {}).get(eid) or {}
    return [drawings._fact_line(f) for f in row.get('facts') or []] if row.get('status') == 'approved' else []


def _place(element, facts):
    """Where the thing is shown: the scene of its own first shot; a place's own description for a place; never the film's first scene."""
    if element.get('kind') == 'place':
        return facts['description'].strip().rstrip('.') or facts['name']
    return ((facts['scene'] or {}).get('place') or '').rstrip('.')


def fp(plan, session, element):
    """What a set was made from, as one string: the plan fields of the thing (ref_find.fingerprint) and the place used. A set whose `made.fp`
    differs from this is marked changed."""
    return ref_find.fingerprint(element) + '|' + _place(element, thing_facts(plan, session, element))


def _lines(element, facts, inputs):
    """The check lines of a v2 set (design/211 section 3.7), all must. `pictures` on a line: the pictures of the set it is asked of."""
    kind = element.get('kind')
    line = lambda check, when, **more: {'check': check, 'weight': 'must', 'pass_when': when, **more}
    out = [line('the view', 'the picture shows what its turn asked'),
           line('same as picture 1', 'the same thing as picture 1 of the set, sent as a reference, in every detail both show', pictures=[2, 3])]
    if any(i['role'] == 'footage' for i in inputs):
        out.append(line('matches the footage picture', "it has the form, colour and material of the film's footage picture sent as a reference"))
    out.append(line('matches the description', 'it agrees with the description of the plan: ' + (facts['description'].strip() or facts['requirements'].strip())))
    return out + [line(*x) for x in _kind_lines(kind)]


def _kind_lines(kind):
    out = []
    if kind in ('object', 'material', 'technique', 'process'):
        out.append(('one thing only', 'everything belongs to one consistent real thing; nothing of a second variant is mixed in'))
    if kind != 'person':
        out.append(('nothing floats', 'nothing floats or stands where it could not really stand'))
    out.append(('no text', 'no caption, number, label, logo or watermark anywhere in the picture'))
    if kind in ('object', 'material'):
        out.append(('no person', "no person and no face; a hand only where the picture's view shows the thing in use"))
    if kind == 'place':
        out.append(('the place is the subject', 'the picture shows the place as its view asks, not one object of it'))
    if kind in ('technique', 'process'):
        out.append(('the action is shown', 'the hands and the tool doing it, or its result where the view asks for the result; no face'))
    if kind == 'person':
        out += [(l['check'], l['pass_when']) for l in V.PERSON_SET_LINES[:2]]   # one person, plain ground: as before
    return out


def set_request(plan, run, session, element, row):
    """The whole request of one set of a v2 round (design/211 section 3.6), by kind: {'prompt', 'views': [{'name', 'ask'}], 'inputs':
    [{'ref', 'role': 'footage'|'drawing'|'photo', 'view'}], 'search': bool, 'lines': [{'check', 'weight', 'pass_when'}], 'parts': {'kind',
    'subject', 'description', 'requirements', 'sizes', 'material', 'signs', 'place', 'look', 'category', 'added', 'operator', 'views',
    'inputs', 'source': 'footage'|'web'|'words'}}. The server places the plan's words; `added` is the row's `prompt`; `operator` the latest of
    its `operator_words`. `source` is 'words' for a person made from the description alone (no picture, no search). `row['drawn_how']`, when
    given, is the paragraph that tells how to read the drawings sent (visuals_stage.generate_image reads it from the stored drawing set)."""
    row = row or {}
    eid, kind = element['id'], element.get('kind')
    facts = thing_facts(plan, session, element)
    name, views = facts['name'], views_for(element, plan)
    inputs, weak = inputs_of(session, element)
    footage = [i for i in inputs if i['role'] == 'footage']
    sheets = [i for i in inputs if i['role'] == 'drawing']
    added = ' '.join(str(row.get('prompt') or '').split())
    operator = ' '.join(str((row.get('operator_words') or [''])[-1] or '').split())
    place = _place(element, facts)
    look = str((plan.get('foundation') or {}).get('appearance') or '').strip().rstrip('.') or 'as the footage'
    try:
        category = V.category_of(run)
    except Problem:
        category = ''
    sizes = [] if element.get('material_spec') else _sizes(element)   # the material spec carries its own
    material = ' '.join(V.material_sentence(m) for m in V.materials_of(plan, eid) if V.material_approved(session, m))
    signs = [] if kind != 'place' or str(element.get('staged_clean') or '').strip() else [s for s in facts['signs'] if s][:2]
    drawn = _drawn_facts(session, eid) if sheets else []
    words = lambda label, text: [f'{label}: {text}'] if str(text).strip() else []
    told = (words('Sizes', '; '.join(sizes) + '.') if sizes else []) + ([material] if material else []) + (words('Signs of use', '; '.join(signs) + '.') if signs else []) \
        + ([ADDED_LINE.format(words=added)] if added else []) + ([OPERATOR_LINE.format(words=operator)] if operator else [])
    if kind == 'person':
        others = [e for e in plan.get('elements') or [] if e.get('kind') == 'person' and e['id'] != eid]
        outfits = [o for o in dict.fromkeys(str((sc.get('outfit') or {}).get(eid) or '').strip() for gap in plan.get('gaps') or [] for sc in all_scenes(gap)) if o]
        text = [f'Character sheet of {name} ({eid}), a person in this film.', *words('Who they are', facts['requirements']), *words('Fixed look', facts['description']),
                *(['Garments: ' + '; '.join(outfits) + '.'] if outfits else []), f"Where the film shows them: {place or NO_PLACE}; the film's look: {look}.", *told,
                *[f"Not {o['id']} ({o.get('name') or o['id']}): {str(o.get('description') or '').strip().rstrip('.')}." for o in others],
                *([V.LIKENESS_PHOTO_LINE] if inputs else []), PERSON_SET.format(a=views[0]['ask'], b=views[1]['ask'], c=views[2]['ask'])]
        prompt, source = '\n'.join(text), 'footage' if inputs else 'words'
    else:
        pictures = [(FRAME_WEAK_LINE if i['ref'] in weak else FRAME_LINE).format(k=k, name=name, view=i['view'] or 'as filmed') for k, i in enumerate(footage, 1)]
        if sheets:
            pictures += [row.get('drawn_how') or '\n'.join(SHEET_LINE.format(k=k, name=name, view=i['view']) for k, i in enumerate(sheets, len(footage) + 1)), V.KEPT_DRAWN_LINE]
            pictures += ['What must be true:\n' + '\n'.join(f'- {f}' for f in drawn)] if drawn else []
        setting = (f"Setting: the place itself, as described, in its own light and time{': ' + facts['scene']['place'] if (facts['scene'] or {}).get('place') else ''}." if kind == 'place' else
                   f"Setting: {place or NO_PLACE}{', as a soft hint at the edges' if kind in ('object', 'material') else ''}; the light of that place and time.")
        subject = [f'The subject: {name}, {KIND_WORDS.get(kind, "a thing")} in this film' + (f' ({category})' if category else '') + '.',
                   *words("Its description, from the film's plan", facts['description']), *words('What it must meet', facts['requirements']), *told]
        text = [OPENING + ' ' + (FROM_FOOTAGE if footage else FROM_WEB) + '\n' + (ONE_THING_FOOTAGE if footage else ONE_THING),
                SET_LINE + ' The three views: ' + '; '.join(f"{n}, {v['name']}" for n, v in enumerate(views, 1)) + '.', '\n'.join(subject), *pictures,
                MAY_SHOW.get(kind, MAY_SHOW['object']) + '\n' + setting + f" The film's look: {look}.\n" + FINISH, NOTES_FOOTAGE if footage else NOTES]
        prompt, source = '\n\n'.join(text), 'footage' if footage else 'web'
    lines = _lines(element, facts, inputs)
    if drawn or sheets:   # the facts of the drawing set are checked on the picture, and it must be a photograph
        lines += [{'check': 'drawn fact: ' + f, 'weight': 'must', 'pass_when': f'the picture shows it as the approved drawings do: {f}'} for f in drawn] + [V.DRAWN_LOOK_LINE]
    parts = {'kind': kind, 'subject': name, 'description': facts['description'], 'requirements': facts['requirements'], 'sizes': sizes, 'material': material, 'signs': signs,
             'place': place, 'look': look, 'category': category, 'added': added, 'operator': operator, 'views': [v['name'] for v in views], 'inputs': inputs, 'source': source}
    return {'prompt': prompt, 'views': views, 'inputs': inputs, 'search': kind != 'person', 'lines': lines, 'parts': parts}


def check_summary(session, ref):
    """One picture's check for the page: {'state': 'pass'|'fail'|'none', 'failed': [{'check', 'seen'}], 'error': str or None}. `ref`: the
    picture's reference id (or its row). 'none': the check did not run (no key, a model error, or not back yet)."""
    row = ref if isinstance(ref, dict) else (session.get('references') or {}).get(ref) or {}
    check = row.get('check')
    if not check:
        return {'state': 'none', 'failed': [], 'error': None}
    failed = list(check.get('must_failed') or [])
    failed += [c for c in check.get('code') or [] if c.get('pass') is False and c.get('check') not in {f.get('check') for f in failed}]
    state = 'fail' if failed else 'none' if check.get('error') or not check.get('lines') else 'pass'
    return {'state': state, 'failed': [{'check': f.get('check'), 'seen': f.get('seen') or ''} for f in failed], 'error': check.get('error')}


def fail_of(ref):
    """Why the picture job of a set failed, from the job's own record on its reference: {'cause', 'model', 'text'}; the text names the
    provider and the model that were really called."""
    gen, e, f = ref.get('generation') or {}, str(ref.get('error') or '').lower(), ref.get('failure') or {}
    cause = ('no_picture' if f.get('failure') == 'no_image' or 'returned no picture' in e else
             'limit' if f.get('http_status') == 429 or 'http 429' in e else
             'timeout' if 'timeout' in e or 'timed out' in e or 'in time' in e else
             'refused' if f.get('failure') in ('moderation_blocked', 'image_generation_user_error') or 'refused' in e or 'rejected the request' in e else 'other')
    who = f"{PROVIDERS.get(gen.get('provider'), 'The picture service')}'s image model {gen.get('model') or ''}".strip()
    return {'cause': cause, 'model': gen.get('model'), 'text': FAIL_TEXT[cause].format(who=who)}


def _pictures(session, eid, row, statuses=('candidate', 'approved')):
    return sorted(V._set_rows(session, eid, row.get('set'), statuses), key=lambda r: int(r.get('set_n') or 1)) if row.get('set') else []


def set_facts(session, plan, eid, row):
    """What the page and the chat show of one made (or failed) set (design/211 section 3.7): {'pictures': [{'ref', 'n', 'view', 'check':
    check_summary, 'look': look or None}], 'inputs': [{'ref', 'role', 'view'}], 'from': 'footage'|'web'|'words', 'notes', 'sources': [{'url',
    'title'}], 'partial': {'made', 'asked', 'missing'} or None, 'rec': {'do', 'golden', 'reason'} or None, 'makes', 'makes_left',
    'asked': the operator's words of the last remake or None, 'history': [{'n', 'set', 'added', 'operator'}], 'changed': bool,
    'fail': {'cause', 'model', 'text'} or None}. The pictures are those of the set the row holds now, candidate or approved."""
    element = _element(plan, eid) or {'id': eid}
    pics = _pictures(session, eid, row)
    parts, look = row.get('parts') or {}, row.get('set_look') or {}
    names = list(parts.get('views') or view_names(element))
    made = row.get('made') or {}
    failed = _pictures(session, eid, row, ('failed',))
    fail = None
    if not pics and not _pictures(session, eid, row, ('generating',)):
        if failed:
            fail = fail_of(failed[-1])
        elif row.get('error'):   # refused by the server before any call: its own sentence, no provider to name
            fail = {'cause': 'limit' if "on this film's visuals" in str(row['error']) else 'other', 'model': None, 'text': V._plain(row['error'])}
    history = list(row.get('history') or [])
    return {'pictures': [{'ref': p['id'], 'n': int(p.get('set_n') or 1), 'view': p.get('view') or (names[int(p.get('set_n') or 1) - 1] if int(p.get('set_n') or 1) <= len(names) else ''),
                          'check': check_summary(session, p), 'look': p.get('look')} for p in pics],
            'inputs': list(parts.get('inputs') or []), 'from': parts.get('source') or 'web',
            'notes': next((p.get('notes') for p in pics if p.get('notes')), '') or '', 'sources': next((p.get('sources') for p in pics if p.get('sources')), []) or [],
            'partial': {'made': len(pics), 'asked': len(names), 'missing': names[len(pics):]} if pics and len(pics) < len(names) else None,
            'rec': {'do': look.get('recommend'), 'golden': look.get('golden'), 'reason': look.get('reason') or ''} if pics and look.get('set') == row.get('set') else None,
            'makes': int(row.get('round') or 0), 'makes_left': max(0, MAKES_MAX - int(row.get('round') or 0)),
            'asked': (history[-1].get('operator') or None) if history and pics else None,
            'history': [{k: h.get(k) for k in ('n', 'set', 'added', 'operator')} for h in history],
            'changed': bool(pics) and bool(made) and ((made.get('fp') is not None and made['fp'] != fp(plan, session, element)) or V._spec_changed(session, plan, eid, row)),
            'fail': fail}


def unused_refs(session, plan, shot, parents):
    """Gap 23, in part: a still whose shot names a thing with an approved reference that is not among the pictures it is made from: one
    warning per such thing."""
    have = {p.get('element_id') for p in parents if p}
    out = []
    for eid in shot.get('element_ids') or []:
        e = _element(plan, eid)
        if not e or e.get('kind') in ('graphic', 'animal') or eid in have:
            continue
        if V.golden_of(session, eid) or any(r.get('element_id') == eid and r.get('status') == 'approved' and r.get('kind') in ('sheet', 'frame', 'supplied') for r in session['references'].values()):
            out.append(UNUSED_REF.format(shot=shot.get('id'), name=e.get('name') or eid, eid=eid))
    return out


# ---------- the states of a v2 round (visuals_stage._round_pass) ----------

def looked(session, eid, row):
    """A set's look is complete: the row's `set_look` is of the set it holds now and each of its pictures has a look."""
    return (row.get('set_look') or {}).get('set') == row.get('set') and all(p.get('look') for p in _pictures(session, eid, row, ('candidate',)))


def _sets(rd):
    return [(eid, r) for eid, r in rd['elements'].items() if r.get('set') and not r.get('ignored') and not r.get('from_footage')]


def rest_of(rd):
    """The things whose set waits for the second go; one the operator set aside since is not among them."""
    return [eid for eid in rd.get('rest') or [] if eid in rd['elements'] and not rd['elements'][eid].get('ignored')]


def state(session, rd):
    """design/211 section 3.8: 1 (step 1 is open), 'making' (a set is being made), 'looking' (a made set has no complete look: Claude's
    turn), 'rewrite' (a request waits for Claude's rewrite), 2 (the operator's turn), 'complete'. The stored `pass` keeps its four values."""
    if rd.get('pass') == 1:
        return 1
    sets = _sets(rd)
    if any(V._set_rows(session, eid, r['set'], ('generating',)) for eid, r in sets):
        return 'making'
    if any(V._set_rows(session, eid, r['set']) and not looked(session, eid, r) for eid, r in sets):
        return 'looking'
    if any(r.get('rewrite_due') and not r.get('ignored') for r in rd['elements'].values()):
        return 'rewrite'
    return 'complete' if rd.get('pass') == 'complete' else 2


def then_of(session):
    """The "what next" of a v2 round past step 1, by its state; None while sets are made, at step 1 and when it is complete."""
    rd = session['round']
    at = state(session, rd)
    if at == 'looking':
        return SETS_LOOK
    if at == 'rewrite':
        return REWRITE_DUE.format(n=sum(1 for r in rd['elements'].values() if r.get('rewrite_due') and not r.get('ignored')))
    return SETS_PAGE if at == 2 and any(V._set_rows(session, eid, r['set']) for eid, r in _sets(rd)) else None


# ---------- the round file: a new round, and one sent again ----------

def _row_faults(session, plan, kinds, made, row, conn_budget):
    """One row of the round file read: (the fields to store, its faults). Every fault of the row is named."""
    eid = (row or {}).get('element_id')
    if eid not in kinds:
        return None, [f'Unknown element {eid}.']
    if kinds[eid] == 'graphic':
        return None, [f'{eid} is a graphic: drawn from the plan, never referenced.']
    if kinds[eid] == 'animal':
        return None, [V.ANIMAL_NO_SHEET.format(eid=eid)]
    faults, rec, reason = [], (row or {}).get('rec'), ' '.join(str((row or {}).get('reason') or '').split())
    if not rec:
        faults.append(REC_MISSING.format(eid=eid))
    elif rec not in RECS:
        faults.append(REC_UNKNOWN.format(eid=eid, rec=rec))
    if not reason or len(reason) > REASON_CHARS:
        faults.append(REASON_MISSING.format(eid=eid, max=REASON_CHARS))
    try:
        frames = list(ref_find.round_frames(session, plan, eid, list((row or {}).get('frames') or [])))
        if rec in ('footage', 'clean') and not frames:
            faults.append(REC_NO_FRAME.format(eid=eid, rec=rec))
    except ValueError as exc:   # FRAME_NO_LOOK, NOT_SEARCHED: part A's refusals, named with the others
        frames = []
        faults.append(str(exc))
    if kinds[eid] == 'person' and eid in made and rec in RECS and rec != 'set':
        faults.append(REC_PERSON.format(eid=eid))
    found = (session.get('found') or {}).get(eid) or {}
    element = _element(plan, eid)
    doubt = bool((row or {}).get('doubt') or any((session['references'].get(f) or {}).get('weak') for f in frames)
                 or (found.get('result') == 'none' and found.get('closest')) or found.get('result') == 'not_searched'
                 or (element.get('identity') == 'exact' and rec not in ('footage', 'clean'))
                 or (rec in ('set', 'clean') and V.set_cause(session, plan, eid, conn_budget)))
    return {'frames': frames, 'prompt': ' '.join(str((row or {}).get('prompt') or '').split()), 'rec': rec, 'reason': reason, 'doubt': doubt, 'first': bool((row or {}).get('first'))}, faults


def _made_ids(plan):
    return {eid for gap in plan['gaps'] for sc in all_scenes(gap) for sh in sc['shots'] if sh.get('visual_type') != 'footage' for eid in sh.get('element_ids') or []}


def _budget(conn, run, session):
    return V._set_budget(run, session, V.visuals_spend(conn, run)) if conn is not None else None


def start(conn, store, user, run, session, plan, kinds, elements):
    """`visuals_stage.round_start` for a film with no round, or a v2 round still at step 1: each row is a proposal with its reason; the frames
    are those that have a look (ref_find.round_frames); every faulty row is named in one refusal. Returns {'pass': 1, 'elements', 'kept',
    'v': 2, 'doubtful', 'then': ROUND_POSTED}."""
    made, budget, rows, faults = _made_ids(plan), _budget(conn, run, session), {}, []
    for row in elements:
        fields, bad = _row_faults(session, plan, kinds, made, row, budget)
        faults += bad
        if fields:
            rows[row['element_id']] = {'keywords': '', 'verdict': None, 'search_id': None, 'error': None, 'corrections': [], 'set': None, 'round': 0, 'operator_words': [], 'history': [], **fields}
    firsts = [eid for eid, r in rows.items() if r['first']]
    if len(firsts) > FIRST_MAX:
        faults.append(FIRST_TOO_MANY.format(n=len(firsts), max=FIRST_MAX))
    missing = [eid for eid, k in kinds.items() if k == 'person' and eid not in rows and eid in made]
    if missing:
        faults.append(f"Every person a picture is made of gets a set: add a row for {', '.join(missing)} (element_id, rec set, reason).")
    V.need(not faults, '\n'.join(faults))
    session['round'] = {'pass': 1, 'at': _now(), 'by': user['id'], 'elements': rows, 'quote': None, 'kept': True, 'v': 2, 'go': 1, 'rest': []}
    V.save_session(store, run, session)
    doubtful = sum(1 for r in rows.values() if r['doubt'])
    return {'pass': 1, 'elements': len(rows), 'kept': True, 'v': 2, 'doubtful': doubtful, 'then': ROUND_POSTED.format(n=len(rows), d=doubtful)}


def merge(conn, store, user, run, session, plan, kinds, elements):
    """`visuals_stage._round_merge` for a v2 round: the round file sent again after step 1 orders nothing. A thing new in the plan, or one the
    operator left out, goes back to the operator as an open line (`reopened`); a thing whose set was not made gets its new words and its
    error cleared, and stays "not made" with its paid button; a thing that has its set, or its footage picture, is left as it is."""
    rd, made, budget = session['round'], _made_ids(plan), _budget(conn, run, session)
    faults, reopened, merged, left = [], [], [], []
    for row in elements:
        eid = (row or {}).get('element_id')
        cur = rd['elements'].get(eid)
        if cur and not cur.get('ignored') and (cur.get('from_footage') or cur.get('rewrite_due') or V._set_rows(session, eid, cur.get('set'), ('generating', 'candidate', 'approved'))):
            left.append(eid)
            continue
        fields, bad = _row_faults(session, plan, kinds, made, row, budget)
        faults += bad
        if not fields:
            continue
        if cur is None:
            rd['elements'][eid] = {'keywords': '', 'verdict': None, 'search_id': None, 'error': None, 'corrections': [], 'set': None, 'round': 0, 'operator_words': [], 'history': [],
                                   **fields, 'first': False, 'reopened': 'new'}
            reopened.append(eid)
        elif cur.get('ignored'):
            cur.update({**fields, 'first': False, 'reopened': 'left_out', 'error': None})
            reopened.append(eid)
        else:
            cur.update({**fields, 'first': bool(cur.get('first')), 'error': None})
            merged.append(eid)
    V.need(not faults, '\n'.join(faults))
    if reopened and rd.get('pass') == 'complete':
        rd['pass'] = 2   # an open line: the round is with the operator again
    V.save_session(store, run, session)
    return {'pass': state(session, rd), 'kept': True, 'v': 2, 'merged': merged, 'reopened': reopened, 'left': left, 'queued': [], 'errors': {}, 'elements': len(rd['elements']), 'cost_inr': 0,
            'then': MERGE_ASK.format(n=len(reopened))}


# ---------- step 1 recorded: the first go ----------

def step1_frames(session, eid, row):
    """The thing's footage frames now: those with a look, in view order (a frame the operator marked "not this" is rejected and gone; one
    kept in its place, or the closest picture taken with "that is it", is among them)."""
    row['frames'] = [f['ref'] for f in ref_find.frames_of(session, eid)]
    return row['frames']


def first_go(plan, rd, todo):
    """Which sets are ordered at "Done" of step 1 and which wait: (first, rest). The rows marked `first` that still ask for a set; with fewer
    than three, the first row of each other kind in the plan's order, then the next in the plan's order, up to three. Three sets or fewer in
    all: no second go."""
    if len(todo) <= FIRST_MAX:
        return list(todo), []
    order = [e['id'] for e in plan['elements'] if e['id'] in todo]
    kinds = {e['id']: e.get('kind') for e in plan['elements']}
    first = [eid for eid in order if rd['elements'][eid].get('first')][:FIRST_MAX]
    for by_kind in (True, False):
        for eid in order:
            if len(first) < FIRST_MAX and eid not in first and (not by_kind or kinds[eid] not in {kinds[x] for x in first}):
                first.append(eid)
    first = [eid for eid in order if eid in first]
    return first, [eid for eid in order if eid not in first]


def done_then(run, queued, rest):
    """The "what next" after step 1 is recorded; None when no set was ordered and none waits."""
    if rest:
        return GO1_MAKING.format(k=len(queued), x=_inr(_price(run, len(queued))), r=len(rest))
    return ALL_MAKING.format(k=len(queued), x=_inr(_price(run, len(queued)))) if queued else None


# ---------- the looks at a made set ----------

def _due(session, rd):
    return [(eid, r) for eid, r in _sets(rd) if V._set_rows(session, eid, r['set']) and not looked(session, eid, r)]


def looks_due(store, run, outputs):
    """`GET /api/runs/{run_id}/visuals/round/looks`: the made sets with no complete look: {'sets': [{'element_id', 'name', 'set', 'facts':
    thing_facts, 'request', 'inputs': [{'ref', 'role', 'view', 'key'}], 'pictures': [{'ref', 'n', 'view', 'key', 'check'}], 'notes'}], 'then'}.
    The picture keys are the 1600 px copies (page_flow.sized)."""
    session = V.session_of(store, run, outputs)
    rd = session.get('round')
    if not V.round_v2(session):
        return {'sets': [], 'then': None}
    plan = V.guarded(lambda: V.current_plan(store, session))
    from .page_flow import sized

    def big(ref_id):
        key = (session['references'].get(ref_id) or {}).get('key')
        try:
            return sized(store, key, 'zoom') if key else None
        except Exception:   # a picture that cannot be shrunk is read at its full size
            return key
    sets = []
    for eid, row in _due(session, rd):
        element = _element(plan, eid) or {'id': eid}
        facts = set_facts(session, plan, eid, row)
        pics = _pictures(session, eid, row, ('candidate',))
        sets.append({'element_id': eid, 'name': element.get('name') or eid, 'set': row['set'], 'facts': thing_facts(plan, session, element),
                     'request': (pics[0].get('generation') or {}).get('prompt') or '', 'inputs': [{**i, 'key': big(i['ref'])} for i in facts['inputs']],
                     'pictures': [{'ref': p['ref'], 'n': p['n'], 'view': p['view'], 'key': big(p['ref']), 'check': p['check']} for p in facts['pictures']],
                     'notes': facts['notes']})
    return {'sets': sets, 'then': SETS_LOOK if sets else then_of(session)}


def round_looks(store, user, run, outputs, sets, by):
    """`POST /api/runs/{run_id}/visuals/round/looks`: sets = [{'element_id', 'set', 'recommend', 'golden', 'reason', 'pictures': [{'ref',
    'view', 'verdict', 'seen'}]}]. Each picture gets its `look`; the row its `set_look`. Refuses LOOK_SET_UNKNOWN, LOOK_PICTURES,
    LOOK_VERDICT, LOOK_SEEN, LOOK_GOLDEN. Returns {'recorded': [eid], 'refused': {eid: message}, 'left': [eid], 'then'}."""
    session = V.session_of(store, run, outputs)
    rd = session.get('round')
    V.need(V.round_v2(session) and rd.get('pass') != 1, 'No set of the reference round waits for a look.')
    who, recorded, refused = by if by in ref_find.WHO else 'assistant', [], {}
    one = lambda text: ' '.join(str(text or '').split())
    for s in sets or []:
        eid = (s or {}).get('element_id')
        row = rd['elements'].get(eid) or {}
        pics = _pictures(session, eid, row, ('candidate',)) if row.get('set') and row.get('set') == s.get('set') else []
        looks = {p.get('ref'): p for p in s.get('pictures') or [] if isinstance(p, dict)}
        missing = [str(p.get('view') or p['id']) for p in pics if p['id'] not in looks]
        mine = [looks[p['id']] for p in pics if p['id'] in looks]
        if not pics:
            refused[eid] = LOOK_SET_UNKNOWN.format(eid=eid, set=s.get('set'))
        elif missing:
            refused[eid] = LOOK_PICTURES.format(eid=eid, missing=', '.join(missing))
        elif s.get('recommend') not in RECOMMENDS or any(l.get('verdict') not in ref_find.VERDICTS for l in mine):
            refused[eid] = LOOK_VERDICT.format(eid=eid)
        elif not one(s.get('reason')) or len(one(s.get('reason'))) > ref_find.SEEN_CHARS or any(not one(l.get('seen')) or len(one(l.get('seen'))) > ref_find.SEEN_CHARS for l in mine):
            refused[eid] = LOOK_SEEN.format(eid=eid, max=ref_find.SEEN_CHARS)
        elif s.get('golden') and s['golden'] not in {p['id'] for p in pics}:
            refused[eid] = LOOK_GOLDEN.format(eid=eid)
        else:
            at = _now()
            for p in pics:
                l = looks[p['id']]
                p['look'] = {'who': who, 'at': at, 'view': one(l.get('view')) or p.get('view') or '', 'verdict': l['verdict'], 'seen': one(l['seen']), 'trial': None, 'ref': p['id']}
            row['set_look'] = {'who': who, 'at': at, 'set': row['set'], 'recommend': s['recommend'], 'golden': s.get('golden') or None, 'reason': one(s['reason'])}
            recorded.append(eid)
    V.save_session(store, run, session)
    left = [eid for eid, _ in _due(session, rd)]
    return {'recorded': recorded, 'refused': refused, 'left': left, 'then': SETS_LOOK if left else then_of(session)}


# ---------- the second go, the rewrite, a thing back after a second send ----------

def _order(conn, store, user, run, outputs, eids):
    """The sets ordered through visuals_stage._queue_sets (its gates, the limit, the log); the round is 'making' when one was."""
    queued, errors = V._queue_sets(conn, store, user, run, outputs, eids)
    session = V.session_of(store, run, outputs)
    if queued:
        session['round']['pass'] = 'making'
        V.save_session(store, run, session)
    return session, queued, errors


def round_rest(conn, store, user, run, outputs, quote):
    """The second go, on the operator's word: every set of `round['rest']` ordered, or none (REST_CAP). Refuses REST_NOT_NOW, REST_NONE.
    Returns {'pass', 'queued': [eid], 'errors': {eid: message}, 'cost_inr', 'then': ALL_MAKING}. It is taken while the first sets are with
    the operator, also when one of them waits for its rewrite: the operator answers both in one visit."""
    session = V.session_of(store, run, outputs)
    rd = session.get('round')
    V.need(V.round_v2(session) and rd.get('go', 1) == 1 and state(session, rd) in (2, 'rewrite'), REST_NOT_NOW)
    rest = rest_of(rd)
    V.need(rest, REST_NONE)
    spent, cap, one = V._set_budget(run, session, V.visuals_spend(conn, run))
    V.need(spent + one * len(rest) <= cap + 1e-9, REST_CAP.format(n=len(rest), x=_inr(one * len(rest)), spent=_inr(spent), cap=_inr(cap)))
    rd.update(go=2, rest=[], rest_word={'by': user['id'], 'at': _now(), 'quote': V.said(quote, 'Make the other sets', user)})
    V.save_session(store, run, session)
    session, queued, errors = _order(conn, store, user, run, outputs, rest)
    return {'pass': V._round_pass(session, session['round']), 'queued': queued, 'errors': errors, 'cost_inr': _price(run, len(queued)),
            'then': ALL_MAKING.format(k=len(queued), x=_inr(_price(run, len(queued))))}


def round_rewrite(conn, store, user, run, outputs, rows):
    """Claude's rewrite of the requests the operator sent back: rows = [{'element_id', 'prompt'}]. The earlier request goes to the row's
    `history`, the new one is stored, `rewrite_due` is cleared and the set is ordered: the operator's "No" or "Correct it" was the word for
    the spend. Refuses REWRITE_NOT_DUE, REWRITE_EMPTY, REWRITE_SAME: every faulty row is named and nothing is ordered. Returns {'pass',
    'queued': [eid], 'errors': {eid: message}, 'cost_inr', 'then': REWRITE_MAKING}."""
    session = V.session_of(store, run, outputs)
    rd = session.get('round') or {}
    V.need(V.round_v2(session), 'No reference round waits for a rewrite.')
    faults, new = [], {}
    for r in rows or []:
        eid = (r or {}).get('element_id')
        row = (rd.get('elements') or {}).get(eid) or {}
        prompt = ' '.join(str((r or {}).get('prompt') or '').split())
        if not row.get('rewrite_due') or row.get('ignored'):
            faults.append(REWRITE_NOT_DUE.format(eid=eid))
        elif not prompt:
            faults.append(REWRITE_EMPTY.format(eid=eid))
        elif prompt.lower() == str(row.get('prompt') or '').lower():
            faults.append(REWRITE_SAME.format(eid=eid))
        else:
            new[eid] = prompt
    V.need(not faults and new, '\n'.join(faults) or 'Give the rewritten requests: rows {element_id, prompt}.')
    for eid, prompt in new.items():
        row = rd['elements'][eid]
        due = row.pop('rewrite_due')
        row.setdefault('history', []).append({'n': int(row.get('round') or 0), 'set': due.get('set'), 'added': row.get('prompt') or '', 'operator': due.get('words') or '', 'at': _now()})
        row.update(prompt=prompt, error=None)
    V.save_session(store, run, session)
    session, queued, errors = _order(conn, store, user, run, outputs, list(new))
    return {'pass': V._round_pass(session, session['round']), 'queued': queued, 'errors': errors, 'cost_inr': _price(run, len(queued)),
            'then': REWRITE_MAKING.format(n=len(queued), x=_inr(_price(run, len(queued))))}


def round_reopen(conn, store, user, run, outputs, eid, verdict, words, quote):
    """The operator's answer to a thing that came back after a second send of the round file (`reopened`), with the meaning of step 1:
    'approve' takes its footage picture as the reference where it has one (free), else orders its set (paid, their word); 'clean' orders a
    set made from its footage picture (CLEAN_NO_FRAME without one); 'ignore' leaves it out. Returns {'element_id', 'queued': bool, 'pass',
    'cost_inr', 'then'}."""
    session = V.session_of(store, run, outputs)
    rd = session.get('round') or {}
    row = (rd.get('elements') or {}).get(eid) or {}
    V.need(V.round_v2(session) and row.get('reopened'), REOPEN_NOT_DUE.format(eid=eid))
    V.need(verdict in STEP1_VERDICTS, f'{eid}: the answer is approve, clean or ignore.')
    plan = V.guarded(lambda: V.current_plan(store, session))
    frames = step1_frames(session, eid, row)
    V.need(verdict != 'clean' or frames, CLEAN_NO_FRAME.format(eid=eid))
    stamp = {'by': user['id'], 'at': _now(), 'quote': V.said(quote, 'Answered on the references', user)}
    row.pop('reopened')
    row.pop('aside', None)
    row.update(verdict=verdict, ignored=verdict == 'ignore', clean=verdict == 'clean', error=None, answered=stamp)
    if ' '.join(str(words or '').split()):
        row.setdefault('operator_words', []).append(' '.join(str(words).split()))
    queued = []
    if verdict != 'ignore':
        for fid in frames:
            r = session['references'][fid]
            if r.get('status') == 'candidate':
                r.update(status='approved', approval={**stamp, 'sha256': r.get('sha256')})
        if eid not in V._from_footage(session, plan, {'elements': {eid: row}, 'v': 2}):
            V.save_session(store, run, session)
            session, queued, _ = _order(conn, store, user, run, outputs, [eid])
    if not queued:
        V.save_session(store, run, session)
    return {'element_id': eid, 'queued': bool(queued), 'pass': V._round_pass(session, session['round']), 'cost_inr': _price(run, len(queued)),
            'then': ALL_MAKING.format(k=1, x=_inr(_price(run, 1))) if queued else then_of(session)}
