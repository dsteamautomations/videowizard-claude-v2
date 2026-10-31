"""Defect 35: `vw visuals image --role start|end` sent a field the request model refused (extra fields are forbidden)."""
import uuid

import pytest
from pydantic import ValidationError

from app.main import ImageGenerate


def body(**kw):
    return {'request_id': str(uuid.uuid4()), 'element_id': 'E1', 'name': 'n', 'kind': 'keyframe', 'subject': 's', 'prompt': 'p', **kw}


def test_role_start_or_end_is_accepted_and_anything_else_refused():
    assert ImageGenerate(**body(role='start')).role == 'start' and ImageGenerate(**body(role='end')).role == 'end'
    assert ImageGenerate(**body()).role is None
    with pytest.raises(ValidationError):
        ImageGenerate(**body(role='middle'))
