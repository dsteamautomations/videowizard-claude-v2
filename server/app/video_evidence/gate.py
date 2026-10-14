"""Source envelope gate, independent row salvage and JSON-safe evidence export."""
from copy import deepcopy
from .contract import _interval, _text
from .expanded import validate_expanded
from .view import usable_view


def identity_errors(body, expected):
    if not isinstance(body, dict):
        return ['A response object is required.']
    errors = [key + ': mismatched identity.' for key in ('contract_version', 'request_id', 'script_id')
              if not _text(expected.get(key)) or body.get(key) != expected[key]]
    sources = body.get('sources')
    if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
        return errors + ['Exactly one requested source is required.']
    source, meta = sources[0], expected['sources'][0]
    for key in ('source_id', 'window_id', 'media_kind'):
        if source.get(key) != meta[key]: errors.append('source.' + key + ': mismatched identity.')
    span = source.get('requested_interval')
    if not _interval(span) or any(abs(span[k] - meta['requested_interval'][k]) > .001 for k in ('start_s', 'end_s')):
        errors.append('Source interval differs from attached original.')
    if source.get('clock') != 'original_source_seconds': errors.append('Incompatible source clock.')
    return errors


def derive(body, expected, schema):
    errors = identity_errors(body, expected)
    if errors: return {'identity_errors': errors, 'gaps': [], 'evidence': None}
    core = deepcopy(body); core.pop('descriptive_name', None)
    rule = deepcopy(schema); rule['properties'].pop('descriptive_name', None)
    rule['required'] = [k for k in rule['required'] if k != 'descriptive_name']
    try:
        validation = validate_expanded(core, expected, rule)
        gaps = validation['identity_errors'] + validation['gaps'] + validation.get('extension_gaps', [])
    except (KeyError, TypeError, ValueError, IndexError, OverflowError, RecursionError):
        gaps = ['Malformed evidence remains unknown; independent rows are checked separately.']
    view = usable_view(expected['sources'][0], {'result': core}, expected, rule)
    source = expected['sources'][0]
    view['usable'] = [{'ref': {'source_id': source['source_id'], 'window_id': source['window_id'],
                              'collection': kind, 'item_id': identifier}, 'item': row}
                      for (kind, identifier), row in view['usable'].items()]
    return {'identity_errors': [], 'gaps': gaps, 'evidence': view}
