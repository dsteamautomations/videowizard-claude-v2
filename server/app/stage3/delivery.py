"""Delivery: bundle with manifest (approved film, narration, originals, normalised fills, plans), SRT, finishing checklist, media-pool CSV;
the Resolve ledger (reserve → dispatched → reported → closed, never replayed); final approval on five points; retention on close."""
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from fractions import Fraction

from .. import core, jobs
from ..errors import Problem
from ..stage2 import stage as S2
from . import CONTRACT_BUNDLE, timeline as TL
from .assembly import key, session_of, save_session, fail

FINAL_WORDS = {'watched': ('watch',), 'listened': ('listen',), 'subtitles read': ('srt', 'subtitle'), 'timeline verified': ('drt', 'timeline'), 'package complete': ('package', 'bundle')}


def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def srt_of(beats, sentences=None, fps=25):
    """design/19 A7: one cue per sentence on the timeline (shifted by every pause before it); falls back to one per beat."""
    lines = []
    if sentences:
        for i, s in enumerate(sentences, 1):
            lines += [str(i), f"{srt_time(s['start_frame'] / fps)} --> {srt_time(s['end_frame'] / fps)}", s['text'].strip(), '']
        return '\n'.join(lines) + '\n'
    for i, b in enumerate(beats, 1):
        lines += [str(i), f"{srt_time(b['narration_first_word_s'])} --> {srt_time(b['narration_last_word_s'])}", b['text'].strip(), '']
    return '\n'.join(lines) + '\n'


def format_line(fmt):
    """design/53 L7: the frame shape and destinations from the brief, for the editor."""
    fmt = fmt or {}
    dests = ', '.join(fmt.get('destinations') or []) or 'destinations not given'
    line = f"Format: frame {fmt.get('frame') or '16:9'} for {dests}" if fmt.get('destinations') else f"Format: frame {fmt.get('frame') or '16:9'}; {dests}"
    return line + ('; watched muted: burn the subtitles in' if fmt.get('watched_muted') else '')


def checklist_of(assembly_summary, pk, master_summary, brief=None):
    items = [{'where': f"frame {i.get('timeline_in_frame', 0)}", 'item': i['item']} for i in assembly_summary.get('finishing') or []]
    for c in pk.get('sfx_cues_flat') or []:
        items.append({'where': c.get('start_tc', ''), 'item': f"A3 SFX to source: {c.get('sfx_type')} — {c.get('description')}"})
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    groups = sorted({r['color_group'] for r in rows.values() if r.get('color_group')})
    check = ((assembly_summary.get('loudness') or {}).get('check') or {})   # design/47 12.3: what the film is, not the blueprint's figures for a film with music
    measured = (f"measured {check['integrated_lufs']} LUFS, peak {check['true_peak_dbfs']} dBTP" if check.get('integrated_lufs') is not None and check.get('true_peak_dbfs') is not None
                else 'not measured')
    items += [{'where': 'Fairlight', 'item': 'A2 nat-sound pieces are placed at unity in the timeline; the film used 4-frame fades and −27 dBFS peaks (API cannot set fades); match if re-rendering'},
              {'where': 'Fairlight bus', 'item': f"Master bus: the approved film is rendered to {check.get('integrated_target_lufs', -16)} LUFS integrated (the narration's target; v2 adds no music) "
                                                f"with a {check.get('peak_ceiling_dbtp', -3)} dBTP ceiling; it {measured}. Keep that if re-rendering"},
              {'where': 'Deliver page', 'item': 'Subtitles: burn in or deliver the SRT alongside (SRT is in the package)'},
              {'where': 'Deliver page', 'item': format_line(((brief or {}).get('production') or {}).get('format'))},   # design/53 L7
              {'where': 'Color page', 'item': 'Colour groups from the logs: ' + (', '.join(groups) if groups else 'none')},
              {'where': 'A4', 'item': 'Add background music on A4, ducked −28 to −32 dBFS under narration, swells to −18 dBFS in pauses (none in v2)'}]
    return items


def media_pool_csv(pk):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['File Name', 'Scene', 'Shot', 'Take', 'Good Take', 'Description', 'Comments', 'Keywords'])
    by_clip = {}
    for r in pk['sub_clips']:
        by_clip.setdefault(r['clip_name'], []).append(r)
    for card in pk['cards']:
        subs = by_clip.get(card['clip_name'], [])
        stage = next((s['process_stage'] for s in subs if s.get('process_stage')), '')
        comments = '; '.join(f"{s['log_sub_clip_id']} (f{s['in_frame']}-{s['out_frame']}) {s['grade']} {s['eligibility']}" for s in subs)
        keywords = sorted({k for s in subs for k in ([stage, s['effective_shot_size'], 'Grade_' + s['grade'], s.get('color_group') or ''] + s['primary_fits']) if k})
        w.writerow([card['clip_name'], stage, card['clip_id'], 1, 1 if any(s['grade'] in ('A', 'B') for s in subs) else 0, (card['lines'] or [''])[0][:200], comments, ','.join(keywords)])
    return buf.getvalue()


# ---------- design/105: the AI-shot list (E-c) and the editor's table (E-b), from the assembly and the visuals record ----------

NOT_AI_REFS = ('frame', 'supplied', 'web')   # a footage frame, a client's file or a web photo held as a still is not AI


def _tc(frames, fps):
    s = int(frames / float(Fraction(str(fps))))   # an fps may be 25, 25.0 or '30000/1001'
    return f'{s // 60:02d}:{s % 60:02d}'


def ai_kind(ev, vis):
    """AI video, AI still, graphic, supplied (a file the operator gave, `vw visuals asset`: maybe AI, maybe not), or None for footage."""
    if ev.get('kind') != 'fill' or ev.get('source') == 'clip':
        return None
    if ev.get('source') == 'asset' and (vis.get(ev.get('shot_id')) or {}).get('supplied'):
        return 'supplied'
    media = ev.get('media') or {}
    if media.get('kind') == 'sequence' or (media.get('kind') == 'still' and media.get('graphic')):
        return 'graphic'
    if ev.get('source') == 'take' or media.get('kind') == 'movie':
        return 'AI video'
    return None if (vis.get(ev.get('shot_id')) or {}).get('reference_kind') in NOT_AI_REFS else 'AI still'


def ai_shots(events, fps, vis):
    return [{'shot_id': ev['shot_id'], 'kind': k, 'timecode': _tc(ev['timeline_in_frame'], fps)} for ev in events for k in [ai_kind(ev, vis)] if k]


def has_ai(rows):
    return any(r['kind'] != 'supplied' for r in rows)


def ai_shots_md(rows):
    pic = [r for r in rows if r['kind'] in ('AI video', 'AI still')]
    gfx = [r for r in rows if r['kind'] == 'graphic']
    own = [r for r in rows if r['kind'] == 'supplied']
    head = ("Every shot made by AI, with its timecode. When uploading, tick the platform's AI-generated or altered-content option.\n\n" if pic or gfx
            else 'No shot was generated here; the files below were supplied by the operator.\n\n')
    return ('# AI shots in this film\n\n' + head
            + ''.join(f"- {r['timecode']} {r['shot_id']}: {r['kind']}\n" for r in pic)
            + ('\n## Graphics\n\nDrawn graphics (diagrams, charts, titles), listed apart:\n\n' + ''.join(f"- {r['timecode']} {r['shot_id']}\n" for r in gfx) if gfx else '')
            + ('\n## Supplied by the operator\n\nFiles the operator gave for these shots; the server cannot tell how they were made: check whether they were made with AI '
               'before ticking the option.\n\n' + ''.join(f"- {r['timecode']} {r['shot_id']}\n" for r in own) if own else ''))


NUMBER = re.compile(r'\d[\d,.]*\s*(?:%|per ?cent)?|\b[a-z-]+ per ?cent\b', re.I)
SOCIAL = ('instagram', 'reels', 'tiktok', 'shorts', 'facebook', 'linkedin')
KINDS = ('look', 'sound', 'text', 'finishing')


def editors_table(events, fps, vis, fmt=None):
    """design/105 E-b: one line per suggestion, from data the server has; the editor decides, nothing is applied."""
    rows, takes, ai = [], 0, False
    for ev in events:
        kind = ai_kind(ev, vis)
        if kind not in ('AI video', 'AI still'):
            continue
        ai = True
        sid, where, v = ev['shot_id'], _tc(ev['timeline_in_frame'], fps), vis.get(ev['shot_id']) or {}
        add = lambda k, rule, line: rows.append({'kind': k, 'rule': rule, 'where': where, 'shot': sid, 'line': line})
        add('sound', 'E5', 'layer sound under it: near, middle, far, from what the scene shows' + (f" ({v['ambient']})" if v.get('ambient') else ''))
        if kind == 'AI video':
            takes += ev.get('source') == 'take'
            m = NUMBER.search(v.get('narration') or '')
            if m:
                add('text', 'E6', f"'{m.group(0).strip()}' is spoken over a video shot: overlay it in the edit; it is not drawn in the take")
        failed = {l.get('check'): l.get('seen') or '' for l in v.get('check_lines') or [] if l.get('pass') is False}
        if 'light and colour' in failed:
            add('look', 'E7', failed['light and colour'] + ': match the grade by eye')
        if 'fine detail' in failed:
            add('look', 'E8', failed['fine detail'] + ': add fine grain to match')
        if 'nothing extra' in failed:
            add('look', 'E10', 'the check saw: ' + failed['nothing extra'] + ': paint it out if it distracts')
    once = lambda k, rule, line: rows.append({'kind': k, 'rule': rule, 'where': '', 'shot': '', 'line': line})
    if takes:
        once('finishing', 'E11', f"{takes} AI take{'s are' if takes > 1 else ' is'} 720p: use Resolve's Super Scale 2x on them before the final render")
    once('sound', 'E13', 'If music is added, move cuts within ±4 frames of a beat where the narration allows')
    once('finishing', 'E15', "End card: place the client's own logo file (never drawn by AI)")
    if ai:
        once('finishing', 'E16', 'Upload with the AI label: see AI-shots.md')
    fmt = fmt or {}
    if fmt.get('frame') == '9:16' or any(w in ' '.join(fmt.get('destinations') or []).lower() for w in SOCIAL):
        once('finishing', 'E17', 'For Reels or TikTok: export 1080p 30 fps, not 4K 60 fps')
    return rows


def editors_table_md(rows):
    out = "\n## Editor's table\n\nSuggestions for the editor, from the film's data; nothing here is applied. One line each: where, the shot, what to do, the rule.\n"
    for k in KINDS:
        mine = [r for r in rows if r['kind'] == k]
        if mine:
            out += f'\n### {k.capitalize()}\n\n' + ''.join(f"- [{r['where']}] {r['shot']}: {r['line']} ({r['rule']})\n" if r['shot'] else f"- {r['line']} ({r['rule']})\n" for r in mine)
    return out


def visuals_info(store, run, outputs):
    """Per shot: its narration, its scene's ambient line, the kind of its placed picture and that picture's check lines. Empty when the run has no visuals."""
    from .. import image_check, visuals_stage as VS
    from ..visual_contract import all_scenes
    try:
        session = VS.session_of(store, run, outputs)
        plan = VS.current_plan(store, session)
    except Exception:
        return {}
    out = {}
    for gap in plan.get('gaps') or []:
        for scene in all_scenes(gap):
            for sh in scene['shots']:
                asset = session.get('assets', {}).get(sh['id']) or {}
                ref = session.get('references', {}).get(asset.get('reference_id') or '') or {}
                check = image_check.expand(ref['check'], ref)['lines'] if ref.get('check') else []
                out[sh['id']] = {'narration': sh.get('narration') or '', 'ambient': scene.get('ambient') or '', 'reference_kind': ref.get('kind'), 'check_lines': check,
                                 'supplied': bool(asset) and not asset.get('reference_id') and asset.get('kind') in ('movie', 'still')}   # add_asset: a file the operator gave
    return out


def bundle(conn, store, user, run, outputs):
    session = session_of(store, run)
    asm_o = S2._output(outputs, 'assembly')
    master_o = S2._output(outputs, 'master')
    voice_o = S2._output(outputs, 'voice')
    media_o = S2._output(outputs, 'media')
    s2 = S2.session_of(store, run)
    pk = S2._package(store, s2)
    assembly, _ = S2._file(store, asm_o, f"assembly-v{asm_o['summary']['version']}.json")
    master, _ = S2._file(store, master_o, f"master-v{master_o['summary']['version']}.json")
    film = next(f for f in asm_o['files'] if f['name'] == 'assembly.mp4')
    files = [{'role': 'approved_film', 'name': 'Approved-film.mp4', **{k: film[k] for k in ('key', 'sha256', 'bytes')}}]
    for f in voice_o['files']:
        if f['name'] in ('narration.mp3', 'timing.json'):
            files.append({'role': 'narration', 'name': layout('narration', f['name']), **{k: f[k] for k in ('key', 'sha256', 'bytes')}})
    used_clips = {}
    for ev in assembly['events']:
        if ev['kind'] == 'event':
            row = next(r for r in pk['sub_clips'] if r['sub_clip_id'] == ev['sub_clip_id'])
            used_clips[row['clip_id']] = row['clip_name']
    clips = {c['id']: c for c in media_o['summary']['clips']}
    for cid, name in used_clips.items():
        c = clips[cid]
        files.append({'role': 'original', 'name': layout('original', name), 'key': f"{run['id']}/media/{name}", 'sha256': c['sha256'], 'bytes': c['bytes']})
    fills = {(ev.get('file') or {}).get('name') for ev in assembly['events'] if ev['kind'] == 'fill'}
    for f in asm_o['files']:
        if f['name'].startswith('normalised/'):
            files.append({'role': 'normalised', 'name': layout('normalised', f['name'].split('/', 1)[1], fills), **{k: f[k] for k in ('key', 'sha256', 'bytes')}})
    for o, name in ((master_o, f"master-v{master_o['summary']['version']}.json"), (asm_o, f"assembly-v{asm_o['summary']['version']}.json")):
        f = next(x for x in o['files'] if x['name'] == name)
        files.append({'role': 'plan', 'name': 'Plans/' + name, **{k: f[k] for k in ('key', 'sha256', 'bytes')}})
    files.append({'role': 'plan', 'name': 'Plans/options-package.json', **{k: s2['package'][k] for k in ('key', 'sha256', 'bytes')}})
    srt = srt_of(pk['beats'], (pk.get('narration') or {}).get('sentences'), pk['timeline']['fps']).encode('utf-8')
    pk_flat = {**pk, 'sfx_cues_flat': assembly.get('sfx_cues') or []}
    brief_summary = (S2._output(outputs, 'brief') or {}).get('summary') or {}
    from .. import auth
    card = auth.client_card(run['client_id']) if run.get('client_id') else {}   # design/50: the brand group re-read live; the rest as the brief saw it
    card = {**(brief_summary.get('client_card') or {}), **{k: v for k, v in card.items() if k in auth.CARD_COLUMNS['brand'] or k in auth.CARD_COLUMNS['contact']}}
    brand = fetch_brand_files(conn, store, run, card)
    for f in brand['files']:
        files.append({'role': 'brand', 'name': 'Graphics/' + f['name'], 'key': f['key'], 'sha256': f['sha256'], 'bytes': f['bytes']})
    checklist = checklist_of(asm_o['summary'], pk_flat, master_o['summary'], brief=brief_summary) + brand_lines(card, {f['kind']: 'Graphics/' + f['name'] for f in brand['files']})
    vis = visuals_info(store, run, outputs)   # design/105
    fps = pk['timeline']['fps']
    table = editors_table(assembly['events'], fps, vis, ((brief_summary.get('production') or {}).get('format')))
    shots = ai_shots(assembly['events'], fps, vis)
    md = '# Human finishing checklist\n\n' + '\n'.join(f"- [{i['where']}] {i['item']}" for i in checklist) + '\n' + editors_table_md(table)
    checklist = checklist + [{'section': 'editor', 'kind': r['kind'], 'rule': r['rule'], 'where': r['where'], 'shot': r['shot'], 'item': r['line']} for r in table]
    csv_text = media_pool_csv(pk).encode('utf-8')
    open_edit = open_edit_text(run, card, brief_summary.get('directory_differences') or [], ai=has_ai(shots)).encode('utf-8')
    events = resolve_events(assembly, pk, master)
    pieces = [{'file': layout('narration', 'narration.mp3'), 'source_in_frame': p['source_start_frame'], 'source_out_frame': p['source_end_frame'], 'record_in_frame': p['timeline_start_frame']}
              for p in ((pk.get('narration') or {}).get('pieces') or [{'source_start_frame': 0, 'source_end_frame': assembly['duration_frames'], 'timeline_start_frame': 0}])]
    used = [e['clip_id'] for e in events if e.get('clip_id')]
    cuts_per_clip = {cid: used.count(cid) for cid in set(used)}
    timeline_files = {f"{run['code']}.fcpxml": (TL.fcpxml(run['code'], pk['timeline'], events, pieces, asm_o['summary'].get('finishing') or [], assembly.get('sfx_cues') or [], assembly['duration_frames']).encode('utf-8'), 'application/xml'),
                      f"{run['code']}.edl": (TL.edl(run['code'], pk['timeline'], events).encode('utf-8'), 'text/plain'),
                      'Relink-list.csv': (TL.relink_csv(media_o['summary']['clips'], set(used), cuts_per_clip).encode('utf-8'), 'text/csv')}   # design/107 slice 1
    generated = {**timeline_files, 'Subtitles.srt': (srt, 'text/plain'), 'Finishing-checklist.md': (md.encode('utf-8'), 'text/markdown'), 'Finishing-checklist.json': (json.dumps(checklist, ensure_ascii=False, indent=1).encode('utf-8'), 'application/json'),
                 'Media-pool.csv': (csv_text, 'text/csv'), 'OPEN-EDIT.md': (open_edit, 'text/markdown'),
                 **({'AI-shots.md': (ai_shots_md(shots).encode('utf-8'), 'text/markdown')} if shots else {})}   # design/105 E-c
    for name, (data, mime) in generated.items():
        k = key(run, 'delivery/' + name)
        store.put(k, data, mime)
        files.append({'role': 'generated', 'name': layout('generated', name), 'key': k, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    manifest = {'contract': CONTRACT_BUNDLE, 'run': run['code'], 'client': run.get('client'), 'created_at': datetime.now(timezone.utc).isoformat(), 'film_sha256': film['sha256'],
                'assembly_digest': asm_o['summary']['assembly_digest'], 'timeline': pk['timeline'], 'files': files, 'resolve_events': events, 'narration_pieces': pieces,
                'timeline_file': layout('generated', f"{run['code']}.fcpxml"), 'film_frames': assembly['duration_frames'], 'cuts': len(events)}   # design/107: what Step D checks against
    mk = S2.save_json(store, key(run, 'delivery/manifest.json'), manifest)
    for f in files + [{'name': 'manifest.json', **mk}]:
        jobs.record_file(conn, run['id'], 'delivery', f['key'], f['name'], f['sha256'], f['bytes'], 'application/octet-stream')
    session['bundle'] = {'manifest': mk, 'film_sha256': film['sha256'], 'files': len(files), 'bytes': sum(f['bytes'] for f in files)}
    session['resolve'] = None if (session.get('resolve') or {}).get('film_sha256') != film['sha256'] else session['resolve']
    save_session(store, run, session)
    return {'manifest': mk, 'files': len(files), 'bytes': session['bundle']['bytes'], 'next': 'on the operator\'s computer (Windows or Mac): `vw pull <code>` then `vw delivery resolve --check`, then `--run --authorization "<operator words>"`'}


NAMES = {'youtube': 'YouTube', 'tiktok': 'TikTok', 'linkedin': 'LinkedIn', 'twitter': 'X'}
FRAME_OF = {'youtube': '16:9', 'instagram': '9:16 or 1:1', 'tiktok': '9:16', 'facebook': '16:9 or 1:1', 'linkedin': '16:9 or 1:1', 'pinterest': '2:3 or 9:16', 'twitter': '16:9', 'x': '16:9'}


def brand_lines(card, fetched):
    """design/50 D: Brand lines for the editor from the directory card; fetched maps logo kinds to bundle paths."""
    if not card:
        return []
    items = []
    if card.get('client_logo_url'):
        items.append({'where': 'Brand', 'item': (f"Logo: {fetched['logo']} (place and size it in Resolve; never in the rendered film)" if fetched.get('logo')
                                                 else 'Logo: not fetched (URL unreachable or not a file); take it from the directory')})
    for k, label in (('client_brand_guidelines', 'Brand guidelines'), ('color_palette', 'Palette'), ('typography_fonts', 'Fonts'), ('trademark_patterns', 'Trademark patterns')):
        if card.get(k):
            v = card[k]
            items.append({'where': 'Brand', 'item': f"{label}: {', '.join(v) if isinstance(v, list) else v}"})
    if card.get('client_cta_instructions'):
        items.append({'where': 'Brand', 'item': f"CTA instructions (directory): {card['client_cta_instructions']}"})
    contact = [card[k] for k in ('website_url', 'phone_number', 'email_address') if card.get(k)]
    if contact:
        items.append({'where': 'Brand', 'item': 'End card details (directory): ' + ', '.join(contact)})
    dests = []
    for k in ('youtube_url', 'instagram_url', 'tiktok_url', 'facebook_url', 'linkedin_url', 'pinterest_url', 'twitter_x_url'):
        if card.get(k):
            name = k.split('_')[0]
            dests.append(f"{NAMES.get(name, name.capitalize())} ({FRAME_OF.get(name, '16:9')})")
    for pf in card.get('social_sharing_platforms') or []:
        if not any(pf.lower().split()[0] in d.lower() for d in dests):
            dests.append(f"{pf} ({FRAME_OF.get(pf.lower().split()[0], '16:9')})")
    if dests:
        items.append({'where': 'Brand', 'item': 'Destinations (directory) with their frame shapes: ' + ', '.join(dests)})
    return items


def open_edit_text(run, card=None, differences=None, ai=False):
    """OPEN-EDIT.md (design/107: a timeline file any Resolve imports, then relink to the originals; design/105: the Editor's table and the AI-shot list;
    design/50: the brand section and the recorded differences). On the operator's computer, Windows or Mac."""
    code = run['code']
    text = (f"# OPEN-EDIT\n\nRun {code} — client {run.get('client')}.\n\nThis folder is the whole edit. It opens on the operator's computer, Windows or Mac, in DaVinci Resolve, free or Studio.\n\n"
            "## Open the edit\n\n"
            "1. Open DaVinci Resolve and make a new project.\n"
            f"2. File > Import > Timeline, and pick `Timeline/{code}.fcpxml`. Every cut lands at its frame, with the voiceover on A1 and the nat sound on A2; A3 and A4 are yours.\n"
            "3. Approved-film.mp4 is the film the operator approved; the timeline reproduces its cuts, crops and zooms. The track named REFERENCE – approved film holds it, switched off: turn it on to compare any moment.\n"
            f"4. `Timeline/{code}.edl` is the same cut list as plain text, a second way in if an import ever fails.\n"
            "5. Subtitles.srt has one cue per narrated sentence, shifted by the approved pauses. Finishing-checklist.md lists everything the API could not do, and ends with the Editor's table: suggestions from the film's data, one line each; nothing in it is applied.\n")
    if ai:   # design/105 E-c
        text += "6. AI-shots.md lists every AI shot with its timecode: tick the platform's AI-generated or altered-content option when uploading.\n"
    text += ("\n## Relink to the full-quality originals\n\n"
             "Media/Camera/ holds the camera files as they were uploaded, which may be compressed copies. Media/AI/ and Media/Voiceover/ are made by VideoWizard and never need relinking.\n\n"
             "1. In the Media Pool, select the camera clips, right-click, Relink, and pick the folder that holds the originals. Resolve matches by file name and timecode; every cut moves to the original.\n"
             "2. Relink-list.csv has one line per camera file: name, length, frame rate, size and timecode, so a renamed original can be found. When the originals' names differ, import the relinked timeline the relink check writes instead.\n"
             "3. Turn on the REFERENCE track and spot-check a few cuts against the approved film.\n"
             "4. In Project Settings, set \"Mismatched resolution files\" to \"Scale entire image to fit\", so zoom and position stay right on the larger originals.\n"
             "\nOn Resolve Studio the plugin can do the import itself and export the project (.drp) and the timeline (.drt) into Timeline/.\n")
    if card:
        text += '\n## Brand\n\nFrom the client directory, for the end card and the graphics (Graphics/ holds the logo files when the directory had them): see the Brand lines of the checklist.\n'
    if differences:
        text += '\n## Where this film departs from the directory\n\n' + ''.join(
            f"- {d.get('field')}: the directory says \"{d.get('directory_says')}\"; this film uses \"{d.get('chosen')}\" (decided by the {d.get('decided_by')}"
            + (f": \"{d['operator_words']}\"" if d.get('operator_words') else '') + ')\n' for d in differences)
    return text


def fetch_brand_files(conn, store, run, card):
    """design/50 D: the logo files named in the directory, fetched live into <run>/brand/; a failed fetch is skipped and named, never fatal."""
    import httpx
    from .. import auth
    files, skipped = [], []
    for field in auth.LOGO_FIELDS:
        url = (card or {}).get(field)
        kind = field.replace('client_', '').replace('_url', '')
        if not url:
            skipped.append(f'{kind}: no URL in the directory')
            continue
        try:
            r = httpx.get(url, follow_redirects=True, timeout=30)
            ok = r.status_code == 200 and r.content and (r.headers.get('content-type', '').startswith('image/') or url.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.webp')))
        except httpx.HTTPError:
            ok = False
        if not ok:
            skipped.append(f'{kind}: URL unreachable or not an image')
            continue
        ext = '.' + url.rsplit('.', 1)[-1].lower().split('?')[0] if '.' in url.rsplit('/', 1)[-1] else '.png'
        name = kind + ext
        k = f"{run['id']}/brand/{name}"
        store.put(k, r.content, r.headers.get('content-type') or 'application/octet-stream')
        sha = hashlib.sha256(r.content).hexdigest()
        jobs.record_file(conn, run['id'], 'brand', k, name, sha, len(r.content), r.headers.get('content-type') or 'application/octet-stream')
        files.append({'name': name, 'kind': kind, 'key': k, 'sha256': sha, 'bytes': len(r.content)})
    return {'files': files, 'skipped': skipped}


def layout(role, name, fills=None):
    """design/107 §4: the fixed layout of the bundle, every run."""
    if role == 'original':
        return 'Media/Camera/' + name
    if role == 'normalised':
        return ('Media/AI/' if name in (fills or set()) else 'Media/Camera/Stabilised/') + name
    if role == 'narration':
        return 'Media/Voiceover/' + name
    if role == 'generated' and name.rsplit('.', 1)[-1] in ('fcpxml', 'edl', 'drp', 'drt'):
        return 'Timeline/' + name
    return name


def resolve_events(assembly, pk, master):
    """What the Resolve timeline must contain: per event the file, source in/out, record in/out, zoom/pan/tilt/rotation, marker, colour group."""
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    out = []
    for ev in assembly['events']:
        if ev['kind'] == 'event':
            r = rows[ev['sub_clip_id']]
            crop = ev.get('crop') in ('solver', 'hands_only') and r.get('zoom')
            if ev.get('stabilize'):   # the stabilised render is the source; crop and zoom are already applied in it
                out.append({'file': layout('normalised', f"{ev['sub_clip_id'].replace(':', '-')}-{ev['timeline_in_frame']}.mp4"), 'kind': 'camera', 'source_in_frame': 0, 'source_out_frame': ev['timeline_frames'],
                            'record_in_frame': ev['timeline_in_frame'], 'record_out_frame': ev['timeline_out_frame'], 'source_fps': str(pk['timeline']['fps']), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0,
                            'rotation': 0.0, 'color_group': r.get('color_group'), 'marker': {'name': ev['sub_clip_id'], 'note': f"option #{ev.get('approved_from_option')}, stabilised copy", 'colour': 'Blue'},
                            'a2': ev.get('a2_intervals') or [], 'stabilized': True})
                continue
            out.append({'file': layout('original', r['clip_name']), 'kind': 'camera', 'clip_id': r['clip_id'], 'source_in_frame': ev['source_in_frame'], 'source_out_frame': ev['source_out_frame'],
                        'record_in_frame': ev['timeline_in_frame'], 'record_out_frame': ev['timeline_out_frame'], 'source_fps': r['source_fps'],
                        'zoom': r['zoom'] if crop else 1.0, 'pan': (r['position'] or [0, 0])[0] if crop else 0.0, 'tilt': (r['position'] or [0, 0])[1] if crop else 0.0,
                        'rotation': r.get('horizon_rotation_deg') or 0.0, 'color_group': r.get('color_group'), 'marker': {'name': ev['sub_clip_id'], 'note': f"option #{ev.get('approved_from_option')}", 'colour': 'Blue'},
                        'a2': ev.get('a2_intervals') or [], 'stabilized': False})
        else:
            name = (ev.get('file') or {}).get('name') or ev['shot_id'] + '.mp4'   # design/107: the fill's real file (a still is a .png)
            out.append({'file': layout('normalised', name, {name}), 'kind': 'still' if (ev.get('media') or {}).get('kind') == 'still' else 'movie', 'source_in_frame': 0, 'source_out_frame': ev['timeline_frames'], 'record_in_frame': ev['timeline_in_frame'],
                        'record_out_frame': ev['timeline_out_frame'], 'source_fps': str(pk['timeline']['fps']), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0, 'rotation': 0.0, 'color_group': None,
                        'marker': {'name': ev['shot_id'], 'note': 'visuals fill', 'colour': 'Green'}, 'a2': [], 'stabilized': False})
    return out


# ---------- Resolve ledger (reserve → dispatched → reported → closed) ----------

def resolve_reserve(store, user, run, machine, authorization):
    session = session_of(store, run)
    if not session.get('bundle'):
        raise Problem(409, 'NOT_ALLOWED', 'Build the bundle first (`vw delivery bundle`).')
    led = session.get('resolve')
    if led and led.get('state') in ('reserved', 'dispatched', 'reported') and led.get('film_sha256') == session['bundle']['film_sha256']:
        raise Problem(409, 'NOT_ALLOWED', f"The Resolve step is already {led['state']} on {led.get('machine')}; inspect or close it, never replay.", state=led['state'])
    if not str(authorization or '').strip():
        fail('The operator\'s words permitting the Resolve timeline are required (--authorization).')
    session['resolve'] = {'state': 'reserved', 'machine': machine, 'authorization': authorization, 'film_sha256': session['bundle']['film_sha256'], 'reserved_at': datetime.now(timezone.utc).isoformat(), 'by': user['id']}
    save_session(store, run, session)
    return session['resolve']


def resolve_mark(store, user, run, state, machine, report=None, note=None):
    session = session_of(store, run)
    led = session.get('resolve')
    if not led:
        raise Problem(409, 'NOT_ALLOWED', 'Nothing reserved.')
    allowed = {'dispatched': ('reserved',), 'reported': ('dispatched',), 'closed': ('dispatched', 'reported', 'reserved')}
    if led['state'] not in allowed.get(state, ()):
        raise Problem(409, 'NOT_ALLOWED', f"Cannot move {led['state']} → {state}.")
    if led.get('machine') != machine and state != 'closed':
        raise Problem(409, 'NOT_ALLOWED', f"Reserved by {led.get('machine')}, not this machine.")
    led['state'] = state
    led[f'{state}_at'] = datetime.now(timezone.utc).isoformat()
    if report is not None:
        led['report'] = report
    if note:
        led['note'] = note
    save_session(store, run, session)
    return led


def verification_missing(led, film_sha256):
    """design/107 Step G: 'the timeline matched the film', by Studio's readback (drt_verified) or the operator's check on free Resolve (timeline_verified)."""
    if (led or {}).get('state') != 'reported' or led.get('film_sha256') != film_sha256:
        return ['a report that the timeline matched this film']
    rep = led.get('report') or {}
    return [] if rep.get('drt_verified') or rep.get('timeline_verified') else ['the timeline matched the film (the report says it did not)']


def final(conn, store, user, run, outputs, quote):
    session = session_of(store, run)
    asm_o = S2._output(outputs, 'assembly')
    film = next(f for f in asm_o['files'] if f['name'] == 'assembly.mp4')
    b = session.get('bundle')
    led = session.get('resolve') or {}
    missing = []
    if not b or b['film_sha256'] != film['sha256']:
        missing.append('bundle for the current assembly film')
    missing += verification_missing(led, film['sha256'])   # design/107: Studio's readback, or the operator's side-by-side check on free Resolve
    if any(o.get('stale') for o in outputs):
        missing.append('no stale stage outputs')
    q = (quote or '').lower()
    for label, words in FINAL_WORDS.items():
        if not any(w in q for w in words):
            missing.append(f"operator's words for: {label}")
    if missing:
        raise Problem(409, 'NOT_ALLOWED', 'Final approval is not possible yet: ' + '; '.join(missing), missing=missing)
    manifest = S2.load_json(store, b['manifest']['key'])
    rep = led['report']
    files = [{'name': 'Approved-film.mp4', 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True},
             {'name': 'manifest.json', **{k: b['manifest'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True}]
    for f in manifest['files']:   # the whole package is the delivery record, so retention keeps it (originals the timeline references included)
        if f['key'] not in {x['key'] for x in files}:
            files.append({'name': f['name'], **{k: f[k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True})
    for name in ('drt', 'report'):
        ref = rep.get(name)
        if ref:
            files.append({'name': 'Approved-timeline.drt' if name == 'drt' else 'resolve-report.json', **{k: ref[k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True})
    for f in files:
        jobs.record_file(conn, run['id'], 'delivery', f['key'], f['name'], f['sha256'], f['bytes'], 'application/octet-stream')
    summary = {'film_sha256': film['sha256'], 'manifest_sha256': b['manifest']['sha256'], 'resolve': {k: led.get(k) for k in ('machine', 'authorization', 'reported_at')},
               'readback': rep.get('readback'), 'drt_verified': rep.get('drt_verified'), 'differences': rep.get('differences') or [], 'checks': list(FINAL_WORDS)}
    out = core.output(conn, user, run, {'stage': 'delivery', 'files': files, 'accepted_quote': quote, 'summary': summary})
    led['state'] = 'closed'
    session['final'] = {'output': str(out['id']), 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'output': str(out['id']), 'files': len(files), 'next': '`vw close`'}


KEEP_STAGES = ('delivery', 'voice', 'visuals')


def retention(conn, store, run, outputs):
    """Plan §1 decision 4: keep the final film and package, approved narration, approved images and takes, and every stage-output record (JSON);
    delete everything else under the run (originals, review/master/assembly films, sessions, frames, normalised copies, inspections)."""
    keep = set()
    for o in outputs:
        for f in o['files']:
            if o['stage'] in KEEP_STAGES or str(f.get('name', '')).endswith('.json'):
                keep.add(f['key'])
    everything = store.list(str(run['id']))
    doomed = [k for k in everything if k not in keep]
    store.delete(doomed)
    conn.execute("delete from vw2_files where run_id=%s and key = any(%s)", (run['id'], doomed))
    return {'kept': len(keep), 'deleted': len(doomed)}
