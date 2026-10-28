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
CATALOG = [
    {**DEFAULT, 'label': 'Gemini Omni · Direct Google', 'min_seconds': 3, 'max_seconds': 10,
     'duration_control': 'prompt_requested', 'end_image': True},
    {'provider': 'higgsfield', 'model': 'kling-video/v3.0/std/image-to-video',
     'label': 'Kling 3.0 Standard · Higgsfield', 'min_seconds': 3, 'max_seconds': 15,
     'duration_control': 'integer_seconds', 'end_image': True},
    {'provider': 'higgsfield', 'model': 'bytedance/seedance-2.5/image-to-video',
     'label': 'Seedance 2.5 · Higgsfield', 'min_seconds': 4, 'max_seconds': 30,
     'duration_control': 'integer_seconds', 'end_image': True},
]


class GeneratorChoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    shot_id: str = Field(min_length=1, max_length=80)
    provider: Literal['google', 'higgsfield']
    model: str

    @model_validator(mode='after')
    def supported(self):
        if not any(c['provider'] == self.provider and c['model'] == self.model for c in CATALOG):
            raise ValueError('Choose a supported provider/model pair from the video generator catalog.')
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
