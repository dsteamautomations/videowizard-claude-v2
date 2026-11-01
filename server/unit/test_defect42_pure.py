"""Defect 42 (VW-12, 31 Oct 2026): 16 finished takes stayed 'storage pending': the provider's answer named no mime_type for the video,
and the output reader required 'video/mp4'. A video with no mime_type is read when its bytes are an MP4 file; anything else is still refused."""
import base64

import pytest

from app import video_providers as VP

MP4 = b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 64


def answer(content):
    return {'steps': [{'type': 'model_output', 'content': [content]}]}


def provider():
    return VP.Provider.__new__(VP.Provider)


def test_a_video_without_mime_type_is_read_when_it_is_an_mp4():
    assert provider().output(answer({'type': 'video', 'data': base64.b64encode(MP4).decode()})) == MP4
    assert provider().output(answer({'type': 'video', 'mime_type': 'video/mp4', 'data': base64.b64encode(MP4).decode()})) == MP4


def test_anything_else_is_still_refused():
    with pytest.raises(ValueError, match='not an MP4'):
        provider().output(answer({'type': 'video', 'data': base64.b64encode(b'GIF89a' + b'\x00' * 64).decode()}))
    with pytest.raises(ValueError, match='one MP4'):
        provider().output(answer({'type': 'video', 'mime_type': 'video/webm', 'data': base64.b64encode(MP4).decode()}))
