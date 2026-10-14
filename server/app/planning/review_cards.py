"""Portable reference review-text checks; local cache paths are not editorial evidence."""
import re
import hashlib
import json

def digest(value):
    # Match the reference formatter, not the application's compact JSON hashes.
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
INTERNAL_ID = re.compile('\\b(?:Q\\d+|P\\d{3}|source-\\d+|(?:visual|speech|event)-\\d+)\\b')

def assert_viewer_text(text):
    if INTERNAL_ID.search(text):
        raise ValueError('Viewer explanation contains an internal reference. The planner must supply evidence-bound review_explanations; the formatter cannot rewrite it.')


def section_text(title, option_numbers):
    if not option_numbers or len(set(option_numbers)) != len(option_numbers):
        raise ValueError('Section needs distinct actual options.')
    assert_viewer_text(title)
    return (f"The next section is: {title.rstrip('.')} .".replace(' .', '.') +
        f"\nNumber of options available: {len(option_numbers)}.\nOption " +
        ('number' if len(option_numbers)==1 else 'numbers') + ': ' +
        ', '.join(str(n) for n in option_numbers) + '.')


def explanation_schema():
    text = {'type':'string','minLength':1}
    fields = {'sequence_id':text, 'passage_ids':{'type':'array','items':text,'minItems':1},
              'source_digest':text, 'why':text, 'shows':text, 'limitations':text,
              'qualifications_preserved':{'const':True}}
    return {'type':'array','items':{'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}}


def explanation_source(sequence_id, passages, explanation, notes, limits, shots):
    return {'sequence_id':sequence_id,'passage_ids':passages,'explanation':explanation,
            'notes':notes,'limitations':limits,'shots':[{k:v for k,v in shot.items() if k!='path'} for shot in shots]}


def explanation_blocks(source, authored=None):
    if authored is not None:
        if authored.get('source_digest') != digest(source) or authored.get('qualifications_preserved') is not True:
            raise ValueError('Viewer explanation binding changed or qualifications were not reviewed by the planner.')
        values = [authored.get(k) for k in ('why','shows','limitations')]
        if any(not isinstance(v,str) or not v.strip() for v in values):
            raise ValueError('Planner must supply all three viewer explanation blocks.')
    else:
        # Verbatim fallback only: no removal of qualifications or expansion of IDs.
        shows = list(dict.fromkeys(n['meaning_and_support'] for n in source['notes'] if n.get('meaning_and_support')))
        if not shows:
            shows = list(dict.fromkeys(s.get('reason','') for s in source['shots'] if s.get('reason')))
        values = [source['explanation'], '\n'.join(shows), '\n'.join(source['limitations'])]
    blocks = [{'label':label,'text':value} for label,value in zip(
        ('Why this option:', 'What it shows:', 'What to keep in mind:'),values) if value]
    for block in blocks: assert_viewer_text(block['text'])
    return blocks
