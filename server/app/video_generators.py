"""Video preparation choices, independent of analysis and paid dispatch."""
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal
import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .config import settings
from .errors import Problem

OMNI = 'gemini-omni-1.1-flash'
DEFAULT = {'provider': 'google', 'model': OMNI}
CATALOG = [   # design/124 A4 decision 5: Gemini Omni only; every take 3-10 s, a longer passage is split
    {**DEFAULT, 'label': 'Gemini Omni · Direct Google', 'min_seconds': 3, 'max_seconds': 10,
     'duration_control': 'prompt_requested', 'end_image': True},
]
OMNI_ONLY = 'Gemini Omni only: every take is Gemini Omni, 3–10 s; split the shot. No other video generator is offered.'
KLING_SEEDANCE_RETIRED = 'Kling and Seedance are retired; every video take is Gemini Omni'   # design/35 Old ways 7


def known(provider, model):
    """The catalogue entry of a choice, or None (Kling and Seedance are retired, design/35 Old ways 7)."""
    return next((c for c in CATALOG if c['provider'] == provider and c['model'] == model), None)


class GeneratorChoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    shot_id: str = Field(min_length=1, max_length=80)
    provider: Literal['google', 'higgsfield']
    model: str

    @model_validator(mode='after')
    def supported(self):
        if not any(c['provider'] == self.provider and c['model'] == self.model for c in CATALOG):
            if self.provider == 'higgsfield':
                raise Problem(410, 'RETIRED', KLING_SEEDANCE_RETIRED)   # one line, not wrapped as a validation error
            raise ValueError(OMNI_ONLY)
        return self


def catalog():
    return {'default': deepcopy(DEFAULT), 'options': deepcopy(CATALOG),
            'selection_stage': 'shot_preparation', 'dispatch_enabled': True,
            'generation_authorized': False, 'model_access': 'not_verified'}


def selection(part, shot_id):
    saved = part.get('generator_choices', {}).get(shot_id)
    if not saved:
        return {**DEFAULT, 'selection': 'default', 'needs_reconfirmation': False}
    return {**deepcopy(saved), 'selection': 'explicit',
            'needs_reconfirmation': saved['plan_id'] != part.get('current')}


def connection_check(client=None):
    """Read one model record; never use generateContent or create an interaction."""
    from . import keys as _keys
    pool = _keys.pool('gemini', settings())   # design/114
    key = pool[0] if pool else ''
    if not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise Problem(503, 'OMNI_CONFIGURATION', 'Configure the existing backend GEMINI_API_KEY, then check again.')
    request = client.get if client else httpx.get
    try:
        response = request('https://generativelanguage.googleapis.com/v1beta/models/' + OMNI,
                           headers={'x-goog-api-key': key}, timeout=20, follow_redirects=False)
    except httpx.RequestError:
        raise Problem(503, 'OMNI_CONNECTION', 'Google could not be reached. No generation was requested; try the check later.') from None
    if not response.is_success:
        raise Problem(502, 'OMNI_CHECK', 'Google did not return the Omni model record. Check the backend Gemini key and model availability. No generation was requested.')
    try:
        body = response.json()
        if body['name'] != 'models/' + OMNI:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise Problem(502, 'OMNI_RESPONSE', 'Google returned an unexpected model record. No generation was requested.') from None
    return {'model': OMNI, 'model_catalog_access': 'verified',
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'generation_access': 'not_verified', 'generation_authorized': False}
