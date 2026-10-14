"""Bind imported word timing to the exact accepted VideoWizard narration.

This validates supplied evidence; it never invents timing, transcribes audio,
regenerates speech, or marks an unchecked boundary as checked.
"""
from copy import deepcopy
import re

from .narration_timing import TimingError, derive_timing


def tokens(text):
    return re.findall(r"\w+(?:['’]\w+)*", text.casefold().replace('’', "'"))


def bind_timing(run, job, file, timing, fps):
    handoff = narration_handoff(run, job, file)
    paragraphs = handoff['spoken_text'].split('\n\n')
    passages = [{'passage_id': f'P{i+1:03d}', 'text': text}
                for i, text in enumerate(paragraphs) if text.strip()]
    result = derive_timing(timing, [p['passage_id'] for p in passages], fps)
    if timing['recording']['sha256'] != handoff['sha256']:
        raise TimingError('Word timing belongs to a different narration recording.')
    # Enforce words and order per passage; syntax validity alone cannot do this.
    for passage in passages:
        words = [word.get('text', '') for word in timing.get('words', [])
                 if word.get('passage_id') == passage['passage_id']]
        if tokens(' '.join(words)) != tokens(passage['text']):
            raise TimingError('Timed words differ from the accepted script in ' + passage['passage_id'])
    return {'contract': 'videowizard-bound-narration-timing-v1',
            'run_id': handoff['run_id'], 'file_id': handoff['file_id'],
            'voice_job_id': handoff['voice_job_id'], 'source_script': handoff['source_script'],
            'recording_sha256': handoff['sha256'], 'passages': passages,
            'timing': result, 'input_timing': deepcopy(timing),
            'verification_scope': 'recording identity, supplied timing structure and script word order; not listening verification'}
