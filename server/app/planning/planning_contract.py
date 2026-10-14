"""Versioned server context and complete reference v3 mechanical acceptance checks."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import math
from .digest import digest
from ..errors import Problem
from . import edit_clarification as clarification
from .direct_gemini_test import schema, planning_prompt
from .direct_plan_contract import validate_decisions
from .planning_checks import extend_schema, validate_bundle
from .direct_pause_timing import apply_pauses
from ..video_evidence.situation import validate_situation

RELEASE='0.8.3'
CONTRACT='videowizard-planning-v1'

def require(ok, message):
    if not ok: raise ValueError(message)

def definition(store=None):
    """v2: the editing procedure (prompts, schemas) lives in the stage table under 'planning'."""
    from ..core import stage_table, _stage
    from ..config import settings
    return _stage(stage_table(settings().DEFAULT_PROCEDURE_VERSION), 'planning')['definition']


def timing_fields(context):
    """Publish existing passage clocks; never split passages or alter word timings."""
    groups=[[w for w in context['mapped_words'] if w['passage_id']==p] for p in context['passage_ids']]
    starts=[context['narration_source_start_s']]+[words[0]['source_start_s'] for words in groups[1:]]
    ends=starts[1:]+[context['narration_source_end_s']]
    origin=context['narration_source_start_s'];fps=Fraction(context['fps'])
    windows=[];boundaries=[]
    for passage,words,start,end in zip(context['passage_ids'],groups,starts,ends):
        windows.append({'passage_id':passage,'source_start_s':start,'source_end_s':end,
            'timeline_start_s':start-origin,'timeline_end_s':end-origin,'duration_s':end-start,
            'baseline_duration_frames':math.ceil((Fraction(str(end))-Fraction(str(start)))*fps)})
        boundaries.append({'after_passage_id':passage,'word_id':words[-1]['id'],
            'source_boundary_s':words[-1]['source_end_s'],'timeline_boundary_s':words[-1]['timeline_end_s']})
    return {'passage_windows':windows,'allowed_pause_boundaries':boundaries}


TIMING_FIELD_INSTRUCTIONS = (
    'Timing fields: passage_windows retains the existing passage IDs and exact source bounds, including existing silence. '
    'For an alternative, set narration_window.source_start_s from the first selected window and source_end_s from the last. '
    'Set narration_window.baseline_duration_frames to ceil((source_end_s-source_start_s)*fps), using exact rational arithmetic; '
    'only terminal picture padding may round up, never spoken source times. Alternative duration_frames is that baseline plus its own added pause frames. '
    'allowed_pause_boundaries lists after_passage_id, last word_id, source_boundary_s and baseline timeline_boundary_s. '
    'A narration_pauses entry uses only after_passage_id, additional_frames and reason. Do not copy boundary metadata into that entry. '
    'For an alternative, use only its selected passage boundaries and subtract its source start from baseline timeline clocks. '
    'A single P001 remains one passage; do not invent additional passage IDs or internal pause boundaries.'
)

def package(inputs, spec, restored_passages=None, scene_grouping=None):
    require(inputs['ready_for_planning'],'Complete accepted script, narration timing and eligible source evidence first.')
    doc=inputs['document']; policy=doc.get('planning_settings',doc['analysis_context'])
    situation=validate_situation(policy.get('workflow_situation'),require_resolved=True)
    require(situation.get('enabled') is True,'New planning needs the confirmed current workflow situation.')
    require(situation['story_carrier'] in ('supplied_narration','mixed') and situation['supplied_narration_policy']=='preserve','Changed narration requires a separate timing contract; do not mute or replace it.')
    require(situation['source_audio_in_output']=='none' or doc['source_audio_policy']=='allowed','Output sound conflicts with the saved source-audio permission.')
    output=policy.get('output',{})
    fps=Fraction(str(output.get('fps',0))); resolution=output.get('resolution')
    require(fps>0 and isinstance(resolution,list) and len(resolution)==2 and all(type(v) is int and v>0 and v%2==0 for v in resolution),'Save confirmed output fps and even width/height through editing/settings; no inferred delivery choice.')
    timing=doc['narration_timing']; duration=timing['audio']['duration_s']
    require(type(duration) in (float,int) and math.isfinite(duration) and duration>0,'Narration duration must be finite and positive.')
    passages={f'P{i+1:03d}':t for i,t in enumerate(doc['accepted_inputs']['script']['spoken_text'].split('\n\n')) if t.strip()}
    from .passages import paragraphs, PARSER
    if timing.get('passage_parser') == PARSER:
        passages = paragraphs(doc['accepted_inputs']['script']['spoken_text'])
    timing_words = timing['words']
    if restored_passages is not None:
        passages = restored_passages
        timing_words = deepcopy(timing_words)
        tokens = [(pid, token) for pid, text in passages.items() for token in text.split()]
        require([token for _, token in tokens] == [w['text'] for w in timing_words], 'Restored paragraphs must retain every accepted narration word in order.')
        for word, (pid, _) in zip(timing_words, tokens):
            word['passage_id'] = pid
    words=[]; seen=set(); cursor=0
    for w in timing_words:
        require(w['id'] not in seen and w['passage_id'] in passages and cursor<=w['start_s']<w['end_s']<=duration,'Narration words must retain ordered, source-bound timings.')
        seen.add(w['id']);cursor=w['end_s']
        words.append({**deepcopy(w),'source_start_s':w['start_s'],'source_end_s':w['end_s'],'timeline_start_s':w['start_s'],'timeline_end_s':w['end_s']})
    require([p for p in dict.fromkeys(w['passage_id'] for w in words)]==list(passages),'Timing must cover all accepted passages in order.')
    require(' '.join(w['text'] for w in words)==' '.join(doc['accepted_inputs']['script']['spoken_text'].split()),'Timing text differs from accepted narration.')
    sources={}
    for s in doc['sources']:
        m=s['metadata']; native=Fraction(str(m['average_fps']));seconds=float(m['duration_seconds'])
        require(native>0 and seconds>0 and math.isfinite(seconds),'Source clock metadata is unavailable.')
        require(all(type(m.get(k)) is int and m[k]>0 for k in ('width','height')),'Source dimensions are missing.')
        sources[s['id']]={**deepcopy(s),'source_id':s['id'],'eligible':True,'media_kind':'video','duration_s':seconds,'metadata':{**deepcopy(m),'frame_rate':str(native),'duration_s':seconds},'native_frame_count':m.get('frame_count') or math.floor(Fraction(str(seconds))*native)}
    registry={}; references={}; limits=[]; provisional=[]
    for a in doc['analyses']:
        view=a['evidence']
        for entry in view['usable']:
            ref=entry['ref']; key='/'.join(ref[k] for k in ('source_id','collection','item_id'))
            require(ref['source_id']==a['media_id'] and key not in registry,'Evidence identity collision or source mismatch.')
            registry[key]=deepcopy(entry['item']); references[key]={**deepcopy(ref),'analysis_job_id':a['id'],'binding':a['evidence_binding']}
        limits.append({'analysis_job_id':a['id'],**{k:deepcopy(view.get(k)) for k in ('excluded_rows','coverage','scope_omissions','unresolved')}})
        provisional.append({'analysis_job_id':a['id'],**{k:deepcopy(view.get(k)) for k in ('provisional_analysis','claim_evidence','script_support','visual_slot_guidance')}})
    segments=[{'id':'accepted-narration','source_start_s':0,'source_end_s':duration,'timeline_start_s':0,'timeline_end_s':duration}]
    context={'contract':CONTRACT,'release':spec.get('release',RELEASE),'experiment_id':doc['run_id'],'input_context_digest':inputs['context_digest'],'definition_digest':digest(spec),
      'planner_engine':'chatgpt_session','planner_api_requests':0,'component_review_contract':'component-review-v1','focused_observations_contract':'focused-observations-v1','clarification_contract':'edit-clarification-v1','editorial_roles_contract':'edit-roles-v1','planning_checks_contract':'passage-review-v1','review_presentation':'grouped-cards-v1',
      'fps':str(fps),'resolution':resolution,'duration_frames':math.ceil(Fraction(str(duration))*fps),'section_start_s':0,'section_end_s':math.ceil(Fraction(str(duration))*fps)/float(fps),
      'narration':deepcopy(doc['narration'])|{'duration_s':duration},'narration_source_start_s':0,'narration_source_end_s':duration,'audio_segments':segments,'expected_audio_segments_sha256':digest(segments),
      'mapped_words':words,'passage_ids':list(passages),'script_passages':passages,'sources':sources,'evidence_registry':registry,'evidence_references':references,'first_pass_limitations':limits,'provisional_analysis':provisional,
      'workflow_situation':situation,'accepted_inputs':doc['accepted_inputs'],'analysis_context':policy,'analysis_job_ids':[a['id'] for a in doc['analyses']], 'clocks':doc['clocks']}
    if scene_grouping is not None:
        context['scene_grouping'] = deepcopy(scene_grouping)
    context.update(timing_fields(context))
    if doc.get('planning_settings'):context['evidence_use_limits']=doc.get('evidence_use_limits','Retained evidence keeps its original scope.')
    contract=schema(doc['run_id'],list(sources),list(passages),str(fps),context['duration_frames'],'direct-gemini-edit-v3',situation)
    contract['properties']['fps']={'type':'string','enum':[str(fps)]}
    contract=clarification.extend_schema(extend_schema(contract),list(sources))
    # Explicit authored alternative narration windows accommodate generation timestamps
    # that are not film-frame aligned without rounding any spoken source boundary.
    alt=contract['properties']['alternatives']['items']
    alt['properties']['narration_window']={'type':'object','properties':{'source_start_s':{'type':'number','minimum':0},'source_end_s':{'type':'number','minimum':0},'baseline_duration_frames':{'type':'integer','minimum':1}},'required':['source_start_s','source_end_s','baseline_duration_frames'],'additionalProperties':False}
    alt['required'].append('narration_window')
    rules=spec['prompts']
    prompt=planning_prompt(rules['planning_document'],'DIRECT EDIT WITH EDITORIAL CHOICES',situation)+'\n\n'+rules['clarification_prompt']
    prompt=prompt.replace('Its duration_frames equals the selected baseline span times output fps plus its own added pause frames.',
        'Its duration_frames equals ceil(selected exact source span times output fps) plus its own added pause frames; preserve exact audio bounds.')
    from .planning_presentation import INSTRUCTIONS
    prompt=spec['planner_instruction']+'\n\n'+prompt+'\n\n'+TIMING_FIELD_INSTRUCTIONS+'\n'+INSTRUCTIONS+'\nCURRENT SERVER CONTEXT\n'+json.dumps(context,ensure_ascii=False)
    return {'context':context,'context_digest':digest(context),'schema':contract,'prompt':prompt,'inspector_prompt':rules['flash_prompt'],'definition_digest':digest(spec),'planner_api_requests':0}

def scoped_context(context, passages, window):
    all_ids=context['passage_ids']; require(bool(passages) and passages[0] in all_ids,'Unknown alternative passages.')
    first=all_ids.index(passages[0]);require(all_ids[first:first+len(passages)]==passages,'Alternative passages must be contiguous and ordered.')
    words=[deepcopy(w) for w in context['mapped_words'] if w['passage_id'] in passages]
    start,end=window['source_start_s'],window['source_end_s'];fps=Fraction(context['fps'])
    require(all(type(t) in (int,float) and math.isfinite(t) for t in (start,end)) and 0<=start<end<=context['narration']['duration_s'],'Invalid explicit alternative narration window.')
    require(all(start<=w['source_start_s']<w['source_end_s']<=end for w in words),'Alternative must preserve every selected word in full.')
    require(not any(w['passage_id'] not in passages and w['source_start_s']<end and w['source_end_s']>start for w in context['mapped_words']),'Alternative cannot cut or include a neighbouring passage word.')
    frames=window['baseline_duration_frames'];require(type(frames) is int and frames==math.ceil((Fraction(str(end))-Fraction(str(start)))*fps),'Explicit baseline film duration must contain exact narration window; only sub-frame terminal silence is permitted.')
    for w in words:w['timeline_start_s']=w['source_start_s']-start;w['timeline_end_s']=w['source_end_s']-start
    segments=[{'id':'alternative-narration','source_start_s':start,'source_end_s':end,'timeline_start_s':0,'timeline_end_s':end-start}]
    scoped={**deepcopy(context),'passage_ids':deepcopy(passages),'mapped_words':words,'audio_segments':segments,'expected_audio_segments_sha256':digest(segments),'narration_source_start_s':start,'narration_source_end_s':end,'duration_frames':frames,'section_start_s':start,'section_end_s':end,'review_baseline_window':deepcopy(window)}
    scoped.update(timing_fields(scoped))
    return scoped


def validate_candidate(plan, package, *, presentation_preview=False):
    from jsonschema import Draft202012Validator
    errors=list(Draft202012Validator(package['schema']).iter_errors(plan))
    require(not errors,'Plan schema: '+'; '.join(e.message for e in errors[:5]))
    context=package['context']; clarification.validate_questions(plan,context)
    original_digest=digest(plan);plan,_=clarification.separate_supplemental_notes(plan);validate_bundle(plan,context)
    ids=[sid for sid,_ in clarification.sequences(plan)]
    require(len(set(ids))==len(ids) and all(s.strip() for s in ids),'Sequence IDs must be unique and nonempty.')
    rows=[]
    for sid,seq in clarification.sequences(plan):
        scoped=context if sid=='recommendation' else scoped_context(context,seq['passage_ids'],seq['narration_window'])
        validate_decisions(seq,scoped)
        rows.append(validate_sequence(seq,scoped,plan['fps']))
    from .planning_execution import execution_document
    from .planning_presentation import preview
    presentation=preview(execution_document({'selected_plan':plan,'package':package,'certificate_digest':None}))
    if not presentation_preview:
        require(presentation['valid'],'Review presentation: '+'; '.join(presentation['errors']))
        # Authoring inputs are a read-only preview, not another saved plan copy.
        presentation.pop('explanation_sources')
    return {'status':'draft_technically_valid' if presentation['valid'] else 'draft_needs_presentation_changes','presentation':presentation,'plan_digest':original_digest,'context_digest':package['context_digest'],'sequences':rows,'execution_authorized':False,'editorial_verification':'not_performed','native_media_checks':'required_by_section3'}

def validate_sequence(seq,context,fps_value):
    fps=Fraction(str(fps_value)); cursor=0;ids=set();registry=context['evidence_registry'];sources=context['sources'];situation=context['workflow_situation']
    require(fps.denominator==1,'The reference native route requires integer output FPS.')
    def evidence(refs,sid,a,b,required=True):
        require(isinstance(refs,list) and (bool(refs) or not required),'Selected source needs exact usable evidence.')
        for ref in refs:
            key='/'.join(ref[k] for k in ('source_id','collection','item_id')); row=registry.get(key)
            require(row is not None and ref['source_id']==sid,'Excluded, raw or other-source evidence cannot support this excerpt.')
            span=row.get('interval')
            if span:require(min(span['end_s'],b)>max(span['start_s'],a),'Evidence lies outside the selected excerpt.')
    def bounds(shot):
        source=sources.get(shot['source_id']);require(source is not None,'Only eligible originals can be selected.')
        native=Fraction(source['metadata']['frame_rate']);a,b=shot['source_start_frame'],shot['source_end_frame'];lo,hi=shot['timeline_start_frame'],shot['timeline_end_frame']
        require(type(a) is int and type(b) is int and 0<=a<b<=source['native_frame_count'],'Invalid native source range.')
        require(Fraction(b-a)/native==Fraction(hi-lo)/fps,'Natural speed requires exact native/film duration equality.')
        evidence(shot['evidence_refs'],shot['source_id'],float(a/native),float(b/native))
        return source,native,a,b
    for shot in seq['shots']:
        require(shot['id'].strip() and shot['id'] not in ids,'Shot IDs must be unique and nonempty.');ids.add(shot['id'])
        lo,hi=shot['timeline_start_frame'],shot['timeline_end_frame']
        require(type(lo) is int and type(hi) is int and lo==cursor<hi<=seq['duration_frames'],'Shots must cover the exact film without hidden gaps/overlap.');cursor=hi
        require(bool(shot['reason'].strip()) and set(shot['passage_ids'])<=set(context['passage_ids']),'Explain each shot and bind actual passages.')
        if shot['kind']=='gap':
            require(all(shot[k] is None for k in ('source_id','source_start_frame','source_end_frame','crop_px')) and shot['evidence_refs']==[] and shot['visible_talking']=='not_applicable','Explicit gaps carry no source/evidence/crop.')
            continue
        source,native,a,b=bounds(shot);crop=shot['crop_px']
        stride=native/fps
        require(stride.denominator==1 and stride>=1 and a%stride==0 and b%stride==0,
            'The reference renderer requires exact integer frame decimation; choose supported source frames/output FPS, never retime silently.')
        if crop:
            w,h=source['metadata']['width'],source['metadata']['height'];ow,oh=context['resolution']
            require(crop['width']>0 and crop['height']>0 and crop['x']+crop['width']<=w and crop['y']+crop['height']<=h and crop['width']*oh==crop['height']*ow,'Crop must fit original pixels and output aspect; no automatic repair.')
        require(shot['visible_talking']!='present' or situation['visible_speaking'] in ('allow','selective'),'Visible-speaking policy conflict.')
    require(cursor==seq['duration_frames'],'Shots must reach the exact film endpoint.')
    timing_plan=deepcopy(seq);timing_plan['fps']=float(fps)
    segments,timing=apply_pauses(timing_plan,context,context['audio_segments'],ValueError)
    occupied=[(s['timeline_start_s'],s['timeline_end_s']) for s in segments];audio_ids=set()
    for audio in seq.get('source_audio_segments',[]):
        source,native,a,b=bounds(audio);lo,hi=audio['timeline_start_frame'],audio['timeline_end_frame'];content=audio['content'];permission=situation['source_audio_in_output']
        require(audio['id'] not in audio_ids and bool(audio['reason'].strip()),'Source audio requires a unique ID and reason.');audio_ids.add(audio['id'])
        require(content in ({'speech','ambient','both'} if permission=='both' else {permission}) and permission!='none','Source-audio permission conflict.')
        require(0<=lo<hi<=seq['duration_frames'] and not any(float(lo/fps)<y-1e-8 and float(hi/fps)>x+1e-8 for x,y in occupied),'Audio overlap requires a later explicit mixing contract.')
        if content in ('speech','both'):
            require(any(r['collection']=='speech' for r in audio['evidence_refs']),'Source speech needs retained speech evidence.')
            if situation['source_speech_under_b_roll']=='avoid':
                for shot in seq['shots']:
                    if shot['timeline_start_frame']<hi and shot['timeline_end_frame']>lo:
                        require(shot['kind']=='video' and shot['source_id']==audio['source_id'] and Fraction(shot['source_start_frame'])/native-Fraction(shot['timeline_start_frame'])/fps==Fraction(a)/native-Fraction(lo)/fps,'This user forbids source speech under different pictures.')
        occupied.append((float(lo/fps),float(hi/fps)))
    return {'duration_frames':cursor,'audio_segments':segments,'pause_timing':timing,'native_media_checks':'pending'}
