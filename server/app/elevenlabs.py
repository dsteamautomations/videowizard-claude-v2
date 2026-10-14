"""Fixed-origin ElevenLabs adapter (ported from v1); never exposes the key or raw provider errors."""
import re
import time

import httpx

from .config import settings
from .errors import Problem

MODELS = ('eleven_v4', 'eleven_multilingual_v2', 'eleven_v3')
DEFAULT_MODEL = 'eleven_v4'
DEFAULT_SETTINGS = {'eleven_v4': {'stability': 0.5, 'similarity_boost': 0.75}, 'eleven_v3': {'stability': 0.5},
                    'eleven_multilingual_v2': {'stability': 0.5, 'similarity_boost': 0.75, 'style': 0, 'speed': 1, 'use_speaker_boost': True}}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise Problem(422, 'PROVIDER_ID', 'Choose a valid provider identity from the catalog.')
    return value


def validate_settings(model, values):
    if model not in MODELS or not isinstance(values, dict):
        raise Problem(422, 'VOICE_SETTINGS', 'Choose a supported speech model and its settings.')
    allowed = {'stability', 'similarity_boost'} if model == 'eleven_v4' else {'stability'} if model == 'eleven_v3' else {'stability', 'similarity_boost', 'style', 'speed', 'use_speaker_boost'}
    if set(values) != allowed:
        raise Problem(422, 'VOICE_SETTINGS', f'Supply exactly these settings for {model}: {sorted(allowed)}.')
    for k, v in values.items():
        ok = isinstance(v, bool) if k == 'use_speaker_boost' else (type(v) in (int, float) and (0.7 <= v <= 1.2 if k == 'speed' else 0 <= v <= 1))
        if not ok:
            raise Problem(422, 'VOICE_SETTINGS', f'Setting {k} is outside the supported range.')
    if model == 'eleven_v3' and values['stability'] not in (0, 0.5, 1):
        raise Problem(422, 'VOICE_SETTINGS', 'Eleven v3 stability must be 0, 0.5 or 1.')


class ElevenLabs:
    def request(self, method, path, **kwargs):
        key = settings().ELEVENLABS_API_KEY.get_secret_value()
        if not key:
            raise Problem(503, 'VOICE_CONFIGURATION', 'The administrator must configure the ElevenLabs key.')
        synthesis = method == 'POST' and path.startswith('/v1/text-to-speech/')
        timeout = httpx.Timeout(connect=15, read=480 if synthesis else 120, write=60, pool=15)
        started = time.monotonic()
        request_id = None
        try:
            with httpx.stream(method, 'https://api.elevenlabs.io' + path, headers={'xi-api-key': key}, timeout=timeout, **kwargs) as response:
                request_id = response.headers.get('request-id')
                response.read()
        except httpx.RequestError as exc:
            error = Problem(502, 'PROVIDER_UNKNOWN' if method == 'POST' else 'PROVIDER_CONNECTION',
                            f'Provider connection interrupted ({type(exc).__name__}, {round(time.monotonic() - started)}s). Check the saved attempt before another generation.')
            error.provider_request_id = request_id
            raise error from None
        if not response.is_success:
            if path.startswith('/v1/history') and response.status_code in (401, 403):
                raise Problem(403, 'HISTORY_PERMISSION', 'ElevenLabs history access is unavailable. Enable History read for the configured key.')
            code = 'PROVIDER_UNKNOWN' if method == 'POST' and (response.status_code >= 500 or response.status_code == 408) else 'PROVIDER_REJECTED'
            detail = ''
            try:   # ElevenLabs says why (e.g. quota_exceeded with the characters needed vs left); pass that on so the operator hears the real reason
                d = response.json().get('detail')
                detail = (f" ElevenLabs says: {d.get('status')}: {d.get('message')}" if isinstance(d, dict) else f' ElevenLabs says: {d}') if d else ''
            except ValueError:
                pass
            error = Problem(502, code, f'ElevenLabs did not complete the request (HTTP {response.status_code}).{detail[:400]} Check account access, quota and model/voice compatibility; no automatic retry.')
            error.provider_request_id = response.headers.get('request-id')
            raise error
        return response

    def models(self):
        return [{'id': m['model_id'], 'name': m.get('name', m['model_id']),
                 'max_characters': min(m.get('maximum_text_length_per_request') or 10000, 10000) if m['model_id'] == 'eleven_v4' else m.get('maximum_text_length_per_request'),
                 'languages': m.get('languages', []), 'supported': m['model_id'] in MODELS}
                for m in self.request('GET', '/v1/models').json() if m.get('can_do_text_to_speech')]

    @staticmethod
    def public_voice(v):
        result = {k: v.get(k) for k in ('voice_id', 'name', 'labels', 'description', 'preview_url', 'category', 'high_quality_base_model_ids', 'verified_languages', 'recording_quality')}
        sharing = v.get('sharing') or {}
        if sharing.get('public_owner_id'):
            result['library_identity'] = {'public_owner_id': sharing['public_owner_id'], 'original_voice_id': sharing.get('original_voice_id') or v['voice_id']}
        return result

    def voice(self, voice_id):
        return self.public_voice(self.request('GET', '/v1/voices/' + identifier(voice_id)).json())

    def synthesize(self, snapshot):
        suffix = '/with-timestamps' if snapshot.get('timing_mode') == 'generation' else ''
        return self.request('POST', '/v1/text-to-speech/' + identifier(snapshot['voice_id']) + suffix, params={'output_format': 'mp3_44100_128'},
                            json={'text': snapshot['text'], 'model_id': snapshot['model_id'], 'voice_settings': snapshot['settings']})


# ---------- catalog discovery (ported from v1 voice_catalog.py) ----------

USE_CASES = ('conversational', 'narrative_story', 'characters_animation', 'social_media', 'informative_educational', 'advertisement', 'entertainment_tv')


def discover(provider, q):
    """q: dict with scope, search, cursor, language, accent, gender, age, use_cases, high_quality."""
    scope = q.get('scope') or 'account'
    params = {k: v for k, v in q.items() if k in ('search', 'language', 'accent', 'gender', 'age', 'use_cases') and v not in ('', [], None)}
    params['page_size'] = 30
    cursor = q.get('cursor') or ''
    if scope == 'library':
        if cursor and (not cursor.isdecimal() or len(cursor) > 6):
            raise Problem(422, 'CATALOG_CURSOR', 'Restart the library search; its page cursor is invalid.')
        page = int(cursor or '0')
        params['page'] = page
        if q.get('high_quality'):
            params['category'] = 'high_quality'
        data = provider.request('GET', '/v1/shared-voices', params=params).json()
        next_cursor = str(page + 1) if data.get('has_more') else None
    else:
        if cursor:
            params['next_page_token'] = cursor
        if q.get('high_quality'):
            params['high_quality'] = True
        data = provider.request('GET', '/v2/voices', params=params).json()
        next_cursor = data.get('next_page_token') if data.get('has_more') else None
    voices = []
    for raw in data.get('voices', []):
        v = provider.public_voice(raw)
        v['labels'] = {**(v.get('labels') or {}), **{k: raw[k] for k in ('language', 'accent', 'gender', 'age', 'use_case', 'descriptive') if raw.get(k)}}
        sharing = raw.get('sharing') or {}
        for k in ('public_owner_id', 'notice_period', 'rate', 'live_moderation_enabled'):
            v[k] = raw.get(k, sharing.get(k))
        v['scope'] = scope
        voices.append(v)
    return {'voices': voices, 'has_more': bool(data.get('has_more')), 'next_page_token': next_cursor, 'total_count': data.get('total_count'), 'scope': scope}


def add_library_voice(provider, owner_id, voice_id):
    """Add a shared library voice to the account, reconciling by stable owner/original id first (never adds twice)."""
    owner_id, voice_id = identifier(owner_id), identifier(voice_id)
    cursor, seen = '', set()
    while True:
        params = {'page_size': 100, **({'next_page_token': cursor} if cursor else {})}
        data = provider.request('GET', '/v2/voices', params=params).json()
        for v in data.get('voices', []):
            share = v.get('sharing') or {}
            if share.get('public_owner_id') == owner_id and share.get('original_voice_id', v['voice_id']) == voice_id:
                return provider.public_voice(v)
        if not data.get('has_more'):
            break
        cursor = data.get('next_page_token')
        if not cursor or cursor in seen:
            raise Problem(502, 'CATALOG_INCOMPLETE', 'Account search is incomplete. Retry discovery before adding a voice.')
        seen.add(cursor)
    found = None
    for page in range(100):
        data = provider.request('GET', '/v1/shared-voices', params={'owner_id': owner_id, 'page': page, 'page_size': 100}).json()
        found = next((v for v in data.get('voices', []) if v.get('voice_id') == voice_id and v.get('public_owner_id') == owner_id), None)
        if found or not data.get('has_more'):
            break
    if not found:
        raise Problem(422, 'LIBRARY_VOICE_UNAVAILABLE', 'This exact library voice could not be verified. Refresh the library; do not substitute by name.')
    data = provider.request('POST', f'/v1/voices/add/{owner_id}/{voice_id}', json={'new_name': found['name']}).json()
    return provider.voice(identifier(data.get('voice_id')))
