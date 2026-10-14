"""Mechanical handoff of the retained Section 2 decision; no new editorial choices."""
from copy import deepcopy
from fractions import Fraction
from .digest import digest
from .planning_contract import scoped_context, validate_sequence
from .edit_clarification import sequences


def execution_document(session):
    plan=session['selected_plan'];context=session['package']['context'];fps=Fraction(context['fps'])
    rows=[]
    for sid,seq in sequences(plan):
        scoped=context if sid=='recommendation' else scoped_context(context,seq['passage_ids'],seq['narration_window'])
        checked=validate_sequence(seq,scoped,plan['fps'])
        compiled={'fps':int(fps) if fps.denominator==1 else str(fps),'resolution':deepcopy(context['resolution']),
            'duration_frames':seq['duration_frames'],'duration_s':float(Fraction(seq['duration_frames'])/fps),
            'shots':deepcopy(seq['shots']),'audio_segments':checked['audio_segments'],
            'source_audio_segments':deepcopy(seq.get('source_audio_segments',[])),
            **checked['pause_timing'],'narration':deepcopy(context['narration']),
            'plan_sha256':digest(plan),'context_sha256':session['package']['context_digest'],
            'editorial_verification':'not_performed'}
        for shot in compiled['shots']:
            shot['duration_frames']=shot['timeline_end_frame']-shot['timeline_start_frame']
            shot.update(timeline_start_s=float(Fraction(shot['timeline_start_frame'])/fps),
                timeline_end_s=float(Fraction(shot['timeline_end_frame'])/fps))
            if shot['kind']=='video':
                source=context['sources'][shot['source_id']]
                shot.update(source_fps=source['metadata']['frame_rate'],source_sha256=source['sha256'])
                native=Fraction(shot['source_fps'])
                shot.update(source_start_s=float(Fraction(shot['source_start_frame'])/native),
                    source_end_s=float(Fraction(shot['source_end_frame'])/native),
                    source_width=source['metadata']['width'],source_height=source['metadata']['height'])
        for sound in compiled['source_audio_segments']:
            source=context['sources'][sound['source_id']];native=Fraction(source['metadata']['frame_rate'])
            sound.update(source_fps=str(native),source_sha256=source['sha256'],
                source_start_s=float(Fraction(sound['source_start_frame'])/native),source_end_s=float(Fraction(sound['source_end_frame'])/native),
                timeline_start_s=float(Fraction(sound['timeline_start_frame'])/fps),timeline_end_s=float(Fraction(sound['timeline_end_frame'])/fps))
        rows.append({'id':sid,'title':'Recommendation' if sid=='recommendation' else seq['title'],
            'tradeoff':seq['sequence_reason'] if sid=='recommendation' else seq['tradeoff'],
            'passage_ids':deepcopy(scoped['passage_ids']),'decision_notes':deepcopy(seq['decision_notes']),
            'plan':deepcopy(seq),'context':deepcopy(scoped),'compiled':compiled})
    return {'contract':'videowizard-compiled-edit-v2','film_fps':str(fps),'resolution':deepcopy(context['resolution']),
        'planning_context_digest':session['package']['context_digest'],'certificate_digest':session['certificate_digest'],
        'source_plan':deepcopy(plan),'sequences':rows,'alternatives':deepcopy(plan['alternatives'])}


def validate_bound_execution(store,run,accepted):
    from .planning_api import require_execution,current_session
    document=accepted['document'];identity=document['planning_context_digest']
    require_execution(store,run,identity)
    expected=execution_document(current_session(store,run,identity))
    if digest(expected)!=accepted['digest'] or document!=expected:
        raise ValueError('Execution document differs from the retained planning certificate.')
