"""Preview the reference grouped-review text without rendering or local media paths."""
from .review_cards import digest
from . import review_cards as cards

INSTRUCTIONS = (
    'Viewer review cards: comparison titles and displayed why/shows/limitations must use readable descriptions, '
    'not internal P001, Q1, source-1 or event-1 identifiers. Keep IDs in structural/evidence fields. '
    'check_draft returns presentation with errors and exact explanation_sources. If verbatim fallback text is unsuitable, '
    'author review_explanations using each returned sequence_id, passage_ids and source_digest, plus why, shows, '
    'limitations and qualifications_preserved:true. Preserve every evidence qualification; do not merely strip IDs. '
    'Run check_draft again after relevant edits and accept only draft_technically_valid. '
    'Native execution requires integer output FPS and exact integer source-frame decimation.'
)

def preview(document):
    sequences=document['sequences'];main=sequences[0];plan=document['source_plan']
    comparisons=plan['alternative_review'];fps=main['compiled']['fps']
    windows=main['compiled']['passage_windows'];ids=[w['passage_id'] for w in windows]
    authored_rows=plan.get('review_explanations',[])
    authored={(r['sequence_id'],tuple(r['passage_ids'])):r for r in authored_rows}
    errors=[];sources=[];used=set()
    if len(authored)!=len(authored_rows):errors.append('Duplicate viewer explanation bindings.')
    cuts={0,len(ids)}
    for i in range(1,len(ids)):
        frame=round(windows[i]['timeline_start_s']*fps)
        crossing=any(s['timeline_start_frame']<frame<s['timeline_end_frame'] for s in main['compiled']['shots'])
        spans=[s['passage_ids'] for s in sequences[1:]]+[r['passage_ids'] for r in comparisons]
        crossing |= any(min(ids.index(p) for p in span)<i<=max(ids.index(p) for p in span) for span in spans)
        if not crossing:cuts.add(i)
    boundaries=sorted(cuts)
    for a,b in zip(boundaries,boundaries[1:]):
        passages=ids[a:b];matching=[r for r in comparisons if set(r['passage_ids'])<=set(passages)]
        title=' / '.join(r['title'] for r in matching) or ', '.join(passages)
        try:cards.assert_viewer_text(title)
        except ValueError:errors.append('Section title for '+', '.join(passages)+' contains an internal reference; supply a viewer-readable title.')
        lo=round(windows[a]['timeline_start_s']*fps);hi=round(windows[b-1]['timeline_end_s']*fps)
        choices=[(main,lo,hi)]+[(s,0,s['compiled']['duration_frames']) for s in sequences[1:] if set(s['passage_ids'])<=set(passages)]
        for sequence,lo,hi in choices:
            shots=[s for s in sequence['compiled']['shots'] if s['timeline_start_frame']>=lo and s['timeline_end_frame']<=hi]
            selected={s['id'] for s in shots}
            notes=[n for n in sequence['decision_notes']['shot_decisions'] if n['shot_id'] in selected]
            explanation='\n'.join(r['recommendation_reason']+' '+r['reason'] for r in matching) if sequence['id']=='recommendation' else sequence['tradeoff']
            limits=list(dict.fromkeys(n['limitations'] for n in notes if n.get('limitations')))
            limits += [s['uncertainty'] for s in shots if s.get('uncertainty')]
            if sequence['id']!='recommendation':limits+=sequence['plan']['unresolved']
            source=cards.explanation_source(sequence['id'],passages,explanation,notes,list(dict.fromkeys(limits)),shots)
            key=(sequence['id'],tuple(passages))
            if key in authored:used.add(key)
            sources.append({'sequence_id':sequence['id'],'passage_ids':passages,'source_digest':digest(source),'source':source})
            try:cards.explanation_blocks(source,authored.get(key))
            except ValueError as exc:errors.append(sequence['id']+' / '+', '.join(passages)+': '+str(exc))
    if used!=set(authored):errors.append('Viewer explanation does not match a selected review option.')
    return {'valid':not errors,'errors':errors,'explanation_sources':sources}
